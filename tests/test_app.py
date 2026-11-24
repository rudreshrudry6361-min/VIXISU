import io
import pytest
from fastapi.testclient import TestClient
from app import db
from app.main import app
from app.data import ROLE_TEMPLATES
from app.intelligence import score_candidates, clean_weights

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        yield client


def test_health_and_seed_data(client):
    assert client.get('/api/health').json()['status'] == 'ok'
    data = client.get('/api/players').json()['players']
    assert len(data) == 16
    assert all(p['demo'] for p in data)
    assert client.get('/api/overview').json()['cricket'] == 8


def test_sport_separation_and_recommendations(client):
    resp = client.post('/api/recommendations', json={'sport':'football','role':'Midfielder'})
    assert resp.status_code == 200
    rows = resp.json()['results']
    assert rows and all(r['player']['sport']=='football' for r in rows)
    assert rows[0]['score'] <= 100
    assert all('reasons' in r and r['reasons'] for r in rows)


def test_requirement_change_changes_ranking(client):
    pool=client.get('/api/players?sport=cricket').json()['players']
    a=score_candidates(pool,'cricket','Opener')
    b=score_candidates(pool,'cricket','Finisher')
    assert a[0]['player']['id'] != b[0]['player']['id']


def test_roster_excluded_and_bonus_bounded(client):
    base=client.post('/api/recommendations',json={'sport':'football','role':'Midfielder'}).json()['results']
    pid=base[0]['player']['id']
    data=client.post('/api/recommendations',json={'sport':'football','role':'Midfielder','roster_ids':[pid]}).json()['results']
    assert pid not in [x['player']['id'] for x in data]
    assert all(0 <= x['gap_bonus'] <= 8 for x in data)


def test_invalid_cross_sport_roster(client):
    res=client.post('/api/recommendations',json={'sport':'football','role':'Midfielder','roster_ids':['C-01']})
    assert res.status_code == 422


def test_invalid_feature_rejected(client):
    res=client.post('/api/players',json={'name':'Test Player','sport':'football','role':'Forward','features':{'passing':150}})
    assert res.status_code == 422
    res=client.post('/api/players',json={'name':'Test Player','sport':'football','role':'Forward','features':{'batting':75}})
    assert res.status_code == 422


def test_add_player_and_persist(client):
    res=client.post('/api/players',json={'name':'Test Footballer','sport':'football','role':'Defender','features':{'defending':92,'positioning':84}})
    assert res.status_code == 201
    pid=res.json()['id']
    assert client.get('/api/players/'+pid).json()['name']=='Test Footballer'


def test_csv_import(client):
    csv_text='name,sport,role,country,passing,vision\nCSV Footballer,football,Midfielder,GB,90,85\n'
    res=client.post('/api/players/import',files={'file':('players.csv',csv_text,'text/csv')})
    assert res.status_code==200
    assert res.json()['imported']==1
    assert client.get('/api/overview').json()['players']==17


def test_csv_invalid_row_rejected_atomically(client):
    csv_text='name,sport,role,passing\nValid One,football,Midfielder,80\nInvalid One,football,Midfielder,300\n'
    res=client.post('/api/players/import',files={'file':('players.csv',csv_text,'text/csv')})
    assert res.status_code==422
    assert client.get('/api/overview').json()['players']==16


def test_team_creation(client):
    res=client.post('/api/teams',json={'name':'Demo Eleven','sport':'football','role':'Midfielder','roster_ids':['F-02']})
    assert res.status_code==201
    assert res.json()['id'] > 0
    assert len(client.get('/api/teams').json()['teams'])==1


def test_missing_weights_and_role_validation():
    with pytest.raises(ValueError): clean_weights('cricket','Goalkeeper')
    with pytest.raises(ValueError): clean_weights('football','Midfielder',{'nonexistent':100})
    with pytest.raises(ValueError): clean_weights('football','Midfielder',{'passing':0})


def test_static_home(client):
    res=client.get('/')
    assert res.status_code==200
    assert 'VIXISU' in res.text
    assert client.get('/assets/app.js').status_code==200


