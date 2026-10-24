"""Claude Code hook: logs every prompt and every reply for Revive.

Wired in .claude/settings.json for UserPromptSubmit and Stop. Reads the hook
JSON from stdin. Never blocks the user and never crashes: any error is logged
to data/hook_errors.log and the hook exits 0 with no output.

Fast path: if the Revive server is running, the hook is a thin client that
POSTs the stdin JSON to /hook (warm Anthropic client, no imports to pay for)
and prints what comes back. If nothing listens there, it runs in-process.

events.jsonl gets metadata only (no text). Raw text goes to memory/raw/
(git-ignored) so the grader can score it.
"""
import json
import os
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


def on_prompt(data: dict) -> dict | None:
    """Log, grade, coach. Returns the hook output (additionalContext) or None."""
    from body.state import get_body_state
    from coach.context import recent_context, silent_fix_text
    from coach.outcome import looks_like_correction
    from coach.policy import decide

    prompt = data.get("prompt") or ""
    session = data.get("session_id", "")
    append_raw("prompts", {"session": session, "cwd": data.get("cwd", ""), "prompt": prompt})
    append_event("prompt", session=session, chars=len(prompt), project=Path(data.get("cwd") or ".").name,
                 correction=looks_like_correction(prompt))
    if os.getenv("REVIVE_COACH", "1") == "0":
        return None

    ctx = recent_context(data.get("transcript_path", ""))
    grade = _grade(prompt, ctx)
    append_event("grade", session=session, **{k: v for k, v in grade.items() if k not in ("reason_text",)})
    body = get_body_state()
    decision = decide(grade, body)
    if decision.get("level") is None:
        return None

    channels = decision.get("channels", [])
    added = silent_fix_text(ctx, grade.get("missing", [])) if "fix" in channels else ""
    can_tap = os.getenv("REVIVE_TAP", "1" if os.getenv("REVIVE_WHO") == "nbz" else "0") == "1"
    tapped = _tap("Slow down: context added") if ("tap" in channels and can_tap) else False
    append_event("action", session=session, level=decision["level"], channels=channels,
                 tapped=tapped, message="Slow down: context added" if tapped else "context added",
                 reason=decision.get("reason"), demo=body.get("source") in ("fake", "replay"))
    if added:
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": added}}
    return None


def on_stop(data: dict, outcome: bool = True) -> None:
    session = data.get("session_id", "")
    last = data.get("last_assistant_message") or ""
    append_raw("replies", {"session": session, "reply": last, "transcript": data.get("transcript_path", "")})
    append_event("reply", session=session, chars=len(last))
    if outcome:
        score_outcome(data)


def score_outcome(data: dict) -> None:
    """Outcome score for the turn that just ended. Errors are logged, never raised."""
    if os.getenv("REVIVE_COACH", "1") == "0":
        return
    try:
        from coach.outcome import score_turn
        score_turn(data)
    except Exception:
        _log_error("outcome")


def _log_error(where: str, t0: float | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    took = f" ({time.time() - t0:.2f}s)" if t0 else ""
    with (DATA_DIR / "hook_errors.log").open("a") as f:
        f.write(f"{time.ctime()} [{where}]{took}\n{traceback.format_exc()}\n")


def handle(data: dict, outcome: bool = True) -> dict | None:
    """The whole hook, in this process. The server calls this too (with outcome=False, then scores it in the background)."""
    event = data.get("hook_event_name", "")
    if event == "UserPromptSubmit":
        return on_prompt(data)
    if event == "Stop":
        on_stop(data, outcome)
    return None


SERVER = os.getenv("REVIVE_SERVER", "http://127.0.0.1:8000")
SERVER_TIMEOUT_S = 2.5
# Per-prompt settings the server should apply as if it were this process.
FORWARD_ENV = ("FAKE_STRAIN", "REVIVE_TAP", "REVIVE_COACH", "REVIVE_WHO")


def via_server(data: dict) -> tuple[bool, dict | None]:
    """(handled, output). handled=False only when no Revive server answered, so the caller can run in-process.
    A slow server counts as handled: it already logged the events, so running again would double them."""
    import socket
    import urllib.error
    import urllib.request

    body = json.dumps({"data": data, "env": {k: os.environ[k] for k in FORWARD_ENV if k in os.environ}}).encode()
    req = urllib.request.Request(f"{SERVER}/hook", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=SERVER_TIMEOUT_S) as r:
            return True, json.loads(r.read() or b"{}").get("output")
    except urllib.error.HTTPError:
        return False, None  # something else on the port, or an old server without /hook
    except (TimeoutError, socket.timeout):
        _log_error("server timeout")
        return True, None
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            _log_error("server timeout")
            return True, None
        return False, None  # connection refused: server not running


def main() -> int:
    t0 = time.time()
    try:
        data = json.loads(sys.stdin.read() or "{}")
        handled, out = (False, None) if os.getenv("REVIVE_INPROC") == "1" else via_server(data)
        if not handled:
            out = handle(data)
        if out:
            print(json.dumps(out))
    except Exception:
        _log_error("hook", t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
