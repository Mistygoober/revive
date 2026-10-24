"""body/state.py (nbz): the one function the rest of Revive calls.

get_body_state() returns the newest 'body' event from the live log (produced
by body/polar.py over the H10, or by its DEMO_MODE replay). If nothing is
newer than STALE_AFTER_S, it falls back to a fake state driven by FAKE_STRAIN
so the system always has something sane to show.

Contract: docs/plan/FOR-NBZ.md.
"""
import os
from datetime import datetime

from body.polar import HR_BASE, RMSSD_BASE, STALE_AFTER_S
from shared.events import now_iso, read_events

_FAKE = {
    "calm": {"hr": 70, "rmssd": 42.0},
    "elevated": {"hr": 82, "rmssd": 30.0},
    "strained": {"hr": 96, "rmssd": 22.4},
}

# Until the real Garmin pull lands; always labeled, never claimed as live.
_TODAY = {"sleep_h": 5.4, "sleep_score": 61, "body_battery": 38, "stress": 44}


def _age_seconds(ts: str) -> float:
    try:
        then = datetime.fromisoformat(ts)
        now = datetime.now().astimezone()
        return (now - then).total_seconds()
    except Exception:
        return float("inf")


def _latest_body_event() -> dict | None:
    for ev in reversed(read_events(last=100)):
        if ev.get("kind") == "body":
            return ev
    return None


def _fake_state() -> dict:
    strain = os.getenv("FAKE_STRAIN", "calm")
    vals = _FAKE.get(strain, _FAKE["calm"])
    return {
        "ts": now_iso(),
        "hr": vals["hr"],
        "rmssd": vals["rmssd"],
        "hr_base": HR_BASE,
        "rmssd_base": RMSSD_BASE,
        "strain": strain,
        "source": "fake",
        "today": dict(_TODAY),
    }


def get_body_state() -> dict:
    ev = _latest_body_event()
    if ev is not None and _age_seconds(ev.get("ts", "")) <= STALE_AFTER_S:
        return {
            "ts": ev["ts"],
            "hr": ev.get("hr"),
            "rmssd": ev.get("rmssd"),
            "hr_base": ev.get("hr_base", HR_BASE),
            "rmssd_base": ev.get("rmssd_base", RMSSD_BASE),
            "strain": ev.get("strain", "calm"),
            "source": ev.get("source", "h10"),
            "today": dict(_TODAY),
        }
    return _fake_state()
