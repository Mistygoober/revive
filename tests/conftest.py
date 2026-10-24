"""Every test writes to a temporary event log, never the real data/events.jsonl."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_event_log(tmp_path, monkeypatch):
    import shared.config as config
    import shared.events as events

    data, raw = tmp_path / "data", tmp_path / "memory" / "raw"
    for mod in (config, events):
        monkeypatch.setattr(mod, "DATA_DIR", data, raising=False)
        monkeypatch.setattr(mod, "EVENTS_PATH", data / "events.jsonl", raising=False)
        monkeypatch.setattr(mod, "RAW_DIR", raw, raising=False)
    try:
        import coach.policy as policy
        monkeypatch.setattr(policy, "STATE", data / "coach_state.json", raising=False)
    except Exception:
        pass
    yield
