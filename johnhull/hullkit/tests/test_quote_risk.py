"""RB-F07 closed forms, independent bootstrap and derivative invariance."""

from dataclasses import replace

import numpy as np
import pytest
from hullkit import _quote_risk as risk
from hullkit import rates, swaps
from scipy.optimize import brentq


def _quotes():
    return (
        risk.Quote("deposit", 0.03, (0.5,)),
        risk.Quote("fra", 0.032, (0.5, 1.0)),
        risk.Quote("swap", 0.033, (1.0, 2.0)),
        risk.Quote("swap", 0.0345, (1.0, 2.0, 3.0)),
        risk.Quote("swap", 0.036, (1.0, 2.0, 3.0, 4.0, 5.0)),
    )


def _discount(t, pillars, zeros, interpolation="zero_linear"):
    # Independent interpolation: no production weights or pricing functions.
    if interpolation == "zero_linear" or t <= pillars[0] or t >= pillars[-1]:
        return np.exp(-t * np.interp(t, pillars, zeros))
    return np.exp(-np.interp(t, pillars, pillars * zeros))


def _reference_quote(quote, pillars, zeros, interpolation):
    dfs = np.array([_discount(t, pillars, zeros, interpolation) for t in quote.times])
    if quote.kind == "deposit":
        return (1 / dfs[0] - 1) / quote.times[0]
    if quote.kind == "fra":
        return (dfs[0] / dfs[1] - 1) / (quote.times[1] - quote.times[0])
    if quote.kind == "bond":
        return np.dot(quote.cashflows, dfs)
    return (1 - dfs[-1]) / np.dot(np.diff((0.0, *quote.times)), dfs)


def _bootstrap(quotes, interpolation="zero_linear"):
    pillars = np.array([q.times[-1] for q in quotes])
    zeros = np.zeros(len(quotes))
    for i, quote in enumerate(quotes):

        def residual(z, index=i, instrument=quote):
            candidate = zeros.copy()
            candidate[index] = z
            return (
                _reference_quote(instrument, pillars, candidate, interpolation) - instrument.value
            )

        zeros[i] = brentq(residual, -0.2, 1.0, xtol=5e-16, rtol=1e-14)
    return pillars, zeros


def _portfolio(calibration):
    swap, swap_grad = risk.receiver_swap_value(calibration, 10_000_000, 0.032, (1, 2, 3, 4))
    bond, bond_grad = risk.cashflow_value(calibration, (1.5,), (-3_000_000,))
    return swap + bond, swap_grad + bond_grad


def _reference_portfolio(quotes, interpolation="zero_linear"):
    pillars, zeros = _bootstrap(quotes, interpolation)
    return _reference_portfolio_curve(pillars, zeros, interpolation)


def _reference_portfolio_curve(pillars, zeros, interpolation="zero_linear"):
    dfs = np.array([_discount(t, pillars, zeros, interpolation) for t in (1, 2, 3, 4)])
    return 10_000_000 * (0.032 * dfs.sum() + dfs[-1] - 1) - 3_000_000 * _discount(
        1.5, pillars, zeros, interpolation
    )


def _bump_risk(quotes, width, interpolation="zero_linear"):
    values = []
    for i, quote in enumerate(quotes):
        up, down = list(quotes), list(quotes)
        up[i] = replace(quote, value=quote.value + width)
        down[i] = replace(quote, value=quote.value - width)
        values.append(
            (_reference_portfolio(up, interpolation) - _reference_portfolio(down, interpolation))
            / (2 * width)
            * 1e-4
        )
    return np.array(values)


def test_hand_calibration_and_quote_risk_against_closed_form_discount_factors():
    quotes = (risk.Quote("deposit", 0.03, (1,)), risk.Quote("swap", 0.035, (1, 2)))
    calibration = risk.calibrate(quotes)
    p1 = 1 / 1.03
    p2 = (1 - 0.035 * p1) / 1.035
    dp1 = -(p1**2)
    dp2_deposit = -0.035 * dp1 / 1.035
    dp2_swap = -(1 + p1) / 1.035**2
    dz_dq = np.array([[p1, 0], [-0.5 * dp2_deposit / p2, -0.5 * dp2_swap / p2]])
    # z(1.5)=(z(1)+z(2))/2: P(1.5)=P(1)**.75 * P(2)**.375.
    pv = 1_000_000 * p1**0.75 * p2**0.375
    expected = (
        pv * np.array([0.75 * dp1 / p1 + 0.375 * dp2_deposit / p2, 0.375 * dp2_swap / p2]) * 1e-4
    )
    value, gradient = risk.cashflow_value(calibration, (1.5,), (1_000_000,))
    result = risk.quote_sensitivity(calibration, gradient)
    np.testing.assert_allclose(
        calibration.zeros, -np.log([p1, p2]) / [1, 2], rtol=1e-12, atol=2e-14
    )
    np.testing.assert_allclose(
        np.linalg.solve(calibration.jacobian, np.eye(2)), dz_dq, rtol=1e-12, atol=2e-14
    )
    assert value == pytest.approx(pv, rel=1e-12, abs=5e-8)
    np.testing.assert_allclose(result.per_step, expected, rtol=1e-12, atol=2e-8)
    assert result.per_step == pytest.approx([-68.17998013, -70.45357276], abs=1e-8)
    assert result.solve_relative_residual < 1e-14


