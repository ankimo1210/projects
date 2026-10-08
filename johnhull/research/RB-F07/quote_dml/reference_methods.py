"""Independent scalar-bootstrap and density-integral quote-DML references.

This file imports neither hullkit nor its production teachers or Jacobians.
The fixed experiment has five decimal rate quotes, continuous zero pillars,
linear zero interpolation, annual swaps and a term-end-settled FRA. Risk
vectors are ordered spot first, then the five raw (not bp-scaled) quotes.
"""

from __future__ import annotations

from math import erfc, exp, isfinite, log, pi, sqrt

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq

PILLARS = (0.5, 1.0, 2.0, 3.0, 5.0)
SCHEDULES = ((0.5,), (0.5, 1.0), (1.0, 2.0), (1.0, 2.0, 3.0), (1.0, 2.0, 3.0, 4.0, 5.0))
COMPLEX_STEP = 1e-25


def _quotes(q):
    values = np.asarray(q, dtype=float)
    if values.shape != (5,) or not np.isfinite(values).all():
        raise ValueError("five finite decimal rate quotes are required")
    if np.any(1 + 0.5 * values[:2] <= 0):
        raise ValueError("deposit and FRA discount ratios must be positive")
    return values


def _contract(spot, maturity, strike, sigma):
    values = tuple(float(x) for x in (spot, maturity, strike, sigma))
    if any(not isfinite(x) or x <= 0 for x in values):
        raise ValueError("spot, maturity, strike and sigma must be finite and positive")
    return values


def _discount(times, zeros):
    """Own interpolation, preserving complex inputs for kernel differentiation."""
    times = np.asarray(times, dtype=float)
    return np.exp(-times * np.interp(times, PILLARS, zeros))


def _model_quotes(zeros):
    deposit_df = _discount(0.5, zeros)
    one_year_df = _discount(1.0, zeros)
    values = [(1 / deposit_df - 1) / 0.5, (deposit_df / one_year_df - 1) / 0.5]
    for schedule in SCHEDULES[2:]:
        dfs = _discount(schedule, zeros)
        values.append((1 - dfs[-1]) / np.sum(dfs))
    return np.asarray(values)


def _scalar_root(residual):
    """Bracket ordinary experiment curves, extending for valid negative rates."""
    lower, upper = -0.2, 1.0
    for _ in range(10):
        left, right = residual(lower), residual(upper)
        if not isfinite(left) or not isfinite(right):
            raise RuntimeError("nonfinite independent bootstrap residual")
        if left == 0:
            return lower
        if right == 0:
            return upper
        if np.signbit(left) != np.signbit(right):
            return brentq(residual, lower, upper, xtol=5e-16, rtol=1e-14)
        # Each successive instrument quote increases with its new zero pillar.
        if left > 0:
            lower *= 2
        else:
            upper *= 2
    raise RuntimeError("independent bootstrap could not bracket a positive-DF curve")


def bootstrap(q):
    """Fit the five zeros with sequential scalar brentq, without production code."""
    targets = _quotes(q)
    zeros = np.zeros(5)
    for index in range(5):

        def residual(zero, pillar_index=index):
            candidate = zeros.copy()
            candidate[pillar_index] = zero
            return float(_model_quotes(candidate)[pillar_index] - targets[pillar_index])

        zeros[index] = _scalar_root(residual)
    fitted = _model_quotes(zeros)
    if not np.allclose(fitted, targets, atol=5e-13, rtol=1e-11):
        raise RuntimeError("independent bootstrap residual exceeds numerical tolerance")
    return np.asarray(PILLARS), zeros


def _jacobian(zeros):
    columns = [
        np.imag(_model_quotes(zeros + 1j * COMPLEX_STEP * unit)) / COMPLEX_STEP
        for unit in np.eye(5)
    ]
    result = np.column_stack(columns)
    if not np.isfinite(result).all() or np.linalg.matrix_rank(result) != 5:
        raise ValueError("independent calibration Jacobian is singular")
    return result


def model_jacobian(q):
    """Return dm/dz from complex steps of this file's own model-quote equations."""
    return _jacobian(bootstrap(q)[1])


def discount(q, maturity):
    """Return the independently bootstrapped discount factor at a year time."""
    time = float(maturity)
    if not isfinite(time) or time < 0:
        raise ValueError("discount time must be finite and nonnegative")
    return float(_discount(time, bootstrap(q)[1]))


def _integrated_rate_gradient(zeros, maturity):
    loading = maturity * np.array([np.interp(maturity, PILLARS, e) for e in np.eye(5)])
    return np.linalg.solve(_jacobian(zeros).T, loading)


def integrated_rate_gradient(q, maturity):
    """Return d[-log P(0,T)]/dq in raw decimal quote coordinates."""
    time = float(maturity)
    if not isfinite(time) or time < 0:
        raise ValueError("discount time must be finite and nonnegative")
    return _integrated_rate_gradient(bootstrap(q)[1], time)


def _normal_density(value):
    return exp(-0.5 * value * value) / sqrt(2 * pi)


def _normal_cdf(value):
    return 0.5 * erfc(-value / sqrt(2))


def _digital_inputs(q, spot, maturity, strike, sigma):
    spot, maturity, strike, sigma = _contract(spot, maturity, strike, sigma)
    _, zeros = bootstrap(q)
    df = float(_discount(maturity, zeros))
    if not isfinite(df) or df <= 0:
        raise ValueError("digital requires a finite positive discount factor")
    root_variance = sigma * sqrt(maturity)
    integrated_rate = -log(df)
    d2 = (log(spot / strike) + integrated_rate - root_variance**2 / 2) / root_variance
    return spot, maturity, df, root_variance, d2, zeros


