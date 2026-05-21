"""ExtractedProperty → Assumptions マッパーのテスト (LLM 不要)。"""

from __future__ import annotations

import pytest
from api.services.extractors.property_brochure import PropertyBrochureExtraction
from api.services.extractors.to_assumptions import to_assumptions
from re_engine.analyze import run_full_analysis


def _full_brochure() -> PropertyBrochureExtraction:
    return PropertyBrochureExtraction(
        property_name="西新宿レジデンス",
        address="東京都新宿区西新宿1-2-3",
        asking_price_yen=39_800_000,
        nearest_station="新宿駅",
        station_walk_min=9,
        exclusive_area_sqm=38.4,
        structure="rc",
        floor_plan="1LDK",
        build_year_month="2011-04",
        gross_yield_pct=4.37,
        estimated_full_rent_monthly_yen=145_000,
        management_fee_monthly_yen=12_000,
        repair_reserve_monthly_yen=8_000,
    )


def test_full_brochure_maps_to_runnable_assumptions():
    b = _full_brochure()
    r = to_assumptions(b, acquisition_year=2026)
    assert r.assumptions.property.purchase_price_yen == 39_800_000
    assert r.assumptions.property.structure == "rc"
    assert r.assumptions.property.building_completion_ym == "2011-04"
    assert r.assumptions.income.gpi_monthly_yen == 145_000
    # full brochure なら必須は揃っているはず
    assert "structure" not in r.needs_confirmation
    assert "build_year_month" not in r.needs_confirmation
    # 計算が回ることまで確認
    out = run_full_analysis(r.assumptions)
    assert out.kpi.cap_rate > 0


def test_missing_fields_filled_with_defaults():
    b = PropertyBrochureExtraction(
        asking_price_yen=30_000_000,
        # structure 未指定 / 築年月 未指定 / 面積 未指定 / 賃料 未指定
    )
    r = to_assumptions(b, acquisition_year=2026)
    assert "structure" in r.needs_confirmation
    assert "build_year_month" in r.needs_confirmation
    assert "building_area_sqm" in r.needs_confirmation
    assert "gpi_monthly_yen" in r.needs_confirmation
    # それでも Assumptions は組み立てられて計算可能
    out = run_full_analysis(r.assumptions)
    assert out.kpi.cap_rate > 0


def test_price_missing_raises():
    with pytest.raises(ValueError):
        to_assumptions(PropertyBrochureExtraction(), acquisition_year=2026)


def test_yield_only_derives_rent():
    b = PropertyBrochureExtraction(
        asking_price_yen=30_000_000,
        structure="rc",
        build_year_month="2010-01",
        exclusive_area_sqm=25.0,
        gross_yield_pct=6.0,
    )
    r = to_assumptions(b, acquisition_year=2026)
    # 6% * 3000万 / 12 = 150,000
    assert r.assumptions.income.gpi_monthly_yen == 150_000


def test_pref_inferred_from_address():
    b = PropertyBrochureExtraction(
        asking_price_yen=30_000_000,
        structure="rc",
        build_year_month="2010-01",
        exclusive_area_sqm=25.0,
        gross_yield_pct=6.0,
        address="大阪府大阪市北区梅田1-1-1",
    )
    r = to_assumptions(b, acquisition_year=2026)
    assert r.assumptions.property.location_pref == "27"
