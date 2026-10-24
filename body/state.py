"""STUB owned by nbz: replace with the real H10 + Garmin version.

Contract (docs/plan/FOR-NBZ.md): get_body_state() returns the dict below.
Until the real reader lands, FAKE_STRAIN=calm|elevated|strained picks the state.
"""
import os

from shared.events import now_iso

_FAKE = {
    "calm": {"hr": 70, "rmssd": 42.0},
    "elevated": {"hr": 82, "rmssd": 30.0},
    "strained": {"hr": 96, "rmssd": 22.4},
}


def get_body_state() -> dict:
    strain = os.getenv("FAKE_STRAIN", "calm")
    vals = _FAKE.get(strain, _FAKE["calm"])
    return {
        "ts": now_iso(),
        "hr": vals["hr"],
        "rmssd": vals["rmssd"],
        "hr_base": 68,
        "rmssd_base": 41.0,
        "strain": strain,
        "source": "fake",
        "today": {"sleep_h": 5.4, "sleep_score": 61, "body_battery": 38, "stress": 44},
    }
