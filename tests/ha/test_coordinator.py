import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spa_care.coordinator import SpaCareCoordinator
from custom_components.spa_care.domain.models import Reading


NOW = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def coordinator():
    hass = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.async_create_task = lambda coro: asyncio.ensure_future(coro)
    store = AsyncMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    coord = SpaCareCoordinator(
        hass=hass,
        entry_id="abc",
        volume_l=1500.0,
        targets=None,
        store=store,
    )
    return coord


async def test_log_reading_persists_and_runs_rules(coordinator):
    await coordinator.async_initialize()
    await coordinator.async_log_reading(
        Reading(timestamp=NOW, total_bromine=2.0, ph=7.4),
    )
    assert coordinator.last_reading is not None
    assert coordinator.last_reading.total_bromine == 2.0
    coordinator._store.async_save.assert_called()
    coordinator.hass.bus.async_fire.assert_called()


async def test_log_dose_appends_and_persists(coordinator):
    await coordinator.async_initialize()
    await coordinator.async_log_dose(
        product_key="brominating_granules",
        amount=10.0,
        when=NOW,
    )
    assert len(coordinator.doses) == 1
    coordinator._store.async_save.assert_called()


async def test_suppression_persists_after_nudge_fired(coordinator):
    await coordinator.async_initialize()
    await coordinator.async_log_reading(
        Reading(timestamp=NOW, total_bromine=2.0),
    )
    # Same reading should not re-fire the same out_of_range:tb nudge
    coordinator.hass.bus.async_fire.reset_mock()
    await coordinator.async_log_reading(
        Reading(timestamp=NOW + timedelta(minutes=10), total_bromine=2.1),
    )
    fired_categories = [
        call.args[0]
        for call in coordinator.hass.bus.async_fire.call_args_list
    ]
    assert "spa_care.nudge" not in fired_categories or all(
        call.args[1].get("subject") != "tb"
        for call in coordinator.hass.bus.async_fire.call_args_list
    )


async def test_log_reading_merges_partial_with_existing(coordinator):
    await coordinator.async_initialize()
    await coordinator.async_log_reading(
        Reading(timestamp=NOW, total_bromine=4.0, ph=7.4,
                total_alkalinity=100, calcium_hardness=180),
    )
    # Partial update — only TB
    await coordinator.async_log_reading(
        Reading(timestamp=NOW + timedelta(minutes=5), total_bromine=4.5),
    )
    last = coordinator.last_reading
    assert last.total_bromine == 4.5
    assert last.ph == 7.4
    assert last.total_alkalinity == 100
    assert last.calcium_hardness == 180
    assert last.timestamp == NOW + timedelta(minutes=5)


async def test_log_reading_first_partial_stored_as_is(coordinator):
    await coordinator.async_initialize()
    await coordinator.async_log_reading(
        Reading(timestamp=NOW, total_bromine=4.5),
    )
    last = coordinator.last_reading
    assert last.total_bromine == 4.5
    assert last.ph is None
