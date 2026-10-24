"""history/: transcript parsing, drop filter, task boundaries and stats, on synthetic transcripts only."""
import json

from history.extract import drop_reason, parse_session
from history.tasks import PlanState, active_seconds, build_tasks, is_correction
from history.validity import cliffs_delta, compare, perm_test, spearman, stratified_sample


def _line(kind, ts, **kw):
    d = {"type": kind, "timestamp": f"2026-10-20T10:{ts:02d}:00Z", "sessionId": "s1", "cwd": "/x"}
    d.update(kw)
    return json.dumps(d)


def _prompt(ts, text, **kw):
    return _line("user", ts, message={"role": "user", "content": text}, turnOrigin="human", promptSource="sdk", **kw)


def _reply(ts, text="ok", tools=()):
    content = [{"type": "text", "text": text}] + [{"type": "tool_use", "name": n, "input": i} for n, i in tools]
    return _line("assistant", ts, message={"role": "assistant", "content": content})


def _tool_result(ts, error=False):
    return _line("user", ts, toolUseResult={}, message={"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t", "content": "x", "is_error": error}]})


def _session(tmp_path, lines):
    f = tmp_path / "s1.jsonl"
    f.write_text("\n".join(lines) + "\n")
    return parse_session(f)


def test_only_typed_prompts_are_kept(tmp_path):
    s = _session(tmp_path, [
        _prompt(0, "add a reader for the H10 in body/h10.py"),
        _reply(1, tools=[("Bash", {})]),
        _tool_result(2, error=True),
        _line("user", 3, message={"role": "user", "content": "<task-notification>done</task-notification>"},
              turnOrigin="task_notification", promptSource="system"),
        _line("user", 4, message={"role": "user", "content": "side session report"}, turnOrigin="sdk", promptSource="sdk"),
        _line("user", 5, message={"role": "user", "content": "<system-reminder>x</system-reminder>"}, isMeta=True),
        _prompt(6, [{"type": "text", "text": "still broken"},
                    {"type": "text", "text": "<system-reminder>injected</system-reminder>"}]),
    ])
    assert [p.text for p in s.prompts] == ["add a reader for the H10 in body/h10.py", "still broken"]
    assert s.prompts[0].tool_errors == 1 and s.prompts[0].next_text == "still broken"
    assert s.prompts[1].prev_assistant_len == 2 and s.prompts[1].prev_tool_error
    assert s.other_turns == 2


def test_drop_filter(monkeypatch):
    import re

    import history.extract as ex
    monkeypatch.setattr(ex, "_CUSTOMER", re.compile(r"acmecorp|\bacme\s", re.I))  # real names live outside the repo
    assert drop_reason("email the AcmeCorp team") == "customer_name"
    assert drop_reason("ask ACME about it") == "customer_name"
    assert drop_reason("x" * 4001) == "too_long"
    pt = "<pasted_content>não está com uma valor para o dia que você</pasted_content> summarize this"
    assert drop_reason(pt) == "portuguese"
    assert drop_reason("fix the RMSSD in body/hrv.py so the coach stops firing") is None
    assert drop_reason("generate a chart") is None


def test_plan_state_and_scope():
    plan = PlanState()
    assert plan.apply("plan", {"items": [{"status": "in_progress"}, {"status": "pending"}], "scope": "first_task"}) == (0, "first_task")
    assert plan.apply("plan", {"advance": True}) == (1, None)
    assert plan.undone() == 1
    assert plan.apply("wrap_up", None) == (1, None)
    assert plan.undone() == 0


def test_tasks_requests_and_turns_to_signal(tmp_path):
    items = lambda scope: ("mcp__ccd_turn__update_plan", {"items": [{"status": "in_progress"}], "scope": scope})
    wrap = ("mcp__ccd_turn__wrap_up", {"recap": "r"})
    s = _session(tmp_path, [
        _prompt(0, "build the extractor"), _reply(1, tools=[items("first_task")]),   # no signal yet
        _prompt(2, "no, skip subagents"), _reply(3, tools=[wrap]),                   # done
        _prompt(4, "now the stats"), _reply(5, tools=[items("continuation"), wrap]),  # new request, done
        _prompt(6, "unrelated: write the pitch"), _reply(7, tools=[items("new_task")]),  # new task, never done
    ])
    turns, tasks, undone = build_tasks(s)
    assert [t.turns_to_signal for t in turns] == [2, 1, 1, None]
    assert turns[0].next_is_correction and not turns[1].next_is_correction
    assert [t.request_turns_to_done for t in turns] == [2, None, 1, None]
    assert len(tasks) == 2 and tasks[0].turns_to_done == 3 and not tasks[1].done
    assert tasks[0].corrections == 1 and undone == 1


def test_corrections_and_active_time(tmp_path):
    assert is_correction("No, that's the wrong file") and is_correction("try again")
    assert not is_correction("now add tests") and not is_correction(None)
    s = _session(tmp_path, [_prompt(0, "a"), _reply(2), _prompt(30, "b"), _reply(31)])
    assert active_seconds(s.timestamps) == 3 * 60  # the 28-min gap is not active time


def test_stats():
    assert perm_test([5, 6, 7, 6, 5, 7], [1, 2, 1, 2, 1, 2]) < 0.05
    assert perm_test([1], [2, 3]) is None
    assert cliffs_delta([3, 4], [1, 2]) == 1.0
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    rows = [{"score": s, "x": v} for s, v in [(2, 3), (3, 4), (1, 3), (8, 1), (9, 1), (7, 2)]]
    c = compare(rows, "x", "mean")
    assert c["n_low"] == 3 and c["n_high"] == 3 and c["ratio_low_over_high"] == 2.5


def test_stratified_sample_spreads_sessions():
    class P:
        def __init__(self, s):
            self.session = s
    ps = [P("a") for _ in range(20)] + [P("b") for _ in range(2)] + [P("c") for _ in range(2)]
    got = stratified_sample(ps, 6)
    assert len(got) == 6 and {p.session for p in got} == {"a", "b", "c"}
