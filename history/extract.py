"""Parse Claude Code transcripts into an in-memory list of real typed prompts. Prints counts only.

Raw transcripts stay in data-private/. Nothing here writes prompt text anywhere.
Usage: uv run python -m history.extract
"""
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from shared.config import ROOT

DEFAULT_DIR = (ROOT / os.getenv("DATA_PRIVATE_DIR", "../data-private")).resolve() / "lucas" / "projects"

# Injected blocks that are not the user's words.
_INJECTED = re.compile(r"<(system-reminder|artifact-view-context)[^>]*>.*?</\1>", re.S)
_PASTED = re.compile(r"<pasted_content[^>]*>(.*?)</pasted_content>", re.S)
# Typed prompts that are really hook / command / shell outputs.
_NOT_TYPED = ("<bash-input>", "<bash-stdout>", "<command-name>", "<command-message>", "<local-command",
              "<task-notification>", "<scheduled-task", "[Request interrupted")

# --- drop filter (confidentiality rules; applied before any grading) ---
MAX_CHARS = 4000
# Names that must never be graded live in a private file outside the repo (one regex per line).
BLOCKLIST = Path(os.getenv("REVIVE_BLOCKLIST", str((ROOT / os.getenv("DATA_PRIVATE_DIR", "../data-private")).resolve() / "blocklist.txt")))


def _load_blocklist() -> re.Pattern | None:
    try:
        terms = [t.strip() for t in BLOCKLIST.read_text(encoding="utf-8").splitlines() if t.strip()]
    except OSError:
        return None
    return re.compile("|".join(terms), re.I) if terms else None


_CUSTOMER = _load_blocklist()
_PT_WORDS = {"não", "nao", "você", "voce", "está", "são", "também", "então", "porque", "para", "uma", "com",
             "que", "dos", "das", "pelo", "pela", "isso", "esse", "essa", "muito", "mais", "em", "os", "ao",
             "é", "pra", "seu", "sua", "foi", "ser", "tem", "como", "mas", "quando", "valor", "dia", "mês"}
_PT_CHARS = re.compile(r"[ãõçÃÕÇ]")


def _portuguese(text: str, min_hits: int) -> bool:
    words = re.findall(r"\w+", text.lower())
    hits = sum(w in _PT_WORDS for w in words)
    return (hits >= min_hits and hits / max(1, len(words)) >= 0.08) or len(_PT_CHARS.findall(text)) >= 3


def drop_reason(text: str) -> str | None:
    """Why a prompt must never be graded, or None. Order: customer name, Portuguese data, length."""
    if _CUSTOMER is None:  # fail closed: never grade without the private blocklist
        raise RuntimeError(f"Private blocklist missing at {BLOCKLIST}; refusing to grade.")
    if _CUSTOMER.search(text):
        return "customer_name"
    if any(_portuguese(p, 3) for p in _PASTED.findall(text)) or _portuguese(text, 8):
        return "portuguese"
    if len(text) > MAX_CHARS:
        return "too_long"
    return None


@dataclass
class Prompt:
    session: str
    idx: int                 # position among this session's real prompts
    ts: datetime
    text: str                # in memory only; never written out
    cwd: str
    prev_assistant_len: int  # chars of Claude's last text reply before this prompt (0 = first prompt)
    prev_tool_error: bool    # the turn before this prompt ended with a tool error
    # Filled from what happens after the prompt, up to the next real prompt:
    tool_errors: int = 0
    tool_calls: int = 0
    plan_ops: list = field(default_factory=list)  # ("plan", input) / ("wrap_up", None) / ("todo", input)
    interrupted: bool = False
    next_text: str | None = None  # the next real prompt's text (memory only)


@dataclass
class Session:
    id: str
    path: str
    timestamps: list = field(default_factory=list)  # every user/assistant event, for active time
    prompts: list = field(default_factory=list)
    other_turns: int = 0  # turns started by side sessions, notifications, schedules


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _user_text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def is_real_prompt(d: dict) -> str | None:
    """The typed text if this transcript line is a prompt Lucas typed, else None."""
    if d.get("type") != "user" or "toolUseResult" in d or d.get("isMeta"):
        return None
    if d.get("turnOrigin", "human") != "human" or d.get("promptSource") == "system":
        return None
    if (d.get("origin") or {}).get("kind", "human") != "human":
        return None
    text = _INJECTED.sub("", _user_text(d.get("message", {}).get("content", ""))).strip()
    if not text or text.startswith(_NOT_TYPED):
        return None
    return text


def parse_session(path: Path) -> Session:
    s = Session(id=path.stem, path=str(path))
    last_text_len, last_err, cur = 0, False, None
    for line in path.open():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = d.get("type")
        if t not in ("user", "assistant") or not d.get("timestamp"):
            continue
        s.timestamps.append(_ts(d["timestamp"]))
        if t == "assistant":
            for b in d.get("message", {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    last_text_len = len(b["text"])
                elif b.get("type") == "tool_use" and cur is not None:
                    cur.tool_calls += 1
                    name, inp = b.get("name", ""), b.get("input") or {}
                    if name.endswith("update_plan"):
                        cur.plan_ops.append(("plan", inp))
                    elif name.endswith("wrap_up"):
                        cur.plan_ops.append(("wrap_up", None))
                    elif name == "TodoWrite":
                        cur.plan_ops.append(("todo", inp))
            continue
        content = d.get("message", {}).get("content")
        if "toolUseResult" in d:
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                        last_err = True
                        if cur is not None:
                            cur.tool_errors += 1
                    elif isinstance(b, dict) and b.get("type") == "tool_result":
                        last_err = False
            continue
        if cur is not None and "[Request interrupted" in _user_text(content or ""):
            cur.interrupted = True
        text = is_real_prompt(d)
        if text is None:
            if not d.get("isMeta"):
                s.other_turns += 1
            continue
        p = Prompt(session=s.id, idx=len(s.prompts), ts=_ts(d["timestamp"]), text=text, cwd=d.get("cwd", ""),
                   prev_assistant_len=last_text_len, prev_tool_error=last_err)
        if cur is not None:
            cur.next_text = text
        s.prompts.append(p)
        cur, last_err = p, False
    s.timestamps.sort()
    return s


def load_sessions(root: Path = DEFAULT_DIR) -> list[Session]:
    files = sorted(f for f in Path(root).rglob("*.jsonl") if "subagents" not in f.parts)
    return [s for s in (parse_session(f) for f in files)]


def drop_counts(prompts: list[Prompt]) -> Counter:
    return Counter(drop_reason(p.text) or "kept" for p in prompts)


def main() -> None:
    sessions = load_sessions()
    prompts = [p for s in sessions for p in s.prompts]
    drops = drop_counts(prompts)
    print(f"sessions: {len(sessions)}  with prompts: {sum(1 for s in sessions if s.prompts)}")
    print(f"real typed prompts: {len(prompts)}  other turns (side sessions, notifications): "
          f"{sum(s.other_turns for s in sessions)}")
    print(f"drop filter: {dict(drops)}")
    print(f"prompts with a tool error after them: {sum(1 for p in prompts if p.tool_errors)}  "
          f"tool errors total: {sum(p.tool_errors for p in prompts)}")
    print(f"prompts whose turn touched a task list: {sum(1 for p in prompts if p.plan_ops)}")


if __name__ == "__main__":
    main()
