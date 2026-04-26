"""Rule engine — given state + clock, return Actions to dispatch.

Pure: no HA imports, no side effects. The coordinator turns Actions
into HA-side effects (entity updates, events, notifications).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import Action, Dose, MaintenanceAction, Reading, TargetRange
from .products import get_product, maintenance_products, scheduled_products
from .recommendations import evaluate_reading

TEST_OVERDUE_DAYS = 5
RETEST_DELAY = timedelta(hours=2)
RETEST_WINDOW = timedelta(hours=24)

SUPPRESSION_OUT_OF_RANGE = timedelta(hours=6)
SUPPRESSION_TEST_OVERDUE = timedelta(hours=24)
SUPPRESSION_RETEST_DUE = timedelta(hours=1)
# schedule_due suppression is 1 cadence cycle, computed per-product.


@dataclass(frozen=True)
class RuleState:
    targets: dict[str, TargetRange]
    volume_l: float
    last_reading: Reading | None
    doses: tuple[Dose, ...]
    actions: tuple[MaintenanceAction, ...]
    suppressions: dict[tuple[str, str], datetime]


def evaluate_rules(state: RuleState, *, now: datetime, trigger: str) -> list[Action]:
    actions: list[Action] = []
    actions.extend(_test_overdue(state, now))
    actions.extend(_reading_recommendation(state, now, trigger))
    actions.extend(_schedule_due(state, now))
    actions.extend(_post_dose_retest(state, now))
    return actions


def _suppressed(state: RuleState, category: str, subject: str, window: timedelta, now: datetime) -> bool:
    last = state.suppressions.get((category, subject))
    return last is not None and (now - last) < window


def _emit_nudge(category: str, subject: str, message: str, **extra) -> Action:
    return Action(
        kind="fire_event",
        payload={"category": category, "subject": subject, "message": message, **extra},
    )


def _test_overdue(state: RuleState, now: datetime) -> list[Action]:
    last_test = state.last_reading.timestamp if state.last_reading else None
    overdue = last_test is None or (now - last_test) > timedelta(days=TEST_OVERDUE_DAYS)
    if not overdue:
        return []
    if _suppressed(state, "test_overdue", "global", SUPPRESSION_TEST_OVERDUE, now):
        return []
    return [_emit_nudge("test_overdue", "global", "It's been a while — time to test the water.")]


def _reading_recommendation(state: RuleState, now: datetime, trigger: str) -> list[Action]:
    if trigger != "log_reading" or state.last_reading is None:
        return []
    recs = evaluate_reading(state.last_reading, state.targets, state.volume_l)
    actions: list[Action] = []
    seen_subjects: set[str] = set()
    for rec in recs:
        # Map product_key back to reading subject for suppression keying.
        subject = _subject_for_recommendation(rec.product_key)
        if subject is None or subject in seen_subjects:
            continue
        seen_subjects.add(subject)
        if _suppressed(state, "out_of_range", subject, SUPPRESSION_OUT_OF_RANGE, now):
            continue
        msg = (
            f"{rec.reason} Suggested: {rec.amount:g} of {rec.product_key}."
            if rec.amount > 0
            else rec.reason
        )
        actions.append(_emit_nudge(
            "out_of_range",
            subject,
            msg,
            product=rec.product_key,
            amount=rec.amount,
        ))
    return actions


def _subject_for_recommendation(product_key: str) -> str | None:
    if product_key == "__recheck__":
        return "recheck"
    if product_key == "__advice__":
        return "advice"
    try:
        product = get_product(product_key)
    except KeyError:
        return None
    return product.target_reading


def _schedule_due(state: RuleState, now: datetime) -> list[Action]:
    actions: list[Action] = []
    last_dose_by_key = _last_dose_by_product(state.doses)
    last_action_by_key = _last_action_by_product(state.actions)

    candidates: list[tuple] = []
    for product in scheduled_products():
        candidates.append((product, last_dose_by_key.get(product.key)))
    for product in maintenance_products():
        candidates.append((product, last_action_by_key.get(product.key)))

    for product, last in candidates:
        cadence = timedelta(days=product.cadence_days or 0)
        if last is not None and (now - last.timestamp) < cadence:
            continue
        if _suppressed(state, "schedule_due", product.key, cadence, now):
            continue
        actions.append(_emit_nudge(
            "schedule_due",
            product.key,
            f"{product.name} is due (every {product.cadence_days} days).",
            product=product.key,
        ))
    return actions


def _post_dose_retest(state: RuleState, now: datetime) -> list[Action]:
    last_reading_dose = last_reading_driven_dose(state.doses)
    if last_reading_dose is None:
        return []
    age = now - last_reading_dose.timestamp
    if age < RETEST_DELAY or age > RETEST_WINDOW:
        return []
    # Cleared if a reading has been logged since the dose.
    if state.last_reading and state.last_reading.timestamp > last_reading_dose.timestamp:
        return []
    if _suppressed(state, "retest_due", "global", SUPPRESSION_RETEST_DUE, now):
        return []
    return [_emit_nudge(
        "retest_due",
        "global",
        f"Two hours since dosing {last_reading_dose.product_key}. Retest the water.",
        product=last_reading_dose.product_key,
    )]


def _last_dose_by_product(doses: tuple[Dose, ...]) -> dict[str, Dose]:
    out: dict[str, Dose] = {}
    for d in doses:
        existing = out.get(d.product_key)
        if existing is None or d.timestamp > existing.timestamp:
            out[d.product_key] = d
    return out


def _last_action_by_product(
    actions: tuple[MaintenanceAction, ...],
) -> dict[str, MaintenanceAction]:
    out: dict[str, MaintenanceAction] = {}
    for a in actions:
        existing = out.get(a.product_key)
        if existing is None or a.timestamp > existing.timestamp:
            out[a.product_key] = a
    return out


def last_reading_driven_dose(doses: tuple[Dose, ...]) -> Dose | None:
    candidates: list[Dose] = []
    for d in doses:
        try:
            product = get_product(d.product_key)
        except KeyError:
            continue
        if product.target_reading is not None and product.direction is not None:
            candidates.append(d)
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.timestamp)
