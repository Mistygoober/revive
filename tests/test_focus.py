"""Focus watcher: distraction timer, cooldowns, domain-only sites, no nudge outside a block.

Every probe, tap and clock is a fake: no osascript, no ntfy, no real event log (conftest).
"""
import json

import pytest

import shared.events as events
from focus.watch import DEMO_RULES, Rules, Watcher, domain_of, is_distracting, streak_start


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def make(minutes=45, rules=Rules(), front=("Cursor", None), idle=0.0, activity=()):
    clock, taps = Clock(), []
    state = {"front": front}
    w = Watcher(minutes=minutes, rules=rules, clock=clock,
                probe=lambda: state["front"], idle=lambda: idle,
                tap=lambda text: taps.append(text) or {"text": text},
                activity_log=lambda: list(activity))
    return w, clock, state, taps


def run(w, clock, seconds, step=5):
    out = []
    for _ in range(int(seconds // step)):
        out += w.tick()
        clock.t += step
    return out


def actions(evs, ch):
    return [e for e in evs if e["kind"] == "action" and ch in e["channels"]]


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s#frag", "youtube.com"),
    ("https://user:secret@old.reddit.com/r/python/comments/abc?utm=1", "old.reddit.com"),
    ("http://m.facebook.com/some.person/posts/123", "facebook.com"),
    ("https://GitHub.com:443/Mistygoober/revive/pull/1?x=y", "github.com"),
    ("about:blank", None),
    ("file:///Users/me/secret.txt", None),
    ("", None),
    (None, None),
])
def test_domain_only(url, expected):
    d = domain_of(url)
    assert d == expected
    if d:
        for leak in ("/", "?", "#", "=", "&", ":", "@", "watch", "secret", "posts", "utm"):
            assert leak not in d


def test_focus_events_never_hold_a_path_or_query(tmp_path):
    w, clock, state, _ = make(rules=DEMO_RULES)
    state["front"] = ("Google Chrome", domain_of("https://www.youtube.com/watch?v=abc&list=xyz"))
    run(w, clock, 60)
    log = events.EVENTS_PATH.read_text()
    assert "watch" not in log and "v=abc" not in log and "list=" not in log
    focus = [json.loads(l) for l in log.splitlines() if json.loads(l)["kind"] == "focus"]
    assert focus and all(e["site"] == "youtube.com" for e in focus)


def test_distraction_list():
    assert is_distracting("Google Chrome", "youtube.com")
    assert is_distracting("Safari", "old.reddit.com")
    assert is_distracting("Netflix", None)
    assert not is_distracting("Google Chrome", "github.com")
    assert not is_distracting("Google Chrome", "notyoutube.com")
    assert not is_distracting("Cursor", None)


def test_distraction_taps_after_90s_not_before():
    w, clock, state, taps = make(minutes=45)
    state["front"] = ("Google Chrome", "youtube.com")
    assert actions(run(w, clock, 85), "focus") == []
    acts = actions(run(w, clock, 10), "focus")
    assert len(acts) == 1 and taps == [acts[0]["message"]]
    a = acts[0]
    assert a["level"] == 1 and a["channels"] == ["focus", "tap"]
    assert a["reason"] == "distracted 90 s on youtube.com"
    assert a["message"].startswith("Back to task") and "44m left" in a["message"]
    assert len(a["message"].split()) <= 5   # act.tap keeps 5 words
    assert "demo_thresholds" not in a


def test_switching_away_resets_the_timer():
    w, clock, state, taps = make()
    state["front"] = ("Google Chrome", "youtube.com")
    run(w, clock, 60)
    state["front"] = ("Cursor", None)
    run(w, clock, 10)
    state["front"] = ("Google Chrome", "youtube.com")
    run(w, clock, 60)
    assert taps == []


def test_distraction_cooldown_5_min():
    w, clock, state, taps = make(minutes=45)
    state["front"] = ("Google Chrome", "x.com")
    run(w, clock, 95)
    assert len(taps) == 1
    run(w, clock, 4 * 60)          # still on x.com, inside the cooldown
    assert len(taps) == 1
    run(w, clock, 60)              # cooldown over
    assert len(taps) == 2


def test_no_nudge_outside_a_block():
    w, clock, state, taps = make(minutes=None)
    state["front"] = ("Google Chrome", "youtube.com")
    evs = run(w, clock, 300)
    assert taps == [] and actions(evs, "focus") == []
    assert any(e["kind"] == "focus" and e["distracted"] and e["block_left_min"] is None for e in evs)


def test_no_nudge_after_the_block_ends():
    w, clock, state, taps = make(minutes=1)
    clock.t += 61
    state["front"] = ("Google Chrome", "youtube.com")
    run(w, clock, 200)
    assert taps == []


def test_focus_event_every_30s_or_on_change():
    w, clock, state, _ = make()
    focus = [e for e in run(w, clock, 60) if e["kind"] == "focus"]
    assert len(focus) == 2                             # t=0 and t=30
    assert focus[0] == {**focus[0], "app": "Cursor", "site": None, "distracted": False, "block_left_min": 45}
    state["front"] = ("Safari", "reddit.com")
    focus = [e for e in w.tick() if e["kind"] == "focus"]
    assert len(focus) == 1 and focus[0]["distracted"] is True


def test_demo_thresholds_20s_and_tagged():
    w, clock, state, taps = make(rules=DEMO_RULES)
    state["front"] = ("Arc", "tiktok.com")
    evs = run(w, clock, 25)
    acts = actions(evs, "focus")
    assert len(acts) == 1 and acts[0]["reason"] == "distracted 20 s on tiktok.com"
    assert all(e.get("demo_thresholds") is True for e in evs)


def test_streak_start():
    assert streak_start([], 100, 10) is None
    assert streak_start([0, 5, 50, 55, 58], 60, 10) == 50   # 45 s gap breaks it
    assert streak_start([0, 5, 9], 30, 10) is None          # already resting


def test_break_after_90_min_active_then_cooldown_30_min():
    w, clock, state, taps = make(minutes=None)          # break rule needs no block
    assert actions(run(w, clock, 89 * 60, step=60), "break") == []
    acts = actions(run(w, clock, 2 * 60, step=60), "break")
    assert len(acts) == 1 and acts[0]["channels"] == ["break", "tap"]
    assert taps == [acts[0]["message"]] and acts[0]["message"].startswith("Take 5")
    assert len(acts[0]["message"].split()) <= 5
    assert actions(run(w, clock, 29 * 60, step=60), "break") == []
    assert len(actions(run(w, clock, 2 * 60, step=60), "break")) == 1


def test_break_counts_logged_prompts_before_the_watcher_started():
    clock0 = 1_000_000.0
    prompts = [clock0 - 89 * 60 + i * 5 * 60 for i in range(18)]  # a prompt every 5 min for 89 min
    w, clock, state, taps = make(minutes=None, activity=prompts)
    acts = actions(run(w, clock, 2 * 60, step=60), "break")
    assert len(acts) == 1


def test_idle_is_not_activity():
    w, clock, state, taps = make(minutes=None, idle=600)
    run(w, clock, 120 * 60, step=60)
    assert taps == []
