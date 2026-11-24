# VIXISU | Cricket Demo Edition

AI Automated Talent Scouting & Team-Fit Intelligence System — local, demonstration-ready MVP. Based on the existing ATHLON prototype. The user interface presents cricket only; the underlying football adapter is retained for future expansion. No mandatory paid services or API keys.

## Start (Windows)
1. Extract the ZIP to a normal folder. Do not run the batch file from inside the ZIP.
2. Open `VIXISU_Cricket_Demo` and double-click `start_windows.bat`.
3. The launcher uses an available Python environment or creates a virtual environment and installs requirements. Internet is needed only if missing dependencies must be installed. Keep the terminal open.
4. Open http://127.0.0.1:8000/home in Chrome or Edge (the launcher also attempts to open it).

Manual setup in VS Code / Anaconda Prompt:

```sh
python -m pip install -r requirements.txt
python run.py --open
```

Python 3.11 or 3.12 recommended; tested here on Python 3.13. If the `python` command is unavailable on Windows, use `py` or Anaconda Prompt. If port 8000 is occupied, set `VIXISU_PORT=8001` (PowerShell: `$env:VIXISU_PORT="8001"`) and run `python run.py --open`. The app uses SQLite; the database is created automatically. To reset demo state, stop the server and rename `vixisu.db` to a backup name. Do not remove a database containing data you need.

## Real cricket scouting

