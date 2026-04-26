"""Number platform: editable TB / pH / TA / CH inputs on the device card.

Each number entity displays the latest reading for its field and, when
adjusted by the user, calls coordinator.async_log_reading with a partial
Reading containing only that field. The coordinator merges into the
existing last_reading so other fields are preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpaCareCoordinator
from .domain.models import Reading
from .entity import SpaCareEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord: SpaCareCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ReadingNumber(coord, entry_id=entry.entry_id, field="total_bromine",
                      name="Total Bromine", unit="ppm",
                      min_v=0.0, max_v=20.0, step=0.1),
        ReadingNumber(coord, entry_id=entry.entry_id, field="ph",
                      name="pH", unit=None,
                      min_v=6.0, max_v=9.0, step=0.1),
        ReadingNumber(coord, entry_id=entry.entry_id, field="total_alkalinity",
                      name="Total Alkalinity", unit="ppm",
                      min_v=0.0, max_v=300.0, step=10.0),
        ReadingNumber(coord, entry_id=entry.entry_id, field="calcium_hardness",
                      name="Calcium Hardness", unit="ppm",
                      min_v=0.0, max_v=1000.0, step=10.0),
    ])


class ReadingNumber(SpaCareEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, *, entry_id, field, name, unit, min_v, max_v, step):
        super().__init__(coordinator, entry_id=entry_id, suffix=field)
        self._field = field
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        if self.coordinator.last_reading is None:
            return None
        return getattr(self.coordinator.last_reading, self._field)

    async def async_set_native_value(self, value: float) -> None:
        partial = Reading(
            timestamp=datetime.now(timezone.utc),
            **{self._field: value},
        )
        await self.coordinator.async_log_reading(partial)
