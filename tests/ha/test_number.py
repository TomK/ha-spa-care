from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from custom_components.spa_care.domain.models import Reading
from custom_components.spa_care.number import ReadingNumber


def _coord(reading: Reading | None = None):
    coord = MagicMock()
    coord.last_reading = reading
    coord.async_log_reading = AsyncMock()
    return coord


def test_reading_number_returns_value_for_field():
    coord = _coord(Reading(timestamp=datetime.now(timezone.utc), total_bromine=4.2))
    n = ReadingNumber(coord, entry_id="x", field="total_bromine", name="TB", unit="ppm",
                     min_v=0.0, max_v=20.0, step=0.1)
    assert n.native_value == 4.2


def test_reading_number_returns_none_when_no_reading():
    coord = _coord(None)
    n = ReadingNumber(coord, entry_id="x", field="total_bromine", name="TB", unit="ppm",
                     min_v=0.0, max_v=20.0, step=0.1)
    assert n.native_value is None


async def test_reading_number_set_value_logs_partial_reading():
    coord = _coord(None)
    n = ReadingNumber(coord, entry_id="x", field="total_bromine", name="TB", unit="ppm",
                     min_v=0.0, max_v=20.0, step=0.1)
    await n.async_set_native_value(4.5)
    coord.async_log_reading.assert_called_once()
    reading = coord.async_log_reading.call_args[0][0]
    assert isinstance(reading, Reading)
    assert reading.total_bromine == 4.5
    assert reading.ph is None
    assert reading.total_alkalinity is None
    assert reading.calcium_hardness is None


def test_reading_number_min_max_step_propagate():
    coord = _coord(None)
    n = ReadingNumber(coord, entry_id="x", field="ph", name="pH", unit=None,
                     min_v=6.0, max_v=9.0, step=0.1)
    assert n.native_min_value == 6.0
    assert n.native_max_value == 9.0
    assert n.native_step == 0.1
    assert n.native_unit_of_measurement is None
