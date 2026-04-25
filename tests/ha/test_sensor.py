from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from custom_components.spa_care.domain.models import Reading
from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS
from custom_components.spa_care.sensor import (
    LastTestAgeSensor,
    ReadingSensor,
    RecommendedActionSensor,
)


def _coord(reading: Reading | None = None):
    coord = MagicMock()
    coord.last_reading = reading
    coord.doses = []
    coord.targets = DEFAULT_TARGETS
    coord.volume_l = 1500.0
    return coord


def test_reading_sensor_returns_value_for_field():
    coord = _coord(Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.2))
    s = ReadingSensor(coord, entry_id="x", field="total_bromine", name="Total Bromine", unit="ppm")
    assert s.native_value == 4.2


def test_reading_sensor_returns_none_when_no_reading():
    coord = _coord(None)
    s = ReadingSensor(coord, entry_id="x", field="total_bromine", name="Total Bromine", unit="ppm")
    assert s.native_value is None


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
