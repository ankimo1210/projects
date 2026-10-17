from datetime import UTC, date, datetime

import numpy as np
import pytest

from macrokit import store
from macrokit.termstructure import curve

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
TRUE = np.array([3.0, -2.9, -1.0, 1.5, 1.0, 10.0])
TENORS = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40], dtype=float)


def test_short_end_is_beta0_plus_beta1():
    assert curve.svensson_zero(TRUE, np.array([1e-9]))[0] == pytest.approx(0.1, abs=1e-6)


def test_flat_continuous_curve_has_the_semiannual_equivalent_par_yield():
    flat = np.array([2.0, 0.0, 0.0, 0.0, 1.0, 5.0])
    expected = 200 * (np.exp(0.01) - 1)
    np.testing.assert_allclose(curve.par_yields(flat, np.array([1.0, 10.0, 40.0])), expected)


def test_a_par_bond_prices_at_par():
    coupon = curve.par_yields(TRUE, np.array([7.0]))[0]
    times = np.arange(1, 15) / 2.0
    disc = np.exp(-curve.svensson_zero(TRUE, times) / 100 * times)
    assert (coupon / 2 * disc).sum() + disc[-1] * 100 == pytest.approx(100.0, abs=1e-10)


def test_fit_recovers_an_exact_svensson_curve():
    par = curve.par_yields(TRUE, TENORS)
    overnight = curve.svensson_zero(TRUE, np.array([curve.OVERNIGHT_T]))[0]
    fit = curve.fit_svensson(TENORS, par, overnight, obs_date=date(2024, 7, 31))
    assert np.abs(fit.errors_bp).max() < 0.01
    months = np.arange(12, 361) / 12
    np.testing.assert_allclose(
        curve.svensson_zero(fit.params, months), curve.svensson_zero(TRUE, months), atol=0.005
    )


def test_fit_runs_with_only_short_tenors():
    short = TENORS[:10]
    fit = curve.fit_svensson(short, curve.par_yields(TRUE, short), None, obs_date=date(1986, 8, 30))
    assert np.abs(fit.errors_bp).max() < 0.5
    assert np.isfinite(curve.svensson_zero(fit.params, np.arange(1, 361) / 12)).all()


def _rate(curve_name, day, tenor, value):
    return store.RateObservation(curve_name, day, tenor, value, "test", "u", NOW)


@pytest.fixture
def market(tmp_path):
    con = store.connect(tmp_path / "t.duckdb")
    rows = []
    for day in (date(2024, 7, 30), date(2024, 7, 31), date(2024, 8, 30), date(1997, 3, 31)):
        par = curve.par_yields(TRUE, TENORS)
        rows += [_rate("jgb", day, t, float(v)) for t, v in zip(TENORS, par, strict=True)]
    rows.append(_rate("jp_call_on", date(2024, 7, 29), 1 / 365, 0.077))
    rows.append(_rate("jp_call_on", date(2024, 8, 1), 1 / 365, 0.227))
    rows.append(_rate("jp_call_on_mavg", date(1997, 3, 1), 1 / 365, 0.48))
    store.insert_rates(con, rows)
    return con


def test_overnight_uses_the_last_daily_value_in_the_month(market):
    assert curve.overnight_at(market, date(2024, 7, 31)) == 0.077  # not 0.227 from August
    assert curve.overnight_at(market, date(2024, 8, 30)) == 0.227


def test_overnight_falls_back_to_the_monthly_average_and_then_to_none(market):
    assert curve.overnight_at(market, date(1997, 3, 31)) == 0.48
    assert curve.overnight_at(market, date(1996, 1, 31)) is None


def test_fit_month_ends_picks_the_last_day_of_each_month(market):
    fits = curve.fit_month_ends(market, date(2024, 7, 1), date(2024, 8, 31))
    assert [f.obs_date for f in fits] == [date(2024, 7, 31), date(2024, 8, 30)]
    assert [f.overnight for f in fits] == [0.077, 0.227]


def test_zero_panel_columns_and_window():
    shifted = TRUE + np.array([0.1, 0, 0, 0, 0, 0])  # level shift of +0.1
    fits = [
        curve.CurveFit(date(2024, 7, 31), TRUE, TENORS, TENORS, TENORS, None),
        curve.CurveFit(date(2024, 8, 30), shifted, TENORS, TENORS, TENORS, None),
    ]
    panel = curve.zero_panel(fits)
    assert panel.yields.shape == (2, 360)
    assert panel.column(120)[1] - panel.column(120)[0] == pytest.approx(0.1)
    assert panel.columns(np.array([1, 120])).shape == (2, 2)
    assert panel.window(date(2024, 8, 1), date(2024, 8, 31)).dates == (date(2024, 8, 30),)
