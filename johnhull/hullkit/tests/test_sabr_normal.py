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


# Worst vol 23 teacher cell (frontier_reference.volume23_reference): alpha=0.04,
# T=10y, ATM strike 0.03 -> teacher_price[2, 2, 4] in rfr_scenarios.npz.
_VOL23_WORST_CELL = dict(forward=0.030, strike=0.030, expiry=10.0, alpha=0.040, rho=-0.30, nu=0.65)


def test_conditional_teacher_shock_option_leaves_seeded_default_unchanged() -> None:
    seed = 20260741 + 1_000 * 2 + 100 * 2 + 4
    default = sabr_normal.normal_sabr_conditional_mc_price(
        **_VOL23_WORST_CELL, n_steps=48, n_paths=8_000, seed=seed
    )
    # Values committed in volumes/23_rfr_post_libor/reference/rfr_scenarios.npz
    # before ``volatility_shocks`` existed; the default path must stay bit-identical.
    assert default.price == 0.06180665230660865
    assert default.standard_error == 0.0010933168252864366

    rng = np.random.default_rng(seed)
    explicit_draws = np.stack([rng.standard_normal(8_000) for _ in range(48)])
    explicit = sabr_normal.normal_sabr_conditional_mc_price(
        **_VOL23_WORST_CELL, n_steps=48, n_paths=8_000, volatility_shocks=explicit_draws
    )
    np.testing.assert_array_equal(explicit.conditional_prices, default.conditional_prices)

    with pytest.raises(ValueError, match="volatility_shocks"):
        sabr_normal.normal_sabr_conditional_mc_price(
            **_VOL23_WORST_CELL, n_steps=48, n_paths=8_000, volatility_shocks=explicit_draws[1:]
        )


def test_conditional_teacher_step_doubling_bias_is_far_below_reported_standard_error() -> None:
    """Common-random-number step doubling for the left-Riemann integrated variance.

    Coarse shocks are ``(z[0::2] + z[1::2]) / sqrt(2)`` of the finer grid, so the
    48/96/192-step estimators share one Brownian path and ``P_n - P_2n`` isolates
    time-discretization error. Measured at seed 200, 40k paths: P_48 - P_96 =
    -0.070 bp, P_96 - P_192 = -0.021 bp against SE_192 = 6.36 bp (0.011 and 0.003
    SE); pathwise RMS difference 39.4 bp -> 23.1 bp (ratio 0.59). Re-seeding
    instead of coupling moves this cell by 28 bp (2.6 SE) between 48 and 192
    steps, which is sampling noise, not discretization bias.
    """
    n_paths = 40_000
    fine = np.random.default_rng(200).standard_normal((192, n_paths))
    shocks = {192: fine}
    shocks[96] = (shocks[192][0::2] + shocks[192][1::2]) / np.sqrt(2.0)
    shocks[48] = (shocks[96][0::2] + shocks[96][1::2]) / np.sqrt(2.0)
    results = {
        n_steps: sabr_normal.normal_sabr_conditional_mc_price(
            **_VOL23_WORST_CELL,
            n_steps=n_steps,
            n_paths=n_paths,
            volatility_shocks=shocks[n_steps],
        )
        for n_steps in (48, 96, 192)
    }
    coarse_gap = results[96].conditional_prices - results[48].conditional_prices
    fine_gap = results[192].conditional_prices - results[96].conditional_prices
    finest_se = results[192].standard_error

    # Pathwise (strong) error of the Riemann sum is O(dt): the RMS gap should
    # roughly halve per doubling. A 40-seed sweep at 8k paths and 20 seeds at 40k
    # paths gave ratios in [0.32, 0.69] at 40k (heavy-tailed alpha paths widen it
    # at 8k), so 0.75 still separates first-order shrinkage from no shrinkage.
    rms_ratio = np.sqrt(np.mean(fine_gap**2)) / np.sqrt(np.mean(coarse_gap**2))
    assert rms_ratio < 0.75

    # Richardson for an O(dt) bias: bias(P_48) ~ 2 (P_48 - P_96). Over the same
    # 60-seed sweep max |P_48 - P_96| / SE_192 was 0.087 (so 2x = 0.17) and max
    # |P_96 - P_192| / SE_192 was 0.061; the bounds below keep a 2x and 4x margin
    # on those worst cases. The pooled sweep mean put bias(P_48) near -0.4 bp.
    assert 2.0 * abs(coarse_gap.mean()) < 0.35 * finest_se
    assert abs(fine_gap.mean()) < 0.25 * finest_se


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
