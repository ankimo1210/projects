import pytest
from japan_noi_comparison import aggregate, normalize_acquisition, normalize_annual


def test_aggregate_is_ratio_of_totals():
    rows = [
        {
            "market": "東京23区",
            "fund": "ADR",
            "noi_annual_yen": n,
            "acquisition_price_yen": p,
            "appraisal_value_yen": p,
            "revenue_annual_yen": n * 2,
            "operating_expense_annual_yen": n,
            "contract_verified": True,
        }
        for n, p in [(10, 100), (10, 900)]
    ]
    assert aggregate(rows)[0]["yield_on_appraisal"] == 0.02
    assert aggregate(rows)[0]["n"] == 2


def test_comforia_dates_use_actual_annual_window_and_unknown_contract():
    row = {
        "name": "test",
        "actual_period_start": "2025-08-01",
        "actual_period_end": "2026-07-31",
        "actual_operating_days": 365,
        "masterlease": None,
        "period_calendar_days": 181,
        "noi_period_yen": 15,
        "noi_annual_yen": 30,
        "acquisition_price_yen": 1000,
        "appraisal_value_yen": 1000,
    }
    result = normalize_annual(row, "CFR")
    assert result["period_start"] == "2025-08-01"
    assert result["operating_days"] == 365
    assert result["period_days"] == 365
    assert "noi_period_yen" not in result
    assert result["contract_verified"] is False


def test_annual_rejects_short_period():
    with pytest.raises(ValueError):
        normalize_annual({"operating_days": 181}, "ADR")


def test_acquisition_never_treats_forecast_as_actual():
    result = normalize_acquisition(
        {
            "name": "new",
            "forecast_noi_annual_yen": 40,
            "noi_annual_yen": 40,
            "forecast_noi_yield_on_purchase": 0.04,
            "acquisition_price_yen": 1000,
        },
        "CFR",
    )
    assert result["income_basis"] == "acquisition_appraisal_forecast_not_actual"
    assert result["noi_forecast_annual_yen"] == 40
    assert "noi_annual_yen" not in result


def test_rounded_adr_yield_has_no_invented_exact_noi():
    result = normalize_acquisition(
        {"property_name": "new", "yield_on_acquisition": 0.037, "acquisition_price_yen": 1000},
        "ADR",
    )
    assert result["noi_forecast_annual_yen"] is None
