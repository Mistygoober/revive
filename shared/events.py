"""The shared event log: one JSON object per line in data/events.jsonl.

Every event has ts, who and kind. Kinds: body, prompt, grade, action, loop,
outcome, reply, mark. Never put prompt text here; raw text goes to memory/raw/.
"""
import json
from datetime import datetime
from typing import Any

from shared.config import DATA_DIR, EVENTS_PATH, RAW_DIR, WHO


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_event(kind: str, who: str | None = None, **fields: Any) -> dict:
    event = {"ts": now_iso(), "who": who or WHO, "kind": kind, **fields}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_events(last: int | None = None) -> list[dict]:
    if not EVENTS_PATH.exists():
        return []
    lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    if last:
        lines = lines[-last:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def append_raw(name: str, record: dict) -> None:
    """Raw facts (prompt text, replies) for grading. Git-ignored, stays on this laptop."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with (RAW_DIR / f"{name}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now_iso(), **record}, ensure_ascii=False) + "\n")
