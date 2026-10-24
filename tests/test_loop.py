"""Loop detector (level 2): a scripted 4-prompt loop gets a hold; a single bad prompt never does. No network."""
import json
from datetime import datetime, timezone

import pytest

import act
import shared.events as events
from capture import hook
from coach import loop

ERR = "ZeroDivisionError: division by zero\n  File body/rmssd.py, line 42"


class Transcript:
    def __init__(self, path):
        self.path, self.lines = path, []

    def add(self, *entries):
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.lines += [{"timestamp": ts, **e} for e in entries]
        self.path.write_text("\n".join(json.dumps(x) for x in self.lines))

    def error(self):
        self.add({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "Bash", "input": {"command": "uv run pytest"}}]}},
                 {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": ERR}]}})

    def passing_test(self):
        self.add({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "ok", "name": "Bash", "input": {"command": "uv run pytest -q"}}]}},
                 {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "ok", "content": "12 passed in 0.4s"}]}})


@pytest.fixture
def run(tmp_path, monkeypatch):
    calls = {"say": [], "tap": []}
    monkeypatch.setattr(act, "say", lambda t: calls["say"].append(t) or {"sent": True})
    monkeypatch.setattr(act, "tap", lambda t: calls["tap"].append(t) or {"sent": True})
    monkeypatch.setattr(hook, "_grade", lambda p, c: {"type": "follow_up", "scored": True, "score": 8, "missing": []})
    monkeypatch.setattr(hook, "DATA_DIR", tmp_path)
    for k in ("REVIVE_WHO", "REVIVE_TAP", "REVIVE_COACH", "REVIVE_VOICE"):
        monkeypatch.delenv(k, raising=False)
    tr = Transcript(tmp_path / "t.jsonl")

    def prompt(text):
        return hook.on_prompt({"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt": text,
                               "cwd": str(tmp_path), "transcript_path": str(tr.path)})
    return prompt, tr, calls


def kinds(kind):
    return [e for e in events.read_events() if e["kind"] == kind]


def test_scripted_four_prompt_loop_gets_a_hold(run):
    prompt, tr, calls = run
    assert prompt("In body/rmssd.py, fix the ZeroDivisionError when every beat is filtered") is None
    tr.error()
    assert prompt("still broken") is None             # 2 prompts: not a loop yet
    assert prompt("try again, same error") is None    # 3 prompts, but the error has shown up only once
    tr.error()
    out = prompt("wtf still broken!!!")               # 4th: same error twice, retries, frustration, no progress
    assert out["decision"] == "block"
    assert out["reason"].startswith("Three tries, same error. Different approach: guard the empty case")
    assert out["reason"].endswith("Take two minutes.")
    (lp,) = kinds("loop")
    assert set(lp["signals"]) == {"repeat_prompts", "same_error", "frustration", "no_progress"} and lp["minutes"] >= 0
    hold = [a for a in kinds("action") if a.get("level") == 2]
    assert len(hold) == 1 and hold[0]["channels"] == ["hold", "voice", "tap"] and hold[0]["tapped"] is False
    assert calls == {"say": ["You're looping. Take two minutes."], "tap": []}   # taps only from nbz's laptop
    assert len(kinds("grade")) == 3                   # the held prompt isn't graded
    assert prompt("still broken") is None             # 15-min cooldown


def test_loop_taps_on_nbz_laptop(run, monkeypatch):
    monkeypatch.setenv("REVIVE_WHO", "nbz")
    prompt, tr, calls = run
    tr.error()
    tr.error()
    prompt("fix it")
    prompt("still broken")
    assert prompt("still broken, try again")["decision"] == "block"
    assert calls["tap"] == ["Looping: take 2"]


def test_single_bad_prompt_never_holds(run):
    prompt, tr, calls = run
    tr.error()
    tr.error()
    assert prompt("wtf still broken!!! same error again") is None   # the only prompt: never a hold
    assert prompt("add a /health route to server.py") is None
    assert prompt("now add a test for it in tests/test_server.py") is None
    assert prompt("no wrong!!! still broken") is None   # stuck prompts not back to back: not a loop
    assert not kinds("loop") and calls["say"] == []


def test_one_bad_prompt_after_normal_work(run):
    prompt, tr, calls = run
    tr.error()
    tr.error()
    for p in ("add a /health route to server.py", "now add a test for it", "and document it in README"):
        assert prompt(p) is None
    assert prompt("wtf this is wrong!!!") is None
    assert not kinds("loop") and calls["say"] == []


def test_passing_test_counts_as_progress(run):
    prompt, tr, calls = run
    tr.error()
    tr.error()
    tr.passing_test()
    prompt("fix it")
    prompt("still broken")
    assert prompt("still broken, try again") is None  # repeat + same error, but a test passed: 2 signals
    assert not kinds("loop")


def test_injected_blocks_are_not_near_duplicates():
    rem = "<system-reminder>Linked sessions now: a, b, c and a long shared boilerplate line</system-reminder>\n"
    assert not loop.is_retry(loop._clean(rem + "add a route"), [loop._clean(rem + "write the README intro")])
    assert loop.is_retry("fix the rmssd zero division in body/rmssd.py", ["fix the rmssd zero division in body/rmssd.py!"])


def test_suggestion_names_the_error():
    assert "installed" in loop.suggestion("ModuleNotFoundError: No module named 'bleak'")
    assert "-x -vv" in loop.suggestion("FAILED tests/test_hrv.py::test_squat - AssertionError")
    assert loop.suggestion("")
