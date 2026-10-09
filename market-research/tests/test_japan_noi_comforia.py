"""Verify Comforia disclosure units, withheld NOI, and stable annual cohorts."""

import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/analysis"))
import japan_noi_comforia as cfr


def test_completed_acquisitions_require_actual_disclosure():
    text = """本投資法人は以下の物件を取得しました。
コンフォリア経堂（注2） 信託不動産 東京都世田谷区 1,500百万円 共同住宅 2026年８月３日
物件の譲渡
コンフォリア予定 不動産 東京都 1,000百万円 共同住宅 2027年２月１日"""
    assert cfr.completed_acquisition_dates(text) == {"コンフォリア経堂": "2026-08-03"}


def tables():
    return {
        "物件概要": {
            2: {"M": "取得価格\n（千円）", "O": "期末算定価額\n（千円）"},
            5: {
                "B": "1",
                "C": "コンフォリア日本橋人形町",
                "E": "東京都中央区",
                "F": "40421",
                "M": "1500000",
                "O": "3000000",
            },
        },
        "鑑定情報": {
            5: {"K": "（百万円）"},
            7: {"B": "1", "C": "コンフォリア日本橋人形町", "K": "3000"},
        },
        "収支状況": {
            2: {"B": "番号", "E": "1"},
            3: {"E": "コンフォリア\n日本橋人形町"},
            4: {"E": "181"},
            5: {"E": "64000"},
            6: {"E": "2000"},
            8: {"E": "66000"},
            18: {"E": "11000"},
            20: {"E": "23000"},
            24: {"B": "（Ａ）‐（Ｃ）+（Ｂ）", "E": "54000"},
            28: {"E": "金額は千円単位"},
        },
    }


def test_thousand_yen_and_million_yen_preserve_reported_subtotals():
    rows, quality = cfr.parse_tables(tables(), "2026-02-01", "2026-07-31")
    row = rows[0]
    assert row["noi_period_yen"] == 54_000_000
    assert row["operating_expense_ex_dep"] == 12_000_000
    assert row["acquisition_price_yen"] == 1_500_000_000
    assert row["appraisal_value_yen"] == 3_000_000_000
    assert row["appraisal_date"] == "2026-07-31"
    assert row["masterlease"] is None
    assert quality["owned"] == 1


@pytest.mark.parametrize("hidden", ["（注）", "-"])
def test_hidden_noi_is_missing_and_never_zero_filled(hidden):
    data = tables()
    for key in (5, 6, 8, 24):
        data["収支状況"][key]["E"] = hidden
    rows, quality = cfr.parse_tables(data, "2026-02-01", "2026-07-31")
    assert rows[0]["noi_period_yen"] is None
    assert quality["noi_withheld"] == ["CFR-001"]


def test_sold_property_zero_operating_days_and_residual_negative_noi_are_retained():
    data = tables()
    for index, value in {
        2: "77",
        3: "コンフォリア新子安",
        4: "0",
        5: "0",
        6: "-",
        8: "0",
        18: "848",
        20: "1531",
        24: "△ 682",
    }.items():
        data["収支状況"][index]["F"] = value
    rows, quality = cfr.parse_tables(data, "2026-02-01", "2026-07-31")
    sold = rows[1]
    assert sold["owned_at_period_end"] is False
    assert sold["operating_days"] == 0
    assert sold["noi_period_yen"] == -682_000
    assert quality["sold_income_ids"] == ["77"]


def test_land_zero_depreciation_dash_is_zero_and_disclosed_noi_is_retained():
    data = tables()
    data["収支状況"][18]["E"] = "-"
    data["収支状況"][24]["E"] = "43000"
    rows, _ = cfr.parse_tables(data, "2026-02-01", "2026-07-31")
    assert rows[0]["operating_expense_ex_dep"] == 23_000_000
    assert rows[0]["noi_period_yen"] == 43_000_000


