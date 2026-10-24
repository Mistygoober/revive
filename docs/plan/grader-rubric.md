# Revive grader rubric (v1, locked)

Sat Oct 24, 11:20. Built from Lucas's draft v0 plus [research/07-prompt-scoring.md](research/07-prompt-scoring.md) (Anthropic, Claude Code, OpenAI, Google, Microsoft/GitHub, research). Weights and additions chosen by Lucas at 11:25.

## The question it answers
**"Given what Claude already knows at this point in the conversation, can it do the right thing on the first try?"** Not "is this a long or polished prompt". "yes, do it" right after Claude proposes a plan is a perfect prompt. Length-blind on purpose: LLM judges are known to favor longer answers (Zheng et al.).

## Two scores per turn (added Sat 12:00, Lucas's comments)
Every prompt is judged against **what it was trying to achieve**, at five layers of context, and later against **what Claude actually produced**.

**Context layers** the grader gets (as short summaries, not raw text):
1. **Immediate conversation:** the last 2–3 turns, the last tool error.
2. **Session:** the session's goal (inferred from its first prompt or task list) and progress so far.
3. **Project:** CLAUDE.md / README of the repo, the folder.
4. **User:** a short profile of how this person works (from `memory/insights/`).
5. **Company / domain:** org-level instructions, if any.

**Score 1: prompt score (before the reply).** The rubric below, 0–10. Drives the live nudges. Never sees Claude's reply to this prompt.

**Score 2: outcome score (after the reply, from the Stop hook, finalized at the end of the task).** "Did what Claude produced deliver what this prompt was trying to achieve?" Inputs: the inferred intent, Claude's final message, tool results and errors, files changed, and whether the next prompt was a correction. Output: **achieved / partial / missed / wrong direction** (mapped to 3 / 2 / 1 / 0) plus one line why.

**Inferred intent:** the grader writes one line per layer, e.g. `immediate: fix the HRV number · session: H10 reader working · project: Revive`. Shown on the judge view as "Intent → Got".

**Validity check, upgraded:** does the prompt score predict the outcome score and turns to done?

## Step 1: classify (only real asks get scored)
| Type | Example | Scored? |
| --- | --- | --- |
| New task | "add a reader for the H10" | Yes |
| Follow-up / fix | "still broken", "now make it faster" | Yes |
| Confirmation | "yes", "go ahead", "looks good" | No |
| Question | "what does RMSSD mean?" | No |
| Exploration | "what's in this repo?", "how could we approach X?" | No (Claude Code: vague is fine when exploring) |

## Step 2: five checks, total 0–10 (locked Sat 11:25)
Weights chosen by Lucas: context and the done check carry the most, matching the research's core three (goal, context, verification).

| Check | Pts | Levels |
| --- | --- | --- |
| **Context**: the error, the file, what was tried, *or a pointer to it* (@file, "look at hr.py", an existing pattern, a URL), unless Claude already has it | 0–3 | 0 = missing and Claude doesn't have it · 1 = a hint ("the reader") · 2 = most of it, or one clear pointer · 3 = everything Claude needs is given, pointed to, or already in the last turn |
| **Done check**: what "fixed" looks like, sized to the task | 0–3 | 0 = none on a non-trivial task · 1 = implied ("make it work") · 2 = a stated result ("bpm stops showing 0") · 3 = a checkable test ("the squat test prints RMSSD under 20"). A trivial one-line change scores 3 without one; on a big task, "plan first" or "ask me questions first" scores 2–3 |
| **Goal**: the specific outcome wanted | 0–2 | 0 = "fix it" · 1 = a vague direction · 2 = a specific result |
| **Scope and constraints**: what to touch, what not to, limits Claude can't see | 0–1 | 1 = bounded ("only hr.py; the strap drops beats when moving") |
| **Why**: the intent behind the ask | 0–1 | 1 = stated ("so the coach doesn't fire on squats") |

**Flag, not points:** `bundled` = unrelated asks mixed in one prompt (steps within one task are fine). It's logged and counted in the metrics but doesn't change the score.

**Check after 2 PM:** on Lucas's 775 prompts, see which checks best predict extra turns. If the data disagrees with these weights, say so in DEMO_NOTES rather than quietly changing them.

## Output (one JSON object per prompt)
```json
{"type": "follow_up", "score": 3, "checks": {"context": 0, "done": 0, "goal": 1, "scope": 1, "why": 0}, "bundled": false,
 "missing": ["context", "done"], "reason": "No error or file given, and Claude's last turn didn't include them.",
 "pattern": "feedback_loop",
 "intent": {"immediate": "fix the HRV number", "session": "H10 reader working", "project": "Revive"}}
```
Outcome (Stop hook): `{"outcome": "achieved", "points": 3, "why": "filter added; test passes", "next_prompt_correction": false}`
```json
{}
```
- `missing` drives the silent fix: `context` → attach the last error and the touched files; `done` → add "say how you verified it".
- `pattern` uses the Anthropic Economic Index labels (directive, feedback_loop, task_iteration, learning, validation), so our numbers can be compared with Anthropic's published Claude Code shares.

## What the grader sees and doesn't
- **Sees:** the prompt, Claude's previous reply (summarized to about 800 characters), the last tool error, the files touched in the last 3 turns.
- **Never sees:** heart data (otherwise "strained → lower scores" would be built in, which is circular), or Claude's reply *to this prompt* (hindsight).
- Model: Claude Haiku 5.5, temperature 0, anchored examples of 0/1/2 for every check in the system prompt. Target under 3 s; heuristic fallback if slower.

## Session-level rules (beyond one prompt)
- **Corrections:** 3 or more corrections in one session → suggest `/clear` and a fresh restate (Claude Code's own rule). This feeds the loop stop.
- Score trend within a session feeds the fatigue slope in [metrics.md](metrics.md).

## Proving it works (two numbers)
1. **Agreement with an expert:** Lucas hand-scores a calibration set; the grader must match within 1 point on at least 80%. Lucas writes them **later today** (his call, Sat 11:25): 10 made-up prompts (great, terrible, short-but-perfect), ideally before the grader is wired at ~3:00, 20 more in the 5:00 slot if time allows. The research suggests about 30.
2. **Validity:** on Lucas's 775 past prompts, do low-scored prompts need more turns to done? Report the ratio with n. No published study links real developers' prompt quality to outcomes, so this would be a new result.

Prompts are graded only through the Anthropic API. Prompts naming the customer are dropped first. Only scores and counts leave the Mac; no prompt text ever goes in the repo, video or README.
