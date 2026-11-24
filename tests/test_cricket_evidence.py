import pytest
from fastapi.testclient import TestClient

from app import cricket, db
from app.main import app


COHORT = {
    "competition": "Indian Premier League",
    "season": "2024",
    "format": "T20",
    "gender": "male",
    "team_type": "club",
}


@pytest.fixture
def evidence_client(tmp_path, monkeypatch):
    path = cricket.evidence_path()
    if not path.is_file():
        pytest.skip("Cricsheet evidence bundle is unavailable")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        yield client


def test_full_archive_and_named_cohort(evidence_client):
    client = evidence_client
    summary = client.get("/api/cricket/coverage").json()
    assert summary["matches"] == 23241
    assert summary["players"] == 13782
    assert {row["gender"] for row in summary["cohorts"]} == {"male", "female"}
    result = client.get("/api/cricket/players", params={**COHORT, "q": "Virat Kohli"}).json()
    assert result["total"] == 1
    assert result["players"][0]["player_id"] == "ba607b88"
    row = client.get("/api/cricket/players/ba607b88", params=COHORT).json()
    assert row["runs"] == 741 and row["matches"] == 15
    assert row["rates"]["batting_average"] == 61.75
    assert row["rates"]["economy"] is None
    assert row["recent_matches"][0]["season"] == "2024"
    assert client.get("/api/cricket/players/ba607b88").json()["rates"] is None


def test_decision_lab_role_change_and_roster(evidence_client):
    client = evidence_client
    def rank(role, **extra):
        response = client.post("/api/cricket/decision-lab", json={"role": role, "cohort": COHORT, **extra})
        assert response.status_code == 200, response.text
        return response.json()

    opener = rank("Opener")
    finisher = rank("Finisher")
    top = opener["results"][0]
    assert top["player"]["id"] != finisher["results"][0]["player"]["id"]
    assert all(result["coverage"] >= 50 for result in opener["results"])
    assert sum(top["contributions"].values()) <= 85
    assert opener["margin"] is not None and len(opener["scenarios"]) == 2
    roster = rank("Opener", roster_ids=[top["player"]["id"]])
    assert top["player"]["id"] not in {row["player"]["id"] for row in roster["results"]}
    assert all(0 <= result["gap_bonus"] <= 8 for result in roster["results"])


def test_decision_lab_rejects_unscoped_or_cross_format_ranking(evidence_client):
    client = evidence_client
    for cohort in ({}, {**COHORT, "format": "Test"}):
        result = client.post("/api/cricket/decision-lab", json={"role": "Opener", "cohort": cohort})
        assert result.status_code == 422
    result = client.post("/api/cricket/decision-lab", json={"role": "Opener", "cohort": COHORT, "roster_ids": ["C-01"]})
    assert result.status_code == 422


def test_entrance_and_scouting_room_routes(evidence_client):
    assert "Enter the Scouting Room" in evidence_client.get("/home").text
    assert "cricket-scout.js" in evidence_client.get("/scout").text
    assert evidence_client.get("/assets/photos/kohli-ink.webp").status_code == 200


def test_scouting_query_uses_real_cohort_and_explains_preferences(evidence_client):
    data = {"cohort":COHORT,"question":"Find aggressive T20 openers in 2024"}
    result = evidence_client.post("/api/scouting/query",json=data)
    assert result.status_code == 200, result.text
    assert result.json()["weights"]["strike"] == 110
    assert result.json()["results"][0]["player"]["matches"] >= 3
    assert evidence_client.post("/api/scouting/query",json={**data,"question":"Find T20I opening batters"}).status_code == 422
    result = evidence_client.post("/api/scouting/query",json={
        **data,"question":"Compare these players","player_ids":["ba607b88","462411b3"],
    })
    assert [player["name"] for player in result.json()["players"]] == ["Jasprit Bumrah","Virat Kohli"]
    assert result.json()["players"][1]["highest_score"] == 113
