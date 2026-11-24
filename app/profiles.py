"""Editable workspace profiles, with provenance kept separate from archive identities."""
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl, StrictBool, field_validator

from .access import require_owner
from .cricket_stats import CricketCounts, cricket_rates
from .data import FEATURES, ROLE_TEMPLATES
from .db import connect, row_player

router = APIRouter(prefix="/api/players", tags=["Workspace profiles"])
owner = Depends(require_owner)


class PlayerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    sport: str
    role: str
    country: str = Field(default="", max_length=5)
    age: int | None = Field(default=None, ge=13, le=100)
    features: dict[str, float] = Field(default_factory=dict)
    team: str = Field(default="", max_length=100)
    style: str = Field(default="", max_length=100)
    source_note: str = Field(default="", max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class PlayerPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    role: str | None = None
    country: str | None = Field(None, max_length=5)
    age: int | None = Field(None, ge=13, le=100)
    features: dict[str, float] | None = None
    team: str | None = Field(None, max_length=100)
    style: str | None = Field(None, max_length=100)
    source_note: str | None = Field(None, max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class Statistics(BaseModel):
    format: Literal["Test", "ODI", "T20", "IT20", "T10", "MDM", "ODM", "Other"]
    competition: str = Field("", max_length=120)
    season: str = Field("", max_length=30)
    counts: CricketCounts
    source: str = Field(max_length=300)

    @field_validator("source", "competition", "season")
    @classmethod
    def trim_context(cls, value):
        return value.strip()


class Media(BaseModel):
    kind: Literal["photo", "video"]
    title: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    attribution: str = Field(min_length=1, max_length=300)
    authorized: StrictBool

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        if value.scheme != "https" or value.username or value.password:
            raise ValueError("Use an HTTPS media link without credentials.")
        return value


class Attempt(BaseModel):
    drill: Literal["batting", "bowling", "fielding"]
    seconds: float = Field(ge=0, le=86400, allow_inf_nan=False)
    success: StrictBool


class Review(BaseModel):
    video_id: str = Field(pattern=r"^[a-f0-9]{12}$")
    attempts: list[Attempt] = Field(min_length=5, max_length=300)


def require_active(db, player_id):
    row = db.execute("SELECT * FROM players WHERE id=? AND archived_at IS NULL", (player_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Player not found")
    return row


def valid_player(sport, role, features):
    if sport not in FEATURES or role not in ROLE_TEMPLATES[sport]:
        raise HTTPException(422, "Choose a role supported by the selected sport.")
    allowed = {key for key, _ in FEATURES[sport]}
    if any(key not in allowed or not (0 <= score <= 100) for key, score in features.items()):
        raise HTTPException(422, "Normalized skill scores must be 0–100 and use supported features.")


def identity_key(name, sport, country):
    return (" ".join(name.split()).casefold(), sport, country.strip().casefold())


def guard_duplicates(db, incoming, except_id=None):
    existing = {
        identity_key(row["name"], row["sport"], row["country"])
        for row in db.execute("SELECT id, name, sport, country FROM players WHERE archived_at IS NULL")
        if row["id"] != except_id
    }
    for name, sport, country in incoming:
        key = identity_key(name, sport, country)
        if key in existing:
            raise HTTPException(409, f'An active profile already exists for "{name}" in this sport and country.')
        existing.add(key)


def store_details(db, item, player_id):
    db.execute("""
        INSERT INTO player_details(player_id,team,style,source_note) VALUES (?,?,?,?)
        ON CONFLICT(player_id) DO UPDATE SET team=excluded.team, style=excluded.style, source_note=excluded.source_note
    """, (player_id, item["team"].strip(), item["style"].strip(), item["source_note"].strip()))


def detail_record(db, player_id):
    row = db.execute("SELECT team,style,source_note FROM player_details WHERE player_id=?", (player_id,)).fetchone()
    return dict(row) if row else {"team": "", "style": "", "source_note": ""}


def initials(name):
    return "".join(word[0] for word in name.split()[:2]).upper()


@router.get("/{player_id}")
def get_player(player_id: str):
    with connect() as db:
        return {**row_player(require_active(db, player_id)), **detail_record(db, player_id)}


@router.post("", status_code=201, dependencies=[owner])
def add_player(data: PlayerCreate):
    valid_player(data.sport, data.role, data.features)
    player_id = "P-" + uuid.uuid4().hex[:9].upper()
    country = data.country.strip().upper()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        guard_duplicates(db, [(data.name, data.sport, country)])
        db.execute("""
            INSERT INTO players(id,name,sport,role,country,age,initials,features,source)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (player_id, data.name, data.sport, data.role, country, data.age, initials(data.name),
              json.dumps(data.features), "User entered normalized scores"))
        store_details(db, data.model_dump(), player_id)
    return get_player(player_id)


@router.patch("/{player_id}", dependencies=[owner])
def update_player(player_id: str, data: PlayerPatch):
    changes = data.model_dump(exclude_unset=True)
    if any(value is None and key != "age" for key, value in changes.items()):
        raise HTTPException(422, "Only age can be cleared with null.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        previous = row_player(require_active(db, player_id))
        item = {**previous, **detail_record(db, player_id), **changes}
        item["country"] = item["country"].strip().upper()
        valid_player(item["sport"], item["role"], item["features"])
        if identity_key(item["name"], item["sport"], item["country"]) != identity_key(
            previous["name"], previous["sport"], previous["country"]
        ):
            guard_duplicates(db, [(item["name"], item["sport"], item["country"])], except_id=player_id)
        source = item["source"]
        if item["features"] != previous["features"] and not previous["demo"]:
            source = "User edited normalized scores"
        db.execute("""
            UPDATE players SET name=?,role=?,country=?,age=?,initials=?,features=?,source=?,updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (item["name"], item["role"], item["country"], item["age"], initials(item["name"]),
              json.dumps(item["features"]), source, player_id))
        store_details(db, item, player_id)
    return get_player(player_id)


@router.delete("/{player_id}", dependencies=[owner])
def archive_player(player_id: str):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        found = db.execute("SELECT id FROM players WHERE id=?", (player_id,)).fetchone()
        if not found:
            raise HTTPException(404, "Player not found")
        db.execute("UPDATE players SET archived_at=CURRENT_TIMESTAMP WHERE id=? AND archived_at IS NULL", (player_id,))
    return {"id": player_id, "archived": True}


@router.get("/archive/list", dependencies=[owner])
def archived_profiles():
    with connect() as db:
        rows = db.execute("""
            SELECT id,name,sport,role,archived_at FROM players
            WHERE archived_at IS NOT NULL ORDER BY archived_at DESC,id
        """).fetchall()
    return {"players": [dict(row) for row in rows]}


@router.post("/{player_id}/restore", dependencies=[owner])
def restore_player(player_id: str):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT name,sport,country,archived_at FROM players WHERE id=?", (player_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Player not found")
        if row["archived_at"] is not None:
            guard_duplicates(db, [(row["name"], row["sport"], row["country"])])
            db.execute("UPDATE players SET archived_at=NULL WHERE id=?", (player_id,))
    return get_player(player_id)


@router.get("/{player_id}/statistics")
def statistics(player_id: str):
    with connect() as db:
        require_active(db, player_id)
        rows = db.execute("""
            SELECT format,competition,season,counts,source FROM player_statistics
            WHERE player_id=? ORDER BY season DESC,format,competition
        """, (player_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["counts"] = json.loads(item["counts"])
        result.append({**item, "rates": cricket_rates(item["counts"]), "source_type": "USER_ENTERED"})
    return {"statistics": result}


@router.put("/{player_id}/statistics", dependencies=[owner])
def store_statistics(player_id: str, data: Statistics):
    if not data.source:
        raise HTTPException(422, "Enter the scorecard or data source.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if require_active(db, player_id)["sport"] != "cricket":
            raise HTTPException(422, "Cricket statistics require a cricket profile.")
        db.execute("""
            INSERT INTO player_statistics(player_id,format,competition,season,counts,source)
            VALUES(?,?,?,?,?,?) ON CONFLICT(player_id,format,competition,season)
            DO UPDATE SET counts=excluded.counts,source=excluded.source
        """, (player_id, data.format, data.competition, data.season, data.counts.model_dump_json(), data.source))
    return statistics(player_id)


def review_metrics(attempts):
    result = {}
    for drill in ("batting", "bowling", "fielding"):
        relevant = [event for event in attempts if event["drill"] == drill]
        count = len(relevant)
        successes = sum(event["success"] for event in relevant)
        result[drill] = {"score": round(100 * successes / count, 2) if count >= 5 else None,
                         "observations": count, "successes": successes}
    return result


@router.get("/{player_id}/media")
def media(player_id: str, _: None = owner):
    with connect() as db:
        require_active(db, player_id)
        links = [dict(row) for row in db.execute(
            "SELECT id,kind,title,url,attribution,created_at FROM player_media WHERE player_id=? ORDER BY id DESC",
            (player_id,),
        )]
        saved = db.execute("""
            SELECT video_jobs.id,filename,preview,output,analysis,video_reviews.attempts,video_reviews.updated_at
            FROM video_reviews JOIN video_jobs ON video_jobs.id=video_reviews.video_id
            WHERE player_id=? ORDER BY video_reviews.updated_at DESC
        """, (player_id,)).fetchall()
    reviews = []
    for row in saved:
        item = dict(row)
        attempts = json.loads(item.pop("attempts"))
        analysis = json.loads(item.pop("analysis"))
        reviews.append({**item, "attempts": attempts, "metrics": review_metrics(attempts),
                        "source_type": "HUMAN_REVIEWED_VIDEO", "sample_duration_s": analysis["sample_duration_s"],
                        "browser_video": analysis["browser_video"]})
    return {"media": links, "reviews": reviews}


@router.post("/{player_id}/media", dependencies=[owner], status_code=201)
def add_media(player_id: str, data: Media):
    if not data.authorized or not data.title.strip() or not data.attribution.strip():
        raise HTTPException(422, "Provide a title, source attribution and permission to use the media.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_active(db, player_id)
        if data.kind == "photo":
            db.execute("DELETE FROM player_media WHERE player_id=? AND kind='photo'", (player_id,))
        elif db.execute("SELECT 1 FROM player_media WHERE player_id=? AND url=?", (player_id, str(data.url))).fetchone():
            raise HTTPException(409, "This link is already in the media library.")
        cursor = db.execute("""
            INSERT INTO player_media(player_id,kind,title,url,attribution) VALUES (?,?,?,?,?)
        """, (player_id, data.kind, data.title.strip(), str(data.url), data.attribution.strip()))
        media_id = cursor.lastrowid
    return {"id": media_id}


@router.delete("/{player_id}/media/{media_id}", dependencies=[owner])
def remove_media(player_id: str, media_id: int):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_active(db, player_id)
        if not db.execute("DELETE FROM player_media WHERE player_id=? AND id=?", (player_id, media_id)).rowcount:
            raise HTTPException(404, "Media link not found.")
    return {"removed": True}


@router.post("/{player_id}/video-reviews", dependencies=[owner])
def save_review(player_id: str, review: Review):
    attempts = sorted((attempt.model_dump() for attempt in review.attempts), key=lambda attempt: attempt["seconds"])
    metrics = review_metrics(attempts)
    if not any(metric["score"] is not None for metric in metrics.values()):
        raise HTTPException(422, "Review at least five distinct attempts for one drill.")
    previous = {}
    for attempt in attempts:
        key = attempt["drill"]
        if attempt["seconds"] - previous.get(key, -1) < 0.249:
            raise HTTPException(422, "Each attempt must have a distinct timestamp.")
        previous[key] = attempt["seconds"]
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if require_active(db, player_id)["sport"] != "cricket":
            raise HTTPException(422, "These drills require a cricket profile.")
        video = db.execute("SELECT analysis FROM video_jobs WHERE id=?", (review.video_id,)).fetchone()
        analysis = json.loads(video["analysis"]) if video and video["analysis"] else {}
        if analysis.get("synthetic_fixture") is not False or not analysis.get("source_duration_s"):
            raise HTTPException(422, "Saving requires an uploaded clip with a known duration.")
        if attempts[-1]["seconds"] > analysis["source_duration_s"] + 0.05:
            raise HTTPException(422, "A timestamp is outside the uploaded clip.")
        saved = db.execute("SELECT player_id FROM video_reviews WHERE video_id=?", (review.video_id,)).fetchone()
        if saved and saved["player_id"] != player_id:
            raise HTTPException(409, "This review is already linked to another profile.")
        db.execute("""
            INSERT INTO video_reviews(video_id,player_id,attempts) VALUES(?,?,?)
            ON CONFLICT(video_id) DO UPDATE SET attempts=excluded.attempts, updated_at=CURRENT_TIMESTAMP
        """, (review.video_id, player_id, json.dumps(attempts)))
    return {"metrics": metrics, "source_type": "HUMAN_REVIEWED_VIDEO"}


@router.get("/{player_id}/talent-vector")
def talent_vector(player_id: str):
    """Describe the inputs to workspace ranking without merging unlike evidence."""
    with connect() as db:
        player = row_player(require_active(db, player_id))
        note = detail_record(db, player_id)["source_note"]
    vector = {}
    for key, label in FEATURES[player["sport"]]:
        score = player["features"].get(key)
        source_type, confidence, method = "UNAVAILABLE", None, None
        if score is not None:
            if player["demo"]:
                source_type, confidence, method = "DEMO_DATA", "Illustrative", "Bundled scenario value"
            elif player["source"].startswith("Raw CSV"):
                source_type, confidence, method = "MODEL_ESTIMATED", "Heuristic reference range", "Bounded normalization of supplied counts"
            else:
                source_type, confidence, method = "USER_ENTERED", "User supplied", "User-entered normalized value"
        vector[key] = {
            "label": label, "score": score, "status": "Unavailable" if score is None else "Available",
            "source_type": source_type, "source": (note or player["source"]) if score is not None else None,
            "confidence": confidence, "sample_size": None, "method": method,
            "last_updated": (player["updated_at"] or player["created_at"]) if score is not None else None,
        }
    return {"version": 2, "sport": player["sport"], "scale": [0, 100], "features": vector}