def test_newton_matches_sequential_brentq_and_public_swap_price_oracles():
    quotes = _quotes()
    calibration = risk.calibrate(quotes)
    pillars, zeros = _bootstrap(quotes)
    np.testing.assert_allclose(calibration.zeros, zeros, rtol=1e-12, atol=2e-14)
    for quote in quotes[2:]:
        assert swaps.swap_rate(quote.times, (pillars, calibration.zeros)) == pytest.approx(
            quote.value, abs=2e-14
        )
    value, gradient = _portfolio(calibration)
    oracle = swaps.irs_value_fras(
        10_000_000, 0.032, (1, 2, 3, 4), (pillars, zeros)
    ) - 3_000_000 * rates.discount_factor(1.5, (pillars, zeros))
    assert value == pytest.approx(oracle, rel=1e-12, abs=5e-8)
    assert value == pytest.approx(-2_980_843.07, abs=0.01)
    result = risk.quote_sensitivity(calibration, gradient)
    assert gradient[0] == pytest.approx(0, abs=2e-8)
    assert result.per_step[0] == pytest.approx(106.30, abs=0.01)
    assert result.per_step.sum() == pytest.approx(-3233.038188, abs=1e-6)
    assert calibration.scaled_residual_norm < 1e-10
    assert calibration.rank == 5 and not calibration.warnings


def test_rebootstrap_central_difference_has_quadratic_truncation_error():
    quotes = _quotes()
    _, gradient = _portfolio(calibration := risk.calibrate(quotes))
    expected = risk.quote_sensitivity(calibration, gradient).per_step
    errors = [np.max(np.abs(_bump_risk(quotes, width) - expected)) for width in (1e-2, 1e-3)]
    assert 60 < errors[0] / errors[1] < 150
    np.testing.assert_allclose(_bump_risk(quotes, 1e-5), expected, rtol=1e-8, atol=2e-6)


def test_zero_and_log_discount_coordinates_preserve_quote_risk():
    _, gradient = _portfolio(calibration := risk.calibrate(_quotes()))
    logdf = -calibration.times * calibration.zeros
    logdf_gradient = np.empty(5)
    logdf_jacobian = np.empty((5, 5))
    for i in range(5):
        shifted = logdf.astype(complex)
        shifted[i] += 1e-25j
        shifted_zeros = -shifted / calibration.times
        logdf_gradient[i] = (
            _reference_portfolio_curve(calibration.times, shifted_zeros).imag / 1e-25
        )
        logdf_jacobian[:, i] = (
            np.array(
                [
                    _reference_quote(q, calibration.times, shifted_zeros, "zero_linear")
                    for q in _quotes()
                ]
            ).imag
            / 1e-25
        )
    expected = np.linalg.solve(logdf_jacobian.T, logdf_gradient)
    np.testing.assert_allclose(
        risk.quote_sensitivity(calibration, gradient).per_unit, expected, rtol=1e-12, atol=2e-4
    )
    assert not np.allclose(gradient, logdf_gradient, rtol=1e-6, atol=1)


def test_pv_residual_scaling_preserves_quote_risk():
    quotes = _quotes()
    _, gradient = _portfolio(calibration := risk.calibrate(quotes))

    def dfs(times):
        return np.array([_discount(t, calibration.times, calibration.zeros) for t in times])

    scales = np.array(
        [
            0.5 * dfs((0.5,))[0],
            0.5 * dfs((1,))[0],
            *[np.dot(np.diff((0.0, *q.times)), dfs(q.times)) for q in quotes[2:]],
        ]
    )
    pv_jacobian = np.empty((5, 5))
    for i in range(5):
        shifted = calibration.zeros.astype(complex)
        shifted[i] += 1e-25j
        for row, quote in enumerate(quotes):
            discount = np.array([_discount(t, calibration.times, shifted) for t in quote.times])
            scale = (
                (quote.times[-1] - (quote.times[0] if quote.kind == "fra" else 0)) * discount[-1]
                if quote.kind in {"deposit", "fra"}
                else np.dot(np.diff((0.0, *quote.times)), discount)
            )
            residual = scale * (
                _reference_quote(quote, calibration.times, shifted, "zero_linear") - quote.value
            )
            pv_jacobian[row, i] = residual.imag / 1e-25
    expected = scales * np.linalg.solve(pv_jacobian.T, gradient)
    np.testing.assert_allclose(
        risk.quote_sensitivity(calibration, gradient).per_unit, expected, rtol=1e-12, atol=2e-4
    )


