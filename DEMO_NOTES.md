# What's real and what's mocked

Status as of 3:00 PM, Sat Oct 24 (update at the 5:15 freeze). This is the README's "What's real" section and our answer when a judge asks "what's mocked?".

| Piece | Real / replayed / mocked | Note |
| --- | --- | --- |
| Capture hooks | **Real** | Claude Code `UserPromptSubmit` and `Stop` hooks in `.claude/settings.json` run `capture/hook.py` on every prompt and reply. The event log gets metadata only (length, session, project); raw text goes to `memory/raw/`, which is git-ignored. |
| Prompt grader | **Real** | Claude Haiku 5.5 (`claude-haiku-5-5`), one forced-tool call per prompt, hard 3 s cap (`grader/_llm.py`). On a timeout, API error or missing key it falls back to a keyword heuristic, logged as `source: "heuristic"`. Rubric: `docs/plan/grader-rubric.md`. |
| Outcome grader | **Real, being wired (3:00 PM)** | `grader/outcome_score.py` (Haiku 5.5, same fallback). `coach/outcome.py` is being hooked into the `Stop` hook right now, so each live turn gets an `outcome` event and corrections are flagged. Confirm at 5:15. |
| Coach | **Real** | `coach/policy.py`: score ≤ 4 → silent fix (level 0); score ≤ 4 and body strained → silent fix + wrist tap (level 1); at most one tap per 20 min. A poor night (sleep < 6 h or Body Battery < 40) raises the threshold to 5. |
| Silent fix | **Real** | `coach/context.py` reads the session transcript and adds the last tool error, recently edited files and a "verify before finishing" line as hook `additionalContext` (≤ 1,500 chars). It can't rewrite the prompt; it adds to it. |
| Wrist tap | **Real** | ntfy push (priority 5) → nbz's phone → Garmin notification. Sent by `coach/act_fallback.py` until nbz's `act/tap()` lands. Only taps from nbz's laptop (`REVIVE_WHO=nbz`). |
| Judge view | **Real** | `web/judge/` reads the live event log over server-sent events. Labeled "behind the scenes"; the user never opens it. Shows a **DEMO DATA** badge whenever demo events or fake body state are on screen. |
| Body state (heart rate, HRV, strain) | **FAKE (for now)** | `body/state.py` is a stub: fixed values picked by `FAKE_STRAIN=calm|elevated|strained`, `source: "fake"`. Replaced when nbz's Polar H10 reader lands. Every coach action taken on fake body state is logged with `demo: true`. |
| Baselines (68 bpm, RMSSD 41 ms) | **FAKE (for now)** | Hard-coded in the stub. To be computed from nbz's 30-day Garmin export (raw file stays in `../data-private/`). |
| Today's Garmin context (sleep, Body Battery, stress) | **FAKE (for now)** | Hard-coded in the stub (5.4 h sleep, Body Battery 38), which means the coach currently uses the "poor night" threshold. |
| Hold + voice (loops) | **Not built** | `decide()` has a `loop` branch, but no loop detector feeds it and `act/say()` doesn't exist yet. |
| Hero bug | **Real bug, replayed from git** | The H10 reader's RMSSD blows up during squats (dropped beats → fake 2–5 s intervals → RMSSD ~1,300 ms). Lucas hit it for real at 11:30; nbz writes the reader without the filter first, tags it `hero-bug`, and the video replays that commit. The squats, the planted bug and the scripted lazy prompt are staged and said out loud. **Tag not created yet.** |
| Seeded demo events | **DEMO DATA** | `scripts/fake_events.py` replays a scripted 3-minute sequence (calm → squats → strained → tap → solved). Every event carries `demo: true`, and the judge view badges it DEMO DATA. |
| History validity number | **Real** | Lucas's own Claude Code prompts, Oct 17–24, graded by the same grader. Aggregates only in `history/results.json` and `history/SUMMARY.md`; prompt text never left the laptop except for grading. |
| Today's numbers (prompts, nudges, accepted) | **Real, filled at 5:15** | Counted from `data/events.jsonl`, excluding `demo: true` events. |

## Known weak spots (the answer to "what breaks first?")
- **The body side is a stub until nbz's reader lands.** Until then every tap is driven by `FAKE_STRAIN`, and the judge view says DEMO DATA.
- **Grader latency.** The 3 s cap is tight on a phone hotspot; slow calls fall back to the heuristic score (still logged, marked `heuristic`).
- **The grader has no temperature setting.** The rubric asks for temperature 0, but the SDK call in use doesn't accept it, so the same prompt can score slightly differently on a rerun. The forced tool and anchored rubric keep it stable in practice; we haven't measured run-to-run spread.
- **Scores run low.** Real asks average 2.76/10 and only 3 of 239 scored prompts reached ≥ 7, so the rubric's "good prompt" bucket is nearly empty (see caveats).
- **Context check carries no signal** on past prompts (ρ ≈ 0 with outcomes), likely because the grader never saw Claude's previous reply as text. The done and goal checks carry the signal.
- **Outcome scoring on live turns is new** (wired at ~3 PM): check it logged `outcome` events before quoting turns-to-done for today.
- **No loop detection, hold or voice yet.**
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
