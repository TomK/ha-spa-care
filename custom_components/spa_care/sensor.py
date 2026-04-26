"""Sensor platform: last_test_age + recommended_action + next_retest_at.

Note: the four reading sensors (TB / pH / TA / CH) live in number.py
because they're user-editable via the device card.
"""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpaCareCoordinator
from .domain.models import ProductForm
from .domain.products import get_product
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
        LastTestAgeSensor(coord, entry_id=entry.entry_id),
        RecommendedActionSensor(coord, entry_id=entry.entry_id),
        NextRetestAtSensor(coord, entry_id=entry.entry_id),
        TubVolumeSensor(coord, entry_id=entry.entry_id),
    ])


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
        if recs[0].product_key == "__recheck__":
            return " · ".join(r.reason for r in recs)
        return " · ".join(_format_action(r) for r in recs)

    @property
    def extra_state_attributes(self):
        last = self.coordinator.last_reading
        if last is None:
            return {"actions": []}
        recs = evaluate_reading(last, self.coordinator.targets, self.coordinator.volume_l)
        if recs and recs[0].product_key == "__recheck__":
            return {"actions": [r.reason for r in recs]}
        return {"actions": [_format_action(r) for r in recs]}


class TubVolumeSensor(SpaCareEntity, SensorEntity):
    _attr_name = "Tub Volume"
    _attr_native_unit_of_measurement = "L"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="volume")

    @property
    def native_value(self) -> float:
        return self.coordinator.volume_l


def _format_action(rec) -> str:
    try:
        product = get_product(rec.product_key)
        unit = "ml" if product.form is ProductForm.LIQUID else "g"
        return f"Add {rec.amount:g}{unit} of {product.name}"
    except KeyError:
        return f"Add {rec.amount:g} of {rec.product_key}"


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
