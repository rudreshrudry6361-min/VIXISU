# VIXISU workspace upgrade report

```yaml
implementation_report:
  status: Verified cricket-first upgrade of the existing local workspace.
  completed_features:
    - Profile creation, editing, duplicate checks, archive, and restore.
    - Format-scoped local cricket scorecards with raw counts and uncapped rates.
    - Cricsheet coverage of 13,782 rostered players in 23,241 matches.
    - Highest innings score, boundary-run share, and dot-ball rates from the archive.
    - Attributed HTTPS photos and video links, including photographer credits for the three curated player portraits.
    - Clip tracking evidence, timestamped human review, and saved review history.
    - Versioned talent vector with measurement source and missing values.
    - Coverage-adjusted Team Fit with individual score contributions.
  modified_files:
    - app/main.py, app/db.py, app/cricket.py, app/intelligence.py, and app/video.py
    - web/index.html and web/assets/app.js, cricket-scout.js, video-assessment.js, and styles.css
    - scripts/build_cricket_evidence.py, data/cricket_evidence.db, tests, README.md, and deployment configuration
  new_files:
    - app/access.py, app/cricket_stats.py, app/profiles.py, and app/scouting_query.py
    - web/assets/workspace-profiles.js and tests/test_workspace_profiles.py
  database_migrations:
    - Added nullable profile archive and modification timestamps and video analysis metadata.
    - Added linked profile metadata, scorecard, media, and clip review records.
    - Preserved the application database and rebuilt the separate public cricket source snapshot.
  api_changes:
    - Added profile PATCH, soft archive, archive list, and restore.
    - Added profile statistics, media, video review, and talent vector endpoints.
    - Added scouting query and non-persistent squad simulation.
    - Protected workspace mutations and private analysis media with local-owner or token authorization.
  computer_vision_capabilities:
    - Bounded OpenCV video sampling and CPU person detection.
    - Optional YOLO person detection with ByteTrack IDs when configured.
    - Detection coverage, track continuity, and annotated playback.
    - Cricket drill scores from human-marked outcomes with at least five attempts.
  implemented_innovations:
    - Cricket Copilot with supported language patterns grounded in selected Cricsheet filters.
    - Before-and-after squad simulation with evidence coverage and recommendation changes.
    - Printable player scouting report and existing Decision Lab brief.
  tests_executed:
    - Pytest, JavaScript syntax checks, Python compilation, and SQLite integrity checks.
    - Chromium mobile workflow for profiles, scorecards, media, video review, ranking, and export.
    - Docker smoke check for startup, cricket coverage, talent vector, and owner access.
  test_results: "33 pytest tests passed. Chromium and Docker checks passed."
  build_status: "Docker image built from the same requirements using downloaded wheels. Direct PyPI access from the build container failed its certificate check."
  application_url:
    workspace: "Port 8768, routes /home, /scout, and /vision."
    local_default: "http://127.0.0.1:8000/home after starting the downloaded project."
  known_limitations:
    - ByteTrack wiring was tested with a stub. Licensed weights and a labeled evaluation set are needed to validate actual tracking accuracy.
    - Cricket technique, physical speed, and sport actions require validated models or calibrated evidence.
    - The user-facing scouting workspace focuses on cricket. Advanced football analysis, multi-user accounts, and public hosting remain outside this release.
    - The Copilot handles documented query patterns and uses the selected cohort.
    - The report exports printable HTML for browser PDF export.
  remaining_setup_steps:
    - Use the existing Windows launcher or install Python requirements and run npm start.
    - For a private non-loopback preview or Docker, configure VIXISU_OWNER_TOKEN and use the app unlock prompt.
    - To enable the optional detector, install its dependencies and supply compatible licensed weights via VIXISU_YOLO_WEIGHTS.
  recommended_next_phase:
    - Validate automated cricket action detection and tracking on authorized clips.
    - Add user and scout accounts, consent management, and a full model-evaluation workflow before public deployment.
```
