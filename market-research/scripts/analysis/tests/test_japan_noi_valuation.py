"""Guard units, cohort joins and financing arithmetic in the NOI pilot."""

from copy import deepcopy

import pytest
from japan_noi_valuation import aggregate_markets, financing, parse_adr_tables, price_change


def tables():
    return {
        "物件概要": {
            5: {"B": "物件NO", "I": "取得価格\n(百万円)\n(注3)"},
            6: {
                "B": "T-001",
                "C": "Example",
                "D": "東京都品川区",
                "E": "38345",
                "F": "パス・スルー型",
                "G": "100",
                "H": "3000",
                "I": "1000000000",
            },
        },
        "帳簿価額": {
            5: {"X": "第32期末\n資本的支出等"},
            6: {"C": "物件番号", "H": "取得価格"},
            7: {"C": "T-001", "E": "Example", "H": "1000000000", "X": "2000000"},
        },
        "鑑定評価": {
            7: {"M": "評価額※2"},
            10: {"B": "T-001", "C": "Example", "L": "46234", "M": "2000", "O": "0.03"},
        },
        "収益状況": {
            5: {"B": "単位：千円"},
            23: {"B": "運用日数", "C": "181"},
            24: {"C": "T-001"},
            25: {"C": "Example"},
            26: {"B": "(A)賃貸事業収入　小計", "C": "50000"},
            28: {"B": "(B)賃貸事業費用　小計", "C": "20000"},
            36: {"B": "減価償却費", "C": "5000"},
            38: {"B": "NOI", "C": "35000"},
        },
    }


def test_raw_yen_thousand_yen_and_million_yen_are_distinguished():
    rows, quality = parse_adr_tables(tables())
    row = rows[0]
    assert row["acquisition_price_yen"] == 1_000_000_000
    assert row["appraisal_value_yen"] == 2_000_000_000
    assert row["noi_period_yen"] == 35_000_000
    assert row["operating_expense_period_yen"] == 15_000_000
    assert row["capex_period_yen"] == 2_000_000
    assert row["noi_annualized_yen"] == pytest.approx(70_580_110.49723756)
    assert row["yield_on_appraisal"] == pytest.approx(0.03529005524861878)
    assert quality["owned"] == 1


def test_missing_appraisal_cannot_silently_remove_an_owned_property():
    data = tables()
    del data["鑑定評価"][10]
    with pytest.raises(ValueError, match="coverage"):
        parse_adr_tables(data)


def test_duplicate_property_identifier_is_rejected():
    data = tables()
    data["物件概要"][7] = deepcopy(data["物件概要"][6])
    with pytest.raises(ValueError, match="Duplicate"):
        parse_adr_tables(data)


def test_partial_period_is_retained_but_excluded_from_baseline():
    data = tables()
    data["収益状況"][23]["C"] = "30"
    rows, quality = parse_adr_tables(data)
    assert rows[0]["baseline_eligible"] is False
    assert quality["partial_period"] == 1
    assert aggregate_markets(rows) == []


def test_prior_184_day_period_uses_its_actual_length():
    data = tables()
    data["収益状況"][23]["C"] = "184"
    rows, quality = parse_adr_tables(data, period_days=184)
    assert rows[0]["baseline_eligible"] is True
    assert rows[0]["noi_annualized_yen"] == pytest.approx(35_000_000 * 365 / 184)
    assert quality["partial_period"] == 0


def test_guaranteed_master_lease_is_excluded_from_baseline():
    data = tables()
    data["物件概要"][6]["F"] = "賃料保証型"
    rows, quality = parse_adr_tables(data)
    assert rows[0]["baseline_eligible"] is False
    assert quality["guaranteed_lease"] == 1


def test_noi_balance_error_fails_instead_of_generating_yields():
    data = tables()
    data["収益状況"][38]["C"] = "45000"
    with pytest.raises(ValueError, match="NOI reconciliation"):
        parse_adr_tables(data)


def test_same_id_with_changed_property_name_is_retained_and_disclosed():
    data = tables()
    data["帳簿価額"][7]["E"] = "Former name"
    rows, quality = parse_adr_tables(data)
    assert len(rows) == 1
    assert quality["name_differences"][0]["property_id"] == "T-001"


def test_different_disclosed_price_bases_are_preserved_and_reported():
    data = tables()
    data["帳簿価額"][7]["H"] = "1002000000"
    rows, quality = parse_adr_tables(data)
    assert rows[0]["acquisition_price_yen"] == 1_000_000_000
    assert rows[0]["book_acquisition_price_yen"] == 1_002_000_000
    assert quality["price_differences"][0]["difference_yen"] == -2_000_000


def test_unreconciled_portfolio_total_is_disclosed_not_called_rounding():
    data = tables()
    data["収益状況"][7] = {"F": "50100"}
    data["収益状況"][19] = {"F": "35050"}
    _, quality = parse_adr_tables(data)
    reconciliation = quality["portfolio_reconciliation"]["noi"]
    assert reconciliation["status"] == "unreconciled"
    assert reconciliation["owned_detail_thousand_yen"] == 35000
    assert reconciliation["owned_minus_reported_thousand_yen"] == -50


def test_aggregate_is_ratio_of_totals_not_mean_of_property_yields():
    a, _ = parse_adr_tables(tables())
    b = deepcopy(a[0])
    b["property_id"] = "T-002"
    b["appraisal_value_yen"] = 8_000_000_000
    row = aggregate_markets([a[0], b])[0]
    assert row["yield_on_appraisal"] == pytest.approx(0.014116022099447512)
    assert row["n"] == 2


def test_debt_service_includes_principal_and_reserve_does_not_change_noi_dscr():
    result = financing(0.045, rate=0.04, ltv=0.7, years=30, reserve=0.005, costs=0.07)
    # Independently evaluated with 50-digit Decimal annuity arithmetic.
    assert result["debt_service_per_price"] == pytest.approx(0.040102884819098597)
    assert result["dscr"] == pytest.approx(1.1221137881474602)
    assert result["cash_on_cash"] == pytest.approx(-0.00027806707864485773)
    assert result["max_price_ratio_for_dscr_125"] == pytest.approx(0.8976910305179681)


def test_zero_interest_has_straight_line_principal_repayment():
    result = financing(0.045, rate=0, ltv=0.7, years=30, reserve=0, costs=0)
    assert result["debt_service_per_price"] == pytest.approx(0.7 / 30)


def test_cap_expansion_requires_noi_growth_even_when_rent_is_increasing():
    result = price_change(0.036, growth=0, cap_increase=0.005, years=5)
    assert result["price_change"] == pytest.approx(-0.12195121951219512)
    assert result["required_noi_growth"] == pytest.approx((0.041 / 0.036) ** 0.2 - 1)


@pytest.mark.parametrize("rate,ltv,years", [(-0.01, 0.7, 30), (0.03, 1.1, 30), (0.03, 0.7, 0)])
def test_invalid_financing_assumptions_are_rejected(rate, ltv, years):
    with pytest.raises(ValueError):
        financing(0.045, rate=rate, ltv=ltv, years=years, reserve=0, costs=0)
