import pytest

from custom_components.spa_care.domain.models import (
    ProductForm,
    ProductMode,
)
from custom_components.spa_care.domain.products import (
    DEFAULT_PRODUCTS,
    get_product,
    products_for_reading,
    scheduled_products,
)


def test_default_registry_contains_brominating_granules():
    p = get_product("brominating_granules")
    assert p.form is ProductForm.SOLID
    assert p.mode is ProductMode.READING_DRIVEN
    assert p.target_reading == "tb"
    assert p.direction == "raise"
    assert p.factor == 3.0  # 3 g/1000 L per 1 ppm


def test_default_registry_contains_spa_no_scale_as_scheduled_liquid():
    p = get_product("spa_no_scale")
    assert p.form is ProductForm.LIQUID
    assert p.mode is ProductMode.SCHEDULE_DRIVEN
    assert p.cadence_days == 7
    assert p.typical_dose_per_1000L == 40.0


def test_get_product_unknown_raises():
    with pytest.raises(KeyError):
        get_product("unobtanium")


def test_products_for_reading_returns_only_matching_direction():
    raisers = products_for_reading("ph", direction="raise")
    lowerers = products_for_reading("ph", direction="lower")
    assert all(p.target_reading == "ph" for p in raisers + lowerers)
    assert all(p.direction == "raise" for p in raisers)
    assert all(p.direction == "lower" for p in lowerers)
    assert raisers and lowerers  # both populated


def test_scheduled_products_returns_only_schedule_driven():
    sched = scheduled_products()
    assert all(p.mode is ProductMode.SCHEDULE_DRIVEN for p in sched)
    assert any(p.key == "spa_no_scale" for p in sched)
    assert any(p.key == "mps_shock" for p in sched)


def test_default_registry_has_at_least_eight_products():
    assert len(DEFAULT_PRODUCTS) >= 8
