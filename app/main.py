"""VIXISU premium sports talent scouting MVP API and static web app."""
import csv
import hmac
import io
import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .access import OWNER_COOKIE, owner_session, require_owner
from .cricket import router as cricket_router
from .cricket_stats import CricketCounts
from .profiles import guard_duplicates, router as profile_router
from .scouting_query import router as scouting_router
from .data import FEATURES, ROLE_TEMPLATES
from .db import BASE, connect, initialize, row_player
from .intelligence import clean_weights, score_candidates
from .ingestion import extract_raw_features
from .video import UPLOADS, OUTPUTS, MAX_UPLOAD_BYTES, process_video

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title='VIXISU Talent Intelligence API', version='0.1.0', lifespan=lifespan)
app.include_router(cricket_router)
app.include_router(profile_router)
app.include_router(scouting_router)

class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    sport: str
    role: str
    weights: dict[str,float] | None = None
    roster_ids: list[str] = Field(default_factory=list, max_length=30)

class RecommendationRequest(BaseModel):
    sport: str
    role: str
    weights: dict[str,float] | None = None
    roster_ids: list[str] = Field(default_factory=list, max_length=30)


class SimulationRequest(RecommendationRequest):
    proposed_roster_ids: list[str] = Field(max_length=30)


def all_players(sport=None):
    with connect() as db:
        if sport:
            rows = db.execute('SELECT * FROM players WHERE sport=? AND archived_at IS NULL ORDER BY name', (sport,)).fetchall()
        else:
            rows = db.execute('SELECT * FROM players WHERE archived_at IS NULL ORDER BY sport,name').fetchall()
    return [row_player(r) for r in rows]


@app.get('/api/health')
def health():
    return {'status':'ok','app':'VIXISU','version':'0.1.0'}

@app.get('/api/config')
def config():
    return {'features':{k:[{'key':key,'label':label} for key,label in vals] for k,vals in FEATURES.items()},
            'roles':ROLE_TEMPLATES,'demo_notice':'Seed players and scores are fictional illustrative data, not verified scouting assessments.'}

@app.get('/api/overview')
def overview():
    players = all_players()
    with connect() as db:
        videos = db.execute('SELECT COUNT(*) FROM video_jobs').fetchone()[0]
        teams = db.execute('SELECT COUNT(*) FROM teams').fetchone()[0]
    return {'players':len(players),'cricket':sum(p['sport']=='cricket' for p in players),
            'football':sum(p['sport']=='football' for p in players),'videos':videos,'teams':teams}

@app.get('/api/players')
def list_players(sport: str | None = Query(default=None)):
    if sport is not None and sport not in FEATURES:
        raise HTTPException(422, 'Unsupported sport')
    return {'players':all_players(sport)}

