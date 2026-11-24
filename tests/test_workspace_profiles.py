import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import db
from app.cricket_stats import CricketCounts, cricket_rates, parse_overs
from app.main import app

LOCAL = ("127.0.0.1", 50000)
NEW_PLAYER = {
    "name": "Practice Batter", "sport": "cricket", "role": "Opener",
    "country": "IN", "features": {"batting": 72},
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "workspace.db")
    monkeypatch.delenv("VIXISU_OWNER_TOKEN", raising=False)
    with TestClient(app, base_url="http://localhost", client=LOCAL) as client:
        yield client


def create(workspace, **fields):
    response = workspace.post("/api/players", json={**NEW_PLAYER, **fields})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_cricket_rates_keep_raw_values_and_missing_denominators():
    counts = CricketCounts(
        innings=4, dismissals=2, runs=50, balls_faced=25, fours=5, sixes=2,
        overs="4.2", wickets=2, runs_conceded=30, dot_balls=13,
    ).model_dump()
    assert cricket_rates(counts) == {
        "batting_average": 25, "strike_rate": 200, "bowling_average": 15,
        "economy": 6.92, "bowling_strike_rate": 13, "boundary_run_percent": 64,
        "dot_ball_percent": 50,
    }
    assert cricket_rates({"runs":25, "balls_faced":25})["strike_rate"] == 100
    assert cricket_rates({"runs":25, "balls_faced":0})["strike_rate"] is None
    assert cricket_rates({"runs":25, "dismissals":0})["batting_average"] is None
    assert parse_overs("4.2") == 26
    for invalid in ("4.6", "4.20", "-1"):
        with pytest.raises(ValueError):
            parse_overs(invalid)
    for invalid in ({"wickets":-1}, {"wickets":True}, {"overs":"4.2", "balls_bowled":42},
                    {"innings":2, "dismissals":3}, {"runs":5, "sixes":1}):
        with pytest.raises(ValueError):
            CricketCounts(**invalid)


def test_edit_duplicate_and_archive_preserve_dependencies(workspace):
    player_id = create(workspace)
    path = "/api/players/" + player_id
    assert workspace.post("/api/players", json={**NEW_PLAYER, "name": " PRACTICE   BATTER "}).status_code == 409
    updated = workspace.patch(path, json={"name":"Updated Batter", "team":"City Eleven", "style":"Right-handed"})
    assert updated.status_code == 200
    assert updated.json()["team"] == "City Eleven"
    assert updated.json()["features"] == {"batting":72}
    assert workspace.patch(path, json={"features":{"batting":125}}).status_code == 422
    assert workspace.post("/api/teams", json={
        "name":"Saved Twelve", "sport":"cricket", "role":"Opener", "roster_ids":[player_id],
    }).status_code == 201
    assert workspace.delete(path).status_code == 200
    assert workspace.get(path).status_code == 404
    assert player_id not in {item["id"] for item in workspace.get("/api/players").json()["players"]}
    assert workspace.get("/api/teams").json()["teams"][0]["roster_ids"] == [player_id]


def test_scorecards_are_separate_and_talent_vector_retains_sources(workspace):
    player_id = create(workspace)
    path = "/api/players/" + player_id
    for format_name, runs in [("T20",50), ("ODI",25)]:
        assert workspace.put(path + "/statistics", json={
            "format":format_name,"competition":"City cup","season":"2026",
            "counts":{"runs":runs,"balls_faced":25},"source":"Supplied scorecard",
        }).status_code == 200
    scores = workspace.get(path + "/statistics").json()["statistics"]
    assert {row["format"]:row["rates"]["strike_rate"] for row in scores} == {"ODI":100,"T20":200}
    vector = workspace.get(path + "/talent-vector").json()["features"]
    assert vector["batting"]["source_type"] == "USER_ENTERED"
    assert vector["bowling"]["score"] is None
    assert vector["bowling"]["source_type"] == "UNAVAILABLE"


def test_authorized_media_add_replace_and_remove(workspace):
    path = "/api/players/" + create(workspace) + "/media"
    record = {"kind":"photo","title":"Licensed portrait","url":"https://example.org/p.jpg",
              "attribution":"Photographer, CC BY 4.0","authorized":True}
    assert workspace.post(path, json={**record, "authorized":False}).status_code == 422
    assert workspace.post(path, json={**record, "url":"http://example.org/image"}).status_code == 422
    assert workspace.post(path, json=record).status_code == 201
    response = workspace.post(path, json={**record, "title":"Replacement"})
    assert response.status_code == 201
    assert [item["title"] for item in workspace.get(path).json()["media"]] == ["Replacement"]
    assert workspace.delete(path + "/" + str(response.json()["id"])).status_code == 200
    assert workspace.get(path).json()["media"] == []


