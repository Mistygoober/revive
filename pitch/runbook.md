# Runbook: what to record and test, when, and what should happen

Written 4:15 PM against main at `06777fc` and the tag `hero-red` (`ad85743`).
**N** = Noam (demo laptop, 172.20.10.10). **L** = Lucas (judge screen, OBS).
Judge view: **http://172.20.10.10:8000/web/judge/**

Each step: who · what to do · ✅ what you should see · ⚠️ if it doesn't happen.

---

## 0. Three rules for every pass (read first)
1. **New Claude Code session every pass.** Quit `claude` and start it again.
   Why: the loop detector counts "fix it" as a retry. Three of them in 15 min in one session → it **holds** the prompt instead of tapping.
2. **`rm -f data/coach_state.json` before every pass.**
   Why: the coach taps at most once per 20 min, and a loop hold blocks holds for 15 min. This file holds both timers.
3. **Focus watcher OFF during hero takes** (Ctrl+C in tab 3).
   Why: with `--demo` it sends "Take 5" after 2 min of activity. That would buzz the wrist in the middle of a take.

---

## 1. Reset before any take or test (5 min)

**L** · close every judge-view tab first. An open stream blocks the server shutdown.

**N** · tab 1 (server). Ctrl+C, then:
```
cd ~/revive && git switch main && git pull --no-rebase --no-edit origin main && git fetch origin --tags
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```
✅ `git log --oneline -1` shows `06777fc` or newer. This is required: the silent fix only picks up a test you ran with `!` from that commit on, and the hook runs inside the server.
⚠️ "address already in use": an old server is still running. Close the judge tabs and Ctrl+C again.

**N** · tab 2 (strap): `uv run python -m body.polar` (start it **on main**, before switching to the take branch)
✅ It prints `connected: Polar H10 …`, then `hr=… rmssd=… strain=calm` every 5 s.
⚠️ "not found; retry": wet the strap, snug it, wait 10 s. No live reading for 15 s → the judge view shows **fake** + DEMO DATA. Don't record like that.
⚠️ Never restart tab 2 while on a take branch. It would load the buggy RMSSD and the judge screen would show inflated HRV.

**N** · tab 3 (focus watcher): **off** for hero takes. Start it only for the focus shot (§3a).

**N** · `scripts/demo_check`
✅ `PASS demo_check: 6/6 steps`. No tap is sent (it uses REVIVE_TAP=0), and it cleans up after itself.

**N** · `rm -f data/coach_state.json`

**N** · phone **locked**, on the hotspot. ntfy notifications on. Laptop on Do Not Disturb (except ntfy).
⚠️ The Garmin only buzzes when the phone is locked.

**L** · open the judge view full-screen, then start OBS (replay buffer on).
✅ Heart rate is live, the H10 dot is green, and there's **no** DEMO DATA badge.

---

## 2. Hero take (5:00–5:30, Geisel 1041; tag `demo-final` at 5:15)

**Setup (N):**
```
git switch -c take-1 hero-red      # take-2, take-3 … for later takes
claude                             # fresh session, font size up
```
✅ `hero-red` = main + `body/rmssd.py` **without** the artifact filter (the 11:30 bug). Your server and strap keep running main's code in memory, which is what we want.

**Cameras (L):** OBS on the judge view · Noam's screen recording (Cmd+Shift+5, show clicks) · Lucas's phone on the wrist. Start all three, then Noam **claps once** (sync point).

**The take (about 90 s of footage, one shot, no cuts):**

1. **N** · in Claude Code: `! uv run pytest tests/test_rmssd.py -q`
   ✅ Red: `2 failed, 5 passed`. Failing: `test_squat_artifacts_do_not_explode_rmssd` and `test_real_squat_fixture_hero_bug` (unfiltered RMSSD **≈ 99 ms**, where the filtered value is ≈ 17 ms).
   ⚠️ Run it with `!` inside Claude Code, **not** in another terminal. Otherwise the silent fix can't see the failure.
   ⚠️ Green? Then you're on main, not the take branch: `git branch --show-current`.

2. **N** · 20 squats, just off frame (~40 s).
   ✅ Judge view flips to **STRAINED**: HR ≥ 88 (base 68 + 20), or RMSSD under 25 ms.
   ⚠️ Strain is judged every 5 s with no hold, so it fades as the heart rate drops. **Type the prompt within ~20 s of sitting down.** Not strained → 10 more squats.

