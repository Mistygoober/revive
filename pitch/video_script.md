# Video script (90 s)

Framing (decided 3:50 PM): lead with the work going wrong. The body is the *why* and the *when*, not the opener.
One-liner: **Revive connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app.**

Every number below comes from a file in the repo (sources at the bottom). Anything marked [__] is filled from the take or from `data/events.jsonl` after recording; leave it blank rather than guess.

## Shot list
| Seconds | Picture | Words on screen | Voice-over | Live / replayed |
| --- | --- | --- | --- | --- |
| 0–5 | Tight on Noam's laptop: `hrv is broken fix it` is typed and sent. Cut to the phone close-up: the Garmin buzzes on Noam's wrist. | `hrv is broken fix it` → "Slow down: context added" | (none, just the buzz) | Cut from the hero take (0:22–0:55) |
| 5–12 | Title card. | **Revive** · "Your body knows you're about to waste an hour with AI. Revive taps your wrist first." | "Revive connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app." | Card |
| 12–22 | Noam at the laptop, strap visible, Garmin on the wrist. Over it, four words appear one by one. | Vague prompts · Loops · Drifting off task · No breaks | "Working with AI all day, your prompts get vaguer, you loop on the same error, you drift, you skip breaks. From the inside you can't tell. Your heart rate and HRV can: Revive compares them to your own baseline from 19 days of Garmin data." | Live footage |
| 22–55 | **Hero shot: one continuous take, no cuts.** Left: Noam's screen. Right: the judge view. Phone close-up of the wrist as a corner inset. Test runs red (RMSSD 99 ms unfiltered vs 17 ms filtered) → Noam types `hrv is broken fix it` → judge view: score [__]/10, missing context + done, strained → WRIST TAP + context added → wrist buzzes → Claude edits `body/rmssd.py` → test reruns green. | "A real bug we hit at 11:30, replayed from git" · score [__]/10 · "strained: HR +[__] bpm" · "context added: the failing test" | "It reads the strap… grades the prompt before Claude sees it… it's vague and Noam is strained, so it taps the wrist and adds the failing test Claude needs. Claude fixes it first try." | Bug replayed from git tag `hero-red` (main without the RMSSD filter); squats and the lazy prompt are staged; strap, grade, tap and fix are live |
| 55–60 | Noam opens YouTube in the middle of a work block. The wrist buzzes. | "Back to task, 45m left" · small label "demo timing: 20 s, normally 90 s" | "Drift off to YouTube mid-block, and it taps you back." | Live, with demo thresholds (`focus/watch.py --demo`) |
| 60–72 | Proof slide, two numbers. | **1.42× more turns to done** for the bottom third of prompt scores vs. the top third (n = 60 vs. 48, p = 0.034); achieved 45% vs. 73% · **Grader agrees with an expert on 7 of 10 prompts** (n = 10) · small print: "One person's past prompts, one week. Associated with, not caused by." | "We checked the grader against a week of Lucas's real prompts: low-scored ones took 1.42 times as many turns to finish. It agrees with an expert 7 times out of 10." | Real (history + calibration files) |
| 72–80 | The how-it-works diagram from the README, then the judge view's decision log scrolling. | "Built today, 1:45–6:30 PM" · "Live: strap, hooks, grader, wrist tap. Replayed: the bug, from git." | "Built today, while wearing it. Everything you saw on the right is behind the scenes. Noam never opened anything." | Diagram; log is live |
| 80–90 | The AI Wrapped card for today (`/web/wrapped/?real=1`), then the end card. | Wrapped card · **Revive** · the one-liner · "Heavy AI users, ~$12/month · one-line Claude Code plugin" · github.com/Mistygoober/revive · Lucas & Noam | "Heavy AI users pay about twelve dollars a month. It spreads as a one-line Claude Code plugin and a Wrapped card you share." | Real (today's events, demo events excluded) |

**If the loop hold lands before 5:15:** swap it into 55–60 instead of the focus moment only if it's more visual; otherwise leave it out. Don't add a sixth beat.

**Rules:** the hero shot is one take with no cuts inside it. If Claude doesn't fix it on the first try, redo the take; never edit it to look like it did. Every number shown is one we measured. Captions burned in. 90 s max: cut content, don't speed it up.

## Recording plan (5:00–5:30, Geisel 1041; freeze tag `demo-final` at 5:15)
**Devices**
- **Lucas's laptop:** OBS records the judge view full-screen (`/web/judge/`), with the replay buffer on a hotkey.
- **Noam's laptop:** records its own screen with Cmd+Shift+5 ("Record Entire Screen", show mouse clicks on). Claude Code open in the repo, a fresh session, font size up.
- **Lucas's phone:** films the wrist handheld, close and steady, for the buzz.
- Start all three, then Noam claps once on camera: that's the sync point for the edit.

**Before each take**
1. `git fetch origin --tags && git switch -c take-N hero-red` on Noam's laptop. Focus watcher off (tab 3). `rm -f data/coach_state.json`.
2. Fresh `claude` session in `~/revive`. Inside it, run `! uv run pytest tests/test_rmssd.py -q`: red (2 squat tests). Running it with `!` inside Claude Code is what lets the silent fix attach the failure.
3. Server running; `scripts/demo_check` green.
4. Strap wet and on. Noam's phone **locked** and on the hotspot (the wrist only buzzes when the phone is locked). Laptop on Do Not Disturb except ntfy.
5. Noam does 20 squats off camera until the judge view shows STRAINED, then types the prompt within 30 s (strain fades in ~90 s).
6. After the take: `git switch main`. Full checklist: `pitch/runbook.md` §1–2.

**Takes:** 2–3 of the hero shot, back to back. Then one take of the focus moment (start `uv run python -m focus.watch --minutes 45 --demo` fresh so it reads 45m, open YouTube, wait ~20 s for the buzz).

**Edit (Noam, 5:30–5:50):** split screen left/right, wrist inset, captions burned in, total ≤ 90 s. Fill every [__] from the take or the event log.

## Sources
- 1.42×, n = 60 vs. 48, p = 0.034; 45% vs. 73%: `history/results.json` → `validity_bottom_vs_top_tertile`
- 7 of 10 agree, n = 10: `grader/calibration/results_set1.json` (summary in DEMO_NOTES.md)
- 19 days of Garmin data: `body/baselines_nbz.json` (`n_days: 19`)
- RMSSD 99 ms unfiltered vs 17 ms filtered on today's real squat recording: `fixtures/squats_rr.jsonl`, `tests/test_rmssd.py::test_real_squat_fixture_hero_bug` (commit `0753302`). The bug was first hit at 11:30 (GAMEPLAN §7).
- Tap texts "Slow down: context added", "Back to task, Nm left": `capture/hook.py`, `focus/watch.py`
- Focus thresholds 90 s (20 s in demo): `focus/watch.py`
- $12/month: `docs/plan/GAMEPLAN.md` §1
