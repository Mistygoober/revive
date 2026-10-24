"""Loop detector (level 2): the same thing tried again and again in the last 15 minutes of a session.

A loop needs at least 3 of these signals:
  repeat_prompts  - 2+ prompts are retries ("still broken", "try again", "fix it") or near-duplicates
  same_error      - the same error text shows up twice (tool errors in the transcript, or pasted in prompts)
  frustration     - "no", "wrong", "wtf", "!!!" ...
  no_progress     - no passing test and no commit in the window
A single bad prompt never counts: it takes 3+ prompts in the window, and the current prompt and the
one before it must both be retries or frustrated (a streak). Cooldown 15 minutes between holds.
"""
import json
import re
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from shared import config

WINDOW_S = 15 * 60
HOLD_COOLDOWN_S = 15 * 60
MIN_SIGNALS = 3

_RETRY = re.compile(r"\b(still (broken|failing|fails|not|wrong|the same|happening)|try again|fix it|same (error|thing|issue)|"
                    r"again|didn'?t work|doesn'?t work|not working|isn'?t working)\b", re.I)
_FRUSTRATION = re.compile(r"^\s*no+\b|\b(wrong|wtf|ffs|ugh+|argh+|seriously|come on)\b|!!!|\?!", re.I)
_ERROR_LINE = re.compile(r"^.*\b\w*(Error|Exception)\b.*$|^.*\bTraceback\b.*$", re.M)
_TEST_CMD = re.compile(r"\b(pytest|npm (run )?test|jest|vitest|cargo test|go test|unittest)\b")
_COMMIT_CMD = re.compile(r"\bgit commit\b")


def _ts(s: str) -> float | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _clean(text: str) -> str:
    """Drop injected blocks (<system-reminder>, <task-notification> ...): their boilerplate looks like a repeat."""
    return re.sub(r"<([a-z][\w-]*)>.*?</\1>", " ", text or "", flags=re.S).strip()


def _norm(text: str) -> str:
    t = re.sub(r"0x[0-9a-f]+|\d+", "#", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()[:160]


def window_prompts(session: str, now: float) -> list[tuple[float, str]]:
    """(ts, text) of this session's prompts in the last 15 min, oldest first (memory/raw/prompts.jsonl)."""
    path = config.RAW_DIR / "prompts.jsonl"
    if not session or not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = _ts(r.get("ts", ""))
        if r.get("session") == session and t is not None and now - WINDOW_S <= t <= now + 5:
            out.append((t, r.get("prompt") or ""))
    return out


def _result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ""


def transcript_window(transcript_path: str, now: float) -> dict:
    """Tool errors (oldest first) and whether a test passed or a commit landed, in the last 15 min."""
    errors, progress, commands = [], False, {}
    p = Path(transcript_path or "")
    if not p.is_file():
        return {"errors": [], "progress": False}
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()[-2000:]:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = _ts(e.get("timestamp", ""))
        if t is not None and t < now - WINDOW_S:
            continue
        msg = e.get("message") or {}
        blocks = msg.get("content") if isinstance(msg, dict) else None
        for b in blocks if isinstance(blocks, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "Bash":
                commands[b.get("id")] = (b.get("input") or {}).get("command", "")
            elif b.get("type") == "tool_result":
                text, cmd = _result_text(b), commands.get(b.get("tool_use_id"), "")
                if b.get("is_error"):
                    errors.append(text)
                elif _COMMIT_CMD.search(cmd):
                    progress = True
                elif _TEST_CMD.search(cmd) and re.search(r"\bpassed\b", text) and not re.search(r"\b(failed|error)\b", text, re.I):
                    progress = True
    return {"errors": errors, "progress": progress}


def is_retry(text: str, earlier: list[str]) -> bool:
    """A retry phrase, or a near-duplicate of an earlier prompt in the window."""
    if _RETRY.search(text):
        return True
    n = _norm(text)
    return bool(n) and any(SequenceMatcher(None, n, _norm(o)).ratio() >= 0.75 for o in earlier if o.strip())


def is_loop_prompt(text: str, earlier: list[str]) -> bool:
    return is_retry(text, earlier) or bool(_FRUSTRATION.search(text))


def check_loop(session: str, prompt: str, transcript_path: str, now: float | None = None,
               state: dict | None = None) -> dict | None:
    """None, or {signals, minutes, last_error}. Call after the current prompt is in prompts.jsonl."""
    now = now or time.time()
    if state is not None and now - state.get("last_hold", 0) < HOLD_COOLDOWN_S:
        return None
    prompts = window_prompts(session, now)
    if not prompts or prompts[-1][1] != prompt:
        prompts.append((now, prompt))
    texts = [_clean(t) for _, t in prompts]
    if len(prompts) < 3:
        return None
    flags = [is_loop_prompt(t, texts[:i]) for i, t in enumerate(texts)]
    streak = next((i for i in range(len(flags)) if all(flags[i:])), len(flags))  # first index of the trailing streak
    if len(flags) - streak < 2:
        return None

    tw = transcript_window(transcript_path, now)
    errors = tw["errors"] + [m.group(0) for t in texts for m in _ERROR_LINE.finditer(t)]
    seen, repeated = set(), False
    for err in errors:
        k = _norm(err)
        if k and k in seen:
            repeated = True
        seen.add(k)
    retries = sum(is_retry(t, texts[:i]) for i, t in enumerate(texts))
    signals = [name for name, on in (
        ("repeat_prompts", retries >= 2),
        ("same_error", repeated),
        ("frustration", any(_FRUSTRATION.search(t) for t in texts)),
        ("no_progress", not tw["progress"]),
    ) if on]
    if len(signals) < MIN_SIGNALS:
        return None
    first = prompts[max(streak - 1, 0)][0]  # from the original ask the streak keeps retrying
    return {"signals": signals, "minutes": round((now - first) / 60, 1), "last_error": errors[-1] if errors else ""}


_FIXES = [
    (r"ModuleNotFoundError|ImportError|No module named", "check the package is installed in this env and the import path is right"),
    (r"ZeroDivisionError|division by zero", "guard the empty case before the division instead of patching the formula"),
    (r"KeyError", "print the keys of the dict right before the failing lookup"),
    (r"AttributeError|NoneType", "print what the value actually is one line before it fails; it's probably None"),
    (r"TypeError", "print the types going into the failing call"),
    (r"FileNotFoundError|No such file", "ls the path it names and check the working directory"),
    (r"SyntaxError|IndentationError", "open the exact line the error names and check brackets and indents"),
    (r"AssertionError|assert|FAILED|failed", "run only the failing test with -x -vv and read the diff before editing"),
    (r"[Tt]imeout|Connection|refused|ECONN", "check the service is up (curl it) before changing code"),
    (r"[Pp]ermission denied|EACCES", "check who owns the file and the permissions, not the code"),
]


def suggestion(last_error: str) -> str:
    for pat, fix in _FIXES:
        if re.search(pat, last_error or ""):
            return fix
    if last_error:
        return "write a 5-line repro of that one error and fix the smallest piece first"
    return "say in one sentence what you expect vs what you see, then ask Claude for a different approach"


def hold_reason(loop: dict) -> str:
    same = "same error" if "same_error" in loop["signals"] else "no progress"
    return f"Three tries, {same}. Different approach: {suggestion(loop.get('last_error', ''))}. Take two minutes."
