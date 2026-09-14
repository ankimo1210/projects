"""Jarrow--Yildirim measure, analytic moment, option, and simulation tests."""

import numpy as np
import pytest
from hullkit import hull_white, inflation, jarrow_yildirim, rates

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
    invalid = jarrow_yildirim.JarrowYildirimParams(0.1, 0.01, 0.1, 0.01, 0.02, 0.9, 0.9, -0.9)
    with pytest.raises(ValueError, match="positive semidefinite"):
        jarrow_yildirim.jy_correlation_matrix(invalid)


def test_cpi_forward_is_real_discount_over_nominal_discount() -> None:
    forward = jarrow_yildirim.jy_cpi_forward(0.0, 5.0, 100.0, NOMINAL_CURVE, REAL_CURVE)
    expected = (
        100.0 * rates.discount_factor(5.0, REAL_CURVE) / rates.discount_factor(5.0, NOMINAL_CURVE)
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
    forward = jarrow_yildirim.jy_cpi_forward(0.0, 2.0, 100.0, NOMINAL_CURVE, REAL_CURVE)
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


# ZCIS: observed at 2y, paid 3 months later so the payment-measure adjustment is live.
ZCIS_TERMS = dict(start_index=100.0, fixed_rate=0.012, accrual_years=2.0, observation=2.0)
ZCIS_PAYMENT = 2.25
# YoY: three annual ratios, each paid 3 months after its end observation.
YOY_PAIRS = ((0.0, 1.0), (1.0, 2.0), (2.0, 3.0))
YOY_PAYMENTS = (1.25, 2.25, 3.25)
YOY_FIXED = 0.01


@pytest.mark.parametrize("pay_fixed", [True, False])
def test_jy_swaps_zero_volatility_limit_equals_deterministic_inflation_npvs(
    pay_fixed: bool,
) -> None:
    """With every JY volatility at zero there is no convexity or measure adjustment.

    The expected end CPI is the curve forward ``I0 P_r/P_n`` and each expected
    YoY ratio is the ratio of curve forwards, so the JY values must reduce to
    ``inflation.zcis_npv`` / ``inflation.yoy_swap_npv`` fed those forwards.
    """
    params = _params(scale=0.0)
    notional = 1_000_000.0
    end_forward = jarrow_yildirim.jy_cpi_forward(
        0.0, ZCIS_TERMS["observation"], 100.0, NOMINAL_CURVE, REAL_CURVE
    )
    zcis = jarrow_yildirim.jy_zcis_value(
        notional,
        ZCIS_TERMS["start_index"],
        ZCIS_TERMS["fixed_rate"],
        ZCIS_TERMS["accrual_years"],
        0.0,
        ZCIS_TERMS["observation"],
        ZCIS_PAYMENT,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        pay_fixed=pay_fixed,
    )
    expected_zcis = inflation.zcis_npv(
        notional,
        ZCIS_TERMS["start_index"],
        end_forward,
        ZCIS_TERMS["fixed_rate"],
        ZCIS_TERMS["accrual_years"],
        ZCIS_PAYMENT,
        NOMINAL_CURVE,
        pay_fixed=pay_fixed,
    )
    # |NPV| is about 3.8e3 per 1e6 notional; the two paths differ only by quad round-off.
    assert zcis == pytest.approx(expected_zcis, rel=1e-12, abs=1e-8)
    assert abs(zcis) > 1_000.0

    ratios = [
        jarrow_yildirim.jy_cpi_forward(0.0, end, 100.0, NOMINAL_CURVE, REAL_CURVE)
        / jarrow_yildirim.jy_cpi_forward(0.0, start, 100.0, NOMINAL_CURVE, REAL_CURVE)
        for start, end in YOY_PAIRS
    ]
    yoy = jarrow_yildirim.jy_yoy_value(
        notional,
        YOY_PAIRS,
        YOY_PAYMENTS,
        YOY_FIXED,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
        pay_fixed=pay_fixed,
    )
    expected_yoy = inflation.yoy_swap_npv(
        notional, ratios, YOY_PAYMENTS, YOY_FIXED, NOMINAL_CURVE, pay_fixed=pay_fixed
    )
    assert yoy == pytest.approx(expected_yoy, rel=1e-12, abs=1e-8)
    assert abs(yoy) > 100.0


def test_jy_swaps_match_nominal_money_market_monte_carlo() -> None:
    """Price both swaps as E[cash flow / B(payment)] on nominal-measure JY paths.

    ``simulate_jy_paths`` is independent of the payment-forward-measure algebra in
    ``jy_payment_forward_cpi`` / ``jy_expected_cpi_ratio`` (it discounts by the
    simulated bank account). Measured with seed 31, 60k paths, dt=1/16: ZCIS
    z=-0.77 (SE 9.1e-5), YoY z=-0.97 (SE 1.3e-4); seeds 32-34 gave |z| <= 0.46.
    The SE exceeds the JY adjustments themselves (-2.3e-5 ZCIS, -4.7e-5 YoY
    versus the zero-vol values), so this checks level and measure consistency,
    not the size of the convexity correction.
    """
    params = _params()
    zcis = jarrow_yildirim.jy_zcis_value(
        1.0,
        ZCIS_TERMS["start_index"],
        ZCIS_TERMS["fixed_rate"],
        ZCIS_TERMS["accrual_years"],
        0.0,
        ZCIS_TERMS["observation"],
        ZCIS_PAYMENT,
        100.0,
        NOMINAL_CURVE,
        REAL_CURVE,
        params,
    )
    yoy = jarrow_yildirim.jy_yoy_value(
        1.0, YOY_PAIRS, YOY_PAYMENTS, YOY_FIXED, 100.0, NOMINAL_CURVE, REAL_CURVE, params
    )

    steps_per_year = 16
    grid = np.linspace(0.0, 3.25, int(3.25 * steps_per_year) + 1)
    simulation = jarrow_yildirim.simulate_jy_paths(
        grid, 100.0, NOMINAL_CURVE, REAL_CURVE, params, n_paths=60_000, seed=31
    )

    def column(time: float) -> int:
        index = round(time * steps_per_year)
        assert grid[index] == pytest.approx(time, abs=1e-12)
        return index

    cpi = simulation.cpi
    bank = simulation.nominal_bank_accounts
    end_levels = cpi[:, column(ZCIS_TERMS["observation"])]
    fixed_growth = (1.0 + ZCIS_TERMS["fixed_rate"]) ** ZCIS_TERMS["accrual_years"]
    cashflows = end_levels / ZCIS_TERMS["start_index"] - fixed_growth
    # Pin the vectorised receive-inflation cash flow to the library convention.
    assert cashflows[0] == pytest.approx(
        inflation.zcis_cashflow(
            1.0,
            ZCIS_TERMS["start_index"],
            float(end_levels[0]),
            ZCIS_TERMS["fixed_rate"],
            ZCIS_TERMS["accrual_years"],
        ),
        rel=1e-10,
        abs=1e-14,
    )
    zcis_paths = cashflows / bank[:, column(ZCIS_PAYMENT)]
    yoy_paths = sum(
        (cpi[:, column(end)] / cpi[:, column(start)] - 1.0 - YOY_FIXED) / bank[:, column(payment)]
        for (start, end), payment in zip(YOY_PAIRS, YOY_PAYMENTS, strict=True)
    )
    for paths, analytic in ((zcis_paths, zcis), (yoy_paths, yoy)):
        standard_error = paths.std(ddof=1) / np.sqrt(len(paths))
        assert abs(paths.mean() - analytic) < 3.0 * standard_error


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
        simulation.nominal_bank_accounts[:, -1] * rates.discount_factor(2.0, NOMINAL_CURVE)
    )
    density_error = terminal_density.std(ddof=1) / np.sqrt(len(terminal_density))
    assert abs(terminal_density.mean() - 1.0) < 4.0 * density_error

    real_zcb = simulation.cpi[:, -1] / simulation.nominal_bank_accounts[:, -1]
    expected_real_zcb = 100.0 * rates.discount_factor(2.0, REAL_CURVE)
    real_error = real_zcb.std(ddof=1) / np.sqrt(len(real_zcb))
    assert abs(real_zcb.mean() - expected_real_zcb) < 4.0 * real_error

    index = len(grid) // 2
    hw_params = hull_white.HullWhiteParams(params.nominal_mean_reversion, params.nominal_volatility)
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
