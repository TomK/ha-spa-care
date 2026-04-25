"""Reading → ranked recommendations."""

from __future__ import annotations

from .chemistry import classify_reading, compute_dose
from .models import Reading, ReadingState, Recommendation, TargetRange
from .products import products_for_reading

# Default UK bromine-spa target ranges. Mutable per config entry — these
# are seeds for first-run config flow.
DEFAULT_TARGETS: dict[str, TargetRange] = {
    "tb": TargetRange(target_low=3.0, target_high=5.0, hard_min=0.0, hard_max=20.0),
    "ph": TargetRange(target_low=7.2, target_high=7.6, hard_min=6.2, hard_max=8.4),
    "ta": TargetRange(target_low=80.0, target_high=120.0, hard_min=0.0, hard_max=300.0),
    "ch": TargetRange(target_low=100.0, target_high=250.0, hard_min=0.0, hard_max=1000.0),
}

# Priority: lower number = recommended first. TB sanitation > pH/TA > CH.
_PRIORITY = {"tb": 1, "ph": 2, "ta": 3, "ch": 4}

# pH delta-per-dose normalisation: products.factor for pH is "g per 0.2 pH",
# so the divisor when computing grams = delta * factor / 0.2.
_PH_DELTA_UNIT = 0.2
# TA / CH delta-per-dose normalisation: factor is "g per 10 ppm".
_PPM_DELTA_UNIT_TA_CH = 10.0


def _reading_value(r: Reading, key: str) -> float | None:
    return {
        "tb": r.total_bromine,
        "ph": r.ph,
        "ta": r.total_alkalinity,
        "ch": r.calcium_hardness,
    }[key]


def _delta_unit(key: str) -> float:
    return _PH_DELTA_UNIT if key == "ph" else _PPM_DELTA_UNIT_TA_CH if key in ("ta", "ch") else 1.0


def evaluate_reading(
    reading: Reading,
    targets: dict[str, TargetRange],
    volume_l: float,
) -> list[Recommendation]:
    out_of_band: list[Recommendation] = []
    dose_recs: list[Recommendation] = []

    for key in ("tb", "ph", "ta", "ch"):
        value = _reading_value(reading, key)
        if value is None:
            continue
        target = targets[key]
        state = classify_reading(value, target)

        if state is ReadingState.OUT_OF_BAND:
            out_of_band.append(Recommendation(
                product_key="__recheck__",
                amount=0.0,
                reason=f"{key.upper()} reading {value} looks wrong — recheck strip and re-log.",
                priority=_PRIORITY[key],
            ))
            continue

        if state is ReadingState.IN_RANGE:
            continue

        direction = "raise" if state is ReadingState.BELOW else "lower"
        candidates = products_for_reading(key, direction=direction)
        if not candidates:
            continue
        product = candidates[0]
        if product.factor is None:
            continue

        delta_raw = abs(target.midpoint - value)
        delta_units = delta_raw / _delta_unit(key)
        amount = compute_dose(delta=delta_units, factor=product.factor, volume_l=volume_l)
        if amount <= 0:
            continue

        dose_recs.append(Recommendation(
            product_key=product.key,
            amount=amount,
            reason=(
                f"{key.upper()} = {value} is {direction.replace('raise', 'low').replace('lower', 'high')}; "
                f"target {target.target_low}–{target.target_high}."
            ),
            priority=_PRIORITY[key],
        ))

    if out_of_band:
        return sorted(out_of_band, key=lambda r: r.priority)
    return sorted(dose_recs, key=lambda r: r.priority)
