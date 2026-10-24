# Revive: game plan for c0mpiled-16

**Sat Oct 24, 2026 · UCSD Student Services Center MPR · check-in 1:00 · rules 1:15 · build 1:45–6:30 (4 h 45 min) · judging 6:45 · top 5 at 7:45 · top 3 at 8:30**

> **Schedule changed (organizer email, Sat 11:35):** submissions are due **6:30 PM**, not 7:30, and hacking starts at **1:45**. We lose 45 minutes, so every gate moved earlier: **gate 3:30 · backup video 4:15 · freeze 5:15 · submit 6:10**. Tracks and the submission link are only announced at the 1:15 opening. **Every team member needs their own Luma registration**, so nbz must have one.
Team: **Lucas** (Claude side) + **nbz** (health side, judge view, video). Locked Sat 10:30 AM.

This page decides everything, so at the event we only build. **The full scope tree, big to small, with status:** [SCOPE.md](SCOPE.md) and the [Revive scope diagram](https://claude.ai/artifact/7sQQ1Q812bb39jxurPYwfk). The research and reasoning behind it are in [plan.md](plan.md), [decisions.md](decisions.md) and [research/](research/). If a rule announced at 1:00 changes something, use [If the rules change](#if-the-rules-change); don't re-plan from scratch.

---

## 1. Locked decisions
| | Decision |
| --- | --- |
| **Idea** | Body × AI work: Revive connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app. (one-liner chosen Sat 12:00) |
| **Name** | **Revive** (decided Sat 10:50; replaces Revive) |
| **Track** | **Consumer**. Unsupervised stays a live option until the rules talk (see §10). The build is the same either way; only the story changes. |
| **Channels** | Level 0, a **silent fix**: the hook adds missing context. Level 1, a **wrist tap**: an ntfy push mirrored to nbz's Garmin. Level 2, **hold + voice**: the hook holds the prompt and the Mac speaks one line. No lamp. |
| **Scoring (12:00)** | Two scores per turn: a **prompt score** before Claude replies (judged against 5 context layers: conversation, session goal, project, user profile, company/domain) and an **outcome score** after (did Claude deliver what the prompt was trying to achieve: achieved / partial / missed / wrong direction), plus one line of **inferred intent** per layer. See [grader-rubric.md](grader-rubric.md). |
| **Body by time scale (12:00)** | **Now:** live heart rate + HRV (H10). **Today:** last night's sleep, Body Battery, stress (Garmin) → sets how early Revive steps in + a morning note. **Trend:** sleep debt, HRV and resting-HR trends → insights. Heart rate is one signal, not the cause. |
| **Usage triggers (12:00)** | The coach acts on usage as a whole, not just prompts: a **long stretch without a break** and **loops** trigger live; open tasks and falling quality go to the insights page. |
| **Demo data (12:00)** | Seeded synthetic history is allowed to show patterns clearly, always badged **DEMO DATA** and listed in DEMO_NOTES. Real: the live strap, hooks, today's log, the hero shot, the validity number. |
| **Memory (12:00)** | `memory/raw/` (facts, never altered) vs `memory/insights/` (generated, labeled). Agents (health, Claude usage, combined, short-term, long-term, researcher) are "what's next", not built today. Nothing from Lucas's other work goes in the repo or video. |
| **Portal** | Optional insights page for the user: "Nothing to open day to day. When you're curious, there's a page." Reuses the judge view. Built by nbz only after `demo-1`, out of the hero shot, ~5 s near the end of the video, and the **first thing cut** if behind. (Sat 11:00) |
| **Moments built** | (1) Context nudge, (2) loop stop. Shown but not built live: the 30-day baseline card. "What's next": morning tip, flow guard. |
| **Live subject** | nbz, wearing the Polar H10 and the Garmin from 1:45 |
| **Headline number** | Turns to done: do low-scored prompts need more follow-ups? Plus today's turns saved after nudges. |
| **Who pays** | "Heavy AI users pay ~$12/month for a coach that runs on their own machine. It spreads as a one-line Claude Code plugin and shareable 'AI Wrapped' cards. Teams come later, aggregate-only." |
| **Privacy line** | Body data never leaves the laptop. Prompts go to Claude for grading (they were Claude prompts already). |

## 2. What we build (and what we don't)
**The one-liner:** *Revive connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app.*

| Must work (the demo) | Nice to have (only after `demo-1`) | Not building |
| --- | --- | --- |
| Live heart rate + HRV from the H10, against nbz's baseline | Garmin heart-rate broadcast as a backup sensor | Any app the user has to open |
| Every prompt captured and graded 0–10 by a hook | Loop detector using HRV trend | Browser extension, MCP server |
| Coach: vague prompt → silent fix; vague + strained → wrist tap | Voice line on loops | Calendar / Focus actions, lamp |
| Judge view on the judge screen (Lucas's laptop): live heart rate and HRV, prompt scores, the coach's decisions | "AI Wrapped" end card from today's log | Morning tip |
| One honest number (grader validity or turns saved) | History findings from Lucas's past prompts | Anything using customer or NDA data |
| | **Portal:** an optional insights page (today's patterns, the 30-day baseline, AI Wrapped), reusing the judge view | |

**Testing is never cut.** The three test blocks (4:00, 4:50, 6:10) stay even if features slip: cut features first.

**Failure drills (in Test 2):** each must recover in under 30 s, or the demo uses the fallback.
| Drill | Expected recovery | Fallback |
| --- | --- | --- |
| Strap loses contact / Bluetooth drops | Reader reconnects by itself within 10 s; judge view shows "reconnecting" | `REPLAY=1` (labeled REPLAY) |
| Grader slower than 3 s or API error | Heuristic score is used, marked "fast score" | Same |
| ntfy push doesn't arrive (venue Wi-Fi) | Phone on the hotspot; push arrives within 5 s | Voice line only |
| Wrist doesn't buzz (phone unlocked) | Lock nbz's phone before the demo | Phone buzz on the table |
| Judge laptop can't reach nbz's laptop on the hotspot | Both on the same hotspot; reload the page | Judge view split-screen on nbz's laptop |
| Claude takes long to answer | Talk over it with the judge view ("here's what Revive did") | Pre-recorded clip of the same moment, labeled |
| A judge's prompt is actually good | Revive does nothing, and we say that's correct: it only steps in when needed | Ask for a vaguer one |

**Before every demo (checklist):** strap wet + on, Garmin + phone + judge screen + laptop charged above 50%, phone locked + on the hotspot, `scripts/demo_check` green, volume up, Do Not Disturb on the laptop (except ntfy).

**Cut order if behind:** morning tip (already out) → portal → voice → loop detector → judge-view polish → live strap (replay today's recorded trace, labeled).
**Never cut:** capture + grading, one live wrist tap, one real number, honest labels.

## 3. How it fits together
Everything runs on **nbz's laptop** (the "demo laptop"): the H10 is next to it, nbz types into Claude Code on it, and the hero moment needs no network apart from the grader call. Lucas builds the Claude side on his laptop and pushes; nbz pulls.

```
Polar H10 ─BLE─▶ body/polar.py ─▶ data/body.jsonl ─▶ body/state.py ─┐
nbz's 30 days ─▶ body/baseline.py ─▶ data/baseline.json ────────────┤ get_body_state()
                                                                      ▼
Claude Code ─UserPromptSubmit/Stop hooks─▶ work/capture ─▶ work/grader ─▶ work/coach ──▶ act/tap()   ntfy → phone → Garmin buzz
                                                    │                      │          ├─▶ act/say()   macOS voice → speaker
                                                    │                      │          └─▶ hook output: add context, or hold the prompt
                                                    ▼                      ▼
                                              data/events.jsonl  ◀── every step logs one line
                                                    │
                                     server.py (/events stream, /body) ─▶ web/ judge view on the judge screen (Lucas's laptop) (the hotspot)
```

### The contract (agree on it at 1:45, then build in parallel)
Both sides build against these from minute one, so neither waits on the other. nbz's UI starts on a fake event replayer; Lucas's coach starts on a fake `get_body_state()`.

**`get_body_state()`** (nbz) returns:
```json
{"ts": "2026-10-24T16:09:12-07:00", "hr": 96, "rmssd": 22.4,
 "hr_base": 68, "rmssd_base": 41.0, "strain": "calm | elevated | strained", "source": "h10 | garmin | replay"}
```
`strained` = heart rate ≥ 20 bpm above baseline **or** RMSSD < 60% of baseline, held for 60 seconds. Tune it at 3:30 with squats.

**Clean the RR intervals before computing RMSSD** (found in the 11:30 H10 test: squats caused dropped beats and fake 2,000–5,500 ms intervals that pushed RMSSD to ~1,300 ms). Drop any RR < 300 ms or > 2,000 ms, and any RR more than 20% away from the median of the last 10 beats. Compute RMSSD over the last 60 s of clean beats, and report `rmssd: null` when fewer than 20 clean beats remain (motion), instead of a fake number.

**`data/events.jsonl`** (everyone appends, one JSON object per line). Every event has `ts`, `who` (`nbz` | `lucas`) and `kind`:
| kind | Extra fields | Written by |
| --- | --- | --- |
| `body` | hr, rmssd, strain (once every 5 s) | nbz |
| `prompt` | session, chars, (no text) | Lucas |
| `grade` | type, score 0–10, missing: [context, done, goal, scope, why], bundled, pattern, latency_ms (see [grader-rubric.md](grader-rubric.md)) | Lucas |
| `action` | level 0/1/2, channel (fix, tap, voice, hold), message | Lucas (calls nbz's `act/`) |
| `loop` | signals: [...], minutes | Lucas |
| `outcome` | turns_to_done, corrected: bool | Lucas |
| `mark` | note ("felt stuck", "gate 4:15") | both, via hotkey |

**`act/tap(text)` and `act/say(text)`** (nbz): ≤ 5 words for a tap, one sentence for voice. Both return within 1 s and never throw.

**Rate limit (coach):** at most one tap per 20 minutes. Never interrupt mid-flow (good prompts in a row).

### Repo folders = ownership
| Folder | Owner | What |
| --- | --- | --- |
| `body/` | nbz | H10 reader, RMSSD, baselines from the Garmin table, today's context, `get_body_state()` |
| `act/` | nbz | ntfy push, macOS voice |
| `web/` | Lucas: judge view · nbz: AI Wrapped, insights page, badges | Agree on a shared style at 1:45 |
| `work/` | Lucas | Hooks, grader, coach, loop detector, outcome tracking |
| `history/` | Lucas | Past-prompt analysis (stays local; only numbers get committed) |
| `server.py` | Lucas | ~40 lines: serve `web/`, stream `events.jsonl`, expose `/body` |
| `pitch/` | both | Script, README, FAQ, predictions, DEMO_NOTES |

**Only Lucas merges to `main`.** nbz works on a branch `nbz` and asks for a merge at each checkpoint.

## 4. Who does what
**Owners confirmed Sat 12:10.**

**Lucas, the Claude side + the judge view:** capture hooks, grader (prompt + outcome score, intent, context layers), coach policy, silent fix, break trigger, loop detector, the hold, metrics, memory split, seeded demo data, history validity number, server, **judge view on the judge screen (Lucas's laptop)**, merges, README, DEMO_NOTES, submission.

**nbz, the health side and the face:** H10 reader + HRV, artifact filter, Garmin baselines, **today's Garmin context** (sleep, Body Battery, stress → sensitivity + morning note), body state, replay mode, wrist tap + voice, AI Wrapped card, insights page, DEMO DATA badges, hero bug + fixture, video edit + captions; live subject on camera.

**Both:** the 1:45 walkthrough, the 3:30 gate call, predictions and "felt stuck" marks, backup video, hero-shot take, the 5:15 freeze, and **pitching together** (Lucas: the problem, how it works, the numbers; nbz: the body side and the live moment), at the table and on stage at 7:45.

### Timeline per person
| Time | Lucas | nbz | Done when |
| --- | --- | --- | --- |
| 12:45 | Table near power, quiet recording corner, hotspot on | Same; put on the H10 (wet the electrodes). Luma: registered and approved ✅ | Set up |
| 1:00–1:15 | Check-in | Check-in | Both checked in |
| 1:15–1:45 | Opening and rules: **record it** (voice memo); note the **tracks** and the **submission link**; ask the [host questions](#questions-for-a-host) | Note anything about video length, the no-app rule, sponsors | Rules captured |
| 1:45–2:05 | Transcript → `RUBRIC.md`; repo + kit + **contract** stubs; first commit. **Claude walks you both through the contract (§3).** | Clone, Claude Code signed in, `body/` stubs with fake data | Repo pushed, both pulled |
| 2:05–2:35 | Capture hooks live on **both** laptops (today's dataset starts) | H10 reader **without** the filter → squats → tag `hero-bug` + save the squat fixture (§7) | Prompts logged; `hero-bug` tagged |
| 2:35–3:15 | Calibration set (10 min), then the grader ([grader-rubric.md](grader-rubric.md), < 3 s) + coach with fake body state | Filter, RMSSD, baseline, `get_body_state()`; `act/tap()` buzzes the Garmin | Grades in events; tap works |
| 3:15–3:30 | Wire coach to real body state → **`demo-1`**: squats + lazy prompt → wrist tap. Write `scripts/demo_check` (one command: starts everything, runs one scripted prompt, checks every step logged) | Today's Garmin context (last night's sleep, Body Battery) into body state + morning note | **`git tag demo-1`** |
| **3:30** | **Gate together.** Not working end to end? Drop the voice, or switch the strap to replay (labeled). | | Decision made |
| 3:30–4:15 | Silent fix (last error + touched files); hold on loops; **judge view** on the real stream (live lines, score chips, decision log, Intent → Got) | `act/say()` voice; DEMO DATA badges; start the AI Wrapped card | Levels 0–2 work |
| **4:00–4:30** | **Recording room booked: Geisel 522 (5th floor).** **4:00–4:15 Test 1:** first full live-demo run-through, with a stranger dictating the prompt if possible; write down every failure. **4:15:** backup video. | Same (subject) | Failure list written |
| **4:15** | **Backup video together (60 s)** of whatever works | | Saved |
| 4:15–4:50 | Validity number (past prompts, Anthropic API only) + today's turns to done; loop detector + break trigger if time (cut 3rd); numbers into DEMO_NOTES | AI Wrapped card + optional portal (cut first); OBS scene set up | Number on screen |
| 4:50–5:15 | **Test 2 (never cut):** fix the Test 1 failures, then live demo + hero shot **3× in a row**, plus the failure drills below | Same, as the subject | 3 clean passes |
| **5:00–5:30** | **Recording room booked: Geisel 1041 (1st floor West).** Last rehearsal at 5:00, hero-shot takes from 5:15. Bring the strap and both laptops; Lucas films the wrist close-up handheld. | | |
| **5:15** | **Freeze.** `git tag demo-final`. Record the hero shot (2–3 takes). | Subject in the hero shot | Takes saved |
| 5:15–5:50 | Narration, README, DEMO_NOTES, submission text | **Edit the video, captions** | Video file |
| 5:50–6:10 | Repo public, test every link in a private window | Upload unlisted to YouTube; keep the MP4 | Links work |
| **6:10** | **Submit** (deadline 6:30) | | Confirmation |
| 6:10–6:45 | **Test 3 (never cut):** set up the demo table in the real room (judge screen, card with QR), then **2 timed dress rehearsals** of the 2-min demo on the venue's Bluetooth and hotspot; ask a host about the stage setup for 7:45 (screen, HDMI, mic) | Strap on, Garmin on; pitch the body side | 2 clean runs under 2 min |
| 6:45–7:45 | Judging: pitch at the table | Live subject; let a judge dictate the lazy prompt | |
| 7:45–8:15 | **If top 5: demo on stage** (same 2-min demo, plus the number) | Live subject on stage | |
| 8:30 | Top 3 announced | | |

## 5. Tools
| Job | Tool | Notes |
| --- | --- | --- |
| Coding | **Claude Code** on both laptops | nbz signs in through Lucas's Console invite. No `ANTHROPIC_API_KEY` in nbz's shell, or Claude Code bills that key. |
| Language | Python 3.12 with **uv** | One `pyproject.toml`; `uv run` everywhere |
| Sensor | **bleak** (Bluetooth LE) → H10 heart-rate service, RR intervals | RMSSD over a rolling 60 s window |
| Grader | Anthropic API, **Claude Haiku 5.5** (`claude-haiku-5-5`) | Fast and cheap; the hook times out at 30 s, so aim for < 3 s, with a heuristic fallback (length, mentions a file or an error) if the call is slow. Store the key as `SW_ANTHROPIC_KEY` in `.env`, never `ANTHROPIC_API_KEY`. |
| Hooks | Claude Code `UserPromptSubmit` + `Stop` | Can add context or block with a reason; can't rewrite the prompt |
| Wrist tap | **ntfy.sh** (priority 5) → nbz's phone → Garmin smart notifications | Long random topic name |
| Voice | macOS `say` → a speaker (not AirPods, so the camera hears it) | |
| Server | **FastAPI** + server-sent events | One process on the demo laptop |
| Judge view | One HTML page + **uPlot** or Chart.js, no build step | Lucas builds it |
| Judge screen | **Lucas's laptop**, browser full-screen, reading nbz's laptop over the phone hotspot | Fallback: judge view split-screen on nbz's laptop. (the hotspot can't work: it needs the same Apple ID on both devices.) |
| Recording | **OBS**: scene = screen + webcam, replay buffer on a hotkey; Lucas's phone, handheld, for the wrist close-up | Install before 12:30 |
| Editing | **CapCut** (auto-captions) or iMovie | nbz's pick |
| Repo | GitHub, private until 7:00 | `gh repo create revive --private` |
| Network | Lucas's phone hotspot | Venue Wi-Fi can block laptop-to-laptop traffic |

## 6. What the judge view looks like
One screen, landscape judge screen, dark background, readable from 2 m away. It's for judges only; the user never sees it.
```
┌───────────────────────────────────────────────────────────────────────┐
│ REVIVE · live · nbz                         4:09 PM · H10 ● live │
├───────────────────────────────────────┬───────────────────────────────┤
│  HEART RATE  96 bpm   (base 68)       │  NOW                          │
│  ~~~~~~~~~~~~~~~~~/\/\/\__/‾‾‾‾\      │  ● STRAINED  +28 bpm, HRV −46%│
│  HRV (RMSSD)  22 ms   (base 41)       │                               │
│  ‾‾‾‾‾‾‾‾\_____________/‾\____        │  Last prompt  2/10            │
│  ▲ prompt dots on the timeline        │  missing: context, success    │
│    (green = good, red = vague)        │                               │
│                                       │  ACTION → wrist tap           │
│                                       │  "Slow down: context added"   │
├───────────────────────────────────────┴───────────────────────────────┤
│ DECISION LOG                                                          │
│ 4:09:12  prompt 2/10 + strained → TAP + added last error, 2 files     │
│ 4:09:40  solved in 1 turn (similar prompts today: 3.4 turns)          │
│ 3:52:05  prompt 7/10, calm → no action                                │
│ 3:31:18  loop: same error ×3, HRV falling → HOLD + voice              │
├───────────────────────────────────────────────────────────────────────┤
│ TODAY  42 prompts · 6 nudges · 4 accepted · turns saved ≈ ?   ●REAL   │
└───────────────────────────────────────────────────────────────────────┘
```
Every number comes from the event log. Anything replayed shows a **REPLAY** badge instead of **REAL**.

## 7. The video (90 s, the most important deliverable)
Most judges score only the form: description + GitHub + video. Two judges are remote and see nothing else.

| Seconds | Picture | Sound / caption |
| --- | --- | --- |
| 0–6 | Cold open, tight: nbz types `hrv is broken fix it`. The Garmin buzzes on their wrist (close-up). | Caption: "It noticed before I did." |
| 6–12 | Title card: **Revive**. The one-liner. | Voice-over: "Revive… No app." |
| 12–20 | nbz at the laptop, strap visible. One stat. | "You've been prompting for 4 hours. Your heart rate is up 28. Your prompts are getting worse, and you can't tell." |
| 20–55 | **The hero shot: one continuous take, split screen.** Left: nbz, no phone in hand. Right: the judge screen. Heart rate climbs → lazy prompt → score 2/10 → wrist tap → context added → Claude solves it first try. | Narrate the hidden work: "It reads the strap… grades the prompt… taps the wrist… adds the error Claude needed." |
| 55–70 | Two charts, each with n: grader validity (low scores need ×? more turns), today's body × work pattern | "Learned from real data: 5 hours today, 30 days of baselines." |
| 70–80 | Diagram + "Built today, 1:45–6:30 PM" + what's replayed or labeled, then ~5 s of the portal | "We built it while wearing it. It nudged us X times today. Nothing to open day to day; when you're curious, there's a page." |
| 80–90 | End card: name, GitHub, "one-line install", team | "Heavy AI users pay $12 a month. It spreads as a Claude Code plugin." |

### The hero shot, step by step (locked Sat 11:30: a real bug from today, replayed from git)
**The bug:** the H10 reader's HRV number blows up when the wearer moves. Lucas hit it for real at 11:30 (squats → dropped beats and fake 2–5 s intervals → RMSSD ~1,300 ms instead of ~5–20). In the build, nbz writes the reader **without** the filter first, so the bug happens again for real.

**How it's set up during the build:**
1. **2:05–2:35 (nbz):** write `body/polar.py` the simple way first (no artifact filter). Do squats; when RMSSD explodes, `git commit` and `git tag hero-bug`. Save the squat trace to `fixtures/squats_rr.jsonl`.
2. Add a check that fails on the bug: `uv run pytest tests/test_rmssd.py` (RMSSD of the squat fixture must be under 100 ms).
3. Fix it (the filter in §3), commit. The fix is the normal build; the tag keeps the broken version.

**The take (about 30 s, at 5:15):**
1. Reset: `git switch -c take-N hero-bug` on the demo laptop. Claude Code open in the repo, a fresh session.
2. nbz does 20 squats off camera; the strap shows strained (the trigger is real).
3. Camera rolls. nbz runs the test: red, RMSSD 1,300.
4. nbz types the lazy prompt: **"hrv is broken fix it"**.
5. Revive: score ~2/10 (missing context, done) + strained → **wrist tap** ("Slow down: context added") + the silent fix attaches the failing test output and `body/polar.py`.
6. Claude fixes it; nbz reruns the test: **green**. One take, no cuts.
7. the judge screen shows every step in the decision log.

**Label in the video:** "A real bug we hit at 11:30, replayed from git at 5:15." If Claude doesn't solve it on the first try in a take, keep the take honest or redo it, never edit it to look like it did.

**Rules:** the hero shot is one take, no cuts inside it. Every number is real (blank it rather than invent it). Captions burned in. 90 s max: cut content, don't speed it up. Save real nudges from the day with the OBS replay hotkey; if one is good, it replaces the staged hero shot.

**Staged, and said out loud:** the squats that raise the heart rate, the planted bug, the scripted lazy prompt. **Never:** a slider posing as a sensor, a number we didn't measure, claiming causation.

## 8. The live table demo (2 min)
1. "Revive notices when your body and your AI work are both going off the rails." (10 s)
2. Point at the judge screen: nbz's live heart rate against their 30-day baseline. (15 s)
3. nbz does 20 squats: "I'm raising my heart rate on purpose; the real one happened at 4:09, it's in the log." (30 s)
4. **The judge dictates a 3-word prompt** for nbz to type → wrist buzz, context added, solved. (30 s)
5. The number and today's log. (20 s)
6. Who pays, then questions. Answers to the hard questions are in [plan.md](plan.md#hard-questions-one-line-answers). (15 s)

## 9. Submission (draft now, finish at 6:50)
- **Title:** Revive
- **Tagline:** Your body knows you're about to waste an hour with AI. Revive taps your wrist first.
- **Description (fill the blanks after 5:15):** Revive joins a live heart-rate strap with your Claude Code session. Every prompt is graded; when your prompts get vague *and* your body is strained, it fixes the prompt silently, taps your wrist, and stops you when you're looping. No app, no dashboard. Built and worn at the event: __ prompts captured, __ nudges, __ accepted. Low-scored prompts needed __× more turns (n = __).
- **README sections:** what it does · demo video · how it works (the diagram) · what's real vs. replayed (DEMO_NOTES) · run it · privacy · built today (commit history).

## 10. If the rules change
The opening and rules run 1:15–1:45, and tracks plus the submission link are only announced then. Decide each of these on the spot, in under 2 minutes, then move on.
| If they say… | Then |
| --- | --- |
| The **Unsupervised** track fits better or has its own prize | Same build. Lead the story with the loop stop and the stop rules ("knows when the human-plus-AI pair is stuck and stops it"), and show the run log. |
| **No screen at all**, even for the coder | We're fine: the user gets a tap and a voice. The laptop is the work, not our UI. Say so in the pitch. |
| **Video ≤ 60 s** | Drop 12–20 and 70–80; the hero shot shrinks to 25 s. |
| **Live demos decide it**, not the video | Move the backup video to 4:45 and spend 5:15–6:10 rehearsing the table demo (the top 5 also demo on stage at 7:45). |
| **A sponsor tool is required or rewarded** | Use it where it's cheapest (e.g. Latted for the 5-second opener). Don't put it on the critical path. |
| **No pre-written config** (the kit) | Skip the kit; Claude Code writes CLAUDE.md fresh at 1:45 (5 min). |
| **The theme is narrower than "Invisible Interfaces"** | Re-check the one-liner against their words in RUBRIC.md; keep the build. |
| **Bluetooth or the H10 fails** | Garmin heart-rate broadcast (heart rate only, no HRV). Last resort: replay today's recorded trace, labeled REPLAY. |

### Questions for a host
1. Is judging on the video and GitHub, live demos, or both? Is there a live finalist round?
2. Video length limit, and where do we submit?
3. Must all code be written after 1:45? Is a config-only starter kit OK?
4. How do the two remote judges see projects?
5. Do judges walk the floor during the build?

## 11. Before 12:45 (today)
| # | Who | Task | Time | Done when |
| --- | --- | --- | --- | --- |
| 0 | Lucas | **Add $40 of Console credit for nbz's Claude Code** (see row 1 for where) | 5 min | Credit shows in the Console |
| 3 | Lucas | Copy `~/.claude/projects` into `data-private/lucas/` (Claude can do it on your OK). Grading itself starts after 1:45. | 2 min | Copied |
| 4 | Lucas | ~~Pair-test the H10 with the Mac~~ Done 11:30: connects, 88→134 bpm on squats, RR intervals present (needs the artifact filter above) | | ✅ |
| 5 | Lucas | `gh auth status` OK; OBS installed; hotspot tested (uv is installed: `~/.local/bin/uv`) | 10 min | |
| 6 | nbz | Accept the Console invite, install Claude Code, sign in, one test prompt; check `echo $ANTHROPIC_API_KEY` is empty | 15 min | Usage shows in Lucas's Console |
| 7 | nbz | Garmin 30-day table done (per [nbz's guide](https://docs.google.com/document/d/1bzPzjAoNmYCeZKjfRULLuisEKQ3pD1zVMoG_AbCc5Zg/edit)) and sent to Lucas | 20 min | CSV received |
| 8 | nbz | ntfy app installed, subscribed to the topic, test push **buzzes the Garmin**; find "Broadcast Heart Rate" on the watch | 10 min | Wrist buzzed |
| 9 | nbz | Python 3.12 + uv + git; GitHub username sent to Lucas | 10 min | |
| 10 | Both | Read this page; write 3 predictions with a timestamp into `pitch/predictions.md` (e.g. "prompts get worse after the 3:30 gate", "loops happen after 5 PM", "prompts written at +15 bpm need more turns") | 10 min | Saved |
| 11 | Both | Pack: chargers, power strip, Garmin charged, H10 | | |

**Hard rules:** no product code before 1:45 · keys only in `.env`, pasted by a person · no customer or NDA data anywhere in the repo, video or README · nobody on camera without their OK.
