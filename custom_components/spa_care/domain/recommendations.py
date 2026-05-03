"""Reading → ranked recommendations."""

from __future__ import annotations

from .chemistry import classify_reading, compute_dose
from .models import Reading, ReadingState, Recommendation, TargetRange
from .products import products_for_reading

# Default UK bromine-spa target ranges. Mutable per config entry — these
# are seeds for first-run config flow.
#
# Hard bounds are deliberately wider than "good" range — they only flag
# readings that are almost certainly a strip misread or input error. A
# reading inside the hard band still gets a real treatment/advice; one
# outside the band gets the same treatment/advice with a "verify with the
# strip" suffix rather than being suppressed.
DEFAULT_TARGETS: dict[str, TargetRange] = {
    "tb": TargetRange(target_low=3.0, target_high=5.0, hard_min=0.0, hard_max=30.0),
    "ph": TargetRange(target_low=7.2, target_high=7.6, hard_min=5.5, hard_max=9.0),
    "ta": TargetRange(target_low=80.0, target_high=120.0, hard_min=0.0, hard_max=500.0),
    "ch": TargetRange(target_low=100.0, target_high=250.0, hard_min=0.0, hard_max=2500.0),
}

# Priority: lower number = recommended first. TB sanitation > pH/TA > CH.
_PRIORITY = {"tb": 1, "ph": 2, "ta": 3, "ch": 4}

# pH delta-per-dose normalisation: products.factor for pH is "g per 0.2 pH",
# so the divisor when computing grams = delta * factor / 0.2.
_PH_DELTA_UNIT = 0.2
# TA / CH delta-per-dose normalisation: factor is "g per 10 ppm".
_PPM_DELTA_UNIT_TA_CH = 10.0

# Advice text for out-of-range readings that have no chemical fix (or whose
# chemical fix has tricky knock-on effects). Emitted as Recommendation with
# product_key="__advice__"; the card and sensor render the reason text
# directly; the Log Recommended Doses button skips them (amount=0).
#
# High CH is intentionally absent: in hard-water areas the only "fix" is a
# partial water change with equally-hard refill, which doesn't meaningfully
# lower hardness. Silently letting the reading sit is more honest than a
# recommendation the user can't act on.
_ADVICE_FOR: dict[tuple[str, str], str] = {
    ("tb", "lower"): (
        "TB is {value} ppm (above target). Stop adding tablets; bromine "
        "decays over a day or two. Avoid the tub above 8 ppm."
    ),
    ("ta", "lower"): (
        "TA is {value} ppm (above target). pH down lowers TA but also "
        "drops pH — dose carefully, then aerate (jets on, no cover) for "
        "an hour to bring pH back up. Or do a partial water change."
    ),
}


def _reading_value(r: Reading, key: str) -> float | None:
    return {
        "tb": r.total_bromine,
        "ph": r.ph,
        "ta": r.total_alkalinity,
        "ch": r.calcium_hardness,
    }[key]


def _delta_unit(key: str) -> float:
    return _PH_DELTA_UNIT if key == "ph" else _PPM_DELTA_UNIT_TA_CH if key in ("ta", "ch") else 1.0


_VERIFY_STRIP_HINT = (
    " (Reading is unusually far off — double-check the strip if this looks wrong.)"
)


def evaluate_reading(
    reading: Reading,
    targets: dict[str, TargetRange],
    volume_l: float,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    for key in ("tb", "ph", "ta", "ch"):
        value = _reading_value(reading, key)
        if value is None:
            continue
        target = targets[key]
        state = classify_reading(value, target)
        if state is ReadingState.IN_RANGE:
            continue

        unusual = state is ReadingState.OUT_OF_BAND
        direction = "raise" if value < target.target_low else "lower"
        rec = _recommend(key, value, direction, target, volume_l, unusual)
        if rec is not None:
            recs.append(rec)

    return sorted(recs, key=lambda r: r.priority)


def _recommend(
    key: str,
    value: float,
    direction: str,
    target: TargetRange,
    volume_l: float,
    unusual: bool,
) -> Recommendation | None:
    """Pick the best recommendation for an out-of-target reading.

    Out-of-band readings still get the normal treatment/advice — they
    just have a verify-strip hint suffixed to the reason. Only when no
    treatment and no advice exist do we fall back to a bare recheck.
    """
    candidates = products_for_reading(key, direction=direction)
    product = candidates[0] if candidates else None
    if product is not None and product.factor is not None:
        delta_units = abs(target.midpoint - value) / _delta_unit(key)
        amount = compute_dose(delta=delta_units, factor=product.factor, volume_l=volume_l)
        if amount > 0:
            descriptor = "low" if direction == "raise" else "high"
            reason = (
                f"{key.upper()} = {value} is {descriptor}; "
                f"target {target.target_low}–{target.target_high}."
            )
            if unusual:
                reason += _VERIFY_STRIP_HINT
            return Recommendation(
                product_key=product.key,
                amount=amount,
                reason=reason,
                priority=_PRIORITY[key],
            )

    advice_template = _ADVICE_FOR.get((key, direction))
    if advice_template is not None:
        reason = advice_template.format(value=value)
        if unusual:
            reason += _VERIFY_STRIP_HINT
        return Recommendation(
            product_key="__advice__",
            amount=0.0,
            reason=reason,
            priority=_PRIORITY[key],
        )

    if unusual:
        return Recommendation(
            product_key="__recheck__",
            amount=0.0,
            reason=f"{key.upper()} reading {value} looks unusual — recheck strip and re-log.",
            priority=_PRIORITY[key],
        )

    return None
