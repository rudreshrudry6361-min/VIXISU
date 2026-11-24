"""Bounded cricket video analysis with optional YOLO, explicit CPU fallback and a controlled fixture."""
import json
import math
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from .db import BASE, connect

UPLOADS = BASE / 'uploads'
OUTPUTS = BASE / 'outputs'
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class CentroidTracker:
    """Short-lived visual tracks, not verified identity. Greedy gated centroid matching."""
    def __init__(self):
        self.active = {}
        self.next_id = 1
        self.paths = {}
        self.observations = {}
        self.longest_streak = 0

    def update(self, boxes, frame_no, max_jump):
        centers = [((x1+x2)/2, (y1+y2)/2) for x1,y1,x2,y2 in boxes]
        pairs = sorted((math.dist(c,old[0]),i,k) for i,c in enumerate(centers) for k,old in self.active.items() if frame_no-old[1]<=2)
        matches = {}; used = set()
        for d,i,k in pairs:
            if d<=max_jump and i not in matches and k not in used:
                matches[i]=k; used.add(k)
        for i in range(len(centers)):
            if i not in matches:
                matches[i]=self.next_id; self.next_id+=1
        tracks = [matches[i] for i in range(len(boxes))]
        self.observe(centers, tracks, frame_no)
        return tracks

    def observe(self, centers, tracks, frame_no):
        for c, k in zip(centers, tracks):
            if k is None:
                continue
            old=self.active.get(k)
            streak = 1
            if old is not None and old[1]==frame_no-1:
                self.paths[k]=self.paths.get(k,0)+math.dist(c,old[0])
                streak = old[2] + 1
            self.longest_streak = max(self.longest_streak, streak)
            self.active[k]=(c,frame_no,streak)
            self.observations[k]=self.observations.get(k,0)+1
        self.active={k:v for k,v in self.active.items() if frame_no-v[1]<=2}


