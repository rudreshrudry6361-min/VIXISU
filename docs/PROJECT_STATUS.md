# VIXISU | Cricket demonstration status

- Working: cricket-only UI, eight labeled fictional seed profiles, filtering, radar charts, comparison, normalized/aggregated CSV import, manual profiles, team saving, configurable weighted team fit and explanations, local video upload, optional YOLO adapter, HOG fallback, approximate centroid association, synthetic red-marker tracking, five-second webcam capture UI, FastAPI docs.
- Tested: 17 pytest tests; JavaScript syntax; offline Chromium DOM harness with real API bridge. Direct localhost browser navigation and physical webcam/YOLO tests unavailable in build environment.
- Scope decisions: tomorrow's demo prioritizes reliable cricket core; no new public hosting, authentication, LLM/MCP server or calibrated athlete-motion measurement. Football adapter retained internally for future work.
- Data: seeded names and scores and bundled raw statistics are fictional. Synthetic marker clip tests actual tracking logic and must be labeled synthetic.

## Integrated cricket milestone

The Scouting Room uses the verified Cricsheet evidence store for discovery, contextual player comparisons and a T20 Decision Lab. The local prototype also includes the photographic entrance and licensed player posters. See [global cricket coverage and scoring](GLOBAL_CRICKET.md) for conventions and reproduction.

The workspace still uses the original prototype's application stack. Configured licensed YOLO weights, ByteTrack validation, continuous live sources, accounts, assistant providers, MCP, and authenticated hosted deployment remain separate milestones.

## Workspace and scouting upgrade

- The SQLite migration adds profile metadata, archived status, scorecards, authorized media links, and human-reviewed video records. Existing players, teams and video jobs are retained.
- Statistics and normalized scouting scores have separate formulas and provenance. The full Cricsheet snapshot includes highest innings scores and dot-ball evidence.
- Team Fit explains weighted contributions and missing evidence. The simulator compares two transient roster setups. The Copilot uses bounded query parsing and the selected cohort. It uses the existing search, comparison and ranking services.
- Vision Lab uses measured detection and tracking evidence, optional YOLO with ByteTrack, and human review for batting contact, target accuracy, and catches. Real model weights and a reviewed evaluation dataset are needed to validate live YOLO/ByteTrack accuracy. Automatic cricket action detection, calibrated speed, and biomechanical judgments remain unavailable.
- The workspace supports a local single owner or an owner token for protected operations. Multi-user accounts and public deployment remain future work.
