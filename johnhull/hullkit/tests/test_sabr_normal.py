"""Normal/shifted SABR model-risk and hedge tests."""

import numpy as np
import pytest
from hullkit import rfr_options, sabr_normal


def test_normal_sabr_flat_limit_matches_bachelier() -> None:
    for strike in (-0.01, 0.02, 0.05):
        sigma = sabr_normal.normal_sabr_implied_vol(0.02, strike, 2.0, 0.01, -0.3, 0.0)
        assert sigma == pytest.approx(0.01)
        price = sabr_normal.normal_sabr_price(0.02, strike, 2.0, 0.01, -0.3, 0.0)
        assert price == pytest.approx(rfr_options.bachelier_price(0.02, strike, 0.01, 2.0))


def test_shifted_and_free_boundary_sabr_make_boundary_explicit() -> None:
    shifted = sabr_normal.shifted_sabr_implied_vol(
        -0.005, 0.0, 1.0, 0.02, 0.5, -0.2, 0.4, shift=0.02
    )
    bounded = sabr_normal.free_boundary_sabr_implied_vol(
        -0.005, 0.0, 1.0, 0.02, 0.5, -0.2, 0.4, lower_boundary=-0.02
    )
    assert bounded == pytest.approx(shifted)
    shifted_price = sabr_normal.shifted_sabr_price(
        -0.005, 0.0, 1.0, 0.02, 0.5, -0.2, 0.4, shift=0.02
    )
    bounded_price = sabr_normal.free_boundary_sabr_price(
        -0.005,
        0.0,
        1.0,
        0.02,
        0.5,
        -0.2,
        0.4,
        lower_boundary=-0.02,
    )
    assert bounded_price == pytest.approx(shifted_price)
    with pytest.raises(ValueError, match="boundary"):
        sabr_normal.shifted_sabr_implied_vol(-0.03, 0.0, 1.0, 0.02, 0.5, 0.0, 0.4, shift=0.02)


def test_normal_sabr_mc_teacher_matches_constant_vol_within_sampling_error() -> None:
    result = sabr_normal.normal_sabr_mc_price(
        0.02,
        0.02,
        1.0,
        0.01,
        -0.4,
        0.0,
        n_steps=8,
        n_paths=40_000,
        seed=4,
    )
    reference = rfr_options.bachelier_price(0.02, 0.02, 0.01, 1.0)
    assert abs(result.price - reference) < 5 * result.standard_error


def test_conditional_normal_sabr_teacher_is_seeded_and_reduces_noise() -> None:
    arguments = dict(
        forward=0.02,
        strike=0.025,
        expiry=5.0,
        alpha=0.02,
        rho=-0.3,
        nu=0.65,
        n_steps=32,
        n_paths=8_000,
        seed=19,
    )
    crude = sabr_normal.normal_sabr_mc_price(**arguments)
    conditional = sabr_normal.normal_sabr_conditional_mc_price(**arguments)
    repeated = sabr_normal.normal_sabr_conditional_mc_price(**arguments)
    np.testing.assert_array_equal(conditional.conditional_prices, repeated.conditional_prices)
    assert conditional.standard_error < crude.standard_error
    assert abs(conditional.price - crude.price) < 5 * (
        conditional.standard_error + crude.standard_error
    )


def test_shifted_sabr_teacher_is_independent_of_hagan_and_respects_boundary() -> None:
    arguments = dict(
        forward=0.03,
        strike=0.03,
        expiry=1.0,
        alpha=0.08,
        beta=0.5,
        rho=-0.35,
        nu=0.6,
        shift=0.03,
        n_steps=32,
        n_paths=20_000,
        seed=23,
    )
    teacher = sabr_normal.shifted_sabr_mc_price(**arguments)
    repeated = sabr_normal.shifted_sabr_mc_price(**arguments)
    np.testing.assert_array_equal(teacher.terminal_forward, repeated.terminal_forward)
    assert teacher.standard_error > 0.0
    assert np.min(teacher.terminal_forward) >= -arguments["shift"]
    hagan = sabr_normal.shifted_sabr_price(
        arguments["forward"],
        arguments["strike"],
        arguments["expiry"],
        arguments["alpha"],
        arguments["beta"],
        arguments["rho"],
        arguments["nu"],
        shift=arguments["shift"],
    )
    assert abs(teacher.price - hagan) < 5 * teacher.standard_error + 5e-4


def test_hagan_error_regions_and_hard_arbitrage_checks() -> None:
    strikes = np.array([0.00, 0.01, 0.02, 0.03, 0.04])
    maturities = np.array([0.5, 2.0])
    teacher = np.array([[0.021, 0.014, 0.008, 0.004, 0.001], [0.025, 0.019, 0.014, 0.010, 0.007]])
    approximation = teacher.copy()
    approximation[1, (0, -1)] += 0.002
    diagnostics = sabr_normal.hagan_error_diagnostics(
        approximation,
        teacher,
        strikes,
        maturities,
        np.array([0.01, 0.03]),
    )
    assert diagnostics.wing_rmse > 0.0
    assert diagnostics.long_maturity_rmse > 0.0
    assert diagnostics.high_vol_rmse > 0.0
    good = sabr_normal.call_grid_arbitrage_diagnostics(strikes, maturities, teacher)
    assert (
        good.nonnegative and good.strike_monotone and good.strike_convex and good.calendar_monotone
    )
    broken = teacher.copy()
    broken[0, 2] = 0.03
    bad = sabr_normal.call_grid_arbitrage_diagnostics(strikes, maturities, broken)
    assert not bad.strike_monotone or not bad.strike_convex
    negative = teacher.copy()
    negative[0, -1] = -0.001
    assert (
        "negative_call_price"
        in sabr_normal.call_grid_arbitrage_diagnostics(strikes, maturities, negative).violations
    )


def test_bartlett_and_sticky_delta_are_compared_on_identical_paths() -> None:
    parameters = dict(
        forward=0.03,
        strike=0.03,
        expiry=2.0,
        alpha=0.02,
        beta=0.5,
        rho=-0.5,
        nu=0.6,
        shift=0.03,
    )
    sticky = sabr_normal.sticky_strike_delta(**parameters)
    bartlett = sabr_normal.bartlett_delta(**parameters)
    assert sticky != pytest.approx(bartlett)
    changes = np.array([-0.01, -0.005, 0.005, 0.01])
    option_pnl = bartlett * changes
    comparison = sabr_normal.compare_delta_hedges(option_pnl, changes, sticky, bartlett)
    assert comparison.bartlett_rmse == pytest.approx(0.0, abs=1e-15)
    assert comparison.sticky_rmse > comparison.bartlett_rmse
