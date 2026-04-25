from datetime import datetime, timezone

from custom_components.spa_care.domain.models import (
    Reading,
    TargetRange,
)
from custom_components.spa_care.domain.recommendations import (
    DEFAULT_TARGETS,
    evaluate_reading,
)

VOLUME_L = 1500.0


def _r(**kwargs) -> Reading:
    return Reading(timestamp=datetime.now(timezone.utc), **kwargs)


def test_all_in_range_returns_empty_list():
    r = _r(total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=180)
    assert evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L) == []


def test_low_tb_recommends_brominating_granules():
    r = _r(total_bromine=2.0, ph=7.4, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 1
    assert recs[0].product_key == "brominating_granules"
    assert recs[0].amount > 0


def test_high_ph_recommends_dry_acid():
    r = _r(total_bromine=4.0, ph=7.9, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert any(rec.product_key == "dry_acid" for rec in recs)


def test_low_ph_recommends_ph_up():
    r = _r(total_bromine=4.0, ph=7.0, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert any(rec.product_key == "ph_up" for rec in recs)


def test_multiple_out_of_range_returns_ranked_list_tb_first():
    r = _r(total_bromine=2.0, ph=7.9, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert recs[0].product_key == "brominating_granules"  # TB-low first
    assert recs[1].product_key == "dry_acid"              # then pH


def test_out_of_band_reading_returns_recheck_recommendation():
    r = _r(total_bromine=99.0, ph=7.4, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 1
    assert recs[0].product_key == "__recheck__"
    assert "tb" in recs[0].reason.lower()


def test_low_tb_above_hard_max_does_not_recommend_dose():
    # If user has somehow logged TB way above hard max, don't recommend dosing
    r = _r(total_bromine=99.0)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert all(rec.product_key == "__recheck__" for rec in recs)


def test_partial_data_only_evaluates_reported_readings():
    r = _r(total_bromine=2.0)  # nothing else logged
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 1
    assert recs[0].product_key == "brominating_granules"
