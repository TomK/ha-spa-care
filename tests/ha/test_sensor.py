from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from custom_components.spa_care.domain.models import Dose, Reading
from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS
from custom_components.spa_care.sensor import (
    LastTestAgeSensor,
    NextRetestAtSensor,
    RecommendedActionSensor,
    TubVolumeSensor,
)


def _coord(reading: Reading | None = None, *, doses: list[Dose] | None = None):
    coord = MagicMock()
    coord.last_reading = reading
    coord.doses = doses or []
    coord.targets = DEFAULT_TARGETS
    coord.volume_l = 1500.0
    return coord


def test_tub_volume_sensor_reports_volume_l():
    coord = _coord()
    s = TubVolumeSensor(coord, entry_id="x")
    assert s.native_value == 1500.0
    assert s.native_unit_of_measurement == "L"


def test_last_test_age_sensor_reports_minutes():
    last = datetime.now(timezone.utc) - timedelta(minutes=37)
    coord = _coord(Reading(timestamp=last))
    s = LastTestAgeSensor(coord, entry_id="x")
    assert 36 <= s.native_value <= 38


def test_recommended_action_sensor_no_reading():
    coord = _coord(None)
    s = RecommendedActionSensor(coord, entry_id="x")
    assert s.native_value == "No reading yet"


def test_recommended_action_sensor_all_in_range():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=180,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    assert s.native_value == "None — looking good"


def test_recommended_action_sensor_single_action():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=2.0, ph=7.4, total_alkalinity=100, calcium_hardness=180,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    assert "Brominating granules" in s.native_value
    assert "g of " in s.native_value


def test_recommended_action_sensor_multiple_actions_joined_in_priority_order():
    # TB low (priority 1), pH high (priority 2)
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=2.0, ph=7.9, total_alkalinity=100, calcium_hardness=180,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    value = s.native_value
    # Both products should appear
    assert "Brominating granules" in value
    assert "pH down" in value
    # TB recommendation should come before pH (priority 1 before priority 2)
    assert value.index("Brominating granules") < value.index("pH down")
    # Joined by separator
    assert " · " in value


def test_recommended_action_sensor_recheck_lists_all_oob_reasons():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=99.0, ph=99.0,  # both out of band
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    value = s.native_value.lower()
    assert "tb" in value
    assert "ph" in value
    assert "recheck" in value


def test_recommended_action_sensor_attributes_actions_list():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=2.0, ph=7.9, total_alkalinity=100, calcium_hardness=180,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    actions = s.extra_state_attributes["actions"]
    assert isinstance(actions, list)
    assert len(actions) == 2
    assert "Brominating granules" in actions[0]
    assert "pH down" in actions[1]


def test_recommended_action_sensor_attributes_empty_when_in_range():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=180,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    assert s.extra_state_attributes == {"actions": []}


def test_recommended_action_sensor_attributes_recheck_uses_reason_text():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=99.0,
    ))
    s = RecommendedActionSensor(coord, entry_id="x")
    actions = s.extra_state_attributes["actions"]
    assert len(actions) == 1
    assert "recheck" in actions[0].lower()


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
