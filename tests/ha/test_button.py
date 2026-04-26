from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from custom_components.spa_care.button import LogRecommendedDosesButton
from custom_components.spa_care.domain.models import Reading
from custom_components.spa_care.domain.recommendations import DEFAULT_TARGETS


def _coord(reading: Reading | None = None):
    coord = MagicMock()
    coord.last_reading = reading
    coord.targets = DEFAULT_TARGETS
    coord.volume_l = 1500.0
    coord.async_log_dose = AsyncMock()
    return coord


async def test_log_recommended_does_nothing_with_no_reading():
    coord = _coord(None)
    b = LogRecommendedDosesButton(coord, entry_id="x")
    await b.async_press()
    coord.async_log_dose.assert_not_called()


async def test_log_recommended_does_nothing_when_all_in_range():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=180,
    ))
    b = LogRecommendedDosesButton(coord, entry_id="x")
    await b.async_press()
    coord.async_log_dose.assert_not_called()


async def test_log_recommended_skips_recheck():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=99.0,  # out of band → only recheck rec
    ))
    b = LogRecommendedDosesButton(coord, entry_id="x")
    await b.async_press()
    coord.async_log_dose.assert_not_called()


async def test_log_recommended_logs_every_recommendation():
    # TB low + pH high → two recommendations
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=2.0, ph=7.9, total_alkalinity=100, calcium_hardness=180,
    ))
    b = LogRecommendedDosesButton(coord, entry_id="x")
    await b.async_press()
    assert coord.async_log_dose.call_count == 2
    products_logged = [
        call.kwargs["product_key"]
        for call in coord.async_log_dose.call_args_list
    ]
    assert "brominating_granules" in products_logged
    assert "dry_acid" in products_logged


async def test_log_recommended_passes_recommended_amount():
    coord = _coord(Reading(
        timestamp=datetime.now(timezone.utc),
        total_bromine=2.0, ph=7.4, total_alkalinity=100, calcium_hardness=180,
    ))
    b = LogRecommendedDosesButton(coord, entry_id="x")
    await b.async_press()
    coord.async_log_dose.assert_called_once()
    call = coord.async_log_dose.call_args
    assert call.kwargs["product_key"] == "brominating_granules"
    assert call.kwargs["amount"] > 0  # actual amount is 75% of computed, rounded
