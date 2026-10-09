"""Guard NAF unit conversion, disclosure gaps and two-period cohort selection."""

from copy import deepcopy
from importlib import util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/analysis/japan_noi_naf.py"


def module():
    assert MODULE.exists(), "NAF parser and annual cohort are not implemented"
    spec = util.spec_from_file_location("japan_noi_naf", MODULE)
    loaded = util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def tables():
    return {
        "ご利用上の注意": {4: {"C": "2026年2月28日時点における保有物件"}},
        "基礎データ": {
            2: {"O": "取得価格合計（千円）", "R": "鑑定評価額（千円）"},
            3: {
                "B": "2",
                "C": "住宅",
                "D": "賃貸住宅",
                "E": "PAX",
                "F": "東京23区",
                "G": "東京都世田谷区",
                "H": "38287",
                "I": "38686",
                "K": "",
                "O": "1000000",
                "R": "2000000",
                "S": "3000",
                "T": "80",
            },
        },
        "物件収支（個別）": {
            3: {"G": "（単位：千円）"},
            28: {"D": "2", "E": "住宅"},
            29: {"E": "期別", "AR": "39", "AS": "40"},
            30: {"AR": "45900", "AS": "46081"},
            31: {"E": "運用日数（日）", "AR": "184", "AS": "181"},
            34: {"E": "賃貸事業収入小計　Ａ", "AR": "50000", "AS": "60000"},
            44: {"F": "減価償却費", "AR": "5000", "AS": "6000"},
            45: {"E": "賃貸事業費用小計　Ｂ", "AR": "20000", "AS": "22000"},
            47: {"E": "賃貸ＮＯＩ", "AR": "35000", "AS": "44000"},
        },
        "物件収支（集計）": {
            2: {"D": "（単位：千円）"},
            4: {"AO": "39", "AP": "40"},
            5: {"AO": "45900", "AP": "46081"},
            6: {"AO": "184", "AP": "181"},
            9: {"AO": "50000", "AP": "60000"},
            22: {"AO": "35000", "AP": "44000"},
        },
        "鑑定評価": {
            2: {"D": "39", "K": "40"},
            3: {"D": "45900", "K": "46081"},
            4: {"D": "鑑定評価額", "K": "鑑定評価額"},
            5: {"D": "百万円", "K": "百万円"},
            6: {"B": "住宅", "D": "1800", "K": "2000", "F": "3.5", "M": "3.4"},
        },
    }


def leases():
    return {39: {"2": "パス・スルー"}, 40: {"2": "パス・スルー"}}


def test_units_and_annual_observations_are_not_halfyear_times_two():
    naf = module()
    rows, quality = naf.parse_naf_tables(tables(), leases())
    annual, cohort = naf.annual_cohort(rows)
    assert rows[1]["noi_period_yen"] == 44_000_000
    assert rows[1]["opex_ex_dep_period_yen"] == 16_000_000
    assert rows[1]["acquisition_price_yen"] == 1_000_000_000
    assert rows[1]["appraisal_value_yen"] == 2_000_000_000
    assert annual[0]["noi_annual_yen"] == 79_000_000
    assert annual[0]["revenue_annual_yen"] == 110_000_000
    assert annual[0]["operating_expense_annual_yen"] == 31_000_000
    assert annual[0]["period_start"] == "2025-03-01"
    assert annual[0]["period_end"] == "2026-02-28"
    assert annual[0]["operating_days"] == 365
    assert cohort["included"] == 1
    assert quality["portfolio_reconciliation"]["40"]["noi"]["status"] == "within_rounding"


def test_partial_period_is_preserved_with_reason_and_not_annualized():
    naf = module()
    data = tables()
    data["物件収支（個別）"][31]["AR"] = "157"
    rows, _ = naf.parse_naf_tables(data, leases())
    annual, quality = naf.annual_cohort(rows)
    assert len(rows) == 2
    assert annual == []
    assert "partial_period" in quality["excluded"][0]["reasons"]


def test_lease_type_change_prevents_a_mixed_annual_cohort():
    naf = module()
    lease = leases()
    lease[39]["2"] = "賃料保証型"
    rows, _ = naf.parse_naf_tables(tables(), lease)
    annual, quality = naf.annual_cohort(rows)
    assert annual == []
    assert "lease_type_changed" in quality["excluded"][0]["reasons"]


def test_missing_latest_appraisal_is_an_explicit_schema_error():
    naf = module()
    data = tables()
    data["鑑定評価"][6]["K"] = "-"
    with pytest.raises(ValueError, match="appraisal"):
        naf.parse_naf_tables(data, leases())


