# VIXISU | 01 — Product Requirements Document

Version 1.0 • 24 November 2026 • Approved user requirements; proposed engineering defaults • Owner: both developers

## 1. Product identity and mission

**Name:** VIXISU. **Tagline:** Discover potential. Understand performance. Build better teams. **Product:** AI Automated Talent Scouting & Team-Fit Intelligence System. **Objective:** an advanced college project with a working, demonstrable web prototype, not a commercial recruitment product. Two developers, four to six weeks, zero mandatory paid services. Initial sports: cricket (T20) and football (association football). Design for future physical sports and esports without implementing them now.

Traditional scouting relies on limited observation, fragmented statistics and subjective decisions. A high-scoring individual is not necessarily the best addition to a specific roster. VIXISU brings together sourced statistics, consented video observations and team requirements to support human scouting decisions. Its differentiator is a sport-aware Universal Talent Vector (UTV) and explainable team-fit ranking that changes with the team's needs. Video and statistics are complementary evidence, not interchangeable measurements. No claim of professional predictive validity or autonomous recruitment.

## 2. Personas and jobs to be done

| Persona | Need | Outcome |
|---|---|---|
| Player | Present authorized performance records and clips; understand what evidence is missing | Manage own profile and choose whether to share it with a scout |
| Scout | Discover candidates, compare comparable roles, inspect evidence | Shortlist relevant players with transparent reasons |
| Team manager (scout account) | Fill a role and address roster skill gaps | Save roster, set skill priorities, rank eligible candidates |
| Demo administrator | Maintain licensed sample data and safe demo access | Seed/reset fictional profiles and inspect job health |
| Guest | Understand the product without signing up | Explore public landing and read-only fictional demo |

## 3. Scope and priority

P0 = required by end of week 4 (usable core); P1 = required target by week 6, subject to explicit feasibility gates; P2 = stretch/future. IDs are stable across the six documents. Do not silently substitute a mock feature for a required one.

| ID | Priority | Feature and acceptance criterion |
|---|---|---|
| F01 | P0 | Signup/login/logout; player and scout roles; owner/grant-based access. Unauthorized cross-account access denied. |
| F02 | P0 | Browse/search/filter players by sport, role, competition and evidence coverage; paginated results; private profiles never leak. |
| F03 | P0 | Player creates/edits own profile; scout manages own authorized profiles; share/revoke consent; sources and sample flags visible. |
| F04 | P0 | CSV upload preview, validation, row errors and commit; import both sports; one reproducible licensed public dataset subset per sport, or documented blocker and clearly fictional fixture. |
| F05 | P0 | Generate versioned UTV from supported metrics, preserve raw units, denominators, reference cohort and missingness. |
| F06 | P0 | Create team, select existing roster, configure role and weights, rank eligible same-sport players, explain components and exclusions; changing requirements changes ranking on controlled fixtures. |
| F07 | P0 | Compare 2–3 same-sport profiles, with compatible reference groups or explicit non-comparability; shortlist candidates. |
| F08 | P0 | Upload short authorized clip; asynchronous YOLO detection and ByteTrack tracking; show model metadata, annotated preview, progress, failure and retry. If weights unavailable, show unavailable status, not fake detections. |
| F09 | P1 | Live webcam and authorized live stream via browser frame source; start/stop, bounded sessions, tracking overlays, dropped-frame counters and measured latency. Stream playback requires source permission and browser compatibility. |
| F10 | P1 | Movement metrics: image-plane displacement and track duration with quality checks; metric distance/speed only after validated fixed-camera calibration; show unavailable when invalid. |
| F11 | P1 | Built-in assistant using approved read-only tools, evidence references and optional local/hosted LLM; deterministic no-LLM report fallback clearly labeled. |
| F12 | P1 | MCP server exposes authorized read-only scouting tools; test with MCP Inspector or compatible client. No unrestricted DB/file access. |
| F13 | P0 | Premium light editorial landing and responsive accessible workspace; real functional controls, not decorative buttons. |
| F14 | P1 | Selective 3D landing visual and reduced-motion/static alternative; do not block dashboard or core flows. |
| F15 | P1 | Local Windows and Docker setup; hosted demo with fictional or licensed nonpersonal data only after security checks. |
| F16 | P2 | Advanced action recognition, multi-camera fusion, trained recruitment prediction, automatic identity recognition, real-time full-match broadcast ingestion, additional sports/esports adapters, multilingual assistant, production scaling. |

