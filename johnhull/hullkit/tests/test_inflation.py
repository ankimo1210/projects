"""CPI convention, seasonality, and deterministic inflation-swap tests."""

from datetime import date

import numpy as np
import pytest
from hullkit import inflation


def _seasonality() -> inflation.MonthlySeasonality:
    raw = np.array([0.003, -0.001, 0.002, -0.002, 0.001, -0.003] * 2)
    raw -= raw.mean()
    return inflation.MonthlySeasonality(tuple(raw))


def test_monthly_seasonality_has_unit_annual_product_and_cancels_annually() -> None:
    seasonality = _seasonality()
    seasonality.validate()
    factors = [seasonality.factor(month) for month in range(1, 13)]
    assert np.prod(factors) == pytest.approx(1.0, abs=1e-12)
    assert seasonality.multiplier(date(2026, 3, 1), date(2027, 3, 1)) == pytest.approx(
        1.0, abs=1e-12
    )
    assert seasonality.multiplier(date(2026, 3, 1), date(2026, 8, 1)) != pytest.approx(1.0)


def test_lagged_cpi_flat_and_linear_observations_are_explicit() -> None:
    fixings = {date(2026, 4, 1): 110.0, date(2026, 5, 1): 112.0}
    day = date(2026, 7, 16)
    flat = inflation.interpolated_cpi(
        day, fixings, inflation.CPIObservationConvention(interpolation="flat")
    )
    linear = inflation.interpolated_cpi(day, fixings)
    assert flat == 110.0
    assert linear == pytest.approx(110.0 + 2.0 * 15.0 / 31.0)

    known = {date(2026, 4, 1): 110.0}
    forecast = {date(2026, 5, 1): 112.0}
    assert inflation.cpi_observation(day, known, forecast) == pytest.approx(linear)
    with pytest.raises(ValueError, match="overlap"):
        inflation.cpi_observation(day, fixings, {date(2026, 5, 1): 113.0})


def test_rebase_bridge_preserves_all_index_ratios() -> None:
    levels = np.array([98.4, 101.2, 104.7])
    rebased = np.array([inflation.apply_cpi_rebase(value, 0.87) for value in levels])
    np.testing.assert_allclose(rebased[1:] / rebased[:-1], levels[1:] / levels[:-1])


def test_zcis_par_value_and_quote_curve_round_trip() -> None:
    nominal_curve = ((0.0, 1.0, 5.0, 10.0), (0.01, 0.012, 0.018, 0.02))
    start_index, end_index, years = 108.5, 121.0, 5.0
    par = inflation.zcis_par_rate(start_index, end_index, years)
    pv = inflation.zcis_npv(
        100_000_000.0, start_index, end_index, par, years, years, nominal_curve
    )
    assert pv == pytest.approx(0.0, abs=1e-10)

    quotes = (0.009, 0.012, 0.015)
    curve = inflation.bootstrap_zc_inflation_curve(
        date(2026, 1, 1), 108.5, (1.0, 5.0, 10.0), quotes
    )
    recovered = tuple(curve.zero_rate(maturity) for maturity in curve.maturities)
    np.testing.assert_allclose(recovered, quotes, atol=1e-10, rtol=0.0)


def test_forward_index_cancels_annual_seasonality_but_retains_off_cycle_effect() -> None:
    base = date(2026, 3, 1)
    curve = inflation.ZeroCouponInflationCurve(
        base, 100.0, (1.0, 5.0), (0.02, 0.02), _seasonality()
    )
    annual = inflation.seasonal_forward_index(date(2027, 3, 1), curve)
    expected = 100.0 * 1.02 ** ((date(2027, 3, 1) - base).days / 365.25)
    assert annual == pytest.approx(expected, abs=1e-12)
    off_cycle = inflation.seasonal_forward_index(date(2026, 8, 1), curve)
    trend_only = 100.0 * 1.02 ** ((date(2026, 8, 1) - base).days / 365.25)
    assert off_cycle != pytest.approx(trend_only)


def test_yoy_swap_consumes_expected_ratios_not_marginal_levels() -> None:
    nominal_curve = ((0.0, 1.0, 2.0), (0.01, 0.01, 0.01))
    ratios = (1.021, 1.024)
    expected = 1_000_000.0 * sum(
        np.exp(-0.01 * time) * (ratio - 1.0 - 0.02)
        for ratio, time in zip(ratios, (1.0, 2.0), strict=True)
    )
    pv = inflation.yoy_swap_npv(1_000_000.0, ratios, (1.0, 2.0), 0.02, nominal_curve)
    assert pv == pytest.approx(expected)
    assert inflation.yoy_rate(100.0, 103.0) == pytest.approx(0.03)


def test_invalid_inflation_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="sum to zero"):
        inflation.MonthlySeasonality((0.01,) * 12).validate()
    with pytest.raises(ValueError, match="first-of-month"):
        inflation.monthly_cpi_value(date(2026, 1, 2), {date(2026, 1, 1): 100.0})
    with pytest.raises(ValueError, match="strictly increasing"):
        inflation.bootstrap_zc_inflation_curve(
            date(2026, 1, 1), 100.0, (2.0, 1.0), (0.01, 0.02)
        )
