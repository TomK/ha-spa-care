"""Spa Care integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_NAME, CONF_VOLUME_L, DOMAIN, HOURLY_TICK_SECONDS, PLATFORMS
from .coordinator import SpaCareCoordinator
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "spa-care-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"
_CARD_REGISTERED_FLAG = "_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and auto-load it on every dashboard.

    Idempotent across config-entry reloads. Only the first call actually
    registers the static path + extra JS URL; subsequent calls short-circuit.
    """
    if hass.data.get(DOMAIN, {}).get(_CARD_REGISTERED_FLAG):
        return
    card_path = Path(__file__).parent / CARD_FILENAME
    if not card_path.exists():
        _LOGGER.warning("spa_care: bundled card %s not found; skipping", card_path)
        return
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), False)]
        )
        add_extra_js_url(hass, CARD_URL)
        hass.data.setdefault(DOMAIN, {})[_CARD_REGISTERED_FLAG] = True
        _LOGGER.info("spa_care: registered card at %s", CARD_URL)
    except Exception:
        _LOGGER.exception("spa_care: failed to register frontend card")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coord = SpaCareCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        name=entry.data.get(CONF_NAME, "Spa"),
        volume_l=entry.data[CONF_VOLUME_L],
        targets=None,
    )
    await coord.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    await async_register_services(hass, coord)
    await _async_register_card(hass)
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
        # Keep the registered card-flag entry in hass.data so the static
        # path + extra JS URL aren't re-registered on the next setup
        # (HA doesn't expose a clean way to unregister either).
        if not [k for k in hass.data[DOMAIN] if not k.startswith("_")]:
            hass.services.async_remove(DOMAIN, "log_reading")
            hass.services.async_remove(DOMAIN, "log_dose")
            hass.services.async_remove(DOMAIN, "log_maintenance")
    return unloaded
