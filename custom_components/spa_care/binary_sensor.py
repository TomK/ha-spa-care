"""Binary sensor platform: test_overdue, *_out_of_range, retest_due."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpaCareCoordinator
from .domain.chemistry import classify_reading
from .domain.models import ReadingState
from .domain.products import get_product
from .domain.rules import RETEST_DELAY, RETEST_WINDOW, TEST_OVERDUE_DAYS
from .entity import SpaCareEntity

_READING_FIELDS = {
    "tb": "total_bromine",
    "ph": "ph",
    "ta": "total_alkalinity",
    "ch": "calcium_hardness",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord: SpaCareCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        TestOverdueBinarySensor(coord, entry_id=entry.entry_id),
        OutOfRangeBinarySensor(coord, entry_id=entry.entry_id, reading_key="tb",
                               name="TB Out of Range"),
        OutOfRangeBinarySensor(coord, entry_id=entry.entry_id, reading_key="ph",
                               name="pH Out of Range"),
        OutOfRangeBinarySensor(coord, entry_id=entry.entry_id, reading_key="ta",
                               name="TA Out of Range"),
        OutOfRangeBinarySensor(coord, entry_id=entry.entry_id, reading_key="ch",
                               name="CH Out of Range"),
        PostDoseRetestBinarySensor(coord, entry_id=entry.entry_id),
    ])


class TestOverdueBinarySensor(SpaCareEntity, BinarySensorEntity):
    __test__ = False  # not a pytest test class
    _attr_name = "Test Overdue"

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="test_overdue")

    @property
    def is_on(self) -> bool:
        last = self.coordinator.last_reading
        if last is None:
            return True
        age = datetime.now(timezone.utc) - last.timestamp
        return age > timedelta(days=TEST_OVERDUE_DAYS)


class OutOfRangeBinarySensor(SpaCareEntity, BinarySensorEntity):
    def __init__(self, coordinator, *, entry_id, reading_key, name):
        super().__init__(coordinator, entry_id=entry_id, suffix=f"{reading_key}_out_of_range")
        self._reading_key = reading_key
        self._attr_name = name

    @property
    def is_on(self) -> bool:
        last = self.coordinator.last_reading
        if last is None:
            return False
        value = getattr(last, _READING_FIELDS[self._reading_key])
        if value is None:
            return False
        target = self.coordinator.targets[self._reading_key]
        return classify_reading(value, target) is not ReadingState.IN_RANGE


class PostDoseRetestBinarySensor(SpaCareEntity, BinarySensorEntity):
    _attr_name = "Retest Due"

    def __init__(self, coordinator, *, entry_id):
        super().__init__(coordinator, entry_id=entry_id, suffix="retest_due")

    @property
    def is_on(self) -> bool:
        # Find last reading-driven dose
        last_dose = None
        for d in reversed(self.coordinator.doses):
            try:
                product = get_product(d.product_key)
            except KeyError:
                continue
            if product.target_reading is not None and product.direction is not None:
                last_dose = d
                break
        if last_dose is None:
            return False
        # If there's been a reading after the dose, retest is no longer due.
        if (
            self.coordinator.last_reading is not None
            and self.coordinator.last_reading.timestamp > last_dose.timestamp
        ):
            return False
        age = datetime.now(timezone.utc) - last_dose.timestamp
        return RETEST_DELAY <= age <= RETEST_WINDOW
