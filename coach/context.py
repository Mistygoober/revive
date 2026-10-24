"""Reads the Claude Code transcript to build the grader's context and the silent fix."""
import json
from pathlib import Path

MAX_LINES = 400


def _tail(path: str, n: int = MAX_LINES) -> list[dict]:
    p = Path(path or "")
    if not p.is_file():
        return []
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def _content(entry: dict) -> list:
    msg = entry.get("message") or {}
    c = msg.get("content") if isinstance(msg, dict) else None
    return c if isinstance(c, list) else ([{"type": "text", "text": c}] if isinstance(c, str) else [])


def recent_context(transcript_path: str) -> dict:
    """Last assistant text, last tool error, files touched, first prompt (session goal)."""
    entries = _tail(transcript_path)
    last_assistant, last_error, files, first_prompt = "", "", [], ""
    for e in entries:
        for block in _content(e):
            if not isinstance(block, dict):
                continue
            if e.get("type") == "assistant" and block.get("type") == "text":
                last_assistant = block.get("text", "")
            if block.get("type") == "tool_use" and block.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                fp = (block.get("input") or {}).get("file_path")
                if fp and fp not in files:
                    files.append(fp)
            if block.get("type") == "tool_result" and block.get("is_error"):
                c = block.get("content")
                last_error = c if isinstance(c, str) else json.dumps(c)[:2000]
            if e.get("type") == "user" and block.get("type") == "text" and not first_prompt:
                t = block.get("text", "")
                if t and not t.startswith("<"):
                    first_prompt = t
    return {
        "last_assistant": last_assistant[-800:],
        "last_error": last_error[-1500:],
        "files_touched": files[-5:],
        "session_goal": first_prompt[:300],
    }


def silent_fix_text(ctx: dict, missing: list[str]) -> str:
    """The context Revive adds to a vague prompt (level 0). Under 1,500 characters."""
    parts = ["[Revive added context: the prompt above was terse, so here is what it most likely refers to.]"]
    if "context" in missing:
        if ctx.get("last_error"):
            parts.append("Most recent error in this session:\n" + ctx["last_error"][-700:])
        if ctx.get("files_touched"):
            parts.append("Files changed recently: " + ", ".join(ctx["files_touched"]))
    if "done" in missing:
        parts.append("Before finishing, run the relevant test or command and say how you verified the fix.")
    text = "\n\n".join(parts)
    return text[:1500] if len(parts) > 1 else ""
