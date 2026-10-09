import pytest
from japan_noi_adr import annual_cohort, parse_pdf_appraisals, parse_pdf_income


def test_pdf_income_handles_expense_wrapped_above_id():
    text = """Ｃ．個別不動産等の損益状況
                         245,520
T-039 名称 611,143 26,259 49,031 6,969 20,957 739 － 9,443 132,119 365,622
Ｄ．次節"""
    assert parse_pdf_income(text)["T-039"] == [611143, 245520, 132119]


def test_pdf_income_fails_on_missing_wrapped_value():
    with pytest.raises(ValueError):
        parse_pdf_income("Ｃ．個別不動産等の損益状況\nT-039 名称 1 2\nＤ．次節")


def test_appraisal_does_not_join_next_property_when_value_missing():
    with pytest.raises(ValueError):
        parse_pdf_appraisals(
            "Ｂ．不動産鑑定評価の概要\nT-001 名称\nT-002 名称 ① 100 110\nＣ．個別不動産等の損益状況"
        )


def item(period_end, **changes):
    return {
        "fund": "ADR",
        "property_id": "T-001",
        "baseline_eligible": True,
        "period_start": "2025-08-01" if period_end == "2026-01-31" else "2026-02-01",
        "period_end": period_end,
        "operating_days": 184 if period_end == "2026-01-31" else 181,
        "acquisition_price_yen": 1000,
        "appraisal_value_yen": 1000,
        "noi_period_yen": 30,
        "revenue_period_yen": 40,
        "operating_expense_period_yen": 10,
        "capex_period_yen": 1,
        **changes,
    }


def test_annual_sum_is_actual_not_double_latest():
    prior = item("2026-01-31", noi_period_yen=20)
    current = item("2026-07-31")
    rows, excluded = annual_cohort([prior], [current])
    assert rows[0]["noi_annual_yen"] == 50
    assert rows[0]["yield_on_appraisal"] == 0.05
    assert rows[0]["yield_on_acquisition"] == 0.05
    assert rows[0]["operating_days"] == 365
    assert excluded == []


def test_annual_excludes_changed_interest_and_partial_period():
    rows, excluded = annual_cohort(
        [item("2026-01-31")], [item("2026-07-31", acquisition_price_yen=500)]
    )
    assert not rows
    assert excluded[0]["reason"] == "取得額・持分変更"
