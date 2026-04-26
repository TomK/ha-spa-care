"""HA service registration."""

from __future__ import annotations

from datetime import datetime, timezone

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .domain.models import Reading

LOG_READING_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional("total_bromine"): vol.Coerce(float),
            vol.Optional("ph"): vol.Coerce(float),
            vol.Optional("total_alkalinity"): vol.Coerce(float),
            vol.Optional("calcium_hardness"): vol.Coerce(float),
        },
        # at least one reading must be present
        lambda d: d if d else (_ for _ in ()).throw(vol.Invalid("at least one reading required")),
    )
)

LOG_DOSE_SCHEMA = vol.Schema(
    {
        vol.Required("product"): str,
        vol.Required("amount"): vol.Coerce(float),
    }
)

LOG_MAINTENANCE_SCHEMA = vol.Schema(
    {
        vol.Required("product"): str,
    }
)


async def async_register_services(hass: HomeAssistant, coordinator) -> None:
    async def _log_reading(call: ServiceCall) -> None:
        reading = Reading(
            timestamp=datetime.now(timezone.utc),
            total_bromine=call.data.get("total_bromine"),
            ph=call.data.get("ph"),
            total_alkalinity=call.data.get("total_alkalinity"),
            calcium_hardness=call.data.get("calcium_hardness"),
        )
        await coordinator.async_log_reading(reading)

    async def _log_dose(call: ServiceCall) -> None:
        await coordinator.async_log_dose(
            product_key=call.data["product"],
            amount=call.data["amount"],
        )

    async def _log_maintenance(call: ServiceCall) -> None:
        await coordinator.async_log_maintenance(
            product_key=call.data["product"],
        )

    hass.services.async_register(DOMAIN, "log_reading", _log_reading, schema=LOG_READING_SCHEMA)
    hass.services.async_register(DOMAIN, "log_dose", _log_dose, schema=LOG_DOSE_SCHEMA)
    hass.services.async_register(DOMAIN, "log_maintenance", _log_maintenance, schema=LOG_MAINTENANCE_SCHEMA)
