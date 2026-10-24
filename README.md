# Revive

**Revive connects how your body is doing with how your AI work is going, and steps in before you waste an hour. No app.**

- A heart-rate strap and your Garmin tell Revive how strained you are, now and today.
- Claude Code hooks grade every prompt you send (Claude Haiku 5.5, under 3 s).
- When a vague prompt meets a strained body, Revive adds the missing context to the prompt and taps your wrist. You never open anything.

Demo video: [__]

## The moment
1. nbz has been squatting next to the laptop; the strap reads strained (heart rate well above baseline, HRV down).
2. A test is red. nbz types `hrv is broken fix it`.
3. Revive grades it ~2/10 (no context, no definition of done). Vague + strained → **silent fix**: the hook attaches the failing test output and the files just edited. **Wrist tap**: "Slow down: context added".
4. Claude fixes the bug; the test goes green. The judge view shows each step in the decision log.

The bug is real (we hit it at 11:30 AM) and replayed from a git tag. The squats and the lazy prompt are staged, and we say so in the video.

## How it works
```
Polar H10 ─BLE─▶ body/ ─▶ heart rate, RMSSD vs. 30-day baseline ─┐
Garmin ─────────▶ body/ ─▶ last night's sleep, Body Battery ─────┤ get_body_state()
                                                                 ▼
Claude Code ─hooks─▶ capture/ ─▶ grader/ ─▶ coach/ ─┬─▶ wrist tap   (ntfy → phone → Garmin)
 (UserPromptSubmit,                                 ├─▶ added context (hook additionalContext)
  Stop)                                             └─▶ hold         (loops; not built yet)
        │                │             │
        ▼                ▼             ▼
                 data/events.jsonl  (one line per step, no prompt text)
                         │
                         ▼
          server.py ─▶ web/judge/  (judge view, "behind the scenes")
```
Right now `body/` is a labeled stub (fixed values, `source: "fake"`) until the H10 reader lands; see [DEMO_NOTES.md](DEMO_NOTES.md).
- **Grader** (`grader/`): two checks per turn. A prompt score 0–10 before Claude replies (context, done check, goal, scope, why; rubric in [docs/plan/grader-rubric.md](docs/plan/grader-rubric.md)), and an outcome score after (achieved / partial / missed / wrong direction). Falls back to a keyword heuristic if the API call takes over 3 s. The outcome score runs from the `Stop` hook (`coach/outcome.py`).
- **Coach** (`coach/`): score ≤ 4 → silent fix. Score ≤ 4 and strained → silent fix + wrist tap. At most one tap per 20 minutes. A poor night (under 6 h sleep or Body Battery under 40) makes it step in earlier.
- **Judge view** (`web/judge/`): live heart rate and HRV, prompt scores, and every coach decision, read from the event log. Only judges see it.

## The numbers
**On Lucas's own Claude Code prompts (Oct 17–24, 665 typed prompts, 239 real asks scored):**
- Higher prompt scores are **associated with** fewer turns to done (Spearman ρ = −0.24, p = 0.003, n = 170) and a higher achieved rate (ρ = +0.23, p = 0.001, n = 229).
- Bottom vs. top third of scores (≤ 2, n = 60, vs. ≥ 4, n = 48): **1.8 vs. 1.27 turns to done (1.42×, permutation p = 0.034, Cliff's δ 0.24)**; achieved 45% vs. 73% (n = 83 vs. 56, p = 0.0007).
- This was the second cut we tried; the first (buggy) cut gave 1.24×, p = 0.095. The pre-registered split (≤ 4 vs. ≥ 7) is underpowered: only 3 prompts scored ≥ 7 (1.23×, p = 0.82).
- No association between time of day and prompt score (ρ = 0.03).

Source: [history/results.json](history/results.json), summary in [history/SUMMARY.md](history/SUMMARY.md). One person, one week, observational. Caveats in [DEMO_NOTES.md](DEMO_NOTES.md#validity-caveats-from-historysummarymd).

**Today, built and worn at the event:** [__] prompts captured, [__] nudges, [__] solved after a nudge.

**Predictions** (written 12:11 PM, before any code, locked at 12:13: [pitch/predictions.md](pitch/predictions.md)). Checked at 5:15 PM:
| Prediction | Result |
| --- | --- |
| Our prompts get worse as the day goes on (last build hour ≥ 1 point lower than the first) | [checked at 5:15] |
| Prompts written while nbz is strained need ≥ 1.3× more turns, or reach "achieved" less often | [checked at 5:15] |
| At least 2 of every 3 loops start after the 3:30 gate | [checked at 5:15] |
| Main validity check: low scores (≤ 4) reach "achieved" less often than high (≥ 7) | Direction holds (46% vs. 67%), but n = 3 for ≥ 7, so p = 0.60: not shown. |

## What's real and what's replayed
Hooks, grader, coach, silent fix, wrist tap and judge view are real. Body state is a labeled stub until the H10 reader lands. The hero bug is real and replayed from git. Seeded events are badged DEMO DATA. Full table: [DEMO_NOTES.md](DEMO_NOTES.md).

## Privacy
- Body data and raw prompts stay on the laptop. Raw prompt and reply text is kept in `memory/raw/`, which is git-ignored.
- The event log stores metadata only (lengths, scores, actions), never prompt text.
- Prompts are sent to the Anthropic API for grading; they were Claude prompts already.
- The wrist tap sends a fixed short phrase to ntfy.sh, nothing else.
- The repo holds aggregates only. Past prompts that named a customer were filtered out before grading, with a blocklist kept outside the repo.

## Run it
```bash
uv sync
cp .env.example .env    # then fill in REVIVE_ANTHROPIC_KEY and NTFY_TOPIC yourself
uv run uvicorn server:app --host 0.0.0.0 --port 8000
```
- Judge view: http://localhost:8000/web/judge/
- Hooks load automatically when you open Claude Code in this folder (`.claude/settings.json`). Set `REVIVE_WHO=nbz` on the laptop that should tap the wrist.
- Without the strap: `FAKE_STRAIN=strained` in `.env`. Without live events: `uv run python scripts/fake_events.py --fast` (badged DEMO DATA).
- Tests: `uv run pytest`. History numbers: `uv run python -m history.validity` (needs the private grade cache, not in the repo).

## Built today
Sat Oct 24, 1:45–6:30 PM, at c0mpiled-16 (UCSD). No product code before 1:45; the plan docs in `docs/plan/` were written beforehand. See the commit history.

## Team
- **Lucas** – the Claude side: hooks, grader, coach, history numbers, judge view.
- **nbz (Noam)** – the health side: Polar H10 reader, HRV, Garmin baselines, wrist tap; live subject in the video.

## What's next
- **Agents over per-person memory:** a health agent, a Claude-usage agent, a combined agent that joins the two, short-term and long-term memory agents, and a researcher that proposes small personal experiments.
- **Two kinds of memory, kept apart:** raw facts (`memory/raw/`, never altered) and generated insights (`memory/insights/`, always labeled as generated).
- Loop detection with hold + voice, and more devices.
