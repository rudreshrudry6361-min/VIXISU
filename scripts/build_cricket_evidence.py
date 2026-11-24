"""Build an independent SQLite evidence store from a Cricsheet JSON archive."""

import argparse
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import astuple, dataclass
from pathlib import Path
from zipfile import ZipFile


BOWLER_WICKETS = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
NON_DISMISSALS = {"retired hurt", "retired not out"}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE source (
    name TEXT NOT NULL, url TEXT NOT NULL, license_url TEXT NOT NULL,
    archive_file TEXT NOT NULL
);
CREATE TABLE matches (
    id TEXT PRIMARY KEY NOT NULL, date TEXT NOT NULL, season TEXT NOT NULL,
    format TEXT NOT NULL, gender TEXT NOT NULL, team_type TEXT NOT NULL,
    competition TEXT
);
CREATE TABLE player_match_stats (
    match_id TEXT NOT NULL REFERENCES matches(id), player_id TEXT NOT NULL,
    display_name TEXT NOT NULL, team TEXT, rostered INTEGER NOT NULL,
    runs INTEGER NOT NULL, legal_balls_faced INTEGER NOT NULL,
    fours INTEGER NOT NULL, sixes INTEGER NOT NULL, dismissals INTEGER NOT NULL,
    batting_innings INTEGER NOT NULL, legal_balls_bowled INTEGER NOT NULL,
    runs_conceded INTEGER NOT NULL, wickets INTEGER NOT NULL,
    catches INTEGER NOT NULL, stumpings INTEGER NOT NULL,
    opening_innings INTEGER NOT NULL, middle_innings INTEGER NOT NULL,
    death_runs INTEGER NOT NULL, death_balls INTEGER NOT NULL,
    highest_score INTEGER, dot_balls INTEGER NOT NULL,
    PRIMARY KEY (match_id, player_id)
);
"""

INDEXES = """
CREATE INDEX cohort_lookup ON matches(format, gender, competition, season, team_type);
CREATE INDEX player_lookup ON player_match_stats(player_id);
CREATE INDEX season_competition ON matches(competition, season, format, gender, team_type);
CREATE VIEW cohort_player_match_stats AS
SELECT matches.date, matches.season, matches.format, matches.gender,
       matches.team_type, matches.competition, player_match_stats.*
FROM player_match_stats JOIN matches ON matches.id = player_match_stats.match_id;
"""


@dataclass
class Counts:
    display_name: str
    team: str | None = None
    rostered: int = 0
    runs: int = 0
    legal_balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    dismissals: int = 0
    batting_innings: int = 0
    legal_balls_bowled: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    catches: int = 0
    stumpings: int = 0
    opening_innings: int = 0
    middle_innings: int = 0
    death_runs: int = 0
    death_balls: int = 0
    highest_score: int | None = None
    dot_balls: int = 0


def match_stats(match):
    info = match["info"]
    registry = info["registry"]["people"]
    players = {}

    def player_id(name):
        identifier = registry[name]
        if identifier not in players:
            players[identifier] = Counts(name)
        return identifier

    for team, roster in info.get("players", {}).items():
        for name in roster:
            player = players[player_id(name)]
            player.team = team
            player.rostered = 1

    for innings in match.get("innings", []):
        if innings.get("super_over"):
            continue
        batters = {}
        regular_t20 = (
            info["match_type"] == "T20" and info.get("overs") == 20
            and innings.get("target", {}).get("overs", 20) == 20
        )
        for over in innings.get("overs", []):
            for ball in over["deliveries"]:
                striker_id = player_id(ball["batter"])
                batters.setdefault(striker_id, 0)
                batters.setdefault(player_id(ball["non_striker"]), 0)
                striker = players[striker_id]
                bowler = players[player_id(ball["bowler"])]
                runs = ball["runs"]
                extras = ball.get("extras", {})
                legal = "wides" not in extras and "noballs" not in extras
                striker.runs += runs["batter"]
                batters[striker_id] += runs["batter"]
                striker.legal_balls_faced += legal
                if regular_t20 and 15 <= over["over"] < 20:
                    striker.death_runs += runs["batter"]
                    striker.death_balls += legal
                if not runs.get("non_boundary"):
                    striker.fours += runs["batter"] == 4
                    striker.sixes += runs["batter"] == 6
                bowler.legal_balls_bowled += legal
                bowler.dot_balls += legal and runs["total"] == 0
                bowler.runs_conceded += (
                    runs["total"] - extras.get("byes", 0)
                    - extras.get("legbyes", 0) - extras.get("penalty", 0)
                )
                for wicket in ball.get("wickets", []):
                    kind = wicket["kind"]
                    dismissed_id = player_id(wicket["player_out"])
                    batters.setdefault(dismissed_id, 0)
                    players[dismissed_id].dismissals += kind not in NON_DISMISSALS
                    bowler.wickets += kind in BOWLER_WICKETS
                    fielders = wicket.get("fielders", [])
                    if kind == "caught and bowled":
                        bowler.catches += 1
                    elif kind in {"caught", "stumped"} and len(fielders) == 1:
                        name = fielders[0].get("name")
                        if name:
                            fielder = players[player_id(name)]
                            fielder.catches += kind == "caught"
                            fielder.stumpings += kind == "stumped"
        for slot, (identifier, innings_runs) in enumerate(batters.items()):
            player = players[identifier]
            player.highest_score = max(player.highest_score or 0, innings_runs)
            player.batting_innings += 1
            player.opening_innings += slot < 2
            player.middle_innings += 2 <= slot < 5
    return players


def build(archive, destination):
    if destination.exists():
        raise FileExistsError(f"Choose a new output path. {destination} already exists.")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
        pending = Path(temporary.name)
    try:
        with closing(sqlite3.connect(pending)) as connection, ZipFile(archive) as source:
            connection.executescript(SCHEMA)
            with connection:
                connection.execute(
                    "INSERT INTO source VALUES (?, ?, ?, ?)",
                    ("Cricsheet", "https://cricsheet.org/downloads/",
                     "https://opendatacommons.org/licenses/by/1-0/", archive.name),
                )
                for member in source.infolist():
                    if not member.filename.endswith(".json") or member.is_dir():
                        continue
                    with source.open(member) as stream:
                        match = json.load(stream)
                    info = match["info"]
                    match_id = Path(member.filename).stem
                    try:
                        players = match_stats(match)
                    except KeyError as error:
                        raise ValueError(f"Missing evidence field in match {match_id}: {error}") from error
                    connection.execute(
                        "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (match_id, min(info["dates"]), str(info["season"]),
                         info["match_type"], info["gender"], info["team_type"],
                         info.get("event", {}).get("name")),
                    )
                    connection.executemany(
                        "INSERT INTO player_match_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        ((match_id, identifier, *astuple(counts)) for identifier, counts in players.items()),
                    )
            connection.executescript(INDEXES)
            matches, = connection.execute("SELECT COUNT(*) FROM matches").fetchone()
            if not matches:
                raise ValueError("Archive contains no match JSON records.")
        # A concurrent import should never overwrite a successfully completed store.
        os.link(pending, destination)
        return matches
    finally:
        pending.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(f"Imported {build(args.archive, args.destination):,} matches into {args.destination}")