def test_parallel_shift_matches_sum_after_independent_recalibration():
    quotes = _quotes()
    _, gradient = _portfolio(calibration := risk.calibrate(quotes))
    expected = risk.quote_sensitivity(calibration, gradient).per_step.sum()
    h = 1e-6
    up = [replace(q, value=q.value + h) for q in quotes]
    down = [replace(q, value=q.value - h) for q in quotes]
    observed = (_reference_portfolio(up) - _reference_portfolio(down)) / (2 * h) * 1e-4
    assert observed == pytest.approx(expected, rel=1e-9, abs=2e-6)


def test_each_interpolation_matches_its_rebootstrap_and_changes_risk():
    results = []
    for interpolation in ("zero_linear", "logdf_linear"):
        calibration = risk.calibrate(_quotes(), interpolation=interpolation)
        _, reference_zeros = _bootstrap(_quotes(), interpolation)
        np.testing.assert_allclose(calibration.zeros, reference_zeros, rtol=1e-12, atol=2e-14)
        value, gradient = _portfolio(calibration)
        result = risk.quote_sensitivity(calibration, gradient)
        np.testing.assert_allclose(
            _bump_risk(_quotes(), 1e-5, interpolation), result.per_step, rtol=1e-8, atol=2e-6
        )
        results.append((value, result.per_step))
    assert results[1][0] == pytest.approx(-2_986_256.89, abs=0.01)
    assert abs(results[0][0] - results[1][0]) > 5000
    assert np.max(np.abs(results[0][1] - results[1][1])) > 400


def test_weak_coverage_warns_without_rejecting_an_invertible_curve():
    quotes = (*_quotes()[:-1], risk.Quote("swap", 0.036, (1, 2, 3, 3.1)))
    calibration = risk.calibrate(quotes, pillar_times=(0.5, 1, 2, 3, 5))
    assert calibration.amplification > 10 and calibration.warnings
    assert calibration.rank == 5 and calibration.scaled_residual_norm < 1e-10
    value, gradient = _portfolio(calibration)
    assert np.isfinite(value)
    assert np.isfinite(risk.quote_sensitivity(calibration, gradient).per_step).all()


@pytest.mark.parametrize("last", [3.0, np.nextafter(3.0, 4.0)])
def test_unresolved_pillar_stops_instead_of_reporting_risk(last):
    schedule = (1, 2, 3) if last == 3 else (1, 2, 3, last)
    quotes = (*_quotes()[:-1], risk.Quote("swap", 0.0345, schedule))
    with pytest.raises(ValueError, match=r"rank|singular"):
        risk.calibrate(quotes, pillar_times=(0.5, 1, 2, 3, 5))


def test_hull_table_4_3_and_risk_in_currency_per_price_unit():
    instruments = [(0.25, 0, 99.6), (0.5, 0, 99.0), (1, 0, 97.8), (1.5, 4, 102.5), (2, 5, 105)]
    quotes = []
    for maturity, coupon, price in instruments:
        times = np.arange(maturity, 0, -0.5)[::-1] if coupon else np.array([maturity])
        cashflows = np.full(times.size, coupon / 2)
        cashflows[-1] += 100
        quotes.append(risk.Quote("bond", price, tuple(times), tuple(cashflows)))
    calibration = risk.calibrate(quotes)
    _, zeros = rates.bootstrap_zero_curve(instruments)
    np.testing.assert_allclose(calibration.zeros, zeros, rtol=1e-12, atol=2e-14)
    _, gradient = risk.cashflow_value(calibration, (1.75,), (1_000_000,))
    result = risk.quote_sensitivity(calibration, gradient)
    np.testing.assert_allclose(
        result.per_step, [0, -218.967, -218.967, 5574.455, 4299.115], atol=0.001, rtol=0
    )
    assert set(result.units) == {"currency / price 1.00"}
    for i, (maturity, coupon, price) in enumerate(instruments):
        up, down = list(instruments), list(instruments)
        up[i] = maturity, coupon, price + 1e-3
        down[i] = maturity, coupon, price - 1e-3
        observed = (
            (
                rates.discount_factor(1.75, rates.bootstrap_zero_curve(up))
                - rates.discount_factor(1.75, rates.bootstrap_zero_curve(down))
            )
            * 1_000_000
            / 2e-3
        )
        assert result.per_step[i] == pytest.approx(observed, rel=1e-8, abs=2e-6)