@app.post('/api/players/import', dependencies=[Depends(require_owner)])
async def import_players(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(422, 'Upload a CSV file')
    raw = await file.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:
        raise HTTPException(413,'CSV exceeds 2 MB limit')
    try:
        content = raw.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames or not {'name','sport','role'}.issubset(reader.fieldnames):
            raise ValueError('CSV requires name,sport,role headers and normalized feature columns')
        staged=[]
        for i,row in enumerate(reader):
            if i >= 300:
                raise ValueError('Import up to 300 players per file')
            sport = (row.get('sport') or '').strip().lower()
            role = (row.get('role') or '').strip()
            name = (row.get('name') or '').strip()
            if len(name)<2 or len(name)>100:
                raise ValueError(f'Row {i+2}: invalid name')
            features={}
            for key,_ in FEATURES.get(sport,[]):
                val = (row.get(key) or '').strip()
                if val:
                    features[key] = float(val)
            if sport not in FEATURES or role not in ROLE_TEMPLATES[sport]:
                raise ValueError(f'Row {i+2}: invalid sport/role')
            if not features or any(not (0 <= v <= 100) for v in features.values()):
                raise ValueError(f'Row {i+2}: normalized feature scores must be 0–100')
            staged.append((f'P-{uuid.uuid4().hex[:9].upper()}',name,sport,role,
                           (row.get('country') or '').strip()[:5],None,
                           ''.join(x[:1] for x in name.split()[:2]).upper(),json.dumps(features),
                           'Imported CSV — user supplied normalized scores'))
        if not staged:
            raise ValueError('CSV contains no data rows')
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        guard_duplicates(db, ((row[1], row[2], row[4]) for row in staged))
        db.executemany('''INSERT INTO players(id,name,sport,role,country,age,initials,features,source)
             VALUES(?,?,?,?,?,?,?,?,?)''', staged)
    return {'imported':len(staged),'notice':'CSV values are treated as pre-normalized 0–100 feature scores; not automatically verified.'}

@app.post('/api/players/import-raw', dependencies=[Depends(require_owner)])
async def import_raw_players(file: UploadFile = File(...)):
    """Import aggregated cricket/football raw statistics using disclosed heuristic ranges."""
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(422, 'Upload a CSV file')
    raw=await file.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:
        raise HTTPException(413,'CSV exceeds 2 MB limit')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not reader.fieldnames or not {'name','sport','role'}.issubset(reader.fieldnames):
            raise ValueError('CSV requires name,sport,role headers')
        staged=[]
        raw_cricket=[]
        for i,row in enumerate(reader):
            if i>=300:
                raise ValueError('Import up to 300 players per file')
            name=(row.get('name') or '').strip()
            sport=(row.get('sport') or '').strip().lower()
            role=(row.get('role') or '').strip()
            if len(name)<2 or len(name)>100 or sport not in FEATURES or role not in ROLE_TEMPLATES[sport]:
                raise ValueError(f'Row {i+2}: invalid name, sport or role')
            try:
                counts = None
                if sport == 'cricket':
                    counts = CricketCounts(**{
                        key: (str(row[key]).strip() if key == 'overs' else int(str(row[key]).strip()))
                        for key in CricketCounts.model_fields if str(row.get(key) or '').strip()
                    })
                features=extract_raw_features(counts.model_dump() if counts else row,sport)
            except (ValueError,TypeError) as exc:
                raise ValueError(f'Row {i+2}: {exc}') from exc
            if not features:
                raise ValueError(f'Row {i+2}: no supported metrics can be derived')
            player_id = f'P-{uuid.uuid4().hex[:9].upper()}'
            if counts:
                format_name = (row.get('format') or 'Other').strip()
                if format_name not in {'Test', 'ODI', 'T20', 'IT20', 'T10', 'MDM', 'ODM', 'Other'}:
                    raise ValueError(f'Row {i+2}: invalid cricket format')
                raw_cricket.append((player_id, format_name, (row.get('competition') or '').strip()[:120],
                                    (row.get('season') or '').strip()[:30], counts.model_dump_json(),
                                    (row.get('source') or 'User-supplied CSV').strip()[:300]))
            staged.append((player_id,name,sport,role,
                           (row.get('country') or '').strip()[:5],None,
                           ''.join(x[:1] for x in name.split()[:2]).upper(),json.dumps(features),
                           'Raw CSV — heuristic range normalization (not professionally calibrated)'))
        if not staged:
            raise ValueError('CSV contains no data rows')
    except (UnicodeDecodeError,ValueError,TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        guard_duplicates(db, ((row[1], row[2], row[4]) for row in staged))
        db.executemany('''INSERT INTO players(id,name,sport,role,country,age,initials,features,source)
          VALUES(?,?,?,?,?,?,?,?,?)''',staged)
        db.executemany('''
            INSERT INTO player_statistics(player_id,format,competition,season,counts,source)
            VALUES(?,?,?,?,?,?)
        ''', raw_cricket)
    return {'imported':len(staged),'notice':'Raw statistics converted using illustrative fixed reference ranges; missing features are not inferred.'}


@app.post('/api/teams',status_code=201, dependencies=[Depends(require_owner)])
def create_team(data: TeamCreate):
    try:
        weights = clean_weights(data.sport,data.role,data.weights)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    ids={p['id'] for p in all_players(data.sport)}
    if any(x not in ids for x in data.roster_ids):
        raise HTTPException(422,'Roster includes invalid or cross-sport player IDs')
    with connect() as db:
        cur = db.execute('INSERT INTO teams(name,sport,role,weights,roster) VALUES(?,?,?,?,?)',
            (data.name.strip(),data.sport,data.role,json.dumps(weights),json.dumps(data.roster_ids)))
        tid=cur.lastrowid
    return {'id':tid,'name':data.name,'sport':data.sport,'role':data.role,'weights':weights,'roster_ids':data.roster_ids}

@app.get('/api/teams')
def list_teams():
    with connect() as db:
        rows=db.execute('SELECT * FROM teams ORDER BY id DESC').fetchall()
    return {'teams':[{'id':r['id'],'name':r['name'],'sport':r['sport'],'role':r['role'],
                       'weights':json.loads(r['weights']),'roster_ids':json.loads(r['roster'])} for r in rows]}

@app.post('/api/recommendations')
def recommend(data: RecommendationRequest):
    try:
        weights = clean_weights(data.sport,data.role,data.weights)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    players=all_players(data.sport)
    ids={p['id'] for p in players}
    if any(x not in ids for x in data.roster_ids):
        raise HTTPException(422,'Roster includes invalid or cross-sport player IDs')
    return {'sport':data.sport,'role':data.role,'weights':weights,'roster_ids':data.roster_ids,
            'results':score_candidates(players,data.sport,data.role,weights,data.roster_ids),
            'disclaimer':'Scores are weighted decision-support estimates, not predictions of real-world success.'}

@app.post('/api/teams/simulate')
def simulate_team(data: SimulationRequest):
    try:
        weights = clean_weights(data.sport, data.role, data.weights)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    pool = all_players(data.sport)
    by_id = {player['id']: player for player in pool}
    if (set(data.roster_ids) | set(data.proposed_roster_ids)) - by_id.keys():
        raise HTTPException(422, 'Both squads must contain active players from the selected sport.')

    def summarize(ids):
        members = [by_id[pid] for pid in dict.fromkeys(ids)]
        skills = {}
        for key in weights:
            scores = [member['features'][key] for member in members if key in member['features']]
            skills[key] = {'mean': round(sum(scores) / len(scores), 1) if scores else None,
                           'observed': len(scores)}
        ranked = score_candidates(pool, data.sport, data.role, weights, ids)
        return {'members': len(members), 'exact_role': sum(player['role'] == data.role for player in members),
                'skills': skills, 'recommendations': ranked[:3]}

    return {'role': data.role, 'before': summarize(data.roster_ids), 'after': summarize(data.proposed_roster_ids),
            'source': 'Workspace scores', 'scenario': 'Team-fit simulation'}


@app.post('/api/videos/analyze', dependencies=[Depends(require_owner)])
async def analyze_video(file: UploadFile = File(...)):
    name = Path(file.filename or '').name
    if not name.lower().endswith(('.mp4','.avi','.mov','.mkv','.webm')):
        raise HTTPException(422,'Supported video formats: MP4, AVI, MOV, MKV, WEBM')
    payload=await file.read(MAX_UPLOAD_BYTES+1)
    if len(payload)>MAX_UPLOAD_BYTES:
        raise HTTPException(413,'Video exceeds 25 MB limit')
    if not payload:
        raise HTTPException(422,'Empty video file')
    src=UPLOADS / f'{uuid.uuid4().hex[:12]}{Path(name).suffix.lower()}'
    src.write_bytes(payload)
    try:
        result=await run_in_threadpool(process_video,src,name)
        return result
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)) from exc
    finally:
        src.unlink(missing_ok=True)

