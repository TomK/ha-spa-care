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


def test_out_of_band_reading_still_emits_advice_with_strip_hint():
    # TB way above hard_max: advice still fires (stop dosing, decay) and
    # the reason carries a "double-check the strip" hint.
    r = _r(total_bromine=99.0, ph=7.4, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 1
    assert recs[0].product_key == "__advice__"
    assert "double-check" in recs[0].reason.lower()


def test_out_of_band_reading_does_not_recommend_a_dose():
    # No tb-lower product exists, so OOB never produces a dose action.
    r = _r(total_bromine=99.0)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert all(rec.amount == 0 for rec in recs)


def test_out_of_band_high_ph_recommends_dry_acid_with_strip_hint():
    # pH way above hard_max=9.0 still gets the standard pH-down treatment
    # — out-of-band shouldn't suppress an actionable dose.
    r = _r(ph=10.0)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    rec = next(r for r in recs if r.product_key == "dry_acid")
    assert rec.amount > 0
    assert "double-check" in rec.reason.lower()


def test_partial_data_only_evaluates_reported_readings():
    r = _r(total_bromine=2.0)  # nothing else logged
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 1
    assert recs[0].product_key == "brominating_granules"


def test_high_ta_returns_advice_recommendation():
    r = _r(total_bromine=4.0, ph=7.4, total_alkalinity=180, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    advice = [rec for rec in recs if rec.product_key == "__advice__"]
    assert len(advice) == 1
    assert "TA" in advice[0].reason
    assert "ph down" in advice[0].reason.lower() or "aerate" in advice[0].reason.lower()


def test_high_ch_produces_no_recommendation():
    # High CH has no practical fix in hard-water areas, so we deliberately
    # stay quiet rather than recommending an unhelpful water change.
    r = _r(total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=800)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert recs == []


def test_low_ch_still_recommends_ch_up():
    # Low CH does have a fix and should still alert.
    r = _r(total_bromine=4.0, ph=7.4, total_alkalinity=100, calcium_hardness=50)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert any(rec.product_key == "ch_up" for rec in recs)


def test_high_tb_returns_advice_recommendation():
    r = _r(total_bromine=8.0, ph=7.4, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    advice = [rec for rec in recs if rec.product_key == "__advice__"]
    assert len(advice) == 1
    assert "decay" in advice[0].reason.lower() or "tablets" in advice[0].reason.lower()


def test_advice_mixes_with_dose_recommendations():
    # TB low (dose) + TA high (advice) — both appear, in priority order.
    r = _r(total_bromine=2.0, ph=7.4, total_alkalinity=180, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 2
    assert recs[0].product_key == "brominating_granules"  # TB priority 1
    assert recs[1].product_key == "__advice__"            # TA priority 3


def test_out_of_band_reading_does_not_suppress_other_recommendations():
    # TB out-of-band (35 > hard_max=30) still produces advice; an in-band
    # high pH still produces its dose recommendation alongside.
    r = _r(total_bromine=35.0, ph=7.9, total_alkalinity=100, calcium_hardness=180)
    recs = evaluate_reading(r, DEFAULT_TARGETS, VOLUME_L)
    assert len(recs) == 2
    # TB priority 1 → first; pH priority 2 → second
    assert recs[0].product_key == "__advice__"
    assert "double-check" in recs[0].reason.lower()
    assert recs[1].product_key == "dry_acid"
    assert "double-check" not in recs[1].reason.lower()  # in-band, no hint