def test_missing_appraisal_or_duplicate_income_identifier_is_rejected():
    data = tables()
    del data["鑑定情報"][7]
    with pytest.raises(ValueError, match="coverage"):
        cfr.parse_tables(data, "2026-02-01", "2026-07-31")
    data = tables()
    data["収支状況"][2]["F"] = "1"
    with pytest.raises(ValueError, match="Duplicate"):
        cfr.parse_tables(data, "2026-02-01", "2026-07-31")


def test_noi_formula_failure_is_rejected_but_revenue_component_difference_is_logged():
    data = tables()
    data["収支状況"][5]["E"] = "75000"
    _, quality = cfr.parse_tables(data, "2026-02-01", "2026-07-31")
    assert len(quality["revenue_component_differences"]) == 1
    data["収支状況"][24]["E"] = "60000"
    with pytest.raises(ValueError, match="NOI reconciliation"):
        cfr.parse_tables(data, "2026-02-01", "2026-07-31")


def annual_rows():
    latest, _ = cfr.parse_tables(tables(), "2026-02-01", "2026-07-31")
    prior = deepcopy(latest)
    prior[0].update(
        period_start="2025-08-01",
        period_end="2026-01-31",
        operating_days=184,
        period_calendar_days=184,
        noi_period_yen=50_000_000,
    )
    return prior, latest


def test_annual_noi_adds_two_real_periods_without_partial_period_annualization():
    prior, latest = annual_rows()
    rows, quality = cfr.annual_cohort(prior, latest)
    assert rows[0]["noi_annual_yen"] == 104_000_000
    assert rows[0]["actual_period_start"] == "2025-08-01"
    assert rows[0]["actual_period_end"] == "2026-07-31"
    assert quality["included"] == 1
    prior[0]["operating_days"] = 100
    rows, quality = cfr.annual_cohort(prior, latest)
    assert rows == []
    assert quality["exclusions"][0]["reason"] == "partial_period"


def test_changed_share_cost_and_missing_prior_and_alternative_housing_are_excluded():
    prior, latest = annual_rows()
    prior[0]["acquisition_price_yen"] /= 2
    assert cfr.annual_cohort(prior, latest)[1]["exclusions"][0]["reason"] == "cost_or_share_changed"
    assert cfr.annual_cohort([], latest)[1]["exclusions"][0]["reason"] == "missing_prior"
    latest[0]["asset_type"] = "alternative_housing"
    assert cfr.annual_cohort(prior, latest)[1]["exclusions"][0]["reason"] == "alternative_housing"


def test_acquisition_appraisal_noi_is_forecast_and_uses_purchase_price():
    text = """１．取得の概要
1 不動産 コンフォリア例 1,500,000
合計 1,500,000
物件名 コンフォリア例
価格時点 2026 年 6 月 1 日
鑑定評価額 1,600,000
③ 運営純収益（NOI、①－②) 60,000
"""
    rows = cfr.parse_acquisitions(text, "example.pdf", {"コンフォリア例": "2026-08-03"})
    assert rows[0]["forecast_noi_annual_yen"] == 60_000_000
    assert rows[0]["acquisition_price_yen"] == 1_500_000_000
    assert rows[0]["forecast_noi_yield_on_purchase"] == pytest.approx(0.04)
    assert rows[0]["income_basis"] == "appraisal_forecast_noi"


def test_published_fund_noi_uses_rental_depreciation_and_keeps_withheld_residual():
    text = """不動産賃貸事業収益合計 100,000 110,000
（減価償却費） 10,000 12,000
不動産賃貸事業費用合計 30,000 35,000
"""
    totals = cfr.financial_totals(text)
    assert totals[0]["noi_yen"] == 80_000_000
    assert totals[1]["noi_yen"] == 87_000_000
    with pytest.raises(ValueError, match="Financial totals"):
        cfr.financial_totals("不動産賃貸事業収益合計 100,000")
