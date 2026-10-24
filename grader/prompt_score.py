"""Prompt score: "given what Claude already knows, can it do the right thing on the first try?" (0-10).

Follows docs/plan/grader-rubric.md. Length-blind. Never sees heart data or Claude's reply to this prompt.
Usage: uv run python -m grader.prompt_score "fix it"
"""
import json
import re
import sys
import time

from grader._llm import call_tool

TYPES = ["new_task", "follow_up", "confirmation", "question", "exploration"]
SCORED = {"new_task", "follow_up"}
PATTERNS = ["directive", "feedback_loop", "task_iteration", "learning", "validation"]
MAX = {"context": 3, "done": 3, "goal": 2, "scope": 1, "why": 1}

# Context fields the caller may pass (all optional, short summaries) and their char caps.
CONTEXT_CAPS = {
    "last_assistant": 800,
    "last_tool_error": 500,
    "files_touched": 300,
    "session_goal": 300,
    "project_summary": 600,
    "user_profile": 400,
}

SYSTEM = """You grade one prompt a developer typed into Claude Code. The question: given what Claude already knows at this point (the context below), can it do the right thing on the first try? Length-blind: a short prompt can be perfect, a long one can be bad. "yes, do it" right after Claude proposed a plan is a perfect prompt.

STEP 1: type
- new_task: a new ask ("add a reader for the H10")
- follow_up: a fix or next step on the current work ("still broken", "now make it faster")
- confirmation: "yes", "go ahead", "looks good", "do it" (approving what Claude proposed)
- question: wants an explanation, no change ("what does RMSSD mean?")
- exploration: open-ended looking around ("what's in this repo?", "how could we approach X?")
Only new_task and follow_up get checks; for the others set every check to 0 (ignored).

STEP 2: checks (count what Claude ALREADY HAS from the context as given)
context 0-3: the error, the file, what was tried, or a pointer to it (@file, "look at hr.py", a URL, an existing pattern), unless Claude already has it.
  0 = "hrv is broken fix it" with no error/file in the context
  1 = a hint: "the reader is acting up"
  2 = one clear pointer: "the RMSSD in body/hrv.py is wrong"
  3 = everything needed: "body/hrv.py:42 raises ZeroDivisionError when rr is empty" OR the error is already in Claude's last turn / last tool error
done 0-3: what "fixed" looks like, sized to the task.
  0 = none on a non-trivial task ("fix it")
  1 = implied ("make it work")
  2 = a stated result ("bpm stops showing 0")
  3 = a checkable test ("the squat test prints RMSSD under 20", "pytest tests/test_hrv.py passes"). A trivial one-line change ("rename foo to bar in x.py") scores 3 without one; on a big task, "plan first" or "ask me questions first" scores 2-3.
goal 0-2:
  0 = "fix it", "make it better"
  1 = a vague direction ("make the chart nicer")
  2 = a specific result ("show RMSSD as a line, last 10 min")
scope 0-1: 1 = bounded: what to touch / not touch, or limits Claude can't see ("only hr.py; the strap drops beats when moving"). 0 otherwise.
why 0-1: 1 = the intent is stated ("so the coach doesn't fire on squats"). 0 otherwise.

bundled: true only if unrelated asks are mixed in one prompt (steps of one task are fine).
pattern (Anthropic Economic Index): directive (do this task), feedback_loop (here's an error/result, fix it), task_iteration (refine prior work), learning (explain/teach me), validation (check/review this).
intent: one short line per layer of what this prompt is trying to achieve: immediate (this prompt), session (the session's goal), project (the project). Use "" if unknown.
reason: one line, plain, naming what's missing or why it's good.

Answer only through the grade_prompt tool."""

TOOL = {
    "name": "grade_prompt",
    "description": "Record the grade for this prompt.",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": TYPES},
            "context": {"type": "integer", "minimum": 0, "maximum": 3},
            "done": {"type": "integer", "minimum": 0, "maximum": 3},
            "goal": {"type": "integer", "minimum": 0, "maximum": 2},
            "scope": {"type": "integer", "minimum": 0, "maximum": 1},
            "why": {"type": "integer", "minimum": 0, "maximum": 1},
            "bundled": {"type": "boolean"},
            "pattern": {"type": "string", "enum": PATTERNS},
            "reason": {"type": "string"},
            "intent": {
                "type": "object",
                "properties": {
                    "immediate": {"type": "string"},
                    "session": {"type": "string"},
                    "project": {"type": "string"},
                },
                "required": ["immediate", "session", "project"],
            },
        },
        "required": ["type", "context", "done", "goal", "scope", "why", "bundled", "pattern", "reason", "intent"],
    },
}


def _context_block(context: dict) -> str:
    lines = []
    for key, cap in CONTEXT_CAPS.items():
        val = context.get(key)
        if isinstance(val, (list, tuple)):
            val = ", ".join(map(str, val))
        if val:
            lines.append(f"{key}: {str(val)[:cap]}")
    return "\n".join(lines) or "(none: this is the first prompt, Claude knows nothing yet)"


def _missing(checks: dict | None) -> list[str]:
    """What the silent fix can add: context/done at a hint or less, goal absent."""
    if not checks:
        return []
    out = []
    if checks["context"] <= 1:
        out.append("context")
    if checks["done"] <= 1:
        out.append("done")
    if checks["goal"] == 0:
        out.append("goal")
    return out


