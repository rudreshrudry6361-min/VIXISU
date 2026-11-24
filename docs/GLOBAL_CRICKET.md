# Global cricket evidence

Open [the photographic entrance](http://127.0.0.1:8000/home) or go straight to [the Scouting Room](http://127.0.0.1:8000/scout) after starting the local app. The original dashboard remains at the root URL.

## Dataset

The verified snapshot uses `data/cricket_evidence.db`, a read-only evidence store with 23,241 matches, 13,782 rostered players, and 515,300 match-player rows. Match start dates range from 19 December 2001 to 3 November 2026. It includes domestic, franchise and international cricket for men and women. The app reports coverage from the data. Competition coverage and season availability vary.

The evidence keeps the Cricsheet ID, match date, competition, season, format, team type and recorded team. Source names and match identifiers come from the archive. Only a small number of featured players have reviewed full-name aliases and licensed photographs.

Contains information from the [Cricsheet database](https://cricsheet.org/downloads/) under the [Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/). The license accompanies the database. The source archive SHA-256 is `13f9f5d5153c36257d9ecf39d7c11a8c5615a5b146150ac5462fb0c0278b9b1b`.

For a fresh GitHub clone or to regenerate the evidence, download the [Cricsheet JSON archive](https://cricsheet.org/downloads/all_json.zip) and choose a new output path.

```sh
python scripts/build_cricket_evidence.py all_json.zip data/cricket_evidence.db
```

If the default database already exists, build to a different path and set `VIXISU_CRICKET_EVIDENCE` to that absolute path. The VIXISU application database continues to store local teams, uploaded records, and video jobs. The archive store is independent.

## Scouting workflow

1. Open Scouting Room and browse by circuit, gender category, format, competition, and season. Search by player or recorded team.
2. Open a profile to inspect a factual summary, rate denominators, and recent match evidence. Choose a shared cohort to compare up to three players.
3. Choose a named T20 cohort to enable Decision Lab. Use **Try IPL 2024** to start with a known cohort. Select current squad members in the results table if you want a roster-gap adjustment.
4. Choose a role and skill weights. Rank candidates and inspect measured values, normalized features, score contributions, missing evidence, leader margin and one-at-a-time weight changes. Download the scouting brief from the results.

## Measurement and scoring

- Runs, wickets, and rostered appearances reflect covered matches and exclude super overs where applicable. Named substitutes can contribute fielding evidence. Legal balls exclude wides and no-balls. Bowling runs exclude byes, leg byes, and penalties. Catches and stumpings depend on recorded attribution.
- Eligibility uses a minimum of three rostered matches. Openers and middle-order candidates need at least 60 legal balls faced and at least three qualifying batting innings. Opening pair and positions 3–5 are inferred from first batting appearances in the feed. Finishers need at least 24 legal balls in overs 16–20 of full scheduled T20 innings, as well as 60 legal balls faced overall. Bowlers need at least 60 legal balls bowled, and all-rounders need the batting and bowling ball minima.
- Batting average requires three dismissals. Economy is a lower-is-better feature. Features use min–max bounds from eligible players in the selected cohort, and flat or unsupported ranges are unavailable. All-rounder eligibility and role names are scouting heuristics. They are not verified roster positions.
- The existing scoring engine requires 50% of selected metric weight to be observed. Weights are divided by the total requested weight, so missing metrics cannot boost scores. It allocates up to 85 points to weighted skill fit and 15 to role eligibility. A bounded squad-gap bonus can add up to eight points before capping the total at 100. Roster members are excluded from recommendations. Sensitivity reruns with one weight increased by 50%. Rankings are contextual decision support.
- T20 scoring currently includes opening, middle order, finishing, bowling, and all-rounder templates. Dedicated wicketkeeper, pace and spin templates require additional role and style evidence.

Highest score uses individual innings totals. Bowling dot-ball rate uses scoreless legal deliveries. Boundary-run share uses recorded fours and sixes divided by total batter runs. Cricsheet databases built before these fields were introduced still load.
