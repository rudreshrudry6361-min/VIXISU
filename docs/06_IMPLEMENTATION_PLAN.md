# Implementation plan and acceptance

| Phase | Work | Acceptance |
| --- | --- | --- |
| 1. Baseline and data | Recover original repository, read its status notes, inventory implemented APIs and execute the existing tests. Validate the full archive in a separate data store. | Test results and source coverage are reproducible, and the source database is preserved. |
| 2. Profiles and interface | Integrate match evidence and cohort filters, improve real player descriptions and deliver the photographic entrance and poster views. | A scout can discover a domestic player, see a source-backed profile and compare candidates in the same format, competition and season. |
| 3. Recorded vision | Verify licensed model and tracker on consented test footage and validate upload, processing and deletion. | Annotated video shows tracked people and pixel-space movement with known limitations. |
| 4. UTV and decisions | Connect evidence to existing UTV, role scoring, roster gaps and Decision Lab. | Role and weight changes produce explainable, reproducible rankings with coverage and margins. |
| 5. Integration | Add authorized account flows, chosen assistant providers and scoped MCP services. | Retrieved statistics match the API and unauthorized account actions are rejected. |
| 6. Demonstration | Run pytest, browser journeys and the deployment checklist. Package a documented local demo. | A complete scouting journey succeeds with realistic data and a published limitations list. |

Publication of account or footage features depends on verified authorization and retention controls. Football remains a separate sport adapter after the cricket workflow is demonstrable.

## Baseline available in this handoff

The supplied demo ZIP includes FastAPI, SQLite, configurable Team Fit and basic recorded video processing. The real-data Scouting Room and contextual Decision Lab build on that prototype. The previously hosted archive is a standalone preview. See [project status](PROJECT_STATUS.md) for open milestones.