def _finish(type_: str, checks: dict | None, bundled: bool, reason: str, pattern: str,
            intent: dict, source: str, latency_ms: int, error: str | None = None) -> dict:
    scored = type_ in SCORED
    if scored:
        checks = {k: max(0, min(MAX[k], int(checks.get(k, 0)))) for k in MAX}
    else:
        checks = None
    out = {
        "type": type_,
        "score": sum(checks.values()) if scored else None,
        "checks": checks,
        "bundled": bool(bundled),
        "missing": _missing(checks),
        "reason": reason,
        "pattern": pattern if pattern in PATTERNS else "directive",
        "intent": {k: str(intent.get(k, "")) for k in ("immediate", "session", "project")},
        "source": source,
        "latency_ms": latency_ms,
    }
    if error:
        out["error"] = error
    return out


# --- heuristic fallback (no key, timeout, any error) ---

_CONFIRM = re.compile(r"^(y(es|ep|eah)?|ok(ay)?|sure|go( ahead)?|do it|ship it|looks good|lgtm|perfect|great|"
                      r"sounds good|proceed|continue|approved?)\b", re.I)
_QUESTION = re.compile(r"^(what|why|how|when|where|who|which|is|are|does|do|can|could|should|explain)\b", re.I)
_EXPLORE = re.compile(r"\b(what's in|look around|explore|how could we|options for|brainstorm|ideas for)\b", re.I)
_FOLLOW = re.compile(r"\b(still|again|now|also|instead|same|that didn't|didn't work|not working)\b", re.I)
_FILE = re.compile(r"(@\S+|\b[\w/.-]+\.(py|js|ts|tsx|html|css|json|md|toml|yaml|yml|sh|sql)\b|https?://)", re.I)
_ERROR = re.compile(r"\b(\w+Error|Exception|Traceback|line \d+|exit code|stack trace|errno|\d{3} (error|status))\b", re.I)
_TEST = re.compile(r"\b(pytest|tests?/|test_\w+|passes|should (print|return|show)|prints|returns|expect(ed)?|assert)\b", re.I)
_RESULT = re.compile(r"\b(should|so that it|until|stops?|shows?|instead of|under|over|at least|no longer)\b", re.I)
_VAGUE = re.compile(r"\b(fix (it|this)|still broken|doesn'?t work|make it (work|better)|it'?s broken|is broken|"
                    r"broken|do something|clean (it )?up)\b", re.I)
_SCOPE = re.compile(r"\b(only|don'?t touch|do not|without|leave .* alone|just the|limit)\b", re.I)
_WHY = re.compile(r"\b(so that|so the|because|in order to|otherwise|the reason)\b", re.I)


def heuristic_grade(prompt: str, context: dict | None = None, error: str | None = None) -> dict:
    context = context or {}
    p = prompt.strip()
    words = p.split()
    if _CONFIRM.match(p) and len(words) <= 8:
        type_ = "confirmation"
    elif _EXPLORE.search(p):
        type_ = "exploration"
    elif p.endswith("?") or (_QUESTION.match(p) and len(words) <= 15 and not _VAGUE.search(p)):
        type_ = "question"
    elif _FOLLOW.search(p) or context.get("last_assistant"):
        type_ = "follow_up"
    else:
        type_ = "new_task"

    has_file, has_error = bool(_FILE.search(p)), bool(_ERROR.search(p))
    ctx = 3 if (has_file and has_error) or context.get("last_tool_error") else 2 if (has_file or has_error) else 0
    done = 3 if _TEST.search(p) else 2 if _RESULT.search(p) else 0
    vague = bool(_VAGUE.search(p))
    goal = 0 if vague and len(words) < 8 else 2 if len(words) >= 12 else 1
    checks = {"context": ctx, "done": done, "goal": goal,
              "scope": int(bool(_SCOPE.search(p))), "why": int(bool(_WHY.search(p)))}
    pattern = ("validation" if re.search(r"\b(review|check|verify)\b", p, re.I)
               else "learning" if type_ == "question"
               else "feedback_loop" if has_error or vague
               else "task_iteration" if type_ == "follow_up" else "directive")
    return _finish(type_, checks, False, "heuristic fallback (keyword checks)", pattern,
                   {"immediate": p[:60], "session": str(context.get("session_goal", ""))[:60],
                    "project": str(context.get("project_summary", ""))[:40]},
                   "heuristic", 0, error)


def grade_prompt(prompt: str, context: dict | None = None) -> dict:
    """Grade one prompt. Never raises; falls back to the heuristic on timeout or any error."""
    context = context or {}
    t0 = time.monotonic()
    user = f"CONTEXT (what Claude already knows)\n{_context_block(context)}\n\nPROMPT TO GRADE\n<<<\n{prompt}\n>>>"
    try:
        r, latency_ms = call_tool(SYSTEM, user, TOOL)
        return _finish(r["type"], r, r.get("bundled", False), r.get("reason", ""), r.get("pattern", ""),
                       r.get("intent") or {}, "llm", latency_ms)
    except Exception as e:  # timeout, no key, API error, bad output
        out = heuristic_grade(prompt, context, error=type(e).__name__ + (f": {e}" if str(e) else ""))
        out["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return out


if __name__ == "__main__":
    print(json.dumps(grade_prompt(" ".join(sys.argv[1:]) or "fix it"), indent=2))
