"""Sensor platform: TB / pH / TA / CH + last_test_age + recommended_action."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.sensor import SensorDeviceClass

from .const import DOMAIN
from .coordinator import SpaCareCoordinator
from .domain.recommendations import evaluate_reading
from .domain.rules import RETEST_DELAY, RETEST_WINDOW, last_reading_driven_dose
from .entity import SpaCareEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord: SpaCareCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ReadingSensor(coord, entry_id=entry.entry_id, field="total_bromine",
                      name="Total Bromine", unit="ppm"),
        ReadingSensor(coord, entry_id=entry.entry_id, field="ph",
                      name="pH", unit=None),
        ReadingSensor(coord, entry_id=entry.entry_id, field="total_alkalinity",
                      name="Total Alkalinity", unit="ppm"),
        ReadingSensor(coord, entry_id=entry.entry_id, field="calcium_hardness",
                      name="Calcium Hardness", unit="ppm"),
        LastTestAgeSensor(coord, entry_id=entry.entry_id),
        RecommendedActionSensor(coord, entry_id=entry.entry_id),
        NextRetestAtSensor(coord, entry_id=entry.entry_id),
    ])


class ReadingSensor(SpaCareEntity, SensorEntity):
    def __init__(self, coordinator, *, entry_id, field, name, unit):
        super().__init__(coordinator, entry_id=entry_id, suffix=field)
        self._field = field
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        if self.coordinator.last_reading is None:
            return None
        return getattr(self.coordinator.last_reading, self._field)


class LastTestAgeSensor(SpaCareEntity, SensorEntity):
    _attr_name = "Last Test Age"
    _attr_native_unit_of_measurement = "min"

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="last_test_age")

    @property
    def native_value(self):
        last = self.coordinator.last_reading
        if last is None:
            return None
        delta = datetime.now(timezone.utc) - last.timestamp
        return int(delta.total_seconds() // 60)


class RecommendedActionSensor(SpaCareEntity, SensorEntity):
    _attr_name = "Recommended Action"

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="recommended_action")

    @property
    def native_value(self) -> str:
        last = self.coordinator.last_reading
        if last is None:
            return "No reading yet"
        recs = evaluate_reading(last, self.coordinator.targets, self.coordinator.volume_l)
        if not recs:
            return "None — looking good"
        top = recs[0]
        if top.product_key == "__recheck__":
            return top.reason
        return f"Add {top.amount:g} of {top.product_key} — {top.reason}"

    @property
    def extra_state_attributes(self):
        last = self.coordinator.last_reading
        if last is None:
            return {"all_recommendations": []}
        recs = evaluate_reading(last, self.coordinator.targets, self.coordinator.volume_l)
        return {
            "all_recommendations": [
                {"product": r.product_key, "amount": r.amount, "reason": r.reason}
                for r in recs
            ]
        }


class NextRetestAtSensor(SpaCareEntity, SensorEntity):
    _attr_name = "Next Retest At"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="next_retest_at")

    @property
    def native_value(self) -> datetime | None:
        last_dose = last_reading_driven_dose(tuple(self.coordinator.doses))
        if last_dose is None:
            return None
        if (
            self.coordinator.last_reading is not None
            and self.coordinator.last_reading.timestamp > last_dose.timestamp
        ):
            return None
        if datetime.now(timezone.utc) - last_dose.timestamp > RETEST_WINDOW:
            return None
        return last_dose.timestamp + RETEST_DELAY
