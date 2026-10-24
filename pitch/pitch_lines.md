# Pitch lines

Lead with the work going wrong; the body is the *why* and the *when*. Lucas: the problem, how it works, the numbers. Noam: the body side and the live moment. Every number here comes from a file in the repo (sources at the bottom).

## The 2-minute live demo
**Setup:** judge view full-screen on Lucas's laptop (`/web/judge/`), Noam's laptop with Claude Code open on the `hero-bug` branch, strap on, phone locked and on the hotspot.

| Time | Who | What to say / do |
| --- | --- | --- |
| 0:00–0:15 | Lucas | "When you work with AI all day, your prompts get vaguer, you loop on the same error, you drift to YouTube and skip breaks, and from the inside you can't tell. Revive notices and steps in before you waste an hour. No app." |
| 0:15–0:35 | Noam | Points at the judge screen. "This is my heart rate and HRV live from this strap, against my own baseline from 19 days of my Garmin data. It's the *when*: Revive steps in earlier when my body is strained." |
| 0:35–0:50 | Noam | Does 20 squats. "I'm raising my heart rate on purpose so you can see it. The judge screen will flip to strained." |
| 0:50–1:10 | Noam | "Give me a three-word prompt for this bug." Types the judge's prompt. Wrist buzzes; holds up the Garmin. "That's the tap. It also quietly added the failing test and the files Claude needed." |
| 1:10–1:25 | Lucas | Points at the decision log. "Behind the scenes: Claude Code hooks send every prompt to a grader before Claude sees it. Vague prompt plus strained body: add context, tap the wrist. Noam never opened anything. It also taps you back from YouTube mid-block and tells you to take five after 90 minutes." |
| 1:25–1:45 | Lucas | "Is the grade worth anything? On a week of my own past prompts, the bottom third by score took 1.42 times as many turns to finish as the top third, n 60 vs 48, p 0.034. It agrees with my own scoring on 7 of 10 test prompts. One person, so: associated with, not caused by." |
| 1:45–2:00 | Lucas | "Heavy AI users pay about $12 a month. It spreads as a one-line Claude Code plugin and a shareable Wrapped card." Noam shows the Wrapped card. "Questions?" |

**If the judge's prompt is actually good:** Revive does nothing. Say: "That's correct, it only steps in when it's needed. Try a vaguer one."
**If Claude is slow:** talk over the judge view: "Here's what Revive already did."
**If the buzz doesn't come:** check the phone is locked; the judge view still shows WRIST TAP sent.

## One-line answers
| Question | Answer |
| --- | --- |
| What's mocked? | Nothing in the live moment: the strap, hooks, grader, silent fix and wrist tap are live; the squats and the lazy prompt are staged, the bug is a real one replayed from git, the focus demo uses 20-second thresholds instead of 90, and any seeded events are badged DEMO DATA. Full list in DEMO_NOTES.md. |
| Who pays? | Heavy AI users, about $12/month; it spreads as a one-line Claude Code plugin plus shareable Wrapped cards. |
| Why won't Whoop, Anthropic or Cursor build it? | Whoop sees your body but not your work; Anthropic and Cursor see your work but not your body, and they sell usage, so telling you to stop isn't their job. Revive joins both, on your laptop, across tools. |
| n = 1? | Personal patterns are the point; for every number we show n, effect size and p, and we disclose the cut we tried first (1.24×, p = 0.095). More users would add population priors. |
| Isn't it creepy? | It runs on your laptop and only you see it; body data never leaves it, prompts go only to Claude for grading (they were Claude prompts already), the focus watcher keeps the app and domain, never page titles or URLs, and there's no employer view. |
| Is it medical? | No. It's performance coaching with no diagnosis; heart rate is one signal, not a cause. |
| What breaks first? | The network: the wrist tap goes through ntfy, so we run on a phone hotspot. If the grader takes over 3 s, a heuristic score is used and labeled; if the strap slips, RMSSD shows blank instead of a fake number. |
| Cost per prompt? | One Claude Haiku 5.5 call, at most 600 output tokens, 1.7–2.2 s through the running server; that's [__]¢ per prompt (today's Console spend ÷ prompts graded today). |
| How do you know the grade is right? | On 10 prompts Lucas scored before seeing the grader, it agreed on 7 (within 1 point, or both left it unscored); where it disagreed it was stricter on vague asks. |

## Sources
- 19 days of Garmin data: `body/baselines_nbz.json`
- 1.42×, n = 60 vs. 48, p = 0.034; first cut 1.24×, p = 0.095: `history/results.json`, `history/SUMMARY.md`
- 7 of 10: `grader/calibration/results_set1.json`
- 90 s distraction, 90 min break, 20 s demo timing: `focus/watch.py`
- 3 s cap, 600 output tokens: `grader/_llm.py`; 1.7–2.2 s: DEMO_NOTES.md (status at 3:25 PM)
- $12/month: `docs/plan/GAMEPLAN.md` §1
