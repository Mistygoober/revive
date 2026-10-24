"""Outcome score in the Stop hook: transcript parsing, corrections, turns to done. No network."""
import json

import pytest

import shared.events as events
from capture import hook
from coach import outcome
from coach.context import last_turn


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "DATA_DIR", tmp_path)
    monkeypatch.setattr(events, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(events, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(outcome, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(hook, "DATA_DIR", tmp_path)
    return tmp_path


def _transcript(tmp_path):
    lines = [
        {"type": "user", "message": {"role": "user", "content": "first prompt"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "old.py"}}]}},
        {"type": "user", "message": {"role": "user", "content": "fix the hrv number"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "body/hrv.py"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True, "content": "Traceback: boom"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed; tests pass."}]}},
    ]
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines))
    return str(p)


def test_last_turn_only_counts_since_last_prompt(tmp_path):
    t = last_turn(_transcript(tmp_path))
    assert t == {"assistant_final": "Fixed; tests pass.", "tool_errors": ["Traceback: boom"], "files_changed": ["body/hrv.py"]}
    assert last_turn("") == {"assistant_final": "", "tool_errors": [], "files_changed": []}


@pytest.mark.parametrize("p,yes", [("still broken", True), ("no, I meant the other file", True),
                                   ("that's wrong", True), ("Wrong file", True),
                                   ("add a test for rmssd", False), ("yes do it", False),
                                   ("x" * 300 + " didn't work", False)])
def test_looks_like_correction(p, yes):
    assert outcome.looks_like_correction(p) is yes


def test_task_state_resets_on_new_task():
    ev = [{"session": "s", "kind": "prompt"}, {"session": "s", "kind": "grade", "type": "new_task"},
          {"session": "s", "kind": "prompt", "correction": True}, {"session": "s", "kind": "grade", "type": "follow_up"},
          {"session": "other", "kind": "prompt"}, {"session": "s", "kind": "prompt"},
          {"session": "s", "kind": "grade", "type": "new_task", "intent": {"immediate": "x"}}]
    st = outcome.task_state("s", ev)
    assert st["turns"] == 1 and st["corrections"] == 0 and st["grade"]["intent"] == {"immediate": "x"}
    st = outcome.task_state("s", ev[:5])
    assert st["turns"] == 2 and st["corrections"] == 1


def test_stop_hook_appends_outcome(tmp_log, monkeypatch):
    import grader.outcome_score as gos
    seen = {}

    def fake(intent, prompt, final, errors, files, next_prompt):
        seen.update(intent=intent, prompt=prompt, final=final, errors=errors, files=files)
        return {"outcome": "achieved", "points": 3, "why": "done", "source": "test", "latency_ms": 1}

    monkeypatch.setattr(gos, "grade_outcome", fake)
    events.append_raw("prompts", {"session": "s1", "prompt": "fix the hrv number"})
    events.append_event("prompt", session="s1", chars=18)
    events.append_event("grade", session="s1", type="new_task", intent={"immediate": "fix hrv"})
    hook.on_stop({"hook_event_name": "Stop", "session_id": "s1", "last_assistant_message": "Fixed.",
                  "transcript_path": _transcript(tmp_log)})
    o = [e for e in events.read_events() if e["kind"] == "outcome"]
    assert len(o) == 1
    assert {k: o[0][k] for k in ("outcome", "points", "why", "intent", "task_turns", "turns_to_done")} == {
        "outcome": "achieved", "points": 3, "why": "done", "intent": {"immediate": "fix hrv"},
        "task_turns": 1, "turns_to_done": 1}
    assert seen["prompt"] == "fix the hrv number" and seen["final"] == "Fixed."
    assert seen["files"] == ["body/hrv.py"] and seen["errors"] == ["Traceback: boom"]


def test_stop_hook_never_raises(tmp_log, monkeypatch):
    monkeypatch.setattr(outcome, "last_prompt", lambda s: 1 / 0)
    hook.on_stop({"hook_event_name": "Stop", "session_id": "s2"})
    assert "ZeroDivisionError" in (tmp_log / "hook_errors.log").read_text()
    assert [e["kind"] for e in events.read_events()] == ["reply"]
