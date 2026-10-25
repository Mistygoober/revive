# What's real and what's mocked

Final status, Sat Oct 24, end of the event (6:30 PM): after the hero takes, the 5:34 PM predictions check and the 5:41 PM count of today's numbers. The dated sections at the end say when each piece landed. This is the README's "What's real" section and our answer when a judge asks "what's mocked?".

| Piece | Real / replayed / mocked | Note |
| --- | --- | --- |
| Capture hooks | **Real** | Claude Code `UserPromptSubmit` and `Stop` hooks in `.claude/settings.json` run `capture/hook.py` on every prompt and reply. The event log gets metadata only (length, session, project); raw text goes to `memory/raw/`, which is git-ignored. |
| Prompt grader | **Real** | Claude Haiku 5.5 (`claude-haiku-5-5`), one forced-tool call per prompt, hard 5 s cap (`grader/_llm.py`; raised from 3 s after Test 2, where 3 s fell back to the heuristic on the phone hotspot). The hook waits up to 9 s for the server (`capture/hook.py`). On a timeout, API error or missing key it falls back to a keyword heuristic, logged as `source: "heuristic"`. Rubric: `docs/plan/grader-rubric.md`. |
| Outcome grader | **Real** | `grader/outcome_score.py` (Haiku 5.5, same fallback), run from the `Stop` hook by `coach/outcome.py`: each live turn gets an `outcome` event (`scripts/demo_check` checks it). |
| Coach | **Real** | `coach/policy.py`: score ≤ 4 → silent fix (level 0); score ≤ 4 and body strained → silent fix + wrist tap (level 1); at most one tap per 20 min. We deleted the cooldown file before each hero take (`pitch/runbook.md`), so taps during the takes are closer together than 20 min. A poor night (sleep < 6 h or Body Battery < 40) raises the threshold to 5. |
| Silent fix | **Real** | `coach/context.py` reads the session transcript and adds what the grader marked missing as hook `additionalContext` (≤ 1,500 chars): for missing context, the last error from the last two turns (a failed tool call, or a failing command the user ran with `!` inside Claude Code) and recently edited files; for a missing done check, a line asking Claude to run the relevant test and say how it verified the fix. In the 5:21:50 PM take the grader marked done and goal missing, so only that line was added. It can't rewrite the prompt; it adds to it. |
| Wrist tap | **Real** | `act.tap()` (nbz): ntfy push → nbz's phone → Garmin notification. Only taps from nbz's laptop (`REVIVE_WHO=nbz`). Seen on the wrist at 4:10 ("Take 5" from the focus watcher). Today: 13 wrist taps, 5 on a vague prompt while strained and 8 from the focus watcher (`pitch/today_numbers.json`). |
| Judge view | **Real** | `web/judge/` reads the live event log over server-sent events. Labeled "behind the scenes"; the user never opens it. Shows a **DEMO DATA** badge whenever demo events or fake body state are on screen. |
| Body state (heart rate, HRV, strain) | **Real on the demo laptop** | `body/polar.py` (nbz) reads the Polar H10 live (HR + RR every 5 s), `body/rmssd.py` cleans RR and computes RMSSD. With no reading newer than 15 s (e.g. Lucas's laptop, no strap), `get_body_state()` falls back to `FAKE_STRAIN`, labeled `source: "fake"`, and actions on it are logged `demo: true`. |
| Baselines (resting HR 68 bpm live, 69 bpm Garmin; RMSSD 41 ms) | **Real, two HR values** | The live strain label (and the judge view's "base") uses a fixed 68 bpm (`HR_BASE` in `body/polar.py`). The 19-day median from nbz's Garmin exports is 69 bpm (`body/baselines_nbz.json`, aggregates only); wiring it into the live label is a TODO. The exports have no HRV, so the RMSSD baseline is the daytime strap value (41 ms). |
| Today's Garmin context (Body Battery, stress) | **Real (yesterday's export)** | Oct 23: Body Battery high 67, average stress 35. No sleep in the export (null), so the coach uses the normal threshold. |
| Hold + voice (loops) | **Real, unit-tested; never fired live** | `coach/loop.py`: 3+ signals in 15 min (retry prompts, same error twice, frustration, no passing test or commit) and a retry streak → hold the prompt + `act.say()` voice line + tap; 15-min cooldown. Unit-tested (`tests/test_loop.py`). No loop was detected in today's live logs (0 loops, `pitch/predictions_result.json`), so the hold has not run on a real session. |
| Hero bug | **Real bug, replayed from git** | RMSSD without the artifact filter blows up when the wearer moves (Lucas hit it at 11:30). Today's real squat recording (`fixtures/squats_rr.jsonl`, nbz, tag `hero-bug`): 99 ms unfiltered vs 17 ms filtered. Tag `hero-red` = `demo-final` (main at the freeze) with the filter removed from `body/rmssd.py`, so `tests/test_rmssd.py` goes red; the takes start from it and Claude restores the filter. The squats, the planted bug and the scripted lazy prompt are staged and said out loud. |
| Seeded demo events | **DEMO DATA** | `scripts/fake_events.py` replays a scripted 3-minute sequence (calm → squats → strained → tap → solved). Every event carries `demo: true`, and the judge view badges it DEMO DATA. |
| History validity number | **Real** | Lucas's own Claude Code prompts, Oct 17–24, graded by the same grader. Aggregates only in `history/results.json` and `history/SUMMARY.md`; prompt text never left the laptop except for grading. |
| Today's numbers (prompts, nudges, taps, solved) | **Real** | Counted at 5:41 PM from both laptops' event logs (`data/events.jsonl` + `nbz_events.jsonl`), excluding `demo: true` events: 110 prompts, 21 nudges, 13 wrist taps, 10 solved after a nudge. Aggregates and definitions in `pitch/today_numbers.json` (the logs themselves are git-ignored). |

## Known weak spots (the answer to "what breaks first?")
- **Strain fades fast.** After 20 squats nbz stays strained for ~90 s, so the prompt has to be typed right away.
- **Hooks need a session started inside the repo.** A Claude Code session opened before the repo existed never loads them (Test 1, 4:05); always start a fresh `claude` in the repo.
- **Grader latency.** Even the 5 s cap can be tight on a phone hotspot; slow calls fall back to the heuristic score (still logged, marked `heuristic`).
- **The grader has no temperature setting.** The rubric asks for temperature 0, but the SDK call in use doesn't accept it, so the same prompt can score slightly differently on a rerun. The forced tool and anchored rubric keep it stable in practice; we haven't measured run-to-run spread.
- **Scores run low.** Real asks average 2.76/10 and only 3 of 239 scored prompts reached ≥ 7, so the rubric's "good prompt" bucket is nearly empty (see caveats).
- **Context check carries no signal** on past prompts (ρ ≈ 0 with outcomes), likely because the grader never saw Claude's previous reply as text. The done and goal checks carry the signal.
- **Live outcomes are graded by the same model.** 98 live turns got an outcome today (54 achieved, 36 partial, 6 missed, 2 wrong direction; `pitch/today_numbers.json`), all judged by Haiku from the transcript, not by a person.
- **The loop hold never fired live** (0 loops today).
- **Two heart-rate baselines.** The live strain label is computed in `body/polar.py` against a fixed strap baseline (68 bpm, `HR_BASE`); the 19-day Garmin median (69 bpm, `body/baselines_nbz.json`) is what `get_body_state()` reports as the baseline. Wiring the Garmin value into the live classifier is a TODO.
- **Most of today's taps came from the focus watcher on demo timing.** 8 of the 13 wrist taps were focus-watcher taps at 20 s / 2 min thresholds; 5 were prompt taps while strained.
- **ntfy needs internet.** On venue Wi-Fi the push can be blocked; the phone stays on the hotspot.
- **The wrist only buzzes when the phone is locked.** Lock nbz's phone before every take.
- **A judge's prompt may be good.** Then Revive correctly does nothing; we ask for a vaguer one.

## Validity caveats (from `history/SUMMARY.md`)
- **One person, one week**, observational: Lucas's prompts, Oct 17–24. Associations, not causes.
- **The tertile cut was the second cut tried.** The first, buggy cut (≤ 2 vs ≥ 3, middle not left out) gave 1.24× turns to done, p = 0.095. We report both.
- **The pre-registered split (≤ 4 vs ≥ 7) is underpowered:** only 3 prompts scored ≥ 7 (1.23× turns, p = 0.82).
- **"Achieved" is a proxy:** the turn ended with a completed task-list step or a wrap-up, and the next prompt wasn't a correction. Explicit corrections are rare (4 of 665).
- **The grader saw prompt text only**; Claude's previous reply and tool errors were passed as length or yes/no, which pushes context scores down.
- **53 of 665 prompts were dropped** by a confidentiality filter before grading (49 named a customer, 3 over 4,000 chars, 1 not in English). The blocklist lives outside the repo.


## Status at 3:25 PM (updated by Lucas's session)
- **Body state is now real on the demo laptop:** nbz's `body/polar.py` reads the Polar H10 live (heart rate + RR), `body/rmssd.py` cleans RR and computes RMSSD, `get_body_state()` uses the newest live reading and falls back to FAKE_STRAIN only when there's no reading newer than 15 s (labeled "fake"). On Lucas's laptop (no strap) it shows "fake".
- **Wrist tap is real:** `act.tap` (nbz) → ntfy → phone → Garmin. Tested: buzz arrives.
- **Hero bug:** the filter was written before the bug was re-recorded, so the hero bug is the reader run with `--no-filter` on a real squat recording (tag `hero-bug`). Not yet recorded at 3:25.
- **Grader vs. an expert:** on 10 made-up prompts scored by Lucas before seeing the grader, 7/10 agree (within 1 point, or correctly left unscored); 8/10 within 2 points. Where it disagrees, the grader is stricter on vague asks. One of the two disagreements used the heuristic fallback because the API call was slow. Not tuned to match (10 items is too few). Source: `grader/calibration/results_set1.json`.
- **Prompt hook latency:** 1.7–2.2 s through the running server (the grade call itself is 1.6–2.0 s).
- **Baselines from 19 days of Garmin data, n = 19 days (Oct 1–23, 20 daily exports):** `hr_base` = median resting HR 69 bpm (n = 18 days); `today` = Oct 23's Body Battery high 67 and average stress 35 (30-day medians: 53 and 41). The exports have no sleep or overnight HRV, so `sleep_h`/`sleep_score` are null and `rmssd_base` stays the daytime strap value (41 ms). With these numbers the coach no longer uses the "poor night" threshold. Computed by `body/baselines.py`; only aggregates are committed (`body/baselines_nbz.json`).
- **Focus watcher (added 4:00 PM, Noam's idea):** `focus/watch.py` checks the frontmost app and, for browsers, only the site's domain every 5 s during a work block. Distraction site for 90 s → wrist tap "Back to task · N min left"; 90 min without a 10-min break → "Take 5". In the demo it runs with `--demo` (20 s / 2 min thresholds), and those events are tagged "demo timing". Page titles and full URLs are never stored.

## Status at 4:20 PM
- **Loop detector** (`coach/loop.py`), **insights page** (`web/insights/`, aggregates only) and **`scripts/check_predictions`** (the 3 locked predictions → `pitch/predictions_result.json`) are on main.
- **Hero take** starts from tag `hero-red` (see the Hero bug row). Runbook for every take and test: `pitch/runbook.md`.
- **Test 1 (4:05):** the focus watcher's break tap reached the Garmin. The prompt tap didn't fire because nbz's Claude Code session predated the repo and never loaded the hooks; fix = fresh `claude` in the repo. Retest: see Final status.

## Final status (end of the event)
- **Hero take:** at 5:21:50 PM a 2/10 prompt while strained → silent fix + wrist tap "Slow down: context added"; the next outcome (5:22:18) was achieved, with the filter restored and `tests/test_rmssd.py` passing (`docs/img/judge-view.jpg`). Prompt taps while strained also fired at 4:19, 4:50, 5:10 and 5:27 PM.
- **Grader cap:** 5 s since `04c3507` (4:55 PM); the hook waits 9 s for the server. The tag `demo-final` is that commit; `hero-red` is `demo-final` plus one commit (`40c2ff5`) that removes the RR artifact filter. The tag was cut three times with the same `body/rmssd.py` change: at 4:09 PM on that time's main, rebased onto `demo-final` at 4:55 PM, and re-made at 5:24 PM (after the 5:21:50 PM take) with a neutral commit message, "RMSSD: compute successive differences over all RR intervals"; the earlier message named the bug.
- **Predictions (5:34 PM):** #1 not enough data (first hour n = 1), #2 true by the pre-set rule on n = 5 vs. 7 (achieved 60% vs. 86%; turns 1.12×), #3 not enough data (0 loops). Source: `pitch/predictions_result.json`.
- **Today (5:41 PM):** 110 prompts, 21 nudges, 13 wrist taps, 10 solved after a nudge (`pitch/today_numbers.json`).
- **Video:** 1:35 with captions and music, over the 90 s plan in `pitch/video_script.md`.
