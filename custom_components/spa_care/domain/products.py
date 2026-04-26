"""Default product registry. Tunable — every factor cites a starting source."""

from __future__ import annotations

from .models import Product, ProductForm, ProductMode

# Reading-driven products. Factors are conservative ballparks from common
# UK product literature (Aquasparkle, Clearwater, Spa Pure). Tune as
# observed dose-vs-response data accumulates.
DEFAULT_PRODUCTS: tuple[Product, ...] = (
    Product(
        key="brominating_granules",
        name="Brominating granules (~60% BCDMH)",
        form=ProductForm.SOLID,
        mode=ProductMode.READING_DRIVEN,
        target_reading="tb",
        direction="raise",
        factor=3.0,  # g/1000 L per 1 ppm TB
    ),
    Product(
        key="dry_acid",
        name="Dry acid (sodium bisulphate)",
        form=ProductForm.SOLID,
        mode=ProductMode.READING_DRIVEN,
        target_reading="ph",
        direction="lower",
        factor=12.0,  # g/1000 L per 0.2 pH
    ),
    Product(
        key="ph_up",
        name="pH up (sodium carbonate)",
        form=ProductForm.SOLID,
        mode=ProductMode.READING_DRIVEN,
        target_reading="ph",
        direction="raise",
        factor=15.0,  # g/1000 L per 0.2 pH
    ),
    Product(
        key="ta_up",
        name="TA increaser (sodium bicarbonate)",
        form=ProductForm.SOLID,
        mode=ProductMode.READING_DRIVEN,
        target_reading="ta",
        direction="raise",
        factor=17.0,  # g/1000 L per 10 ppm TA
    ),
    Product(
        key="ch_up",
        name="Calcium hardness increaser (calcium chloride)",
        form=ProductForm.SOLID,
        mode=ProductMode.READING_DRIVEN,
        target_reading="ch",
        direction="raise",
        factor=14.0,  # g/1000 L per 10 ppm CH
    ),
    # Schedule-driven products. Cadences and typical doses from product
    # instructions; user-tunable via options flow.
    Product(
        key="spa_no_scale",
        name="Spa No Scale (sequestrant)",
        form=ProductForm.LIQUID,
        mode=ProductMode.SCHEDULE_DRIVEN,
        cadence_days=7,
        typical_dose_per_1000L=40.0,  # ml/1000 L weekly
    ),
    Product(
        key="mps_shock",
        name="Non-chlorine shock (MPS)",
        form=ProductForm.SOLID,
        mode=ProductMode.SCHEDULE_DRIVEN,
        cadence_days=7,
        typical_dose_per_1000L=10.0,  # g/1000 L weekly baseline
    ),
    # Maintenance-only products — scheduled but not dosed into the water.
    # Filter cleaner soaks the cartridge in a separate bowl; surface cleaner
    # wipes the waterline. Logged via spa_care.log_maintenance, no amount.
    Product(
        key="filter_cleaner",
        name="Filter cartridge cleaner",
        form=ProductForm.LIQUID,
        mode=ProductMode.MAINTENANCE,
        cadence_days=30,
    ),
    Product(
        key="surface_cleaner",
        name="Surface cleaner",
        form=ProductForm.LIQUID,
        mode=ProductMode.MAINTENANCE,
        cadence_days=7,
    ),
    # Manual-only products (no recommendation, no nudge — logged for history).
    Product(
        key="defoamer",
        name="Defoamer",
        form=ProductForm.LIQUID,
        mode=ProductMode.MANUAL,
        typical_dose_per_1000L=10.0,  # ml; reactive dose when foam appears
    ),
    Product(
        key="clarifier",
        name="Clarifier",
        form=ProductForm.LIQUID,
        mode=ProductMode.MANUAL,
        typical_dose_per_1000L=30.0,  # ml; reactive dose for hazy water
    ),
    Product(
        key="sodium_bromide",
        name="Sodium bromide reserve",
        form=ProductForm.SOLID,
        mode=ProductMode.MANUAL,
        typical_dose_per_1000L=30.0,  # g; at refill or after heavy shock
    ),
    Product(
        key="bromine_tablets",
        name="Bromine tablets (BCDMH 20 g floater)",
        form=ProductForm.SOLID,
        mode=ProductMode.MANUAL,
    ),
)

_BY_KEY: dict[str, Product] = {p.key: p for p in DEFAULT_PRODUCTS}


def get_product(key: str) -> Product:
    return _BY_KEY[key]


def products_for_reading(reading: str, *, direction: str | None = None) -> list[Product]:
    matches = [p for p in DEFAULT_PRODUCTS if p.target_reading == reading]
    if direction is not None:
        matches = [p for p in matches if p.direction == direction]
    return matches


def scheduled_products() -> list[Product]:
    return [p for p in DEFAULT_PRODUCTS if p.mode is ProductMode.SCHEDULE_DRIVEN]


def maintenance_products() -> list[Product]:
    return [p for p in DEFAULT_PRODUCTS if p.mode is ProductMode.MAINTENANCE]
