"""Grader tests. Live-API tests skip when REVIVE_ANTHROPIC_KEY is missing."""
import os
import time

import pytest

import shared.config  # noqa: F401  (loads .env)
from grader import _llm
from grader.outcome_score import grade_outcome
from grader.prompt_score import grade_prompt, heuristic_grade

HAS_KEY = bool(os.getenv("REVIVE_ANTHROPIC_KEY"))
live = pytest.mark.skipif(not HAS_KEY, reason="REVIVE_ANTHROPIC_KEY not set")

PLAN = ("Here's my plan: 1) add a median filter to body/hrv.py that drops RR intervals more than 20% off "
        "the last 10 beats, 2) add tests/test_hrv.py with the squat trace. Want me to go ahead?")
DETAILED = ("In body/hrv.py, rmssd() raises ZeroDivisionError at line 42 when every RR interval is filtered out "
            "during squats. Only change rmssd(): return None when fewer than 20 clean beats remain, so the coach "
            "doesn't fire on motion. Done when `uv run pytest tests/test_hrv.py::test_squat_trace` passes.")


# --- fallback (no network) ---

def test_fallback_no_key(monkeypatch):
    monkeypatch.setenv("REVIVE_ANTHROPIC_KEY", "")
    monkeypatch.setattr(_llm, "_client", None)
    r = grade_prompt("hrv is broken fix it", {})
    assert r["source"] == "heuristic" and "no_key" in r["error"]
    assert r["score"] <= 3 and {"context", "done"} <= set(r["missing"])
    o = grade_outcome({}, "fix it", "Done.", [], ["body/hrv.py"], "still broken")
    assert o["source"] == "heuristic" and o["next_prompt_correction"] and o["points"] in (0, 1, 2, 3)


def test_fallback_timeout(monkeypatch):
    class Slow:
        class messages:
            @staticmethod
            def create(**kw):
                time.sleep(2)

    monkeypatch.setattr(_llm, "_get_client", lambda: Slow)
    monkeypatch.setattr(_llm, "TIMEOUT_S", 0.2)
    t0 = time.monotonic()
    r = grade_prompt(DETAILED, {})
    assert time.monotonic() - t0 < 1.0
    assert r["source"] == "heuristic" and r["error"].startswith("TimeoutError")
    o = grade_outcome({}, "x", "y", [], [], None)
    assert o["source"] == "heuristic"


def test_heuristic_shapes():
    assert heuristic_grade("yes do it", {"last_assistant": PLAN})["type"] == "confirmation"
    assert heuristic_grade("yes do it")["score"] is None
    assert heuristic_grade(DETAILED)["score"] >= 7
    assert heuristic_grade("what does RMSSD mean?")["type"] == "question"


# --- live (Haiku) ---

@live
def test_live_confirmation_not_scored():
    r = grade_prompt("yes do it", {"last_assistant": PLAN})
    assert r["source"] == "llm", r.get("error")
    assert r["type"] == "confirmation" and r["score"] is None and r["missing"] == []


@live
def test_live_vague_prompt_low():
    r = grade_prompt("hrv is broken fix it", {})
    assert r["source"] == "llm", r.get("error")
    assert r["score"] <= 3 and {"context", "done"} <= set(r["missing"])
    assert r["latency_ms"] < 3000


@live
def test_live_detailed_prompt_high():
    r = grade_prompt(DETAILED, {"project_summary": "Revive: heart-rate coach for Claude Code users."})
    assert r["source"] == "llm", r.get("error")
    assert r["score"] >= 7 and r["type"] in ("new_task", "follow_up")
    assert set(r["intent"]) == {"immediate", "session", "project"}


@live
def test_live_outcome_correction():
    o = grade_outcome({"immediate": "stop RMSSD crashing on squats"}, "fix the squat crash",
                      "I added a filter in body/hrv.py.", [], ["body/hrv.py"], "still crashes on squats")
    assert o["source"] == "llm", o.get("error")
    assert o["next_prompt_correction"] is True and o["outcome"] != "achieved"
    assert o["points"] == {"achieved": 3, "partial": 2, "missed": 1, "wrong_direction": 0}[o["outcome"]]
