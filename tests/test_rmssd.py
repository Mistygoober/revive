"""Tests for the RR cleaner + RMSSD core (nbz).

The squat case is the hero bug: motion artifacts inject fake RR intervals.
Without the filter RMSSD explodes; with it, it stays sane.
"""
import json
from pathlib import Path

from body.rmssd import classify_strain, clean_rr, rmssd

SQUAT_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "squats_rr.jsonl"


def _calm_rr(n: int, base: float = 850.0) -> list[float]:
    """A steady resting trace: small alternating beat-to-beat variation."""
    return [base + (6 if i % 2 else -6) for i in range(n)]


def test_clean_rr_drops_out_of_range():
    rr = [850, 851, 120, 850, 5000, 852, 849]  # 120 too low, 5000 too high
    cleaned = clean_rr(rr)
    assert 120 not in cleaned
    assert 5000 not in cleaned
    assert cleaned == [850, 851, 850, 852, 849]


def test_clean_rr_drops_median_outliers():
    # Steady ~850 ms, then a single beat >20% off the rolling median.
    rr = _calm_rr(12) + [1300] + _calm_rr(4)
    cleaned = clean_rr(rr)
    assert 1300 not in cleaned


def test_rmssd_none_when_too_few_beats():
    assert rmssd(_calm_rr(10)) is None  # under 20 clean beats


def test_rmssd_reasonable_on_calm_trace():
    val = rmssd(_calm_rr(60))
    assert val is not None
    # Alternating +/-6 around base -> successive diffs ~12 ms.
    assert 8 < val < 16


def test_squat_artifacts_do_not_explode_rmssd():
    # The hero bug: resting trace with motion-artifact long intervals spliced in.
    resting = _calm_rr(60)
    artifacts = [2500, 3800, 2100, 4200, 2900]  # fake long RR from squats
    noisy = []
    for i, beat in enumerate(resting):
        noisy.append(beat)
        if i in (15, 20, 25, 30, 35):
            noisy.append(artifacts.pop(0))

    raw = rmssd(noisy)             # with the filter
    unfiltered_clean = noisy[:]    # same beats, but skip the median gate
    # Prove the artifacts are what blow it up: RMSSD on the raw-including-artifacts
    # series is huge, while the filtered one stays in the calm range.
    big = rmssd(unfiltered_clean, already_clean=True)
    assert big is not None and big > 300          # artifacts explode it
    assert raw is not None and raw < 20           # filter tames it


def test_real_squat_fixture_hero_bug():
    """The recorded squat trace (Polar H10 19C01935): raw motion artifacts
    explode RMSSD; the filter brings it back to a plausible value."""
    rows = [json.loads(ln) for ln in SQUAT_FIXTURE.read_text().splitlines() if ln.strip()]
    rr = [v for r in rows for v in r.get("rr", [])]
    assert len(rr) >= 20, "fixture too short to judge"

    unfiltered = rmssd(rr, already_clean=True)   # --no-filter path: the hero bug
    filtered = rmssd(rr)                          # with the artifact filter
    assert unfiltered is not None and filtered is not None
    assert unfiltered > 50, "expected artifacts to inflate RMSSD"
    assert filtered < 40, "filter should tame RMSSD to a plausible value"
    assert unfiltered > 2 * filtered, "filter should make a decisive difference"


def test_classify_strain_thresholds():
    assert classify_strain(70, 42.0, 68, 41.0) == "calm"
    assert classify_strain(96, 22.4, 68, 41.0) == "strained"   # HR +28, RMSSD 55%
    assert classify_strain(88, 24.0, 68, 41.0) == "strained"   # RMSSD 58% < 60%
    assert classify_strain(80, 35.0, 68, 41.0) == "elevated"   # RMSSD 85%? -> HR +12
    assert classify_strain(70, None, 68, 41.0) == "calm"       # missing RMSSD, calm HR
