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


def on_prompt(data: dict) -> None:
    prompt = data.get("prompt") or ""
    session = data.get("session_id", "")
    append_raw("prompts", {"session": session, "cwd": data.get("cwd", ""), "prompt": prompt})
    append_event("prompt", session=session, chars=len(prompt), project=Path(data.get("cwd") or ".").name)


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