## 4. Key user stories and product behavior

- As a player, I can create a profile, upload statistics or consented clips, review source quality and revoke access so I control my information.
- As a scout, I can filter eligible candidates, compare performance with denominators and inspect evidence so I can make informed decisions.
- As a manager, I can define a missing role, select a roster, weight relevant skills and receive a reproducible ranking so I can identify complementary talent.
- As a user, I can ask the assistant why a player fits, and receive tool-backed explanations with links to records, or a clear insufficient-evidence response.
- As a demonstrator, I can switch from aggressive opener to consistency-focused batter, or from attacking to defensive football role, and see ranking changes on a known fixture.
- As a user, I can analyze an authorized clip or camera session and distinguish detected people, temporary track IDs and measured movement from actual identity or sport skill.

## 5. Human-centered and responsible product rules

Players are people, not a single score. Present strengths, trade-offs, sample sizes, limitations and evidence rather than labels such as 'bad player'. Never infer identity, health, protected traits, personality, appearance-based talent or future potential from video. Do not score facial features or body shape. No face recognition, biometric identification, covert surveillance, scraping private accounts, automated rejection or contacting players. Obtain rights/consent for uploads and live capture; avoid identifiable youth footage in the demo. Private by default; use fictional data for public demo accounts; public dataset use must satisfy terms. User-uploaded data remains private unless explicitly granted. Revocation applies to media, derived results and assistant access; deletion and retention rules in 05. Human review is required before decisions. No ranking across sports or incompatible cohorts.

## 6. Success criteria and evaluation

These are **targets**, not achieved measurements. Week 1 establishes hardware baseline; report actual outcomes in Week 6.

| Measure | Target / verification |
|---|---|
| Core completion | All P0 acceptance checks pass; no critical security bugs |
| Data | At least 20 eligible records per sport if available, including role diversity; fixture minimum 8 per sport; provenance for every metric |
| Calculations | All hand-calculated metric and ranking fixtures pass; no missing-as-zero errors |
| Ranking | At least 10 predefined team scenarios, expected top candidate or justified tie; compare general ranking vs role-aware ranking |
| Vision | At least 2 authorized short clips per sport; manually annotate a small held-out sample; report precision/recall, ID switches and limitations |
| Live | One webcam and one authorized compatible stream test; measure processed FPS and end-to-end latency, show actual values; degrade gracefully on CPU |
| Usability | 3–5 volunteer evaluators complete import/search/compare/rank tasks; record completion and feedback; no real recruitment decisions |
| Performance | Target p95 list/rank API <1 s on 200 local fixture profiles; record machine and sample size; no promise of GPU-speed inference |
| Accessibility | Keyboard access, visible focus, contrast WCAG 2.2 AA target, reduced motion; 360px mobile layout without unintended overflow |
| Reliability | Restart preserves records; cancellation/failed jobs visible; local offline core demo works |

“10x better” is an aspiration, not a benchmark claim. Compare usability, evidence traceability, ranking responsiveness and design quality against the existing ATHLON baseline, with measured results only.

## 7. Demo deliverable and non-goals

Deliver local web app, source, migrations, tests, sample fixtures, attribution, architecture diagram, report, presentation and backup recording. Hosted deployment is conditional on free capacity and security; do not require payment or expose a development server to the internet. Do not train a custom action model, promise scouting accuracy, build mobile native apps, process arbitrary broadcast URLs or implement payments. MVP uses explainable deterministic ranking; LLM is an interface, not the ranking authority. Decisions and dependencies: 02–06.

## Current cricket milestone

The latest project brief prioritizes cricket and its Decision Lab. The current acceptance path is the photographic entrance, real player search, same-cohort comparison, role weighting, squad-gap matching, and an evidence-backed scouting brief. See [the current implementation plan](06_IMPLEMENTATION_PLAN.md) for the sequence and [global cricket coverage](GLOBAL_CRICKET.md) for the evidence conventions.
