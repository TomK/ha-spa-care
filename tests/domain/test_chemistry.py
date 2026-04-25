from custom_components.spa_care.domain.chemistry import (
    classify_reading,
    compute_dose,
)
from custom_components.spa_care.domain.models import ReadingState, TargetRange

TB = TargetRange(target_low=3.0, target_high=5.0, hard_min=0.0, hard_max=20.0)


def test_compute_dose_returns_zero_for_negative_or_zero_delta():
    assert compute_dose(delta=0, factor=3.0, volume_l=1500) == 0.0
    assert compute_dose(delta=-1, factor=3.0, volume_l=1500) == 0.0


def test_compute_dose_applies_factor_volume_and_75_percent_cap():
    # delta=1 ppm, factor=3 g/1000 L per ppm, volume=2000 L
    # raw = 1 * 3 * 2 = 6 g; cap = 6 * 0.75 = 4.5 g; rounded to 5 g
    assert compute_dose(delta=1.0, factor=3.0, volume_l=2000) == 5.0


def test_compute_dose_rounds_to_nearest_5():
    # raw = 4 * 3 * 1.5 = 18 g; cap = 13.5; rounds to 15
    assert compute_dose(delta=4.0, factor=3.0, volume_l=1500) == 15.0


def test_compute_dose_can_be_overridden_with_no_cap():
    # raw = 4 * 3 * 1.5 = 18 g; no cap; rounds to 20
    assert compute_dose(delta=4.0, factor=3.0, volume_l=1500, cap=1.0) == 20.0


def test_classify_reading_in_range():
    assert classify_reading(4.0, TB) is ReadingState.IN_RANGE


def test_classify_reading_below_target():
    assert classify_reading(2.0, TB) is ReadingState.BELOW


def test_classify_reading_above_target():
    assert classify_reading(6.0, TB) is ReadingState.ABOVE


def test_classify_reading_out_of_band_below_hard_min():
    assert classify_reading(-1.0, TB) is ReadingState.OUT_OF_BAND


def test_classify_reading_out_of_band_above_hard_max():
    assert classify_reading(25.0, TB) is ReadingState.OUT_OF_BAND