@pytest.mark.parametrize("interpolation", ["zero_linear", "logdf_linear"])
def test_four_instrument_jacobians_match_complex_step(interpolation):
    quotes = (*_quotes(), risk.Quote("bond", 102, (2, 4, 6), (2, 2, 102)))
    times = np.array([q.times[-1] for q in quotes])
    zeros = np.array([0.028, 0.03, 0.032, 0.034, 0.036, 0.037])
    _, jacobian = risk.model_quotes(quotes, times, zeros, interpolation=interpolation)
    observed = np.empty_like(jacobian)
    for i in range(6):
        perturbed = zeros.astype(complex)
        perturbed[i] += 1e-25j
        values, _ = risk.model_quotes(quotes, times, perturbed, interpolation=interpolation)
        observed[:, i] = values.imag / 1e-25
    np.testing.assert_allclose(jacobian, observed, rtol=1e-12, atol=2e-12)


def test_rate_step_units_and_approximate_gradient_label_are_explicit():
    _, gradient = _portfolio(calibration := risk.calibrate(_quotes()))
    result = risk.quote_sensitivity(calibration, gradient, gradient_method="finite_difference")
    assert result.gradient_method == "finite_difference"
    assert set(result.units) == {"currency / quote 1bp"}
    np.testing.assert_allclose(result.per_step, result.per_unit * 1e-4, rtol=1e-12, atol=2e-8)


@pytest.mark.parametrize(
    "kind,value,times,cashflows",
    [
        ("deposit", 0.03, (-1,), ()),
        ("deposit", -2, (1,), ()),
        ("fra", 0.03, (1, 1), ()),
        ("swap", 0.03, (), ()),
        ("bond", 100, (1, 2), (100,)),
        ("deposit", np.nan, (1,), ()),
    ],
)
def test_invalid_mathematical_quotes_are_rejected(kind, value, times, cashflows):
    with pytest.raises(ValueError):
        risk.Quote(kind, value, times, cashflows)


def test_nonconvergence_never_returns_an_unfinished_curve():
    with pytest.raises(RuntimeError, match="converg"):
        risk.calibrate(_quotes(), max_iterations=1)


def test_inconsistent_dimensions_cannot_return_plausible_risk():
    with pytest.raises(ValueError):
        risk.calibrate(_quotes(), pillar_times=(1, 2))
    calibration = risk.calibrate(_quotes())
    with pytest.raises(ValueError):
        risk.quote_sensitivity(calibration, np.ones(4))
    with pytest.raises(ValueError):
        risk.quote_sensitivity(calibration, np.full(5, np.nan))


def test_quote_order_is_preserved_with_sorted_pillars():
    quotes = _quotes()
    permutation = (4, 1, 0, 3, 2)
    calibration = risk.calibrate([quotes[i] for i in permutation])
    _, gradient = _portfolio(calibration)
    expected = _bump_risk(quotes, 1e-5)[list(permutation)]
    np.testing.assert_allclose(
        risk.quote_sensitivity(calibration, gradient).per_step, expected, rtol=1e-8, atol=2e-6
    )


def test_mixed_price_and_rate_quotes_keep_distinct_step_units():
    quotes = (*_quotes(), risk.Quote("bond", 102, (2, 4, 6), (2, 2, 102)))
    calibration = risk.calibrate(quotes)
    _, gradient = risk.cashflow_value(calibration, (6.25,), (1_000_000,))
    result = risk.quote_sensitivity(calibration, gradient)
    assert result.units == ("currency / quote 1bp",) * 5 + ("currency / price 1.00",)
    for i, quote in enumerate(quotes):
        width = 1e-3 if quote.kind == "bond" else 1e-5
        up, down = list(quotes), list(quotes)
        up[i] = replace(quote, value=quote.value + width)
        down[i] = replace(quote, value=quote.value - width)
        pu, zu = _bootstrap(up)
        pd, zd = _bootstrap(down)
        observed = (
            (_discount(6.25, pu, zu) - _discount(6.25, pd, zd))
            * 1_000_000
            / (2 * width)
            * result.steps[i]
        )
        assert result.per_step[i] == pytest.approx(observed, rel=1e-8, abs=2e-6)
