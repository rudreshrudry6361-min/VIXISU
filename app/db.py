"""Small SQLite persistence layer for a portable prototype."""
import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .data import DEMO_PLAYERS

BASE = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get('VIXISU_DB_PATH', str(BASE / 'vixisu.db')))

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    finally:
        con.close()


def initialize():
    with connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sport TEXT NOT NULL CHECK(sport IN ('cricket','football')),
                role TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT '',
                age INTEGER,
                initials TEXT NOT NULL,
                features TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'User entered',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sport TEXT NOT NULL,
                role TEXT NOT NULL,
                weights TEXT NOT NULL,
                roster TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS video_jobs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                detector TEXT NOT NULL,
                status TEXT NOT NULL,
                frames INTEGER NOT NULL DEFAULT 0,
                detections INTEGER NOT NULL DEFAULT 0,
                preview TEXT,
                output TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS player_details (
                player_id TEXT PRIMARY KEY REFERENCES players(id),
                team TEXT NOT NULL DEFAULT '',
                style TEXT NOT NULL DEFAULT '',
                source_note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS player_statistics (
                player_id TEXT NOT NULL REFERENCES players(id),
                format TEXT NOT NULL,
                competition TEXT NOT NULL,
                season TEXT NOT NULL,
                counts TEXT NOT NULL,
                source TEXT NOT NULL,
                PRIMARY KEY (player_id, format, competition, season)
            );
            CREATE TABLE IF NOT EXISTS player_media (
                id INTEGER PRIMARY KEY,
                player_id TEXT NOT NULL REFERENCES players(id),
                kind TEXT NOT NULL CHECK(kind IN ('photo', 'video')),
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                attribution TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_profile_photo
                ON player_media(player_id) WHERE kind = 'photo';
            CREATE TABLE IF NOT EXISTS video_reviews (
                video_id TEXT PRIMARY KEY REFERENCES video_jobs(id),
                player_id TEXT NOT NULL REFERENCES players(id),
                attempts TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS player_video_reviews ON video_reviews(player_id);
        ''')
        db.execute('BEGIN IMMEDIATE')
        player_columns = {row['name'] for row in db.execute('PRAGMA table_info(players)')}
        for column in ('archived_at', 'updated_at'):
            if column not in player_columns:
                db.execute(f'ALTER TABLE players ADD COLUMN {column} TEXT')
        if 'analysis' not in {row['name'] for row in db.execute('PRAGMA table_info(video_jobs)')}:
            db.execute('ALTER TABLE video_jobs ADD COLUMN analysis TEXT')
        n = db.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        if n == 0:
            for pid, name, sport, role, country, age, features, initials in DEMO_PLAYERS:
                db.execute('''INSERT INTO players(id,name,sport,role,country,age,initials,features,source)
                    VALUES(?,?,?,?,?,?,?,?,?)''',
                    (pid,name,sport,role,country,age,initials,json.dumps(features),'Fictional demo profile — illustrative scores'))


def row_player(row):
    obj = dict(row)
    obj['features'] = json.loads(obj['features'])
    obj['demo'] = obj['source'].startswith('Fictional demo')
    return obj
