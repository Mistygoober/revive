"""Tests for the interventions (nbz). No real network or speech here:
send=False / speak=False keep every test offline and silent.
"""
import time

from act import say, tap


def test_tap_truncates_to_five_words():
    ev = tap("one two three four five six seven", send=False)
    assert ev["text"] == "one two three four five"
    assert ev["medium"] == "tap"
    assert ev["sent"] is False


def test_tap_returns_fast():
    start = time.perf_counter()
    tap("breathe and reset", send=False)
    assert time.perf_counter() - start < 1.0


def test_say_takes_first_sentence():
    ev = say("Take a breath. You have been at this a while.", speak=False)
    assert ev["text"] == "Take a breath."
    assert ev["medium"] == "say"


def test_actions_never_throw_on_empty():
    assert tap("", send=False)["text"] == ""
    assert say("", speak=False)["text"] == ""


def test_actions_logged_to_event_log():
    from shared.events import read_events

    tap("test nudge here", send=False)
    events = read_events(last=5)
    assert any(e.get("kind") == "action" and e.get("medium") == "tap" for e in events)
