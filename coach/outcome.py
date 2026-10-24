"""Outcome score (Stop hook) and turn counting, so turns to done works.

On Stop: the session's last prompt + its grade intent + what Claude did this turn
-> grader.grade_outcome -> one `outcome` event. A correction ("still broken",
"no, I meant...") is flagged on the next `prompt` event (correction: true).
"""
import json
import re

from coach.context import last_turn
from shared.config import RAW_DIR
from shared.events import append_event, read_events

# metrics.md: corrections are prompts starting "no / still / wrong / that's not"
_STARTS = re.compile(r"^\s*(no\b|nope|still\b|wrong|that'?s not|not what|i meant|it didn'?t|didn'?t work|"
                     r"doesn'?t work|isn'?t working|undo|revert|again\b)", re.I)
_ANYWHERE = re.compile(r"\b(still (broken|failing|wrong|not)|not what i|i meant|didn'?t work|doesn'?t work|"
                       r"isn'?t working|that'?s wrong|that'?s not)\b", re.I)


def looks_like_correction(prompt: str) -> bool:
    p = (prompt or "").strip()
    return bool(_STARTS.match(p) or (len(p) < 200 and _ANYWHERE.search(p)))


def last_prompt(session: str) -> str:
    """The session's most recent prompt text, from memory/raw/prompts.jsonl (read from the end)."""
    path = RAW_DIR / "prompts.jsonl"
    if not session or not path.exists():
        return ""
    for line in reversed(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("session") == session:
            return r.get("prompt") or ""
    return ""


def task_state(session: str, events: list[dict] | None = None) -> dict:
    """Prompts and corrections in the current task (a task starts at a new_task grade), plus the last grade."""
    turns, corrections, grade = 0, 0, {}
    for e in events if events is not None else read_events(2000):
        if e.get("session") != session:
            continue
        if e.get("kind") == "prompt":
            turns += 1
            corrections += bool(e.get("correction"))
        elif e.get("kind") == "grade":
            grade = e
            if e.get("type") == "new_task":
                turns, corrections = 1, 0
    return {"turns": turns, "corrections": corrections, "grade": grade}


def score_turn(data: dict) -> dict | None:
    """Grade the turn that just finished and append the `outcome` event. Returns the event (None if no prompt)."""
    from grader.outcome_score import grade_outcome

    session = data.get("session_id", "")
    prompt = last_prompt(session)
    if not prompt:
        return None
    st = task_state(session)
    intent = st["grade"].get("intent") or {}
    turn = last_turn(data.get("transcript_path", ""))
    final = data.get("last_assistant_message") or turn["assistant_final"]
    o = grade_outcome(intent, prompt, final, turn["tool_errors"], turn["files_changed"], None)
    return append_event(
        "outcome", session=session, outcome=o["outcome"], points=o["points"], why=o.get("why", ""),
        intent=intent, source=o.get("source"), latency_ms=o.get("latency_ms"),
        tool_errors=len(turn["tool_errors"]), files_changed=len(turn["files_changed"]),
        task_turns=st["turns"], corrections=st["corrections"],
        turns_to_done=st["turns"] if o["outcome"] == "achieved" else None,
    )
