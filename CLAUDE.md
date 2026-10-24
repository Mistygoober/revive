# Revive – c0mpiled-16 build, Sat Oct 24, 1:45–6:30 PM Pacific (submit by 6:10)

## Goal
Make the demo script in SPEC.md work end to end, reliably, for a 90-second video. Judges see three things: the submission form, this GitHub repo and the video.

## How to work
- Build only what the demo script needs. Stub or hard-code anything else and list it in DEMO_NOTES.md.
- One step at a time: implement, run the step's check, show me the output, then commit.
- Never refactor working code unless I ask. Ask before adding a dependency or a service.
- If the same fix fails twice, stop, tell me what you tried, and propose a simpler fallback.
- Keep the demo path deterministic: DEMO_MODE=1 replays fixtures/ instead of live calls that can fail.
- Only notify my own devices (NTFY_TOPIC, the Mac's voice). Never message or call anyone else.
- The user never opens an app or dashboard. Interventions are a buzz, a voice or added prompt context. Any UI is the judge view, labeled "behind the scenes".
- Never claim causation. Findings say "associated with" and show n and effect size.

## Secrets and data
- Keys live in .env, which I fill. Never read .env, print keys or hard-code them. Use the names in .env.example.
- nbz's raw exports live in ../data-private/, outside this repo. Never copy raw prompts or health records into the repo, logs or video. Commit aggregates only.
- Only today's hackathon prompts are captured live. Never put prompts or data from anyone's other work in the repo.
- Seeded demo data is allowed but always labeled DEMO DATA in the UI and in DEMO_NOTES.md.

## Commands
- run: `uv run uvicorn server:app --host 0.0.0.0 --port 8000` (judge view at /web/judge/)
- test: TODO
- test: `uv run pytest`
- pre-demo check: `scripts/demo_check` (starts the server if needed, runs one vague prompt + one Stop through the real hook with FAKE_STRAIN=strained, REVIVE_TAP=0; PASS/FAIL per event, then removes its "demo-check" events and restores the tap cooldown). Restart the server after pulling, so the hook gets the fast path (POST /hook).
- tunnel (only if needed): `ngrok http 8000`

## Fixed decisions (don't change)
- Capture: Claude Code hooks (UserPromptSubmit, Stop). UserPromptSubmit can block a prompt or add additionalContext (≤10,000 chars), but can't rewrite it. Its default timeout is 30 s.
- Sensor: Polar H10 over Bluetooth with bleak (heart rate + RR intervals → rolling RMSSD). Fallback: replay of a recorded trace, labeled.
- Grader: Claude Haiku 5.5, rubric in docs/plan/grader-rubric.md. Two scores per turn: prompt score (before the reply) and outcome score + inferred intent (after, from the Stop hook).
- Actions: ntfy push (Garmin wrist tap), the Mac `say` voice, and hook additionalContext or a hold. At most one intervention per 20 min. Triggers: weak prompt + strain, loops, long stretch without a break. Today's Garmin context (sleep, Body Battery) sets how early it steps in.
- Server: Python 3.12 + FastAPI, run with uv. Storage: SQLite.
- Judge view: one HTML page served by the same app, shown full-screen on Lucas's laptop over the phone hotspot (fallback: split-screen on the demo laptop).

## Owners and folders
- **Lucas:** capture/, coach/, history/, server.py, web/judge (judge view), memory/. Merges to main.
- **nbz:** body/, act/, web/wrapped + web/insights + badges, fixtures/. Works on branch `nbz`.
- **Shared:** shared/ (events log + config: change only with both agreeing), pitch/, DEMO_NOTES.md.
Never edit the other person's folders. The contract between the halves is in docs/plan/FOR-NBZ.md and docs/plan/GAMEPLAN.md §3.

## Plan docs
docs/plan/: GAMEPLAN.md (timeline, gates, contract), FOR-NBZ.md, grader-rubric.md, metrics.md, SCOPE.md, prompt-scoring-research.md. Gates: 3:30 gate, 4:15 backup video, 5:15 freeze, 6:10 submit.

## Docs
- docs/*-llms.txt: read the relevant section before writing integration code.
