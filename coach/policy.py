"""The coach: decides whether Revive steps in, and how.

Level 0 silent fix: a vague prompt (score <= 4) gets missing context added.
Level 1 wrist tap: vague prompt AND body strained (or a poor night lowers the bar).
Level 2 hold + voice: a loop. At most one tap per 20 minutes.
"""
import json
import time

from shared.config import DATA_DIR

TAP_COOLDOWN_S = 20 * 60
STATE = DATA_DIR / "coach_state.json"


def _load() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _save(s: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s))


def vague_threshold(body: dict) -> int:
    """A poor night or low Body Battery makes Revive step in earlier (today's context)."""
    today = body.get("today") or {}
    poor_night = (today.get("sleep_h") or 8) < 6 or (today.get("body_battery") or 100) < 40
    return 5 if poor_night else 4


def decide(grade: dict, body: dict, loop: bool = False, now: float | None = None) -> dict:
    now = now or time.time()
    st = _load()
    if not grade.get("scored", grade.get("type") in ("new_task", "follow_up")):
        return {"level": None, "reason": "not a task prompt"}
    score = grade.get("score", 10)
    strained = body.get("strain") == "strained"
    cooldown_ok = now - st.get("last_tap", 0) > TAP_COOLDOWN_S
    if loop:
        return {"level": 2, "channels": ["hold", "voice"], "reason": "loop"}
    if score <= vague_threshold(body):
        if strained and cooldown_ok:
            st["last_tap"] = now
            _save(st)
            return {"level": 1, "channels": ["fix", "tap"], "reason": f"score {score} + strained"}
        return {"level": 0, "channels": ["fix"], "reason": f"score {score}"}
    return {"level": None, "reason": f"score {score}, no action"}
