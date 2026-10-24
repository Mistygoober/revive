"""The fast hook path: POST /hook in the server, thin client with in-process fallback. No network."""
import os

import pytest
from fastapi.testclient import TestClient

import server
import shared.events as events
from capture import hook


@pytest.fixture
def tmp_log(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "DATA_DIR", tmp_path)
    monkeypatch.setattr(events, "EVENTS_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(events, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(hook, "DATA_DIR", tmp_path)
    return tmp_path


def test_hook_endpoint_logs_and_applies_env_per_call(tmp_log, monkeypatch):
    monkeypatch.delenv("REVIVE_COACH", raising=False)
    seen = {}
    monkeypatch.setattr(hook, "on_prompt", lambda d: seen.update(coach=os.getenv("REVIVE_COACH")) or {"x": 1})
    r = TestClient(server.app).post("/hook", json={"data": {"hook_event_name": "UserPromptSubmit"},
                                                    "env": {"REVIVE_COACH": "0", "PATH": "/nope"}})
    assert r.json() == {"output": {"x": 1}}
    assert seen["coach"] == "0" and "REVIVE_COACH" not in os.environ and os.environ["PATH"] != "/nope"


def test_stop_scores_outcome_after_response(tmp_log, monkeypatch):
    calls = []
    monkeypatch.setattr(hook, "score_outcome", lambda d: calls.append(d["session_id"]))
    r = TestClient(server.app).post("/hook", json={"data": {"hook_event_name": "Stop", "session_id": "s"}})
    assert r.json() == {"output": None} and calls == ["s"]
    assert [e["kind"] for e in events.read_events()] == ["reply"]


def test_thin_client_falls_back_when_no_server(tmp_log, monkeypatch):
    monkeypatch.setattr(hook, "SERVER", "http://127.0.0.1:9")  # nothing listens on the discard port
    assert hook.via_server({"hook_event_name": "Stop"}) == (False, None)
