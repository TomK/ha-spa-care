from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from custom_components.spa_care.binary_sensor import (
    OutOfRangeBinarySensor,
    PostDoseRetestBinarySensor,
    TestOverdueBinarySensor,
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


def test_test_overdue_true_when_no_reading_or_old():
    coord = _coord(last_reading=None)
    s = TestOverdueBinarySensor(coord, entry_id="x")
    assert s.is_on is True


def test_test_overdue_false_when_recent_reading():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0))
    s = TestOverdueBinarySensor(coord, entry_id="x")
    assert s.is_on is False


def test_out_of_range_true_when_value_below_target():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=2.0))
    s = OutOfRangeBinarySensor(coord, entry_id="x", reading_key="tb", name="TB Out of Range")
    assert s.is_on is True


def test_out_of_range_false_when_value_in_target():
    coord = _coord(last_reading=Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.0))
    s = OutOfRangeBinarySensor(coord, entry_id="x", reading_key="tb", name="TB Out of Range")
    assert s.is_on is False


def test_retest_due_true_within_window():
    last = datetime.now(timezone.utc) - timedelta(hours=3)
    coord = _coord(doses=[Dose(timestamp=last, product_key="brominating_granules", amount=10)])
    s = PostDoseRetestBinarySensor(coord, entry_id="x")
    assert s.is_on is True


def test_retest_due_false_outside_window():
    last = datetime.now(timezone.utc) - timedelta(hours=30)
    coord = _coord(doses=[Dose(timestamp=last, product_key="brominating_granules", amount=10)])
    s = PostDoseRetestBinarySensor(coord, entry_id="x")
    assert s.is_on is False


def test_retest_due_false_when_reading_after_dose():
    dosed = datetime.now(timezone.utc) - timedelta(hours=3)
    reading_after = datetime.now(timezone.utc) - timedelta(hours=1)
    coord = _coord(
        last_reading=Reading(timestamp=reading_after, total_bromine=4.0),
        doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)],
    )
    s = PostDoseRetestBinarySensor(coord, entry_id="x")
    assert s.is_on is False
