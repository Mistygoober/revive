"""Reads the Claude Code transcript to build the grader's context and the silent fix."""
import json
import re
from pathlib import Path

MAX_LINES = 400
_SHELL_OUT = re.compile(r"<bash-(?:stdout|stderr)>(.*?)(?:</bash-(?:stdout|stderr)>|$)", re.S)
_FAILED = re.compile(r"\b(FAILED|failed|Error|Traceback|AssertionError|error:)")


def _shell_error(text: str) -> str:
    """Output of a failing `!` command the user ran inside Claude Code (e.g. a red test), else ""."""
    if "<bash-stdout>" not in text and "<bash-stderr>" not in text:
        return ""
    out = "\n".join(m.strip() for m in _SHELL_OUT.findall(text) if m.strip())
    return out if _FAILED.search(out) else ""


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
            if e.get("type") == "user" and block.get("type") == "text":
                shell_err = _shell_error(block.get("text", ""))
                if shell_err:
                    last_error = shell_err[-2000:]
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


def _is_prompt(entry: dict) -> bool:
    """A real user prompt (not a tool result, not a meta entry)."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    blocks = _content(entry)
    return bool(blocks) and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks)


def last_turn(transcript_path: str) -> dict:
    """What happened since the last user prompt: Claude's final text, tool errors, files changed (outcome score)."""
    entries = _tail(transcript_path, 2000)
    start = max((i for i, e in enumerate(entries) if _is_prompt(e)), default=-1)
    final, errors, files = "", [], []
    for e in entries[start + 1:]:
        for block in _content(e):
            if not isinstance(block, dict):
                continue
            if e.get("type") == "assistant" and block.get("type") == "text":
                final = block.get("text", "")
            if block.get("type") == "tool_use" and block.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                fp = (block.get("input") or {}).get("file_path") or (block.get("input") or {}).get("notebook_path")
                if fp and fp not in files:
                    files.append(fp)
            if block.get("type") == "tool_result" and block.get("is_error"):
                c = block.get("content")
                errors.append((c if isinstance(c, str) else json.dumps(c))[:500])
    return {"assistant_final": final[-1500:], "tool_errors": errors[-5:], "files_changed": files[-20:]}
