"""Read-only Cricsheet evidence and cohort-specific scouting services."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .cricket_stats import cricket_rates
from .db import BASE
from .ingestion import bounded_score, safe_ratio
from .intelligence import clean_weights, score_candidates

router = APIRouter(prefix="/api/cricket", tags=["Cricsheet scouting"])
SOURCE = "https://cricsheet.org/downloads/"
FEATURED_PLAYERS = {
    "ba607b88": ("Virat Kohli", "/assets/photos/kohli.webp"),
    "462411b3": ("Jasprit Bumrah", "/assets/photos/bumrah.webp"),
    "be150fc8": ("Ellyse Perry", "/assets/photos/perry.webp"),
}
FIT_WEIGHTS = {
    "Opener": {"strike": 55, "batting": 45},
    "Middle Order": {"batting": 65, "strike": 35},
    "Finisher": {"finishing": 65, "strike": 25, "batting": 10},
    "All-Rounder": {"batting": 25, "strike": 25, "bowling": 25, "economy": 25},
    "Bowler": {"bowling": 45, "economy": 55},
}
COUNT_FIELDS = (
    "runs", "legal_balls_faced", "fours", "sixes", "dismissals", "batting_innings",
    "legal_balls_bowled", "runs_conceded", "wickets", "catches", "stumpings",
    "opening_innings", "middle_innings", "death_runs", "death_balls",
)


def evidence_path():
    return Path(os.environ.get("VIXISU_CRICKET_EVIDENCE", BASE / "data" / "cricket_evidence.db"))


@contextmanager
def evidence_db():
    path = evidence_path()
    if not path.is_file():
        raise HTTPException(503, "Cricket evidence is unavailable. See docs/GLOBAL_CRICKET.md for setup.")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


class Cohort(BaseModel):
    competition: str = Field("", max_length=180)
    season: str = Field("", max_length=30)
    format: str = Field("", max_length=20)
    gender: str = Field("", max_length=20)
    team_type: str = Field("", max_length=25)


class FitRequest(BaseModel):
    cohort: Cohort
    role: str
    weights: dict[str, float] | None = None
    roster_ids: list[str] = Field(default_factory=list, max_length=30)


def condition(cohort, player_id=None, search=""):
    clauses = []
    values = []
    for key, value in cohort.model_dump().items():
        if value:
            clauses.append(f"{key} = ?")
            values.append(value)
    if player_id:
        clauses.append("player_id = ?")
        values.append(player_id)
    if search:
        clauses.append("(instr(lower(display_name), lower(?)) OR instr(lower(team), lower(?)))")
        values.extend([search, search])
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), values


def identity(row):
    player = dict(row)
    featured = FEATURED_PLAYERS.get(player["player_id"])
    if featured:
        player["name"], player["photo"] = featured
    return player


def totals_query(where):
    counts = ", ".join(f"SUM({field}) AS {field}" for field in COUNT_FIELDS)
    return f"""
        SELECT player_id, MAX(display_name) AS name, GROUP_CONCAT(DISTINCT team) AS teams,
               SUM(rostered) AS matches, MIN(date) AS first_match, MAX(date) AS latest_match,
               {counts}
        FROM cohort_player_match_stats {where}
        GROUP BY player_id HAVING SUM(rostered) > 0
    """


def rates(row):
    return cricket_rates({
        **dict(row), "balls_faced": row["legal_balls_faced"],
        "balls_bowled": row["legal_balls_bowled"],
    })


@router.get("/coverage")
def coverage():
    with evidence_db() as db:
        summary = dict(db.execute(
            "SELECT COUNT(*) AS matches, MIN(date) AS first_match, MAX(date) AS latest_match FROM matches"
        ).fetchone())
        summary["players"] = db.execute(
            "SELECT COUNT(DISTINCT player_id) FROM player_match_stats WHERE rostered = 1"
        ).fetchone()[0]
        cohorts = [dict(row) for row in db.execute("""
            SELECT competition, season, format, gender, team_type, COUNT(*) AS matches
            FROM matches GROUP BY competition, season, format, gender, team_type
            ORDER BY matches DESC, competition, season DESC
        """)]
    return {**summary, "cohorts": cohorts, "source": SOURCE, "role_weights": FIT_WEIGHTS}


@router.get("/players")
def players(
    cohort: Cohort = Depends(),
    q: str = Query("", max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    criterion: str = Query("matches", pattern=r"^(matches|runs|wickets|name)$"),
):
    where, values = condition(cohort)
    matched, search_values = condition(cohort, search=q.strip())
    if query := q.strip():
        # Find identities by any matching name or team while keeping totals for the entire selected cohort.
        matches = f"player_id IN (SELECT player_id FROM cohort_player_match_stats{matched})"
        featured = [pid for pid, (name, _) in FEATURED_PLAYERS.items() if query.casefold() in name.casefold()]
        if featured:
            matches += " OR player_id IN (" + ",".join("?" for _ in featured) + ")"
        where += (" AND " if where else " WHERE ") + f"({matches})"
        values += search_values + featured
    select = totals_query(where)
    order = "name COLLATE NOCASE" if criterion == "name" else f"{criterion} DESC, name COLLATE NOCASE"
    with evidence_db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM ({select})", values).fetchone()[0]
        rows = db.execute(f"{select} ORDER BY {order}, player_id LIMIT ? OFFSET ?",
                          [*values, limit, offset]).fetchall()
    return {"players": [identity(row) for row in rows], "total": total, "cohort": cohort, "source": SOURCE}


@router.get("/players/{player_id}")
def profile(player_id: str, cohort: Cohort = Depends()):
    where, values = condition(cohort, player_id)
    with evidence_db() as db:
        row = db.execute(totals_query(where), values).fetchone()
        if row is None:
            raise HTTPException(404, "No rostered appearance for this player in the selected coverage.")
        columns = {field["name"] for field in db.execute("PRAGMA table_info(player_match_stats)")}
        additional = {"highest_score": None, "dot_balls": None}
        if {"highest_score", "dot_balls"} <= columns:
            additional = dict(db.execute(f"""
                SELECT MAX(highest_score) AS highest_score, SUM(dot_balls) AS dot_balls
                FROM cohort_player_match_stats {where}
            """, values).fetchone())
        history = db.execute(f"""
            SELECT match_id, date, season, competition, team, format, runs, legal_balls_faced,
                   wickets, legal_balls_bowled, runs_conceded
            FROM cohort_player_match_stats {where} ORDER BY date DESC, match_id DESC LIMIT 20
        """, values).fetchall()
    summary = {**identity(row), **additional}
    summary["description"] = (
        f'{summary["name"]} recorded {row["matches"]} rostered appearances in this selection, '
        f'with {row["runs"]} runs and {row["wickets"]} bowler-credited wickets. '
        f'Recorded teams include {row["teams"] or "an unnamed team"}.'
    )
    return {
        **summary, "rates": rates(summary) if cohort.format else None, "cohort": cohort,
        "recent_matches": [dict(match) for match in history], "source": SOURCE,
    }


def eligible(row, role):
    batting = row["legal_balls_faced"] >= 60
    bowling = row["legal_balls_bowled"] >= 60
    return row["matches"] >= 3 and {
        "Opener": batting and row["opening_innings"] >= 3,
        "Middle Order": batting and row["middle_innings"] >= 3,
        "Finisher": batting and row["death_balls"] >= 24,
        "All-Rounder": batting and bowling,
        "Bowler": bowling,
    }[role]


def measurements(row):
    return {
        "batting": safe_ratio(row["runs"], row["dismissals"]) if row["dismissals"] >= 3 else None,
        "strike": safe_ratio(row["runs"], row["legal_balls_faced"], 100) if row["legal_balls_faced"] >= 60 else None,
        "finishing": safe_ratio(row["death_runs"], row["death_balls"], 100) if row["death_balls"] >= 24 else None,
        "bowling": safe_ratio(row["wickets"], row["legal_balls_bowled"], 120)
        if row["legal_balls_bowled"] >= 60 else None,
        "economy": safe_ratio(row["runs_conceded"], row["legal_balls_bowled"], 6)
        if row["legal_balls_bowled"] >= 60 else None,
    }


@router.post("/decision-lab")
def decision_lab(data: FitRequest):
    role = data.role
    cohort = data.cohort
    if role not in FIT_WEIGHTS:
        raise HTTPException(422, "Choose a supported archive role.")
    if cohort.format != "T20" or not all([cohort.competition, cohort.season, cohort.gender, cohort.team_type]):
        raise HTTPException(422, "Choose a named T20 competition, season, gender category and team type.")
    template = FIT_WEIGHTS[role]
    if data.weights is not None and set(data.weights) - set(template):
        raise HTTPException(422, "Weights must use supported metrics for this archive role.")
    try:
        weights = clean_weights("cricket", role, template if data.weights is None else data.weights)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    where, values = condition(cohort)
    with evidence_db() as db:
        rows = db.execute(totals_query(where), values).fetchall()
    roster = set(data.roster_ids)
    if roster - {row["player_id"] for row in rows}:
        raise HTTPException(422, "Roster players must have an appearance in the selected cohort.")
    qualified = {row["player_id"] for row in rows if eligible(row, role)}
    evidence = {row["player_id"]: measurements(row) for row in rows if row["player_id"] in qualified | roster}
    bounds = {}
    for key in template:
        sample = [evidence[pid][key] for pid in qualified if evidence[pid][key] is not None]
        if len(sample) >= 2 and min(sample) < max(sample):
            bounds[key] = (min(sample), max(sample))

    candidates = []
    for row in rows:
        pid = row["player_id"]
        if pid not in evidence:
            continue
        features = {}
        for key, (low, high) in bounds.items():
            score = bounded_score(evidence[pid][key], low, high, reverse=key == "economy")
            if score is not None:
                features[key] = score
        candidates.append({
            "id": pid, "name": identity(row)["name"], "sport": "cricket", "role": role,
            "features": features, "matches": row["matches"],
        })

    def rank(priorities):
        return score_candidates(candidates, "cricket", role, priorities, roster)

    baseline = rank(weights)
    scenarios = []
    for key, weight in weights.items():
        ranked = rank({**weights, key: min(1000, weight * 1.5)})
        scenarios.append({
            "metric": key,
            "leader": ranked[0]["player"]["name"] if ranked else None,
            "same_leader": bool(baseline and ranked and
                                baseline[0]["player"]["id"] == ranked[0]["player"]["id"]),
        })
    for item in baseline[:10]:
        player = item["player"]
        item["reasons"] = item["reasons"][1:]  # Existing scorer assumes verified role assignments.
        player["measurements"] = evidence[player["id"]]
    return {
        "cohort": cohort, "weights": weights, "bounds": bounds, "source": SOURCE,
        "eligible": len(qualified - roster), "ranked": len(baseline), "results": baseline[:10],
        "margin": round(baseline[0]["score"] - baseline[1]["score"], 1) if len(baseline) > 1 else None,
        "scenarios": scenarios,
    }
