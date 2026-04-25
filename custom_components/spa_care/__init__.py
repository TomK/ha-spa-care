"""Spa Care integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_VOLUME_L, DOMAIN, HOURLY_TICK_SECONDS, PLATFORMS
from .coordinator import SpaCareCoordinator
from .services import async_register_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coord = SpaCareCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        volume_l=entry.data[CONF_VOLUME_L],
        targets=None,
    )
    await coord.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    await async_register_services(hass, coord)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            lambda _now: hass.async_create_task(coord.async_hourly_tick()),
            interval=timedelta(seconds=HOURLY_TICK_SECONDS),
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "log_reading")
            hass.services.async_remove(DOMAIN, "log_dose")
    return unloaded
