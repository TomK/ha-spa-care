"""Pure dose maths and reading classification."""

from __future__ import annotations

from .models import ReadingState, TargetRange


def compute_dose(
    *,
    delta: float,
    factor: float,
    volume_l: float,
    cap: float = 0.75,
) -> float:
    """Compute dose in grams or ml (unit-generic — caller knows the form).

    `delta` is target_midpoint − current. Negative or zero deltas mean
    no dose needed. Result is rounded to nearest 5 for measurability.
    """
    if delta <= 0:
        return 0.0
    raw = delta * factor * (volume_l / 1000.0)
    capped = raw * cap
    return round(capped / 5.0) * 5.0


def classify_reading(value: float, target: TargetRange) -> ReadingState:
    if value < target.hard_min or value > target.hard_max:
        return ReadingState.OUT_OF_BAND
    if value < target.target_low:
        return ReadingState.BELOW
    if value > target.target_high:
        return ReadingState.ABOVE
    return ReadingState.IN_RANGE
