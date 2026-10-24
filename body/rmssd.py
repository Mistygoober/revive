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


def clean_rr(rr_ms: list[float]) -> list[float]:
    """Return only the physiologically plausible, non-artifact RR intervals.

    Two passes per beat: an absolute range gate, then a rolling-median gate
    against the last up-to-10 beats we have already accepted.
    """
    accepted: list[float] = []
    for rr in rr_ms:
        if rr is None:
            continue
        if rr < RR_MIN_MS or rr > RR_MAX_MS:
            continue
        window = accepted[-MEDIAN_WINDOW:]
        if window:
            med = median(window)
            if med > 0 and abs(rr - med) / med > ARTIFACT_TOLERANCE:
                continue
        accepted.append(float(rr))
    return accepted


def rmssd(rr_ms: list[float], *, already_clean: bool = False) -> float | None:
    """Root mean square of successive RR differences, in ms.

    Cleans first unless told the input is already clean. Returns None when
    fewer than MIN_CLEAN_BEATS survive (too little to trust).
    """
    clean = rr_ms if already_clean else clean_rr(rr_ms)
    if len(clean) < MIN_CLEAN_BEATS:
        return None
    diffs = [clean[i + 1] - clean[i] for i in range(len(clean) - 1)]
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
