"""JGBi redemption-floor decomposition and Jarrow--Yildirim option tests."""

from datetime import date

import pytest
from hullkit import jarrow_yildirim, jgbi, rates

NOMINAL_CURVE = ((0.0, 1.0, 5.0, 10.0), (0.015, 0.015, 0.015, 0.015))
REAL_CURVE = ((0.0, 1.0, 5.0, 10.0), (0.005, 0.005, 0.005, 0.005))


def _params(inflation_volatility: float) -> jarrow_yildirim.JarrowYildirimParams:
    return jarrow_yildirim.JarrowYildirimParams(
        0.10,
        0.0,
        0.12,
        0.0,
        inflation_volatility,
        0.0,
        0.0,
        0.0,
    )


def _terms(principal_floor: bool) -> jgbi.JGBITerms:
    return jgbi.JGBITerms(
        issue_date=date(2026, 1, 10),
        maturity_date=date(2027, 1, 10),
        coupon_dates=(date(2026, 7, 10), date(2027, 1, 10)),
        coupon_rate=0.005,
        face_value=100_000_000.0,
        base_reference_date=date(2026, 1, 10),
        principal_floor=principal_floor,
    )


def test_floor_is_non_negative_and_increases_with_inflation_volatility() -> None:
    low = jgbi.jgbi_deflation_floor_jy(
        100.0,
        108.0,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        _params(0.005),
    )
    high = jgbi.jgbi_deflation_floor_jy(
        100.0,
        108.0,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        _params(0.03),
    )
    assert 0.0 <= low < high


def test_zero_volatility_floor_equals_discounted_intrinsic_value() -> None:
    base_index = 108.0
    forward_index = jarrow_yildirim.jy_cpi_forward(
        0.0, 5.0, 100.0, NOMINAL_CURVE, REAL_CURVE
    )
    expected = (
        100.0
        * rates.discount_factor(5.0, NOMINAL_CURVE)
        * max(1.0 - forward_index / base_index, 0.0)
    )
    value = jgbi.jgbi_deflation_floor_jy(
        100.0,
        base_index,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        _params(0.0),
    )
    assert value == pytest.approx(expected, abs=1e-12)


def test_analytic_floor_matches_exact_forward_measure_monte_carlo() -> None:
    params = _params(0.02)
    analytic = jgbi.jgbi_deflation_floor_jy(
        100.0,
        108.0,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
    )
    monte_carlo = jgbi.jgbi_deflation_floor_jy_mc(
        100.0,
        108.0,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        n_paths=240_000,
        seed=41,
    )
    assert abs(monte_carlo.value - analytic) < 3.0 * monte_carlo.standard_error


def test_floor_adjustment_respects_legacy_contract_flag() -> None:
    unfloored, option = 102.5, 1.25
    assert jgbi.jgbi_floor_adjusted_price(unfloored, option, _terms(True)) == 103.75
    assert jgbi.jgbi_floor_adjusted_price(unfloored, option, _terms(False)) == unfloored


def test_floor_risk_has_negative_cpi_delta_and_positive_vega() -> None:
    risk = jgbi.jgbi_floor_risk(
        100.0,
        108.0,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        _params(0.02),
    )
    assert risk.value > 0.0
    assert risk.cpi_delta < 0.0
    assert risk.inflation_vega > 0.0
