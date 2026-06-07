import pandas as pd

from src.model.debt_schedule import build_debt_schedule


def test_debt_schedule_no_negative_debt_and_cash_floor():
    projection = pd.DataFrame(
        [
            {"scenario": "Test", "year": 1, "fiscal_year": "FY1", "ebitda": 100.0, "ebit": 80.0, "capex": 20.0, "change_nwc": 5.0},
            {"scenario": "Test", "year": 2, "fiscal_year": "FY2", "ebitda": 120.0, "ebit": 95.0, "capex": 20.0, "change_nwc": 5.0},
        ]
    )
    schedule = build_debt_schedule(
        projection=projection,
        opening_debt=50.0,
        opening_cash=30.0,
        min_cash=25.0,
        interest_rate=0.05,
        cash_tax_rate=0.30,
        cash_sweep_pct=1.0,
    )
    assert (schedule["ending_debt"] >= -1e-9).all()
    assert (schedule["ending_cash"] >= 25.0 - 1e-9).all()