3. **N** · type exactly: `hrv is broken fix it`
   ✅ About 2 s later:
   - judge view: score **~2/10**, missing *context* + *done*, strained → **WRIST TAP**, decision log line "score 2 + strained"
   - wrist: buzz, "Slow down: context added"
   - Claude Code: the hook's added context holds the failing test output plus "run the relevant test and say how you verified"
   ⚠️ Score shown but **no tap**: either not strained anymore (the log says "score 2", not "+ strained"), or the cooldown file wasn't deleted. Redo the take.
   ⚠️ Prompt **blocked** with "Three tries…": the loop detector fired because the session wasn't fresh (rule 1). Redo the take.
   ⚠️ Tap in the log but no buzz: the phone isn't locked, or ntfy is off.

4. **Claude** · fixes `body/rmssd.py`, restoring the filter (it should use `_valid_flags`). It runs the test itself because the added context told it to.
   ✅ `7 passed`.
   ⚠️ Not fixed on the first try: **redo the take, never edit it to look solved** (video rules).

5. **N** · (optional, for the shot) `! uv run pytest tests/test_rmssd.py -q` → green.

**After each take (N):**
```
git switch main            # leave take-N as is; never merge it
rm -f data/coach_state.json
```
Then quit `claude` and do the next take on `take-N+1`.

