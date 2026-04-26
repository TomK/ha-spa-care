"""Shared entity base."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SpaCareCoordinator


class SpaCareEntity(CoordinatorEntity[SpaCareCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SpaCareCoordinator, *, entry_id: str, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": coordinator.spa_name,
            "manufacturer": "spa_care",
        }
