"""Button platform: one-tap shortcut for logging the recommended doses."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpaCareCoordinator
from .domain.recommendations import evaluate_reading
from .entity import SpaCareEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord: SpaCareCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LogRecommendedDosesButton(coord, entry_id=entry.entry_id),
    ])


class LogRecommendedDosesButton(SpaCareEntity, ButtonEntity):
    _attr_name = "Log Recommended Doses"

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="log_recommended_doses")

    async def async_press(self) -> None:
        last = self.coordinator.last_reading
        if last is None:
            _LOGGER.debug("Log recommended doses pressed with no reading; ignoring")
            return
        recs = evaluate_reading(last, self.coordinator.targets, self.coordinator.volume_l)
        logged = 0
        for rec in recs:
            if rec.product_key == "__recheck__":
                continue
            if rec.amount <= 0:
                continue
            await self.coordinator.async_log_dose(
                product_key=rec.product_key,
                amount=rec.amount,
            )
            logged += 1
        _LOGGER.info("Logged %d recommended dose(s)", logged)