def process_video(source: Path, original_name: str, *, fixture=False):
    try:
        import cv2
    except ImportError as e:
        raise RuntimeError('OpenCV is not installed; install video dependencies') from e
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        cap.release()
        raise ValueError('This video cannot be decoded by OpenCV')
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    known_fps = math.isfinite(source_fps) and 0 < source_fps <= 240
    fps = source_fps if known_fps else 24
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    count = int(frame_count) if math.isfinite(frame_count) and frame_count > 0 else 0
    max_source_frames = min(count, max(1, int(fps * 15))) if count>0 else max(1, int(fps * 15))
    stride = max(1, round(fps / 5))
    job = uuid.uuid4().hex[:12]
    detector = 'Controlled red-marker tracking (synthetic sample)' if fixture else 'OpenCV HOG person detector (CPU fallback)'
    model = None
    yolo_weights = os.environ.get('VIXISU_YOLO_WEIGHTS') or os.environ.get('ATHLON_YOLO_WEIGHTS')
    if not fixture and yolo_weights and Path(yolo_weights).is_file():
        try:
            from ultralytics import YOLO
            model = YOLO(yolo_weights)
            detector = 'YOLO person detection with ByteTrack'
        except Exception:
            model = None
    hog = None
    if not fixture and model is None:
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    writer = None
    out_path = OUTPUTS / f'{job}.mp4'
    preview_path = OUTPUTS / f'{job}.jpg'
    frames_processed = total_detections = idx = 0
    frames_with_detection = 0
    tracker = CentroidTracker()
    trail = []
    decoded = False
    try:
        while frames_processed < 100 and idx < max_source_frames:
            ok, frame = cap.read()
            if not ok: break
            idx+=1
            if (idx-1) % stride: continue
            h,w=frame.shape[:2]
            if w>720: frame=cv2.resize(frame,(720,round(h*720/w)))
            tracked_ids = None
            if fixture:
                hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
                mask=cv2.inRange(hsv,(0,130,140),(10,255,255)) | cv2.inRange(hsv,(170,130,140),(179,255,255))
                contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                boxes=[]
                if contours:
                    c=max(contours,key=cv2.contourArea)
                    if cv2.contourArea(c)>20:
                        x,y,w,h=cv2.boundingRect(c);boxes=[(x,y,x+w,y+h)]
            elif model is not None:
                try:
                    pred = model.track(frame, persist=True, tracker='bytetrack.yaml', classes=[0],
                                       conf=.25, verbose=False)[0]
                    boxes = [tuple(map(int,b)) for b in pred.boxes.xyxy.cpu().numpy()]
                    ids = pred.boxes.id
                    tracked_ids = [int(value) for value in ids.cpu().tolist()] if ids is not None else [None] * len(boxes)
                except Exception as error:
                    raise RuntimeError('Configured YOLO/ByteTrack could not analyze this clip. Check the optional dependencies and weights.') from error
            else:
                rects,_=hog.detectMultiScale(frame,winStride=(8,8),padding=(8,8),scale=1.08) if min(frame.shape[:2])>=128 else ([],[])
                boxes=[(int(x),int(y),int(x+w),int(y+h)) for x,y,w,h in rects]
            total_detections+=len(boxes)
            frames_with_detection += bool(boxes)
            if tracked_ids is None:
                tracks=tracker.update(boxes,frames_processed,max_jump=max(frame.shape[:2])*.14)
            else:
                tracks = tracked_ids
                tracker.observe([((x1+x2)/2, (y1+y2)/2) for x1,y1,x2,y2 in boxes], tracks, frames_processed)
            for k,(x1,y1,x2,y2) in zip(tracks,boxes):
                color=(55,230,255) if fixture else (126,245,184)
                cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
                label = f'{"MARKER" if fixture else "TRACK"} {k:02}' if k is not None else 'PERSON'
                cv2.putText(frame,label,(x1,max(42,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.47,color,1,cv2.LINE_AA)
                if fixture: trail.append(((x1+x2)//2,(y1+y2)//2))
            if fixture and len(trail)>1:
                for a,b in zip(trail,trail[1:]):cv2.line(frame,a,b,(0,235,255),2,cv2.LINE_AA)
            cv2.rectangle(frame,(0,0),(frame.shape[1],32),(22,38,26),-1)
            cv2.putText(frame,f'VIXISU / {"SYNTHETIC TRACKING TEST" if fixture else "VISION LAB"}  |  FRAME {frames_processed+1}',(12,22),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1,cv2.LINE_AA)
            if writer is None:
                hh,ww=frame.shape[:2]
                writer=cv2.VideoWriter(str(out_path),cv2.VideoWriter_fourcc(*'mp4v'),fps/stride,(ww,hh))
                if not writer.isOpened():raise RuntimeError('Could not create annotated video file')
            writer.write(frame)
            cv2.imwrite(str(preview_path),frame)
            frames_processed+=1
        decoded = frames_processed > 0
    finally:
        cap.release()
        if writer is not None:writer.release()
        if not decoded:
            out_path.unlink(missing_ok=True)
            preview_path.unlink(missing_ok=True)
    if frames_processed==0:raise ValueError('No readable video frames were found')
    # H.264 when a local FFmpeg executable is available; image preview always works.
    browser_video=False
    if shutil.which('ffmpeg'):
        converted=OUTPUTS/f'{job}_browser.mp4'
        try:
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(out_path),'-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(converted)],check=True,timeout=30,capture_output=True)
            if converted.exists() and converted.stat().st_size>0:
                converted.replace(out_path);browser_video=True
        except (OSError,subprocess.SubprocessError):converted.unlink(missing_ok=True)
    stable_tracks=sum(n>=2 for n in tracker.observations.values())
    max_path=round(max(tracker.paths.values(),default=0),1)
    note=('Synthetic fixture only: follows the red marker using actual color segmentation and centroid tracking. Pixel distance is measured in resized frames, not real-world distance or athlete performance.' if fixture else 'Frame-level person detections and approximate centroid tracks; not verified player identities, physical speed or skill scores. Camera motion and missed detections can invalidate movement estimates. No physical measurements are inferred.')
    analysis = {
        'synthetic_fixture': fixture,
        'source_duration_s': round(count / fps, 3) if known_fps and count > 0 else None,
        'sample_duration_s': round(frames_processed * stride / fps, 2),
        'browser_video': browser_video,
        'evidence': {'frames_with_detection': frames_with_detection,
                     'longest_track_frames': tracker.longest_streak},
    }
    with connect() as db:
        db.execute('''INSERT INTO video_jobs(id,filename,detector,status,frames,detections,preview,output,note,analysis)
          VALUES(?,?,?,?,?,?,?,?,?,?)''', (job,original_name,detector,'complete',frames_processed,total_detections,
          f'/outputs/{job}.jpg',f'/outputs/{job}.mp4',note,json.dumps(analysis)))
    return {'id':job,'filename':original_name,'detector':detector,'status':'complete','frames':frames_processed,
            'detections':total_detections,'tracks':stable_tracks,'marker_path_px':max_path if fixture else None,
            'preview':f'/outputs/{job}.jpg','output':f'/outputs/{job}.mp4','note':note, **analysis}