def test_uploaded_clip_review_preserves_timestamps_and_score(workspace):
    path = "/api/players/" + create(workspace)
    other = "/api/players/" + create(workspace, name="Second Batter")
    payload = (db.BASE / "web" / "assets" / "pitch_fixture.mp4").read_bytes()
    result = workspace.post("/api/videos/analyze", files={"file":("test.mp4", payload, "video/mp4")}).json()
    attempts = [
        {"drill":"batting","seconds":0.3 + n * 0.5,"success":n != 4} for n in range(5)
    ]
    review = {"video_id":result["id"],"attempts":attempts}
    response = workspace.post(path + "/video-reviews", json=review)
    assert response.status_code == 200, response.text
    assert response.json()["metrics"]["batting"]["score"] == 80
    assert response.json()["metrics"]["bowling"]["score"] is None
    assert workspace.post(other + "/video-reviews", json=review).status_code == 409
    assert workspace.post(path + "/video-reviews", json={**review,"attempts":[attempts[0]] * 5}).status_code == 422
    sample = workspace.post("/api/videos/sample").json()
    assert workspace.post(path + "/video-reviews", json={**review,"video_id":sample["id"]}).status_code == 422
    saved = workspace.get(path + "/media").json()["reviews"][0]
    assert saved["attempts"] == attempts
    assert saved["source_type"] == "HUMAN_REVIEWED_VIDEO"


def test_workspace_access_checks_origin_remote_clients_and_token(workspace, monkeypatch):
    assert workspace.post("/api/players", json=NEW_PLAYER, headers={"Origin":"https://elsewhere.example"}).status_code == 403
    with TestClient(app,base_url="http://localhost",client=("192.0.2.10",50000)) as remote:
        assert remote.post("/api/players",json=NEW_PLAYER).status_code == 403
    monkeypatch.setenv("VIXISU_OWNER_TOKEN", "pytest-owner-token")
    assert workspace.post("/api/players",json=NEW_PLAYER).status_code == 401
    response = workspace.post("/api/workspace/unlock",headers={"Authorization":"Bearer pytest-owner-token"})
    assert response.status_code == 204
    assert "HttpOnly" in response.headers["set-cookie"]
    assert workspace.post("/api/players",json=NEW_PLAYER).status_code == 201


def test_additive_schema_migration_preserves_existing_profile(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    monkeypatch.setattr(db, "DB_PATH", old)
    with sqlite3.connect(old) as connection:
        connection.execute("""
            CREATE TABLE players (id TEXT PRIMARY KEY, name TEXT, sport TEXT, role TEXT, country TEXT,
              age INTEGER, initials TEXT, features TEXT, source TEXT, created_at TEXT)
        """)
        connection.execute("INSERT INTO players VALUES ('legacy','Legacy Batter','cricket','Opener','IN',25,'LB','{}','Local','2026-01-01')")
    db.initialize()
    db.initialize()
    with db.connect() as connection:
        row = connection.execute("SELECT * FROM players WHERE id='legacy'").fetchone()
        assert row["name"] == "Legacy Batter"
        assert row["archived_at"] is None
        assert row["updated_at"] is None


def test_archived_profile_can_be_restored_with_original_scorecards(workspace):
    path = "/api/players/" + create(workspace)
    payload = {"format":"T20","source":"Club scorebook","counts":{"runs":50,"balls_faced":25}}
    assert workspace.put(path + "/statistics", json=payload).status_code == 200
    assert workspace.delete(path).status_code == 200
    assert workspace.get("/api/players/archive/list").json()["players"][0]["name"] == NEW_PLAYER["name"]
    assert workspace.post(path + "/restore").status_code == 200
    assert workspace.get(path + "/statistics").json()["statistics"][0]["rates"]["strike_rate"] == 200


def test_ranking_charges_missing_weight_and_simulation_preserves_saved_teams(workspace):
    from app.intelligence import score_candidates

    template = {"sport":"cricket","role":"Opener"}
    pool = [
        {**template, "id":"complete", "name":"Complete", "features":{"batting":80,"strike":80}},
        {**template, "id":"partial", "name":"Partial", "features":{"batting":95}},
    ]
    result = score_candidates(pool,"cricket","Opener",{"batting":50,"strike":50})
    assert result[0]["player"]["id"] == "complete"
    assert result[1]["coverage"] == 50 and result[1]["missing_features"] == ["strike"]
    assert result[1]["contributions"]["batting"] == 40.38
    simulation = workspace.post("/api/teams/simulate", json={
        **template,"roster_ids":[],"proposed_roster_ids":["C-01"],
    }).json()
    assert simulation["before"]["exact_role"] == 0
    assert simulation["after"]["exact_role"] == 1
    assert all(item["player"]["id"] != "C-01" for item in simulation["after"]["recommendations"])
    assert workspace.get("/api/teams").json()["teams"] == []