**If main moves before the takes** (a fix lands after 4:15), re-cut the tag so the take has the latest code:
```
git switch -c hero-red-2 origin/main && git cherry-pick ad85743
git tag -f hero-red && git push -f origin hero-red && git switch main && git branch -D hero-red-2
```
(Lucas's laptop does this. N then runs `git fetch origin --tags -f`.)

---

## 3. Other shots for the video (after the hero takes)

### 3a. Focus: YouTube → "Back to task" (video 55–60 s)
**N** · `git switch main` · tab 3: `uv run python -m focus.watch --minutes 45 --demo`
✅ It prints "… with demo timing".
**N** · open youtube.com in the browser, frontmost, and wait.
✅ After **20 s**: wrist buzz "Back to task, 45m left" (minutes left in the block). The judge view logs a focus tap tagged "demo timing".
⚠️ Nothing happens: the browser must be the frontmost app. Only youtube.com/x.com/instagram/… count. Repeats need a 5 min cooldown, so Ctrl+C and restart the watcher for take 2.
⚠️ "Take 5" fires after 2 min of activity in demo mode. Fine for this shot, bad for any other: **Ctrl+C tab 3 afterwards.**

### 3b. Loop stop (only if it's more visual than 3a; never a sixth beat)
Do it **after** the hero takes. Its tap starts the 20-min tap cooldown.
**N** · `rm -f data/coach_state.json` · on a take branch, a **fresh** `claude` session. Within 15 min, send these and press **Esc** right after each so Claude doesn't fix anything:
1. `why is the hrv test failing`
2. `still broken`
3. `no, try again!!!`

✅ On prompt 3 (it needs 3 of 4 signals: repeated retries ✓, frustration ✓, no passing test or commit ✓):
- Claude Code: prompt **blocked**, "Three tries, no progress. Different approach: … Take two minutes."
- Mac voice: "You're looping. Take two minutes."
- wrist: "Looping: take 2"
- judge view: a loop event plus a level-2 action (hold · voice · tap)

⚠️ The detector logic was dry-run on these 3 prompts (fires: repeat, frustration, no progress), but **not yet through the real hook. Do it once at Test 2.** If Claude ran a test that **passed** in between, "no progress" is off and it won't fire. Start over in a fresh session.

### 3c. AI Wrapped card (video 80–90 s)
**L** · http://172.20.10.10:8000/web/wrapped/?real=1&who=nbz
✅ Today's real numbers (demo events dropped), no DEMO DATA badge.

### 3d. Insights page (~5 s, optional, merged at `7e51eb7`)
**L** · http://172.20.10.10:8000/web/insights/
✅ Today, what it learned, your body (aggregates only). First thing to cut if short on time.

---

## 4. Test 2 (4:50, 10 min)

**3 clean passes** of §2 (steps 1–4), each with the §0 rules (fresh session + rm the state file). Time each pass.
Pass = red → strained → tap + buzz + added test output → green, all in one go.

**Failure drills (one each, ~1 min):**

| Drill | Do | Expect | Recover |
| --- | --- | --- | --- |
| No internet | Turn off Wi-Fi on N's laptop, then send `hrv is broken fix it` | Prompt still goes through (never blocked). Grade is labeled `heuristic` (3 s cap); action logged, **no buzz** | Wi-Fi back on. Say: "the tap needs internet; the coach still decided" |
| Strap drops | Ctrl+C tab 2 (or unclip it), wait 20 s | Judge view: **fake** + DEMO DATA badge; strain from FAKE_STRAIN (calm), so no tap | Restart tab 2 **on main**; badge gone within ~5 s |
| Grader slow | Same as "No internet" (it's the same fallback) | `source: heuristic` on the grade line | Nothing to do |
| Good prompt | Type: `In body/rmssd.py the squat tests fail: unfiltered RMSSD is 99 ms. Restore the artifact filter in rmssd() and run tests/test_rmssd.py to confirm green.` | Score ≥ 5, **no action**, no buzz | Say: "correct, it only steps in when needed" |
| Loop | §3b once | Hold + voice + tap | Fresh session; rm the state file |

**Cut rule:** anything that fails twice at Test 2 leaves the video and the table demo. Say so in DEMO_NOTES.

---

## 5. Live table demo (2 min, from 6:45)

**Before each judge group (N, 30 s):**
```
git restore body/rmssd.py         # put the bug back (git reset --hard hero-red if Claude committed)
rm -f data/coach_state.json       # otherwise the second group within 20 min gets no tap
```
Quit and restart `claude`. Run `! uv run pytest tests/test_rmssd.py -q` → red. Phone locked. Focus watcher off.

| Time | Who | Do / say | You should see |
| --- | --- | --- | --- |
| 0:00 | L | The problem + one-liner (pitch_lines.md) | — |
| 0:15 | N | Points at the judge screen: live HR + HRV vs the baseline from 19 days of Garmin data | Live, no DEMO DATA badge |
| 0:35 | N | 20 squats: "raising my heart rate on purpose" | STRAINED within ~30 s |
| 0:50 | N | "Give me a three-word prompt for this bug." Types it **right away** (strain fades) | Score low → WRIST TAP; holds up the Garmin |
| 1:10 | L | The decision log: hook → grader → body → tap + added failing test | The log lines for this prompt |
| 1:25 | L | The validity numbers (1.42×, n 60 vs 48, p 0.034; 7/10) | — |
| 1:45 | L+N | Who pays; N shows the Wrapped card | `/web/wrapped/?real=1&who=nbz` |

⚠️ The judge's prompt is good → no action. "Correct, it only steps in when needed. Try a vaguer one."
⚠️ No buzz → the judge view still shows WRIST TAP sent; check the phone is locked.
⚠️ Don't say "the real one happened at 4:09" (GAMEPLAN §8) unless a real 4:09 tap is in today's log.

---

## 6. Real vs staged (say it out loud)
- **Live:** the strap (HR + RR → RMSSD), the hooks, the grader (Claude Haiku 5.5), the silent fix, the wrist tap, the judge view, the decision log.
- **Staged:** the squats, the scripted lazy prompt, the planted bug.
- **Replayed from git:** the bug, a real one from 11:30 (tag `hero-red`), on real squat data recorded today.
- **Demo timing:** the focus watcher at 20 s / 2 min instead of 90 s / 90 min, tagged on every event.
- **DEMO DATA:** any seeded events or fake body state are badged on screen.
- **Never:** a slider posing as a sensor, a number we didn't measure, "causes" (say "associated with").

---

## 7. Video script fixes needed (`pitch/video_script.md`, Lucas to approve)
1. **Tag:** `hero-bug` → `hero-red` (shot 22–55 and recording plan step 1). `hero-bug` is Noam's recording commit and already has the filter, so its test is green.
2. **The number:** "RMSSD [__] ms, should be ~5–20" → **"RMSSD 99 ms, filtered 17 ms"** (Noam's real squat fixture, commit `0753302`). In Sources, "~1,300 ms" is wrong; that was the 11:30 test, not today's recording.
3. **The file Claude edits:** `body/polar.py` → **`body/rmssd.py`**.
4. **Caption** "context added: failing test + files" → **"context added: the failing test"**. A fresh session has no edited files, so the silent fix adds the test output and the "verify before finishing" line only.
5. **Recording plan time:** "5:15–5:30" → **5:00–5:30** (the Geisel 1041 booking). Freeze tag at 5:15.
6. **Before each take:** add "fresh `claude` session, `rm -f data/coach_state.json`, focus watcher off", and "run the red test with `!` inside Claude Code".
7. **Focus take:** "Back to task, [__]m left" will read **45m** if the watcher was just started with `--minutes 45`.
8. `pitch/pitch_lines.md` setup says "the `hero-bug` branch" → `hero-red`.
