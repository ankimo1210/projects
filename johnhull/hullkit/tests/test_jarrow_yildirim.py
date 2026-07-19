"""Jarrow--Yildirim measure, analytic moment, option, and simulation tests."""

import numpy as np
import pytest
from hullkit import hull_white, jarrow_yildirim, rates

NOMINAL_CURVE = ((0.0, 1.0, 5.0, 10.0), (0.02, 0.02, 0.02, 0.02))
REAL_CURVE = ((0.0, 1.0, 5.0, 10.0), (0.01, 0.01, 0.01, 0.01))


def _params(*, scale: float = 1.0) -> jarrow_yildirim.JarrowYildirimParams:
    return jarrow_yildirim.JarrowYildirimParams(
        nominal_mean_reversion=0.08,
        nominal_volatility=0.010 * scale,
        real_mean_reversion=0.12,
        real_volatility=0.008 * scale,
        inflation_volatility=0.015 * scale,
        rho_nominal_real=0.25,
        rho_nominal_inflation=-0.15,
        rho_real_inflation=0.30,
    )


def test_correlation_matrix_rejects_non_psd_inputs() -> None:
    valid = jarrow_yildirim.jy_correlation_matrix(_params())
    np.testing.assert_allclose(np.diag(valid), 1.0)
    invalid = jarrow_yildirim.JarrowYildirimParams(
        0.1, 0.01, 0.1, 0.01, 0.02, 0.9, 0.9, -0.9
    )
    with pytest.raises(ValueError, match="positive semidefinite"):
        jarrow_yildirim.jy_correlation_matrix(invalid)


def test_cpi_forward_is_real_discount_over_nominal_discount() -> None:
    forward = jarrow_yildirim.jy_cpi_forward(
        0.0, 5.0, 100.0, NOMINAL_CURVE, REAL_CURVE
    )
    expected = 100.0 * rates.discount_factor(5.0, REAL_CURVE) / rates.discount_factor(
        5.0, NOMINAL_CURVE
    )
    assert forward == pytest.approx(expected, abs=1e-12)


def test_payment_forward_level_and_yoy_ratio_match_exact_joint_mc() -> None:
    params = _params()
    expected_level = jarrow_yildirim.jy_payment_forward_cpi(
        0.0, 1.0, 2.0, 100.0, NOMINAL_CURVE, REAL_CURVE, params
    )
    expected_ratio = jarrow_yildirim.jy_expected_cpi_ratio(
        0.0, 1.0, 2.0, 2.0, 100.0, NOMINAL_CURVE, REAL_CURVE, params
    )
    samples = jarrow_yildirim.simulate_jy_forward_levels(
        (1.0, 2.0),
        2.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        n_paths=180_000,
        seed=17,
    )
    level_error = samples[:, 0].std(ddof=1) / np.sqrt(len(samples))
    ratio_samples = samples[:, 1] / samples[:, 0]
    ratio_error = ratio_samples.std(ddof=1) / np.sqrt(len(samples))
    assert abs(samples[:, 0].mean() - expected_level) < 3.0 * level_error
    assert abs(ratio_samples.mean() - expected_ratio) < 3.0 * ratio_error


def test_cpi_option_matches_forward_measure_monte_carlo() -> None:
    params = _params()
    strike = 105.0
    analytic = jarrow_yildirim.jy_cpi_option(
        1.0,
        strike,
        0.0,
        5.0,
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
    )
    levels = jarrow_yildirim.simulate_jy_forward_levels(
        (5.0,),
        5.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        n_paths=220_000,
        seed=23,
    )[:, 0]
    discounted = rates.discount_factor(5.0, NOMINAL_CURVE) * np.maximum(levels - strike, 0.0)
    standard_error = discounted.std(ddof=1) / np.sqrt(len(discounted))
    assert abs(discounted.mean() - analytic) < 3.0 * standard_error


def test_zero_volatility_recovers_deterministic_prices_and_no_yoy_convexity() -> None:
    params = _params(scale=0.0)
    forward = jarrow_yildirim.jy_cpi_forward(
        0.0, 2.0, 100.0, NOMINAL_CURVE, REAL_CURVE
    )
    option = jarrow_yildirim.jy_cpi_option(
        2.0,
        101.0,
        0.0,
        2.0,
        2.0,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
    )
    expected = 2.0 * rates.discount_factor(2.0, NOMINAL_CURVE) * max(forward - 101.0, 0.0)
    assert option == pytest.approx(expected)
    ratio = jarrow_yildirim.jy_expected_cpi_ratio(
        0.0, 1.0, 2.0, 2.0, 100.0, NOMINAL_CURVE, REAL_CURVE, params
    )
    first = jarrow_yildirim.jy_cpi_forward(0.0, 1.0, 100.0, NOMINAL_CURVE, REAL_CURVE)
    assert ratio == pytest.approx(forward / first)


def test_nominal_measure_simulation_preserves_numeraire_martingales() -> None:
    params = _params()
    grid = np.linspace(0.0, 2.0, 81)
    simulation = jarrow_yildirim.simulate_jy_paths(
        grid,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        n_paths=24_000,
        seed=29,
    )
    terminal_density = 1.0 / (
        simulation.nominal_bank_accounts[:, -1]
        * rates.discount_factor(2.0, NOMINAL_CURVE)
    )
    density_error = terminal_density.std(ddof=1) / np.sqrt(len(terminal_density))
    assert abs(terminal_density.mean() - 1.0) < 4.0 * density_error

    real_zcb = simulation.cpi[:, -1] / simulation.nominal_bank_accounts[:, -1]
    expected_real_zcb = 100.0 * rates.discount_factor(2.0, REAL_CURVE)
    real_error = real_zcb.std(ddof=1) / np.sqrt(len(real_zcb))
    assert abs(real_zcb.mean() - expected_real_zcb) < 4.0 * real_error

    index = len(grid) // 2
    hw_params = hull_white.HullWhiteParams(
        params.nominal_mean_reversion, params.nominal_volatility
    )
    bond_values = np.asarray(
        [
            hull_white.hw_discount_bond(grid[index], 2.0, state, NOMINAL_CURVE, hw_params)
            for state in simulation.nominal_factors[:, index]
        ]
    )
    discounted_bonds = bond_values / simulation.nominal_bank_accounts[:, index]
    bond_error = discounted_bonds.std(ddof=1) / np.sqrt(len(discounted_bonds))
    assert abs(discounted_bonds.mean() - rates.discount_factor(2.0, NOMINAL_CURVE)) < (
        4.0 * bond_error
    )
