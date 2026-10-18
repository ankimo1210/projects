from datetime import date

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.gsw import GswCurve
from bond_timing.returns import (
    delayed_switch_excess,
    grid_months,
    holding_log_return,
    real_outcomes,
    rolling_forward_sum,
    rx12,
)
from macrokit.sources.us_term import GswDay


def flat(rate: float = 0.05, periods: int = 30) -> pd.DataFrame:
    index = pd.period_range("2000-01", periods=periods, freq="M")
    return pd.DataFrame(rate, index=index, columns=grid_months())


def test_grid_has_every_maturity_the_returns_need():
    grid = set(grid_months())
    assert {12, 23, 24, 108, 119, 120, 89, 90, 203, 204} <= grid


def test_flat_curve_has_no_term_premium():
    zeros = flat()
    assert np.allclose(rx12(zeros, 10).dropna(), 0.0)
    assert np.allclose(holding_log_return(zeros, 120).dropna(), 0.05 / 12)


def test_rx12_matches_a_hand_calculation():
    zeros = flat()
    s = pd.Period("2001-01", "M")
    zeros.loc[s, 120], zeros.loc[s, 12], zeros.loc[s + 12, 108] = 0.06, 0.04, 0.07
    assert rx12(zeros, 10)[s] == pytest.approx(10 * 0.06 - 9 * 0.07 - 0.04)


def test_holding_return_buys_at_the_end_of_the_previous_month():
    zeros = flat()
    p = pd.Period("2000-06", "M")
    zeros.loc[p - 1, 120], zeros.loc[p, 119] = 0.06, 0.055
    assert holding_log_return(zeros, 120)[p] == pytest.approx(10 * 0.06 - 119 / 12 * 0.055)


def test_rolling_forward_sum_adds_the_next_twelve_months():
    index = pd.period_range("2000-01", periods=30, freq="M")
    monthly = pd.DataFrame({10: np.arange(1.0, 31.0)}, index=index)
    out = rolling_forward_sum(monthly, 12)
    assert out[10].iloc[0] == sum(range(2, 14))
    assert out[10].iloc[17] == sum(range(19, 31))
    assert np.isnan(out[10].iloc[18])


def test_real_outcomes_align_targets_and_instruments():
    zeros = flat()
    cash = pd.Series(0.004, index=zeros.index)
    out = real_outcomes(zeros, cash)
    s = pd.Period("2000-05", "M")
    assert out.xr1[s] == pytest.approx(out.monthly_log_excess[10][s + 1])
    assert out.excess["tlt"][s] == pytest.approx(np.expm1(0.05 / 12) - 0.004)
    assert list(out.rx12.columns) == list(range(2, 11))
    assert out.rxbar[s] == pytest.approx(0.0)


def test_delayed_switch_legs_on_a_flat_curve():
    days = tuple(
        GswDay(ts.date(), (6.0, 0.0, 0.0, 0.0, 1.0, 1.0))
        for ts in pd.bdate_range("2020-01-01", "2020-03-31")
    )
    curve = GswCurve(days, {d.obs_date: 30 for d in days})
    cash = pd.Series(0.0, index=pd.period_range("2020-01", "2020-03", freq="M"))
    legs = delayed_switch_excess(curve, 204, cash)
    february = pd.Period("2020-02", "M")
    t_old = (date(2020, 2, 7) - date(2020, 1, 31)).days / 365.25
    t_new = (date(2020, 2, 28) - date(2020, 2, 7)).days / 365.25
    assert legs.loc[february, "out"] == pytest.approx(np.expm1(0.06 * t_old))
    assert legs.loc[february, "in"] == pytest.approx(np.expm1(0.06 * t_new))
