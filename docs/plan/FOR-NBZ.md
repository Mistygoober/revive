# For nbz (and nbz's Claude)

Read this first, then GAMEPLAN.md. Give this file to your Claude at the start of every session: "Read docs/plan/FOR-NBZ.md and docs/plan/GAMEPLAN.md before we start."

## What we're building
**Revive** connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app.
- Body signals by time scale: **now** = live heart rate + HRV from the Polar H10; **today** = last night's sleep, Body Battery, stress from your Garmin; **trend** = weeks of baselines.
- Work signals: every prompt to Claude Code is scored (prompt score before Claude replies, outcome score after), plus usage as a whole (breaks, loops, tasks left undone).
- Actions: a silent fix to the prompt, a wrist tap on your Garmin, a voice line, or holding the prompt when someone is looping.

## You own the health side and the face
| Time | Your task | Done when |
| --- | --- | --- |
| 1:45–2:05 | Clone the repo, Claude Code signed in, `body/` stubs returning fake data | You can import `get_body_state()` and it returns the fake dict |
| 2:05–2:35 | `body/polar.py`: H10 reader **without** the artifact filter → do squats → when RMSSD explodes, commit and `git tag hero-bug`; save the squat trace to `fixtures/squats_rr.jsonl`; add `tests/test_rmssd.py` that fails on it | Tag exists, test is red |
| 2:35–3:15 | Artifact filter + RMSSD (60 s), baselines from your 30-day Garmin table, `get_body_state()`, `act/tap()` buzzes your Garmin via ntfy | Test green; squats → `strained`; wrist buzzes |
| 3:15–3:30 | Today's Garmin context (last night's sleep, Body Battery) into body state + a one-line morning note | Body state includes `today` |
| 3:30–4:15 | `act/say()` voice; DEMO DATA badges; start the AI Wrapped card | Voice plays; badges visible |
| 4:15–4:50 | AI Wrapped card + optional insights page (cut first if behind); OBS scene | Card renders from the event log |
| 4:00–4:15 | **Test 1:** first full live-demo run-through (Geisel 522), as the subject | Failure list written |
| 4:50–5:15 | **Test 2 (never cut):** fix the failures; demo + hero shot 3× in a row; failure drills (strap drop → auto-reconnect within 10 s; `REPLAY=1` fallback) | 3 clean passes |
| 5:15–5:50 | Edit the video, burn in captions | MP4 ready |
| 5:50–6:10 | Upload unlisted to YouTube | Link works |
| 6:10–6:45 | **Test 3 (never cut):** 2 timed dress rehearsals at the demo table | 2 clean runs under 2 min |
| Pitch | You present the body side and the live moment; Lucas does the problem, how it works and the numbers | |

Lucas owns the Claude side (hooks, grader, coach, server) **and the judge view**. You both share the walkthrough, the 3:30 gate, the backup video, the hero shot and the demos.

## The contract (don't change without telling Lucas)
`get_body_state()` returns:
```json
{"ts": "...", "hr": 96, "rmssd": 22.4, "hr_base": 68, "rmssd_base": 41.0,
 "strain": "calm | elevated | strained", "source": "h10 | garmin | replay",
 "today": {"sleep_h": 5.4, "sleep_score": 61, "body_battery": 38, "stress": 44}}
```
- `strained` = heart rate ≥ 20 above baseline **or** RMSSD < 60% of baseline, held 60 s.
- **Clean the beat-to-beat (RR) data first:** drop RR < 300 ms or > 2,000 ms and any RR more than 20% from the median of the last 10 beats; report `rmssd: null` when fewer than 20 clean beats remain. (Squats caused fake 2–5 s intervals in our 11:30 test.)
- Every event goes to `data/events.jsonl`, one JSON per line with `ts`, `who`, `kind` (`body` every 5 s from you). Format in GAMEPLAN §3.
- `act/tap(text)` (≤ 5 words) and `act/say(text)` (one sentence) return within 1 s and never throw.
- Your folders: `body/`, `act/`, and in `web/` the AI Wrapped card, insights page and badges. Work on branch `nbz`; Lucas merges.

## Checking your work with Claude
Ask your Claude things like:
- "Does `body/` match the contract in docs/plan/FOR-NBZ.md exactly? List any mismatch."
- "Run the RMSSD test and the squat fixture. Is the artifact filter doing what the contract says?"
- "Am I on schedule? It's [time]. Compare with my table in FOR-NBZ.md and tell me what to cut."
- "Before I commit: does this touch anything outside my folders?"

## Rules
- No product code before 1:45. Keys only in `.env`, never in code or chat.
- Your raw Garmin data stays outside the repo (`../data-private/`); commit aggregates only.
- Seeded demo data is fine, but always badged DEMO DATA.
- Never fake a sensor, a number or a claim. If a take fails, redo it.
