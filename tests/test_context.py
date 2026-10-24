"""The silent fix picks up a failing test the user ran with `!` inside Claude Code."""
import json

from coach.context import recent_context, silent_fix_text


def _write(tmp_path, entries):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries))
    return str(p)


def test_failing_bang_command_becomes_last_error(tmp_path):
    out = ("<bash-input>uv run pytest tests/test_rmssd.py -q</bash-input>"
           "<bash-stdout>FAILED tests/test_rmssd.py::test_real_squat_fixture_hero_bug - "
           "AssertionError: filter should tame RMSSD\n1 failed, 6 passed</bash-stdout><bash-stderr></bash-stderr>")
    path = _write(tmp_path, [{"type": "user", "message": {"role": "user", "content": out}}])
    ctx = recent_context(path)
    assert "test_real_squat_fixture_hero_bug" in ctx["last_error"]
    assert "<bash" not in ctx["last_error"]
    assert "hero_bug" in silent_fix_text(ctx, ["context", "done"])
    assert ctx["session_goal"] == ""  # a shell command isn't the session goal


def test_passing_bang_command_is_ignored(tmp_path):
    out = "<bash-input>ls</bash-input><bash-stdout>README.md\nbody</bash-stdout><bash-stderr></bash-stderr>"
    path = _write(tmp_path, [{"type": "user", "message": {"role": "user", "content": out}}])
    assert recent_context(path)["last_error"] == ""
