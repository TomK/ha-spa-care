from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from custom_components.spa_care.binary_sensor import (
    OutOfRangeBinarySensor,
    TestDueBinarySensor,
)
from custom_components.spa_care.domain.models import Dose, Reading


def _coord(*, last_reading=None, doses=None):
    coord = MagicMock()
    coord.last_reading = last_reading
    coord.doses = doses or []
    coord.targets = {}
    coord.volume_l = 1500.0
    from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS
    coord.targets = DEFAULT_TARGETS
    return coord


def test_test_due_off_when_recent_reading_no_dose():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0))
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is False
    assert s.extra_state_attributes == {"reasons": []}


def test_test_due_routine_when_no_reading():
    coord = _coord(last_reading=None)
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is True
    assert s.extra_state_attributes == {"reasons": ["routine"]}


def test_test_due_routine_when_reading_older_than_5_days():
    old = datetime.now(timezone.utc) - timedelta(days=6)
    coord = _coord(last_reading=Reading(timestamp=old, total_bromine=4.0))
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is True
    assert s.extra_state_attributes["reasons"] == ["routine"]


def test_test_due_post_dose_within_retest_window():
    last = datetime.now(timezone.utc) - timedelta(hours=3)
    coord = _coord(
        last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0),
        doses=[Dose(timestamp=last, product_key="brominating_granules", amount=10)],
    )
    # No reading after the dose → retest pending
    coord.last_reading = None  # simplest setup: no later reading
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is True
    reasons = s.extra_state_attributes["reasons"]
    assert "post_dose" in reasons


def test_test_due_post_dose_does_not_fire_for_schedule_driven():
    last = datetime.now(timezone.utc) - timedelta(hours=3)
    coord = _coord(
        last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0),
        doses=[Dose(timestamp=last, product_key="spa_no_scale", amount=60)],
    )
    s = TestDueBinarySensor(coord, entry_id="x")
    # Recent reading with all-in-range chemistry, schedule-driven dose only → no reasons
    assert s.is_on is False
    assert s.extra_state_attributes["reasons"] == []


def test_test_due_clears_after_reading_logged_after_dose():
    dosed = datetime.now(timezone.utc) - timedelta(hours=3)
    reading_after = datetime.now(timezone.utc) - timedelta(hours=1)
    coord = _coord(
        last_reading=Reading(timestamp=reading_after, total_bromine=4.0),
        doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)],
    )
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is False


def test_test_due_both_when_old_reading_and_recent_dose():
    old_reading = datetime.now(timezone.utc) - timedelta(days=6)
    dosed = datetime.now(timezone.utc) - timedelta(hours=3)
    coord = _coord(
        last_reading=Reading(timestamp=old_reading, total_bromine=4.0),
        doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)],
    )
    s = TestDueBinarySensor(coord, entry_id="x")
    assert s.is_on is True
    reasons = s.extra_state_attributes["reasons"]
    assert "post_dose" in reasons
    assert "routine" in reasons


def test_out_of_range_true_when_value_below_target():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=2.0))
    s = OutOfRangeBinarySensor(coord, entry_id="x", reading_key="tb", name="TB Out of Range")
    assert s.is_on is True


def test_out_of_range_false_when_value_in_target():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0))
    s = OutOfRangeBinarySensor(coord, entry_id="x", reading_key="tb", name="TB Out of Range")
    assert s.is_on is False
