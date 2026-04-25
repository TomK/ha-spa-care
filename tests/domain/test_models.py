from datetime import datetime, timezone

from custom_components.spa_care.domain.models import (
    Action,
    Dose,
    ProductForm,
    ProductMode,
    Reading,
    ReadingState,
    Recommendation,
    TargetRange,
)


def test_target_range_midpoint():
    tr = TargetRange(target_low=3.0, target_high=5.0, hard_min=0.0, hard_max=20.0)
    assert tr.midpoint == 4.0


def test_reading_allows_partial_data():
    r = Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0)
    assert r.total_bromine == 4.0
    assert r.ph is None


def test_dose_carries_product_and_amount():
    d = Dose(
        timestamp=datetime.now(timezone.utc),
        product_key="brominating_granules",
        amount=15.0,
    )
    assert d.product_key == "brominating_granules"
    assert d.amount == 15.0


def test_recommendation_priority_orders_lower_first():
    a = Recommendation(product_key="x", amount=1, reason="r", priority=2)
    b = Recommendation(product_key="y", amount=1, reason="r", priority=1)
    assert sorted([a, b], key=lambda r: r.priority)[0] is b


def test_action_payload_is_arbitrary_dict():
    act = Action(kind="fire_event", payload={"category": "test_overdue"})
    assert act.payload["category"] == "test_overdue"


def test_enums_present():
    assert ReadingState.IN_RANGE.value == "in_range"
    assert ProductForm.SOLID.value == "solid"
    assert ProductMode.READING_DRIVEN.value == "reading_driven"
