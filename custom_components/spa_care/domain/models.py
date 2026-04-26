"""Pure domain models. No HA imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ReadingState(Enum):
    IN_RANGE = "in_range"
    BELOW = "below"
    ABOVE = "above"
    OUT_OF_BAND = "out_of_band"


class ProductForm(Enum):
    SOLID = "solid"
    LIQUID = "liquid"


class ProductMode(Enum):
    READING_DRIVEN = "reading_driven"
    SCHEDULE_DRIVEN = "schedule_driven"
    MAINTENANCE = "maintenance"  # scheduled, no amount (filter clean, surface wipe)
    MANUAL = "manual"


@dataclass(frozen=True)
class TargetRange:
    target_low: float
    target_high: float
    hard_min: float
    hard_max: float

    @property
    def midpoint(self) -> float:
        return (self.target_low + self.target_high) / 2


@dataclass(frozen=True)
class Product:
    key: str
    name: str
    form: ProductForm
    mode: ProductMode
    target_reading: str | None = None      # "tb" / "ph" / "ta" / "ch"
    direction: str | None = None           # "raise" / "lower"
    factor: float | None = None            # units per delta per 1000 L
    cadence_days: int | None = None        # schedule-driven cadence
    typical_dose_per_1000L: float | None = None


@dataclass
class Reading:
    timestamp: datetime
    total_bromine: float | None = None
    ph: float | None = None
    total_alkalinity: float | None = None
    calcium_hardness: float | None = None


@dataclass
class Dose:
    timestamp: datetime
    product_key: str
    amount: float


@dataclass
class MaintenanceAction:
    """Logged maintenance event (e.g. filter cleaned, waterline wiped).

    No amount — the only piece of data that matters is "this happened at
    this timestamp", which clears the schedule_due nudge for the product.
    """
    timestamp: datetime
    product_key: str


@dataclass
class Recommendation:
    product_key: str
    amount: float
    reason: str
    priority: int


@dataclass
class Action:
    kind: str  # "set_entity" | "fire_event" | "create_notification"
    payload: dict[str, Any]
