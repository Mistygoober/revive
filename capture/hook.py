"""Claude Code hook: logs every prompt and every reply for Revive.

Wired in .claude/settings.json for UserPromptSubmit and Stop. Reads the hook
JSON from stdin. Never blocks the user and never crashes: any error is logged
to data/hook_errors.log and the hook exits 0 with no output.

events.jsonl gets metadata only (no text). Raw text goes to memory/raw/
(git-ignored) so the grader can score it.
"""
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import DATA_DIR  # noqa: E402
from shared.events import append_event, append_raw  # noqa: E402


def _heuristic_grade(prompt: str) -> dict:
    """Stand-in until grader/ lands. Same output shape, marked heuristic."""
    p = prompt.strip().lower()
    if p in {"yes", "y", "ok", "go", "go ahead", "do it", "yes do it", "looks good", "continue"}:
        return {"type": "confirmation", "scored": False, "score": None, "missing": [], "source": "heuristic"}
    has_context = any(k in p for k in ("error", "traceback", ".py", "/", "line ", "test"))
    has_done = any(k in p for k in ("test", "pass", "should print", "expect", "until"))
    score = min(10, (3 if has_context else 0) + (3 if has_done else 0) + (2 if len(p) > 60 else 1) + (1 if " so " in p or "because" in p else 0))
    missing = [m for m, ok in (("context", has_context), ("done", has_done)) if not ok]
    return {"type": "follow_up", "scored": True, "score": score, "missing": missing, "source": "heuristic"}


def _grade(prompt: str, ctx: dict) -> dict:
    try:
        from grader.prompt_score import grade_prompt  # built by the grader session
        g = grade_prompt(prompt, ctx)
        g.setdefault("scored", g.get("type") in ("new_task", "follow_up"))
        return g
    except Exception:
        return _heuristic_grade(prompt)


def _tap(text: str) -> bool:
    try:
        from act.tap import tap  # nbz's version
    except Exception:
        from coach.act_fallback import tap
    return tap(text)


def on_prompt(data: dict) -> None:
    import os

    from body.state import get_body_state
    from coach.context import recent_context, silent_fix_text
    from coach.policy import decide

    prompt = data.get("prompt") or ""
    session = data.get("session_id", "")
    append_raw("prompts", {"session": session, "cwd": data.get("cwd", ""), "prompt": prompt})
    append_event("prompt", session=session, chars=len(prompt), project=Path(data.get("cwd") or ".").name)
    if os.getenv("REVIVE_COACH", "1") == "0":
        return

    ctx = recent_context(data.get("transcript_path", ""))
    grade = _grade(prompt, ctx)
    append_event("grade", session=session, **{k: v for k, v in grade.items() if k not in ("reason_text",)})
    body = get_body_state()
    decision = decide(grade, body)
    if decision.get("level") is None:
        return

    channels = decision.get("channels", [])
    added = silent_fix_text(ctx, grade.get("missing", [])) if "fix" in channels else ""
    can_tap = os.getenv("REVIVE_TAP", "1" if os.getenv("REVIVE_WHO") == "nbz" else "0") == "1"
    tapped = _tap("Slow down: context added") if ("tap" in channels and can_tap) else False
    append_event("action", session=session, level=decision["level"], channels=channels,
                 tapped=tapped, message="Slow down: context added" if tapped else "context added",
                 reason=decision.get("reason"), demo=body.get("source") in ("fake", "replay"))
    if added:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": added}}))


def on_stop(data: dict) -> None:
    session = data.get("session_id", "")
    last = data.get("last_assistant_message") or ""
    append_raw("replies", {"session": session, "reply": last, "transcript": data.get("transcript_path", "")})
    append_event("reply", session=session, chars=len(last))


def main() -> int:
    t0 = time.time()
    try:
        data = json.loads(sys.stdin.read() or "{}")
        event = data.get("hook_event_name", "")
        if event == "UserPromptSubmit":
            on_prompt(data)
        elif event == "Stop":
            on_stop(data)
    except Exception:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with (DATA_DIR / "hook_errors.log").open("a") as f:
            f.write(f"{time.ctime()} ({time.time() - t0:.2f}s)\n{traceback.format_exc()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