A fresh GitHub clone needs a local Cricsheet evidence database for the Scouting Room. Download the [Cricsheet JSON archive](https://cricsheet.org/downloads/all_json.zip) as `all_json.zip` and run:

```sh
python scripts/build_cricket_evidence.py all_json.zip data/cricket_evidence.db
```


The [Scouting Room](http://127.0.0.1:8000/scout) connects the original app to 13,782 real player records across 23,241 matches. Search and compare candidates within a shared competition, season, format, gender category and circuit. Select a named T20 cohort to test custom role priorities and squad gaps in Decision Lab. See [dataset coverage and scoring](docs/GLOBAL_CRICKET.md).

## Workspace players and owner access

Create players in **Data Studio**. On a player profile, use **Edit profile** to manage identity fields and manual normalized scores. Under **Profile records**, add a scorecard by format, competition and season. You can add attributed HTTPS photo or video links that you have permission to use. Vision Lab can save human-reviewed attempts and their annotated clip to the same profile. **Archived profiles** in the Talent Pool restores hidden profiles with their existing records.

The workspace is single-owner. Local writes and analysis media require a loopback connection by default. To use an authenticated private preview, set a strong `VIXISU_OWNER_TOKEN` in the server environment and enter that token when the app prompts. API clients can send a Bearer token. Profile and team metadata use the local SQLite database.

Docker Compose binds to the host loopback and mounts the `data` directory. Set `VIXISU_OWNER_TOKEN` before starting Compose to authorize requests that reach the container from the host.

**Team Fit** shows each weighted score contribution and a squad simulation. **Scouting Room → Scouting copilot** interprets supported questions against the selected Cricsheet cohort and runs the same evidence filters and ranking engine. For example, choose IPL 2024 and ask “Find aggressive T20 openers.”

## Seven-minute demonstration

1. Overview: show the editorial cricket homepage and eight fictional player profiles.
2. Talent Pool: select Opener, search Arjun, open Arjun Rao. Explain the seven normalized cricket signals and radar chart. Seed values are illustrative, not actual player performance measurements.
3. Compare Players: compare Arjun Rao and Kabir Mehta (or another player) and explain that overall ability differs from role suitability.
4. Team Fit: choose **Opener**, click Generate Recommendations. Then choose **Finisher**, click Generate Recommendations. With the clean seed database, the top candidate changes from Arjun Rao to Rehan Malik. Change weights and optionally select existing squad members to demonstrate role matching and roster-gap bonuses. Enter a team name and save it if desired.
5. Vision Lab: click **Analyze Sample Clip**. This processes a synthetic pitch fixture using actual red-marker segmentation and centroid tracking. The marker path is measured in pixels; not a real ball-speed or player-skill measurement. Use an authorized short cricket video for actual person detection/approximate tracking, if available. A 5-second webcam recording option is available on localhost with camera permission; this is not continuous live tracking. Test your webcam on your own machine before presenting.
6. Data Studio: choose Raw aggregated match statistics, upload `sample_data/example_raw_import.csv`, then inspect the imported Sample T20 Opener profile. The statistics are fictional sample input, converted using illustrative reference ranges. For example, 450 runs / 12 dismissals = 37.5 batting average; 450 / 320 balls x 100 = 140.625 strike rate. Missing skills are not fabricated.
7. The System: explain the transparent ranking equation, feature coverage requirement, and future roadmap. FastAPI's interactive API documentation is at http://127.0.0.1:8000/docs.

## Video processing / optional YOLO

After an upload, Vision Lab shows detection coverage and the longest continuous track as percentages of sampled frames. Under **Skill meter → Review attempts and score skills**, pause the original clip at each visible attempt by one player and mark success or miss. Batting contact, bowling target accuracy, and catching success each use five or more reviewed attempts. The score is successes divided by attempts and multiplied by 100. Review marks are timestamped. Select a cricket profile and choose **Save to profile** to keep the attempts and annotated clip in its media library. The original file is previewed from the browser.

The CPU fallback works with standard OpenCV dependencies. It uses HOG person detection and approximate centroid association for uploaded footage. It may miss players, especially at broadcast distances. It is not a calibrated physical speed or cricket-specific action-recognition model. The bundled sample uses a distinct, labeled synthetic-marker tracker and measures pixel path, not real athlete movement.

For actual YOLO person detection, if you already have suitable, licensed weights:

```powershell
python -m pip install -r requirements-optional.txt
$env:VIXISU_YOLO_WEIGHTS="C:\path\to\your\model.pt"
python run.py --open
```

Model weights and Ultralytics are not bundled. They were unavailable in the build environment; the YOLO branch is not verified. The actual detector name appears in the result. The optional model uses class 0 for person detection and ByteTrack for IDs, so use compatible COCO-style weights and the dependencies in `requirements-optional.txt`. Check the applicable Ultralytics and model licensing terms. FFmpeg is optional for browser-compatible H.264 video playback; without it, the preview image and downloadable MP4 output remain available. Input videos are deleted after processing; annotated outputs are retained locally in `outputs`. Use only footage you have permission to analyze and avoid sensitive clips. A local demo is not production-secured; do not expose it to the public Internet with private data.

## Implementation and verification

- FastAPI + SQLite, static responsive JavaScript frontend, OpenCV; no Node build step.
- `app/data.py`: cricket feature definitions, role templates and fictional seeds.
- `app/ingestion.py`: raw cricket aggregate-statistics transformation; missing-value handling.
- `app/intelligence.py`: deterministic weighted role match, 50% minimum coverage, optional bounded roster-gap bonus.
- `app/video.py`: bounded video decoding, HOG/optional YOLO, centroid tracking, controlled marker fixture.
- `web/`: premium light editorial cricket demo, original illustrations.
- `tests/test_app.py`: regression and new video tests. Run `python -m pytest -q` (requires pytest/httpx, listed in requirements). Optional `node --check web/assets/app.js`.
- Tests executed: 17 API/algorithm/video tests passed; offline Chromium DOM harness connected to real FastAPI TestClient passed search, role filter, profile, compare, dynamic ranking, save team, sample tracking, video upload, raw CSV import and mobile navigation. Direct browser-to-local-server navigation was blocked by the execution environment, so full live network/browser test and physical webcam test remain to be performed on your laptop.

## What is deliberately not included for tomorrow

Multi-user authentication and consent sharing, continuous live analysis, calibrated measurements, validated automatic cricket-action ratings, MCP, hosted or local LLM integration, PostgreSQL and public deployment remain future milestones. No claim of professional scouting accuracy. The existing prototype is extended, not rewritten into a React stack. The deadline drove a no-build architecture to reduce setup and failure points.