@app.post('/api/videos/sample', dependencies=[Depends(require_owner)])
def analyze_sample():
    return process_video(BASE/'web'/'assets'/'pitch_fixture.mp4','Synthetic pitch tracking test',fixture=True)

@app.get('/api/videos', dependencies=[Depends(require_owner)])
def list_videos():
    with connect() as db:
        rows=db.execute('SELECT * FROM video_jobs ORDER BY created_at DESC LIMIT 20').fetchall()
    return {'videos':[dict(r) for r in rows]}

@app.post('/api/workspace/unlock', status_code=204, include_in_schema=False)
def unlock_workspace(request: Request):
    token = os.environ.get('VIXISU_OWNER_TOKEN')
    if token:
        supplied = request.headers.get('authorization', '')
        if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
            raise HTTPException(401, 'Workspace owner token did not match.')
    else:
        require_owner(request)
    response = Response(status_code=204)
    if token:
        response.set_cookie(OWNER_COOKIE, owner_session(token), httponly=True, samesite='strict',
                            secure=request.url.scheme == 'https', max_age=8 * 3600)
    return response

@app.get('/outputs/{filename}', dependencies=[Depends(require_owner)], include_in_schema=False)
def analysis_output(filename: str):
    if not re.fullmatch(r'[0-9a-f]{12}\.(jpg|mp4)', filename) or not (OUTPUTS / filename).is_file():
        raise HTTPException(404, 'Analysis media not found.')
    return FileResponse(OUTPUTS / filename, headers={'Cache-Control':'private, no-store'})
app.mount('/assets', StaticFiles(directory=str(BASE/'web'/'assets')),name='assets')

@app.get('/home', include_in_schema=False)
def home():
    return FileResponse(str(BASE / 'web' / 'home.html'))

@app.get('/')
def index():
    return FileResponse(str(BASE/'web'/'index.html'))

@app.get('/{path:path}')
def spa(path: str):
    if path.startswith('api/'):
        raise HTTPException(404,'Not found')
    return FileResponse(str(BASE/'web'/'index.html'))
