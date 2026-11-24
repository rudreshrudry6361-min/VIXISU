# Backend schema and permissions

These are target boundaries to map onto the existing schema after inspecting its models and migrations.

| Data boundary | Records and relationships |
| --- | --- |
| Identity | Users and roles, public player identities, source-specific IDs, and claimed profiles |
| Cricket evidence | Competitions, seasons, match records and per-player match counts with a stable source match ID |
| Scouting | UTV snapshots linked to cohort and source version, shortlists, owned squads, and role requirements |
| Analysis | Report and ranking snapshots linked to candidate cohort and versioned weights |
| Video | Owner, authorization and retention data, job state, detector output and deletable artifacts |
| AI | Optional conversation records and data-source references used by signed-in users |

Match-player evidence uses the pair of source match and source player IDs. Keep event, season, match type, team type, date, gender category and recorded team at match-level granularity. Aggregate rates from their raw counts using the same filters as the discovery and ranking endpoints.

| Interface | Purpose |
| --- | --- |
| `GET /api/players`, `GET /api/players/{id}` | Paginated discovery and evidence-backed profiles |
| `POST /api/players/import` | Validate and import authorized evidence |
| `POST /api/teams`, `POST /api/teams/{id}/requirements` | Manage owned squads and requirements |
| `POST /api/recommendations`, `POST /api/decision-lab` | Rank and explain candidates using a common cohort |
| `POST /api/videos/upload`, `POST /api/videos/analyze`, `GET /api/videos/{id}/result` | Authorize, enqueue and retrieve recorded analysis |
| `POST /api/assistant/chat`, `/ws/live-analysis` | Grounded assistant queries and authorized progress |

Apply ownership checks to profile claims, imports, teams, reports, videos and team chat data. Enforce restrictions server-side. Use password hashing or an established identity provider, request validation, size limits and credential storage outside the source repository. MCP tools invoke authorized services rather than accessing storage directly.
