from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

from custom_components.spa_care.const import DOMAIN
from custom_components.spa_care.services import (
    LOG_DOSE_SCHEMA,
    LOG_READING_SCHEMA,
    async_register_services,
)


def test_log_reading_schema_accepts_partial_data():
    LOG_READING_SCHEMA({"total_bromine": 4.2})
    LOG_READING_SCHEMA({"ph": 7.4, "total_alkalinity": 100})


def test_log_reading_schema_rejects_no_data():
    with pytest.raises(vol.Invalid):
        LOG_READING_SCHEMA({})


def test_log_dose_schema_requires_product_and_amount():
    LOG_DOSE_SCHEMA({"product": "brominating_granules", "amount": 10.0})
    with pytest.raises(vol.Invalid):
        LOG_DOSE_SCHEMA({"product": "x"})  # no amount


async def test_async_register_services_registers_two_services():
    hass = MagicMock()
    hass.services.async_register = MagicMock()
    coord = MagicMock()
    coord.async_log_reading = AsyncMock()
    coord.async_log_dose = AsyncMock()
    await async_register_services(hass, coord)
    names = [call.args[1] for call in hass.services.async_register.call_args_list]
    assert "log_reading" in names
    assert "log_dose" in names