def test_raw_cricket_import(client):
    text='name,sport,role,runs,balls_faced,dismissals,matches,catches\nRaw Opener,cricket,Opener,480,320,12,14,6\n'
    res=client.post('/api/players/import-raw',files={'file':('raw.csv',text,'text/csv')})
    assert res.status_code==200
    p=next(p for p in client.get('/api/players?sport=cricket').json()['players'] if p['name']=='Raw Opener')
    assert 'batting' in p['features'] and 'strike' in p['features']
    assert 'consistency' not in p['features']


def test_raw_football_import(client):
    text='name,sport,role,minutes_played,goals,passes_attempted,passes_completed,tackles,interceptions,dribbles_completed\nRaw Midfielder,football,Midfielder,1800,4,1120,985,41,27,34\n'
    res=client.post('/api/players/import-raw',files={'file':('raw.csv',text,'text/csv')})
    assert res.status_code==200
    p=next(p for p in client.get('/api/players?sport=football').json()['players'] if p['name']=='Raw Midfielder')
    assert 'passing' in p['features'] and 'defending' in p['features']
    assert 'vision' not in p['features']


def test_cricket_demo_sample(client):
    result=client.post('/api/videos/sample')
    assert result.status_code==200, result.text
    row=result.json()
    assert row['synthetic_fixture'] is True
    assert row['frames']>5 and row['tracks']==1
    assert row['detections']==row['frames']
    assert row['evidence'] == {
        'frames_with_detection': row['frames'],
        'longest_track_frames': row['frames'],
    }
    assert 250 < row['marker_path_px'] < 300
    assert client.get(row['preview']).status_code==200
    assert client.get(row['output']).status_code==200


def test_upload_real_processing(client):
    from app.db import BASE
    payload=(BASE/'web/assets/pitch_fixture.mp4').read_bytes()
    res=client.post('/api/videos/analyze',files={'file':('authorized_example.mp4',payload,'video/mp4')})
    assert res.status_code==200, res.text
    result=res.json()
    assert result['frames']>0 and result['synthetic_fixture'] is False
    assert result['marker_path_px'] is None
    assert result['detector'] != 'Controlled red-marker tracking (synthetic sample)'
    evidence = result['evidence']
    assert 0 <= evidence['longest_track_frames'] <= evidence['frames_with_detection'] <= result['frames']
    assert evidence['frames_with_detection'] <= result['detections']


def test_track_continuity_does_not_count_gaps_or_other_people():
    from app.video import CentroidTracker

    tracker = CentroidTracker()
    boxes = [(0, 0, 20, 20), (100, 100, 120, 120)]
    tracker.update(boxes, 0, max_jump=20)
    tracker.update(boxes, 1, max_jump=20)
    tracker.update([], 2, max_jump=20)
    tracker.update(boxes, 3, max_jump=20)
    assert tracker.longest_streak == 2
    assert sorted(tracker.observations.values()) == [3, 3]


def test_invalid_video(client):
    res=client.post('/api/videos/analyze',files={'file':('broken.mp4',b'not a video','video/mp4')})
    assert res.status_code==422


def test_configured_yolo_path_uses_bytetrack_ids(client, tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    import numpy as np
    from app.db import BASE

    calls = []

    class Tensor:
        def __init__(self, values):
            self.values = np.asarray(values)

        def cpu(self):
            return self

        def numpy(self):
            return self.values

        def tolist(self):
            return self.values.tolist()

    class Detector:
        def __init__(self, weights):
            assert str(weights).endswith("configured-test.pt")

        def track(self, frame, **options):
            calls.append(options)
            return [SimpleNamespace(boxes=SimpleNamespace(
                xyxy=Tensor([[10, 40, 60, 110]]), id=Tensor([42])
            ))]

    weights = tmp_path / "configured-test.pt"
    weights.touch()
    monkeypatch.setitem(sys.modules,"ultralytics",SimpleNamespace(YOLO=Detector))
    monkeypatch.setenv("VIXISU_YOLO_WEIGHTS", str(weights))
    payload = (BASE / "web" / "assets" / "pitch_fixture.mp4").read_bytes()
    response = client.post("/api/videos/analyze",files={"file":("stub.mp4",payload,"video/mp4")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert calls and all(call["tracker"] == "bytetrack.yaml" for call in calls)
    assert result["tracks"] == 1 and result["evidence"]["longest_track_frames"] == result["frames"]
