# Revive metrics, by time window

Draft, Sat Oct 24, 11:20. The question every metric answers: **how well is this person working with AI, and when does that change?** Prompt grading is one input; this page covers the rest. Research backing for the prompt rubric: [prompt-scoring-research.md](prompt-scoring-research.md).

## What the data can actually see
Checked on Lucas's history (70 sessions, Oct 17–24; counts only, no content read):

| Signal | Where it comes from | Present? |
| --- | --- | --- |
| Every prompt and reply, with timestamps, session, folder | Claude Code transcripts | Yes |
| Tokens (so cost) per reply | `usage` on every assistant message | Yes (10,961 replies) |
| Tool calls by type (edits, writes, shell, browser, web search, sheets) | `tool_use` | Yes |
| Tool errors | `tool_result` with `is_error` | Yes (215) |
| User interruptions (Esc mid-reply) | "[Request interrupted by user]" | Yes (3) |
| **Task lists with done / pending steps** | Task-list tool calls (`update_plan` in the desktop app; `TodoWrite` / task tools in the CLI) | Yes (538 updates) |
| End-of-turn recap | `wrap_up` in the desktop app | Yes (345) |
| Git commits | `git log` | Only for code projects; **most of Lucas's work has no git** |
| Body: heart rate, HRV (live), sleep, resting HR, stress (30 days) | Polar H10, Garmin | nbz only |

**Task boundary rule** (used by "turns to done" and "tasks left undone"): a task starts at a *new-task* prompt and ends at the first of: a task-list step marked completed, a commit, or the user moving on to a different task. Commits alone don't work, because most AI work isn't code.

## The windows
| Window | Used for | Who sees it |
| --- | --- | --- |
| **Now** (rolling 15 min) | Live coaching: should Revive step in? | Nobody; the coach acts on it |
| **Prompt** | Grade + silent fix | Logged; judge view |
| **Task** | Did it get done, and how painfully? | Portal |
| **Session** | One sitting with Claude | Portal |
| **Day** | "How was my AI day?" | Portal, end-of-day tap |
| **Week / 30 days** | Patterns and "AI Wrapped" | Portal, share card |

## Metric catalog
### 1. Time ("Screen Time for AI")
| Metric | Definition | Windows |
| --- | --- | --- |
| Active time | Time with activity, merging gaps under 5 min | session, day, week |
| Sessions | Count of sessions with ≥ 1 real prompt | day, week |
| Session length | Median and longest active time per session | day, week |
| Your time vs. AI time | Your read/think time (reply done → your next prompt) vs. waiting time (your prompt → reply done) | session, day |
| Longest stretch without a break | Active time with no gap ≥ 10 min | day |
| Hour-of-day profile | Active time and average prompt score per hour | day, 30 days |
| Parallel sessions | Max sessions active at once | day |
| Context switches | Changes of project folder per active hour | day |

### 2. Output (what got made)
| Metric | Definition | Windows |
| --- | --- | --- |
| Tasks completed | Task-list steps marked completed, plus commits | session, day, week |
| Files created / edited | Write and Edit tool calls (distinct files) | session, day |
| Lines changed | From edits and `git diff --stat` | session, day |
| Commits | `git log` in project folders | day, week |
| Other outputs | Published pages, sheet updates, docs, drafts (tool calls by type) | day, week |

### 3. Unfinished work
| Metric | Definition | Windows |
| --- | --- | --- |
| **Tasks left undone** | Task-list steps still pending or in progress when the session ends | session, day |
| Abandoned tasks | A new-task prompt followed by no completion signal before the session ends | session, day |
| Interrupted replies | User stopped Claude mid-reply | session, day |
| Completion rate | Tasks completed ÷ tasks started | day, week |

### 4. Prompt quality (from the grader)
| Metric | Definition | Windows |
| --- | --- | --- |
| Prompt score | 0–10 per scored prompt (rubric in GAMEPLAN / grader-rubric) | prompt |
| Average score | Mean over scored prompts | session, day, week |
| Weak-prompt rate | % of scored prompts under 4 | session, day |
| Most-missed check | Which rubric check is most often 0 (context, done check…) | day, week |
| Fatigue slope | Change in score from the first to the last hour of a session or day | session, day |

### 5. Efficiency (how painful was it)
| Metric | Definition | Windows |
| --- | --- | --- |
| **Turns to done** | Your prompts per completed task | task, day |
| Corrections | Prompts starting "no / still / wrong / that's not" per task | task, day |
| Tool errors | Errors per task | task, day |
| Loops | Count and minutes (loop definition in GAMEPLAN §2) | session, day |
| Tokens / cost per completed task | Sum of usage ÷ tasks completed | day, week |

### 6. Body (nbz; joined on timestamps)
| Metric | Definition | Windows |
| --- | --- | --- |
| Strain minutes | Minutes with `strain = strained` | session, day |
| HR / HRV vs. baseline | Average difference from nbz's 30-day baseline | now, session, day |
| Sleep the night before | From the Garmin history | day |
| Body × work | Score, turns to done and loops when strained vs. calm | day, 30 days |

### 7. Revive itself (does the coach help?)
| Metric | Definition | Windows |
| --- | --- | --- |
| Nudges fired | By level (fix, tap, hold + voice) | day |
| Accepted | Rated useful, or the next prompt improved | day |
| Turns saved | Turns to done on nudged tasks vs. similar un-nudged ones | day, week |
| False alarms | Nudges rated "not now" | day |

## Headlines (one screen per window, no composite "productivity score")
A single blended score would be vague, and judges will poke at it. Each window shows 3–4 named numbers instead:
- **Session:** active time · tasks done / started · avg prompt score · loops
- **Day:** active time · tasks done · tasks left undone · turns to done · best and worst hour
- **Week / 30 days:** completion rate trend · score by hour of day · sleep → next-day score · "AI Wrapped" card

## What gets built today (the rest is "what's next")
**Build:** prompt score, turns to done, tasks completed / left undone, active time, session length, loops, strain minutes, nudges fired / accepted. That covers the day and session windows on the portal, plus the validity number.
**Show from history, not live:** hour-of-day profile and completion rate over Lucas's week.
**Next:** context switches, parallel sessions, other outputs, week and 30-day trends.
