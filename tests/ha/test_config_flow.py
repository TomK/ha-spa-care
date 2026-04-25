from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.spa_care.const import CONF_VOLUME_L, DOMAIN


async def test_user_flow_creates_entry(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    with patch(
        "custom_components.spa_care.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_VOLUME_L: 1500.0}
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_VOLUME_L] == 1500.0


async def test_user_flow_rejects_zero_volume(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_VOLUME_L: 0.0}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] is not None
