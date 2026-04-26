from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from custom_components.spa_care.domain.models import Dose, Reading
from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS
from custom_components.spa_care.sensor import (
    LastTestAgeSensor,
    NextRetestAtSensor,
    RecommendedActionSensor,
)


def _coord(reading: Reading | None = None, *, doses: list[Dose] | None = None):
    coord = MagicMock()
    coord.last_reading = reading
    coord.doses = doses or []
    coord.targets = DEFAULT_TARGETS
    coord.volume_l = 1500.0
    return coord


def test_last_test_age_sensor_reports_minutes():
    last = datetime.now(timezone.utc) - timedelta(minutes=37)
    coord = _coord(Reading(timestamp=last))
    s = LastTestAgeSensor(coord, entry_id="x")
    assert 36 <= s.native_value <= 38


def test_recommended_action_sensor_returns_top_text():
    coord = _coord(Reading(timestamp=datetime.now(timezone.utc), total_bromine=2.0))
    s = RecommendedActionSensor(coord, entry_id="x")
    # Triggers a re-eval inside the sensor; just assert it's a string and not None.
    assert isinstance(s.native_value, str)


def test_next_retest_at_returns_dose_timestamp_plus_delay():
    dosed = datetime.now(timezone.utc) - timedelta(minutes=30)
    coord = _coord(doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)])
    s = NextRetestAtSensor(coord, entry_id="x")
    assert s.native_value == dosed + timedelta(hours=2)


def test_next_retest_at_returns_none_when_no_dose():
    coord = _coord()
    s = NextRetestAtSensor(coord, entry_id="x")
    assert s.native_value is None


def test_next_retest_at_returns_none_after_subsequent_reading():
    dosed = datetime.now(timezone.utc) - timedelta(hours=1)
    later = datetime.now(timezone.utc) - timedelta(minutes=30)
    coord = _coord(
        Reading(timestamp=later, total_bromine=4.0),
        doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)],
    )
    s = NextRetestAtSensor(coord, entry_id="x")
    assert s.native_value is None


def test_next_retest_at_returns_none_after_window_expires():
    dosed = datetime.now(timezone.utc) - timedelta(hours=30)
    coord = _coord(doses=[Dose(timestamp=dosed, product_key="brominating_granules", amount=10)])
    s = NextRetestAtSensor(coord, entry_id="x")
    assert s.native_value is None


def test_next_retest_at_ignores_schedule_driven_doses():
    # Schedule-driven products (e.g. spa_no_scale) shouldn't trigger a retest
    dosed = datetime.now(timezone.utc) - timedelta(minutes=30)
    coord = _coord(doses=[Dose(timestamp=dosed, product_key="spa_no_scale", amount=60)])
    s = NextRetestAtSensor(coord, entry_id="x")
    assert s.native_value is None
