"""HRV core owned by nbz: clean beat-to-beat (RR) intervals, then RMSSD.

Spec (docs/plan/FOR-NBZ.md):
- Drop RR < 300 ms or > 2000 ms.
- Drop any RR more than 20% from the median of the last 10 accepted beats
  (squats caused fake 2-5 s intervals in the 11:30 test -> the hero bug).
- Report rmssd = None when fewer than 20 clean beats remain.
- strained = HR >= 20 above baseline OR RMSSD < 60% of baseline (held 60 s,
  which the state aggregator enforces; this module judges a single sample).
"""
from __future__ import annotations

from statistics import median

RR_MIN_MS = 300
RR_MAX_MS = 2000
MEDIAN_WINDOW = 10
ARTIFACT_TOLERANCE = 0.20
MIN_CLEAN_BEATS = 20


def _valid_flags(rr_ms: list[float]) -> list[bool]:
    """Per-beat validity: absolute range gate, then a rolling-median gate
    against the last up-to-10 beats already accepted."""
    accepted: list[float] = []
    flags: list[bool] = []
    for rr in rr_ms:
        ok = rr is not None and RR_MIN_MS <= rr <= RR_MAX_MS
        if ok:
            window = accepted[-MEDIAN_WINDOW:]
            if window:
                med = median(window)
                if med > 0 and abs(rr - med) / med > ARTIFACT_TOLERANCE:
                    ok = False
        if ok:
            accepted.append(float(rr))
        flags.append(ok)
    return flags


def clean_rr(rr_ms: list[float]) -> list[float]:
    """Return only the physiologically plausible, non-artifact RR intervals.

    For display/counts. RMSSD does NOT run on this list directly, because
    dropping a beat would make its neighbours look consecutive; see rmssd().
    """
    flags = _valid_flags(rr_ms)
    return [float(rr) for rr, ok in zip(rr_ms, flags) if ok]


def rmssd(rr_ms: list[float], *, already_clean: bool = False) -> float | None:
    """Root mean square of successive RR differences, in ms.

    A successive difference is counted only between two beats that are
    adjacent in the *original* stream and both valid -- never across a
    removed artifact, which would invent a fake large difference and wreck
    the estimate. Returns None when fewer than MIN_CLEAN_BEATS survive.
    """
    if already_clean:
        clean = [float(x) for x in rr_ms]
        if len(clean) < MIN_CLEAN_BEATS:
            return None
        diffs = [clean[i + 1] - clean[i] for i in range(len(clean) - 1)]
    else:
        flags = _valid_flags(rr_ms)
        if sum(flags) < MIN_CLEAN_BEATS:
            return None
        diffs = [
            rr_ms[i + 1] - rr_ms[i]
            for i in range(len(rr_ms) - 1)
            if flags[i] and flags[i + 1]  # both valid AND adjacent in the raw stream
        ]
    if not diffs:
        return None
    mean_sq = sum(d * d for d in diffs) / len(diffs)
    return round(mean_sq ** 0.5, 1)


def classify_strain(
    hr: float | None,
    rmssd_val: float | None,
    hr_base: float,
    rmssd_base: float,
) -> str:
    """Single-sample strain label. The 60-s hold lives in the aggregator.

    strained: HR >= 20 over baseline, or RMSSD below 60% of baseline.
    elevated: HR >= 10 over baseline, or RMSSD below 80% of baseline.
    calm:     otherwise.
    """
    hr_high = hr is not None and hr >= hr_base + 20
    rmssd_low = rmssd_val is not None and rmssd_base > 0 and rmssd_val < 0.60 * rmssd_base
    if hr_high or rmssd_low:
        return "strained"

    hr_mid = hr is not None and hr >= hr_base + 10
    rmssd_mid = rmssd_val is not None and rmssd_base > 0 and rmssd_val < 0.80 * rmssd_base
    if hr_mid or rmssd_mid:
        return "elevated"

    return "calm"