def test_sold_property_is_in_reconciliation_but_not_latest_owned_output():
    naf = module()
    data = tables()
    for offset in [0, 1, 2, 3, 6, 16, 17, 19]:
        data["物件収支（個別）"][100 + offset] = deepcopy(data["物件収支（個別）"][28 + offset])
    data["物件収支（個別）"][100] = {"D": "57", "E": "売却物件"}
    data["物件収支（集計）"][9] = {"AO": "100000", "AP": "120000"}
    data["物件収支（集計）"][22] = {"AO": "70000", "AP": "88000"}
    rows, quality = naf.parse_naf_tables(data, leases())
    assert len(rows) == 2
    assert quality["sold_or_not_latest_owned_with_income"] == ["57"]
    assert quality["portfolio_reconciliation"]["40"]["noi"]["difference_yen"] == 0


def test_non_disclosed_revenue_is_null_and_residual_is_not_labeled_rounding():
    naf = module()
    data = tables()
    data["基礎データ"][3]["D"] = "ホスピタリティ施設"
    data["物件収支（個別）"][34]["AS"] = "非開示"
    rows, quality = naf.parse_naf_tables(data, leases())
    assert rows[1]["revenue_period_yen"] is None
    assert "revenue_period_yen" in rows[1]["missing_fields"]
    reconciliation = quality["portfolio_reconciliation"]["40"]["revenue"]
    assert reconciliation["status"] == "non_disclosed_residual"
    assert reconciliation["difference_yen"] == -60_000_000


def test_noi_identity_failure_stops_parser():
    naf = module()
    data = tables()
    data["物件収支（個別）"][47]["AS"] = "50000"
    with pytest.raises(ValueError, match="NOI reconciliation"):
        naf.parse_naf_tables(data, leases())


def test_property_id_and_lease_section_are_not_confused_with_decimal_area():
    naf = module()
    text = "１．住宅\n面積 3847.27㎡\nマスターリース種別 パス・スルー\n２．寮\n管理運営形態 オペレータへの一括賃貸方式"
    assert naf.parse_master_leases(text) == {"1": "パス・スルー"}


def test_ascii_heading_with_space_also_maps_master_lease_to_property():
    naf = module()
    text = "45. 住宅\n面積 3847.27㎡\nマスターリース種別 パス・スルー\n46. 寮\n管理運営形態 オペレータへの一括賃貸方式"
    assert naf.parse_master_leases(text) == {"45": "パス・スルー"}


def test_appraisal_forecast_uses_operating_noi_before_capital_expenditure():
    naf = module()
    text = (
        "（単位：千円）\n③ 運営純収益[①-②] 83,356\n(l)資本的支出 8,320\n④ 純収益[③+(k)-(l)] 75,108"
    )
    assert naf.appraisal_nois(text) == [83_356_000]


def test_appraisal_date_comes_from_the_matching_table_not_an_earlier_footnote():
    naf = module()
    text = "価格時点 2025 年 8 月 31 日\n鑑定評価書の概要\n価格時点 2025年11月１日\n③ 運営純収益[①-②] 70,891\n価格時点 2025年12月１日\n③ 運営純収益[①-②] 59,915"
    assert naf.appraisal_forecasts(text) == [
        {"noi_forecast_annual_yen": 70_891_000, "appraisal_date": "2025-11-01"},
        {"noi_forecast_annual_yen": 59_915_000, "appraisal_date": "2025-12-01"},
    ]


def test_transfer_completion_date_requires_explicit_completion_evidence():
    naf = module()
    text = "2026 年４月９日\nパークアクシス西馬込\n本日、資産の取得及び譲渡を完了しました。"
    assert naf.completion_date(text, "パークアクシス西馬込") == "2026-04-09"
    assert (
        naf.completion_date(text.replace("完了しました", "決定しました"), "パークアクシス西馬込")
        is None
    )


def test_non_disclosed_days_are_missing_evidence_not_a_known_partial_period():
    naf = module()
    data = tables()
    data["物件収支（個別）"][31]["AS"] = "非開示"
    rows, _ = naf.parse_naf_tables(data, leases())
    annual, quality = naf.annual_cohort(rows)
    assert annual == []
    assert "missing_operating_days" in quality["excluded"][0]["reasons"]
    assert "partial_period" not in quality["excluded"][0]["reasons"]


def test_portfolio_capex_is_retained_without_assigning_it_to_every_property():
    naf = module()
    assert naf.portfolio_capex("当期の資本的支出は1,054百万円であり") == 1_054_000_000
    assert naf.portfolio_capex("物件別の資本的支出は非開示") is None
