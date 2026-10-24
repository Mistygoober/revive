"""scripts/check_predictions on a synthetic log: verdicts, n, demo events left out."""
import importlib.machinery
import importlib.util
import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader("check_predictions", str(ROOT / "scripts" / "check_predictions"))
cp = importlib.util.module_from_spec(importlib.util.spec_from_loader("check_predictions", _loader))
_loader.exec_module(cp)

DAY = "2026-10-24"


def ev(hhmm, kind, **f):
    return {"ts": f"{DAY}T{hhmm}:00-07:00", "who": f.pop("who", "lucas"), "kind": kind, **f}


def write(tmp_path, rows):
    p = tmp_path / "events.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return cp.load([p], date.fromisoformat(DAY))


def test_fatigue_true_and_demo_excluded(tmp_path):
    rows = [ev(f"14:0{i}", "grade", score=7) for i in range(3)] + [ev(f"16:3{i}", "grade", score=5) for i in range(3)]
    rows.append(ev("16:40", "grade", score=10, demo=True))
    r = cp.fatigue(write(tmp_path, rows), datetime.fromisoformat(f"{DAY}T18:00:00-07:00"), date.fromisoformat(DAY))
    assert r["verdict"] == "TRUE" and r["drop"] == 2 and r["last_hour"]["n"] == 3


def test_fatigue_not_enough(tmp_path):
    r = cp.fatigue(write(tmp_path, [ev("14:00", "grade", score=7)]), datetime.now().astimezone(), date.fromisoformat(DAY))
    assert r["verdict"] == "NOT ENOUGH DATA"


def test_body_x_work(tmp_path):
    rows = []
    for i, (strain, outcome, ttd) in enumerate([("strained", "partial", None)] * 5 + [("calm", "achieved", 1)] * 5):
        m = f"{15 + i // 6}:{(i * 7) % 60:02d}"
        rows += [ev(m, "body", who="nbz", strain=strain), ev(m, "prompt", who="nbz", session=f"s{i}"),
                 ev(m, "outcome", who="nbz", session=f"s{i}", outcome=outcome, turns_to_done=ttd)]
    r = cp.body_x_work(write(tmp_path, rows))
    assert r["strained"]["n"] == 5 and r["calm"]["n"] == 5
    assert r["strained"]["achieved_rate"] == 0 and r["calm"]["achieved_rate"] == 1 and r["verdict"] == "TRUE"


def test_loops_start_time_uses_minutes(tmp_path):
    rows = [ev("15:35", "loop", minutes=10), ev("16:00", "loop", minutes=2), ev("16:30", "loop", minutes=1)]
    r = cp.loops(write(tmp_path, rows))
    assert r["loops"] == 3 and r["after_330"] == 2 and r["verdict"] == "TRUE"  # the 15:35 loop started at 15:25
