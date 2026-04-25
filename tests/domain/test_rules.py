from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from custom_components.spa_care.domain.models import Dose, Reading
from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS
from custom_components.spa_care.domain.rules import RuleState, evaluate_rules

NOW = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
VOLUME_L = 1500.0


@dataclass
class _Suppressions:
    last_fired: dict[tuple[str, str], datetime] = field(default_factory=dict)


def _state(
    *,
    last_reading: Reading | None = None,
    doses: list[Dose] | None = None,
    suppressions: dict[tuple[str, str], datetime] | None = None,
) -> RuleState:
    return RuleState(
        targets=DEFAULT_TARGETS,
        volume_l=VOLUME_L,
        last_reading=last_reading,
        doses=tuple(doses or ()),
        suppressions=suppressions or {},
    )


def test_test_overdue_fires_when_no_reading_for_more_than_5_days():
    state = _state(last_reading=None)
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    kinds = [a.payload.get("category") for a in actions if a.kind == "fire_event"]
    assert "test_overdue" in kinds


def test_test_overdue_does_not_fire_when_recent_reading_logged():
    recent = NOW - timedelta(days=2)
    state = _state(last_reading=Reading(timestamp=recent, total_bromine=4.0, ph=7.4))
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    kinds = [a.payload.get("category") for a in actions if a.kind == "fire_event"]
    assert "test_overdue" not in kinds


def test_reading_recommendation_fires_for_each_out_of_range():
    r = Reading(timestamp=NOW, total_bromine=2.0, ph=7.9)
    state = _state(last_reading=r)
    actions = evaluate_rules(state, now=NOW, trigger="log_reading")
    nudges = [a.payload for a in actions if a.kind == "fire_event"]
    subjects = [n["subject"] for n in nudges if n["category"] == "out_of_range"]
    assert "tb" in subjects
    assert "ph" in subjects


def test_reading_recommendation_suppressed_within_6h():
    r = Reading(timestamp=NOW, total_bromine=2.0)
    state = _state(
        last_reading=r,
        suppressions={("out_of_range", "tb"): NOW - timedelta(hours=2)},
    )
    actions = evaluate_rules(state, now=NOW, trigger="log_reading")
    nudges = [a.payload for a in actions if a.kind == "fire_event"]
    out_of_range_tb = [n for n in nudges if n["category"] == "out_of_range" and n["subject"] == "tb"]
    assert out_of_range_tb == []


def test_schedule_due_fires_when_cadence_elapsed():
    last_dose = NOW - timedelta(days=8)
    state = _state(
        doses=[Dose(timestamp=last_dose, product_key="spa_no_scale", amount=60)],
    )
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    nudges = [a.payload for a in actions if a.kind == "fire_event"]
    assert any(
        n["category"] == "schedule_due" and n["subject"] == "spa_no_scale"
        for n in nudges
    )


def test_schedule_due_does_not_fire_within_cadence():
    last_dose = NOW - timedelta(days=2)
    state = _state(
        doses=[Dose(timestamp=last_dose, product_key="spa_no_scale", amount=60)],
    )
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    nudges = [a.payload for a in actions if a.kind == "fire_event"]
    assert not any(
        n["category"] == "schedule_due" and n["subject"] == "spa_no_scale"
        for n in nudges
    )


def test_post_dose_retest_fires_2h_after_reading_driven_dose():
    last_dose = NOW - timedelta(hours=3)
    state = _state(
        doses=[Dose(timestamp=last_dose, product_key="brominating_granules", amount=10)],
    )
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    kinds = [a.payload.get("category") for a in actions if a.kind == "fire_event"]
    assert "retest_due" in kinds


def test_post_dose_retest_does_not_fire_for_schedule_driven_dose():
    last_dose = NOW - timedelta(hours=3)
    state = _state(
        doses=[Dose(timestamp=last_dose, product_key="spa_no_scale", amount=60)],
    )
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    kinds = [a.payload.get("category") for a in actions if a.kind == "fire_event"]
    assert "retest_due" not in kinds


def test_post_dose_retest_clears_after_subsequent_reading():
    last_dose = NOW - timedelta(hours=3)
    later_reading = Reading(timestamp=NOW - timedelta(hours=1), total_bromine=4.0)
    state = _state(
        last_reading=later_reading,
        doses=[Dose(timestamp=last_dose, product_key="brominating_granules", amount=10)],
    )
    actions = evaluate_rules(state, now=NOW, trigger="hourly")
    kinds = [a.payload.get("category") for a in actions if a.kind == "fire_event"]
    assert "retest_due" not in kinds