def digital_price(q, spot, maturity, *, strike=100.0, sigma=0.2):
    """Return the cash digital price using independent bootstrap and math.erfc."""
    _, _, df, _, d2, _ = _digital_inputs(q, spot, maturity, strike, sigma)
    return df * _normal_cdf(d2)


def digital_moments(q, spot, maturity, *, strike=100.0, sigma=0.2):
    """Integrate price, LRM means and second moments against the normal density.

    Quote score includes the discount derivative: -1 + Z/(sigma*sqrt(T)).
    The independent calibration Jacobian supplies the quote directions.
    Second moments are per path; standard errors still require a path count.
    """
    spot, maturity, df, v, d2, zeros = _digital_inputs(q, spot, maturity, strike, sigma)
    a_q = _integrated_rate_gradient(zeros, maturity)
    integrals = np.array(
        [
            quad(
                lambda z, power=power: z**power * _normal_density(z),
                -d2,
                np.inf,
                epsabs=1e-13,
                epsrel=1e-11,
            )[0]
            for power in range(3)
        ]
    )
    probability, first, second = integrals
    price = df * probability
    gradient = np.r_[df * first / (spot * v), df * (-probability + first / v) * a_q]
    second_moment = np.r_[
        df**2 * second / (spot**2 * v**2),
        df**2 * (probability - 2 * first / v + second / v**2) * a_q**2,
    ]
    return {
        "price": price,
        "g_quote": gradient,
        "lrm_second_moment": second_moment,
        "discount": df,
        "integrated_rate_gradient": a_q,
        "hit_probability": probability,
        "naive_pathwise_mean": np.r_[0.0, -price * a_q],
        "discount_omitted_mean": gradient + np.r_[0.0, price * a_q],
    }


def conditioning_moments(q, spot, maturity, *, strike=100.0, sigma=0.2, alpha=0.5):
    """Independently integrate conditional price, Greeks and second moments.

    Differentiation holds the intermediate Gaussian noise fixed. Therefore
    both earlier and later deterministic drift changes contribute to R(T).
    """
    fraction = float(alpha)
    if not isfinite(fraction) or not 0 <= fraction < 1:
        raise ValueError("conditioning alpha must lie in [0,1)")
    spot, maturity, df, v, d2, zeros = _digital_inputs(q, spot, maturity, strike, sigma)
    a_q = _integrated_rate_gradient(zeros, maturity)
    remaining_v = v * sqrt(1 - fraction)

    def terms(z):
        b = (v * d2 + v * sqrt(fraction) * z) / remaining_v
        cdf, density = _normal_cdf(b), _normal_density(b)
        return (
            df * cdf,
            df * density / (spot * remaining_v),
            df * (-cdf + density / remaining_v),
        )

    def integrate(index, power):
        return quad(
            lambda z: terms(z)[index] ** power * _normal_density(z),
            -np.inf,
            np.inf,
            epsabs=1e-13,
            epsrel=1e-11,
        )[0]

    price = integrate(0, 1)
    gradient = np.r_[integrate(1, 1), integrate(2, 1) * a_q]
    second_moment = np.r_[integrate(1, 2), integrate(2, 2) * a_q**2]
    return {"price": price, "g_quote": gradient, "second_moment": second_moment}


def _held_prices(zeros, spot, contract_quotes, notional):
    d_half, d_year = _discount(0.5, zeros), _discount(1.0, zeros)
    prices = [
        spot,
        notional * ((1 + contract_quotes[0] * 0.5) * d_half - 1),
        notional * ((1 + contract_quotes[1] * 0.5) * d_year - d_half),
    ]
    for index, schedule in enumerate(SCHEDULES[2:], start=2):
        dfs = _discount(schedule, zeros)
        prices.append(notional * (contract_quotes[index] * np.sum(dfs) + dfs[-1] - 1))
    return np.asarray(prices)


def _hedge_inputs(spot, contract_quotes, notional):
    spot, notional = float(spot), float(notional)
    coupons = np.asarray(contract_quotes, dtype=float)
    if not isfinite(spot) or spot <= 0 or not isfinite(notional) or notional <= 0:
        raise ValueError("spot and hedge notional must be finite and positive")
    if coupons.shape != (5,) or not np.isfinite(coupons).all():
        raise ValueError("five finite held contract coupons are required")
    return spot, coupons, notional


def held_prices(q, spot, contract_quotes, *, notional=1e6):
    """Price stock and five frozen-coupon contracts, FRA paid at its term end."""
    spot, coupons, notional = _hedge_inputs(spot, contract_quotes, notional)
    return _held_prices(bootstrap(q)[1], spot, coupons, notional)


def held_risk(q, spot, contract_quotes, *, notional=1e6):
    """Return B with spot/quote rows and stock/five-held-contract columns.

    Frozen-coupon cashflow derivatives and calibration Jacobian are both
    computed by complex steps of this reference's own equations. At par,
    the quote-risk block is diagonal; coupons remain fixed during shocks.
    """
    spot, coupons, notional = _hedge_inputs(spot, contract_quotes, notional)
    zeros = bootstrap(q)[1]
    grad_zeros = np.column_stack(
        [
            np.imag(_held_prices(zeros + 1j * COMPLEX_STEP * e, spot, coupons, notional))
            / COMPLEX_STEP
            for e in np.eye(5)
        ]
    )
    result = np.zeros((6, 6))
    result[0, 0] = 1
    result[1:] = np.linalg.solve(_jacobian(zeros).T, grad_zeros.T)
    return result
