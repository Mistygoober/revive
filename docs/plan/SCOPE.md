# Revive: full scope, big to small

Sat Oct 24, 11:35; updated 12:00 with Lucas's comments. Everything we have to achieve or finish, as one tree. Status as of now. **Owners confirmed by Lucas, Sat 12:10.** L = Lucas, N = nbz, B = both. Diagram version: the "Revive scope" artifact.

**Goal:** win c0mpiled-16 with Revive. That means: submitted by 6:10 PM (deadline 6:30), one real nudge caught on camera, and one honest number.

**Gates (new schedule, Sat 11:35):** 12:45 arrive · 1:00 check-in · 1:15 rules · 1:45 build starts · 3:30 gate · 4:15 backup video · 5:15 freeze · 6:10 submit (deadline 6:30) · 6:45 judging · 7:45 top 5 demos · 8:30 top 3

## 1. Product: Revive works end to end
### 1.1 Body (sensing)
| Item | Status | Owner |
| --- | --- | --- |
| Strap connection tested (H10 → Mac, heart rate + beat-to-beat) | Done 11:30 | L |
| Reader in the repo, logging to `body.jsonl` | To do | N |
| Artifact filter + RMSSD over 60 s | To do | N |
| Baselines from nbz's 30-day Garmin table | To do (needs the table) | N |
| `get_body_state()` + the "strained" rule | To do | N |
| Recorded trace + replay mode (labeled REPLAY) | To do | N |
| Garmin heart-rate broadcast as a backup sensor | Optional | N |
| Today's Garmin numbers (sleep, Body Battery, stress) → coach sensitivity + morning note | To do | N |

### 1.2 Work (the Claude side)
| Item | Status | Owner |
| --- | --- | --- |
| Capture hooks on both laptops | To do | L |
| Grader rubric | Done 11:25 ([grader-rubric.md](grader-rubric.md)) | L |
| Grader: Haiku 5.5, under 3 s, heuristic fallback | To do | L |
| Calibration set (10 prompts, hand-scored) | To do (~2:35) | L |
| Task boundaries, turns to done, tasks left undone | To do | L |
| Outcome score + inferred intent (Stop hook) | To do | L |
| Context layers: session goal, project, user profile | To do | L |
| Loop detector | To do (cut 3rd if behind) | L |

### 1.3 Coach and actions
| Item | Status | Owner |
| --- | --- | --- |
| Coach policy: levels 0–2 + rate limit | To do | L |
| Silent fix: adds the last error + touched files | To do | L |
| Wrist tap: ntfy → nbz's phone → Garmin | To do | N |
| Hold the prompt + a voice line on loops | To do (cut 2nd) | B |
| Usage trigger: long stretch without a break | To do | L |

### 1.4 Screens
| Item | Status | Owner |
| --- | --- | --- |
| Server: event stream, `/body`, serves the pages | To do | L |
| Judge view on the judge screen (Lucas's laptop) | To do | L |
| AI Wrapped card | To do | N |
| Portal: optional insights page | Optional (cut 1st) | N |

### 1.5 Metrics
| Item | Status | Owner |
| --- | --- | --- |
| Metric catalog by time window | Done ([metrics.md](metrics.md)) | L |
| Session + day metrics computed | To do | L |
| Memory split: memory/raw vs memory/insights | To do | L |
| Seeded demo history (labeled DEMO DATA) | To do | L |
| DEMO DATA badges in the views | To do | N |

## 2. Proof: numbers judges trust
| Item | Status | Owner |
| --- | --- | --- |
| Lucas's past prompts copied (stays on the Mac) | Done | L |
| Grader agrees with an expert (calibration set) | To do | L |
| Validity: low scores → more turns, with n | To do | L |
| Today's numbers: nudges, accepted, turns saved | To do | L |
| Body × work pattern from the build day | To do | B |
| Predictions written before 1:45, checked at 5:15 | To do | B |
| "Felt stuck" marks during the day (ground truth) | To do | B |

## 3. Story and submission
| Item | Status | Owner |
| --- | --- | --- |
| Hero-shot scenario | Decided (real H10 bug, replayed from git) | B |
| Hero bug tagged + squat fixture saved (2:05–2:35) | To do | N |
| Backup video (4:15) | To do | B |
| Hero-shot take (5:15): nbz on camera, Lucas filming | To do | B |
| 90-second video: edit + captions | To do | N |
| README + DEMO_NOTES (what's real, what's replayed) | To do | L |
| Submission text, repo public, links tested | To do | L |
| Live table demo (2 min) | To do | B |
| Pitch + hard-question answers (Lucas: problem, how it works, numbers; nbz: body side, live moment) | To do | B |
| "What's next" slide: agents + per-person memory | To do | L |

## 4. Setup (before 1:45)
| Item | Status | Owner |
| --- | --- | --- |
| Console for nbz: $54 balance, team org, invite sent | Done | L |
| nbz's own Luma registration | Done (approved) | N |
| nbz's Claude Code test prompt | Waiting on nbz | N |
| H10 tested | Done | L |
| uv + Python 3.12 | Done for Lucas; nbz to do | B |
| GitHub CLI installed / signed in (`gh auth login`) | Installed; sign-in to do | L |
| OBS downloaded / installed + screen-recording permission | Downloaded; install to do | L |
| Lucas's Claude history copied | Done | L |
| Garmin 30-day table | To do | N |
| ntfy wrist-buzz test on the Garmin | To do | N |
| GitHub username → added to the repo | To do | N |
| 3 predictions written down | To do | B |
| Pack, hotspot test, arrive 12:45 | To do | B |
| Record the rules talk → RUBRIC.md; host questions | To do (1:15) | L |
| Top-5 stage demo ready (7:45) | To do | B |
| 1:45: repo + kit + contract walkthrough | To do | B |

## 5. Rules and admin
| Item | Status | Owner |
| --- | --- | --- |
| No customer or NDA data; aggregates only | Standing rule | B |
| nbz's consent: on camera, first name shown or not | To do | N |
| What's mocked, written in DEMO_NOTES | To do | L |
