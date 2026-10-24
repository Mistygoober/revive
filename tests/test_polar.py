"""Tests for the H10 packet parser and get_body_state() wiring (nbz).
No Bluetooth: parse_hr_measurement is pure, and the state tests monkeypatch
the event lookup.
"""
import body.state as state
from body.polar import parse_hr_measurement
from shared.events import now_iso


def test_parse_8bit_hr_no_rr():
    hr, rr = parse_hr_measurement(bytes([0x00, 60]))
    assert hr == 60 and rr == []


def test_parse_16bit_hr_with_rr():
    # flags 0x11 = 16-bit HR + RR present; hr=300 (LE), rr raw=1024 -> 1000 ms
    hr, rr = parse_hr_measurement(bytes([0x11, 0x2C, 0x01, 0x00, 0x04]))
    assert hr == 300
    assert len(rr) == 1 and abs(rr[0] - 1000.0) < 0.5


def test_parse_skips_energy_expended():
    # flags 0x18 = energy expended (2 bytes) + RR present, 8-bit HR
    hr, rr = parse_hr_measurement(bytes([0x18, 70, 0xAA, 0xBB, 0x00, 0x04]))
    assert hr == 70
    assert len(rr) == 1 and abs(rr[0] - 1000.0) < 0.5


def test_parse_multiple_rr():
    # two RR values: 1024 and 512 -> 1000 ms and ~500 ms
    hr, rr = parse_hr_measurement(bytes([0x10, 65, 0x00, 0x04, 0x00, 0x02]))
    assert hr == 65 and len(rr) == 2
    assert abs(rr[0] - 1000.0) < 0.5 and abs(rr[1] - 500.0) < 0.5


def test_parse_bad_packets_never_raise():
    assert parse_hr_measurement(b"") == (None, [])
    assert parse_hr_measurement(bytes([0x01])) == (None, [])  # claims 16-bit, no data


def test_get_body_state_uses_fresh_event(monkeypatch):
    fresh = {
        "ts": now_iso(), "kind": "body", "hr": 101, "rmssd": 18.0,
        "strain": "strained", "source": "h10", "hr_base": 68, "rmssd_base": 41.0,
    }
    monkeypatch.setattr(state, "_latest_body_event", lambda: fresh)
    st = state.get_body_state()
    assert st["source"] == "h10" and st["strain"] == "strained" and st["hr"] == 101
    assert "today" in st


def test_get_body_state_falls_back_when_stale(monkeypatch):
    stale = {"ts": "2000-01-01T00:00:00-08:00", "kind": "body", "hr": 99}
    monkeypatch.setattr(state, "_latest_body_event", lambda: stale)
    monkeypatch.setenv("FAKE_STRAIN", "elevated")
    st = state.get_body_state()
    assert st["source"] == "fake" and st["strain"] == "elevated"


def test_get_body_state_falls_back_when_no_event(monkeypatch):
    monkeypatch.setattr(state, "_latest_body_event", lambda: None)
    monkeypatch.setenv("FAKE_STRAIN", "calm")
    st = state.get_body_state()
    assert st["source"] == "fake" and st["strain"] == "calm"
