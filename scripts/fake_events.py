"""Dev replayer: appends a scripted 3-minute demo sequence to data/events.jsonl.

Every event carries demo: true, so the judge view shows DEMO DATA.
Run: uv run python scripts/fake_events.py [--fast] [--who nbz]
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.events import append_event  # noqa: E402

DURATION = 180  # seconds of scripted time
BODY_EVERY = 5


def body_at(t: float) -> dict:
    """Calm → elevated → strained (squats) → recovering after the fix."""
    if t < 40:
        hr, rmssd = 70, 42.0
    elif t < 80:
        k = (t - 40) / 40
        hr, rmssd = 70 + 14 * k, 42.0 - 12 * k
    elif t < 150:
        hr, rmssd = 96, 22.4
    else:
        k = (t - 150) / 30
        hr, rmssd = 96 - 14 * k, 22.4 + 8 * k
    hr += random.uniform(-1.5, 1.5)
    rmssd += random.uniform(-1.2, 1.2)
    # same rule as GAMEPLAN §3: +20 bpm or RMSSD < 60% of base (68 / 41)
    if hr >= 88 or rmssd < 24.6:
        strain = "strained"
    elif hr >= 78 or rmssd < 32:
        strain = "elevated"
    else:
        strain = "calm"
    return {"hr": round(hr), "rmssd": round(rmssd, 1), "strain": strain}


# (scripted second, kind, fields)
SCRIPT = [
    (0, "mark", {"note": "demo replay start"}),
    (100, "prompt", {"session": "demo", "chars": 20}),
    (102, "grade", {
        "type": "follow_up", "score": 2, "missing": ["context", "done"],
        "intent": {"immediate": "fix the HRV number", "session": "H10 reader working", "project": "Revive"},
        "pattern": "feedback_loop", "latency_ms": 1840, "source": "haiku",
    }),
    (103, "action", {"level": 1, "channel": "tap", "message": "Slow down: context added"}),
    (103, "action", {"level": 0, "channel": "fix", "message": "added failing test output + body/polar.py"}),
    (150, "outcome", {"outcome": "achieved", "points": 3, "why": "filter added; squat test passes"}),
    (165, "prompt", {"session": "demo", "chars": 214}),
    (167, "grade", {
        "type": "new_task", "score": 8, "missing": [],
        "intent": {"immediate": "log RMSSD per minute", "session": "H10 reader working", "project": "Revive"},
        "pattern": "specified", "latency_ms": 1510, "source": "haiku",
    }),
    (DURATION, "mark", {"note": "demo replay end"}),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true", help="run 10x faster (~18 s)")
    ap.add_argument("--who", default=None, help="who field (default: REVIVE_WHO)")
    args = ap.parse_args()
    speed = 10 if args.fast else 1

    timeline = [(t, "body", None) for t in range(0, DURATION + 1, BODY_EVERY)]
    timeline += SCRIPT
    timeline.sort(key=lambda e: (e[0], e[1] != "body"))

    start = time.monotonic()
    for t, kind, fields in timeline:
        wait = start + t / speed - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        data = body_at(t) | {"source": "fake"} if kind == "body" else fields
        ev = append_event(kind, who=args.who, demo=True, **data)
        if kind != "body":
            print(f"{t:>4}s  {kind:8} {ev}")
    print(f"done: {len(timeline)} events appended")


if __name__ == "__main__":
    main()
