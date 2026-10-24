"""Outcome score (Stop hook): did what Claude produced deliver what the prompt was trying to achieve?

achieved / partial / missed / wrong_direction -> 3 / 2 / 1 / 0. See docs/plan/grader-rubric.md.
"""
import json
import re
import sys
import time

from grader._llm import call_tool

POINTS = {"achieved": 3, "partial": 2, "missed": 1, "wrong_direction": 0}

SYSTEM = """You judge one Claude Code turn after it finished: did what Claude produced deliver what the developer's prompt was trying to achieve?
You get the inferred intent (immediate / session / project), the prompt, Claude's final message, tool errors, files changed, and the developer's next prompt if there is one.
- achieved: the immediate intent was delivered (and verified if it could be).
- partial: real progress, but something asked for is missing, unverified, or still failing.
- missed: little or nothing that was asked got done (errors left unresolved, Claude gave up or only asked questions).
- wrong_direction: Claude did something other than what was meant (wrong file, wrong feature, misread the ask).
next_prompt_correction: true if the next prompt corrects or redirects Claude ("still broken", "no, I meant...", "that's wrong"); false if it moves on, approves, or there is no next prompt.
Do not reward long replies; judge only against the intent. why: one short line.
Answer only through the grade_outcome tool."""

TOOL = {
    "name": "grade_outcome",
    "description": "Record the outcome grade for this turn.",
    "input_schema": {
        "type": "object",
        "properties": {
            "outcome": {"type": "string", "enum": list(POINTS)},
            "why": {"type": "string"},
            "next_prompt_correction": {"type": "boolean"},
        },
        "required": ["outcome", "why", "next_prompt_correction"],
    },
}

_CORRECTION = re.compile(r"\b(still|again|no,|nope|wrong|not what|i meant|didn'?t work|doesn'?t work|broken|"
                         r"undo|revert|that's not|isn'?t working)\b", re.I)
_GAVE_UP = re.compile(r"\b(i couldn'?t|unable to|i can'?t|not sure how|failed to)\b", re.I)


def _finish(outcome: str, why: str, correction: bool, source: str, latency_ms: int, error: str | None = None) -> dict:
    outcome = outcome if outcome in POINTS else "partial"
    out = {"outcome": outcome, "points": POINTS[outcome], "why": why,
           "next_prompt_correction": bool(correction), "source": source, "latency_ms": latency_ms}
    if error:
        out["error"] = error
    return out


def heuristic_outcome(assistant_final: str, tool_errors: list[str], files_changed: list[str],
                      next_prompt: str | None, error: str | None = None) -> dict:
    correction = bool(next_prompt and _CORRECTION.search(next_prompt))
    if correction and not files_changed:
        outcome, why = "missed", "next prompt is a correction and nothing changed"
    elif correction:
        outcome, why = "partial", "files changed but the next prompt is a correction"
    elif _GAVE_UP.search(assistant_final or "") or (tool_errors and not files_changed):
        outcome, why = "missed", "errors left unresolved"
    elif tool_errors:
        outcome, why = "partial", "changes made with tool errors along the way"
    else:
        outcome, why = "achieved", "no errors and no correction followed"
    return _finish(outcome, f"heuristic: {why}", correction, "heuristic", 0, error)


def grade_outcome(intent: dict, prompt: str, assistant_final: str, tool_errors: list[str],
                  files_changed: list[str], next_prompt: str | None) -> dict:
    """Grade one finished turn. Never raises; falls back to the heuristic on timeout or any error."""
    t0 = time.monotonic()
    intent = intent or {}
    user = "\n".join([
        "INTENT",
        *(f"{k}: {intent.get(k, '')}" for k in ("immediate", "session", "project")),
        f"\nPROMPT\n<<<\n{prompt[:1500]}\n>>>",
        f"\nCLAUDE'S FINAL MESSAGE\n<<<\n{(assistant_final or '')[:1500]}\n>>>",
        f"\nTOOL ERRORS ({len(tool_errors or [])})\n" + "\n".join(e[:200] for e in (tool_errors or [])[-5:]),
        f"\nFILES CHANGED: {', '.join((files_changed or [])[:20]) or '(none)'}",
        f"\nNEXT PROMPT: {next_prompt[:500] if next_prompt else '(none yet)'}",
    ])
    try:
        r, latency_ms = call_tool(SYSTEM, user, TOOL)
        return _finish(r["outcome"], r.get("why", ""), r.get("next_prompt_correction", False), "llm", latency_ms)
    except Exception as e:
        out = heuristic_outcome(assistant_final, tool_errors, files_changed, next_prompt,
                                error=type(e).__name__ + (f": {e}" if str(e) else ""))
        out["latency_ms"] = int((time.monotonic() - t0) * 1000)
        return out


if __name__ == "__main__":
    # uv run python -m grader.outcome_score '{"intent": {...}, "prompt": "...", "assistant_final": "...", ...}'
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    print(json.dumps(grade_outcome(args.get("intent", {}), args.get("prompt", ""), args.get("assistant_final", ""),
                                   args.get("tool_errors", []), args.get("files_changed", []),
                                   args.get("next_prompt")), indent=2))
