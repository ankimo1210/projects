"""Private frozen-contract quote hedges for the RB-F07 DML comparison.

The six hedges are one stock unit and receive-fixed deposit, term-end FRA,
2/3/5-year annual swaps, each rate contract with its declared notional.
Coupons are the center market's par quotes and stay fixed during shocks.
Risk rows are spot followed by five raw decimal quote rates. This module
does not advance time, generate shocks or simulate a self-financing strategy.
"""

from __future__ import annotations

import numpy as np

from . import _quote_risk as risk

RISK_STEPS = np.array([1.0, 1e-4, 1e-4, 1e-4, 1e-4, 1e-4])


def _held_inputs(spot, contract_quotes, notional):
    coupons = np.asarray(contract_quotes, dtype=float)
    if coupons.shape != (5,) or not np.isfinite(coupons).all():
        raise ValueError("five finite held-contract coupons are required")
    spot, notional = float(spot), float(notional)
    if not np.isfinite(spot) or spot <= 0 or not np.isfinite(notional) or notional <= 0:
        raise ValueError("spot and hedge notional must be finite and positive")
    return spot, coupons, notional


def _cashflows(coupons, notional):
    """Fixed cashflows and initial constants, including term-end FRA settlement."""
    contracts = [
        ((0.5,), (notional * (1 + coupons[0] * 0.5),), -notional),
        ((0.5, 1.0), (-notional, notional * (1 + coupons[1] * 0.5)), 0.0),
    ]
    for coupon, maturity in zip(coupons[2:], (2, 3, 5), strict=True):
        times = tuple(float(t) for t in range(1, maturity + 1))
        flows = np.full(maturity, notional * coupon)
        flows[-1] += notional
        contracts.append((times, flows, -notional))
    return contracts


def held_prices(market, spot, contract_quotes, *, notional=1e6):
    """Price stock and fixed-coupon contracts without resetting shocked coupons.

    Returns prices in stock/deposit/FRA/swap2/swap3/swap5 order. The FRA
    pays its cashflow at t=1; it is not the advance-settled FRA convention.
    Annual swap floating legs are valued at reset on the single curve.
    """
    spot, coupons, notional = _held_inputs(spot, contract_quotes, notional)
    values = [spot]
    for times, flows, constant in _cashflows(coupons, notional):
        value, _ = risk.cashflow_value(market.calibration, times, flows)
        values.append(value + constant)
    return np.asarray(values)


def held_risk(market, spot, contract_quotes, *, notional=1e6):
    """Return a 6x6 risk matrix with spot/quote rows and held-contract columns.

    Fixed-cashflow zero gradients are transformed by the calibration adjoint.
    No price bump or coupon derivative is used. At the coupon's par market,
    each rate hedge has only its own quote bucket; off-par coupons can have
    cross-bucket risk. Derivatives are raw rates, before the 1bp display step.
    """
    _, coupons, notional = _held_inputs(spot, contract_quotes, notional)
    matrix = np.zeros((6, 6))
    matrix[0, 0] = 1.0
    for column, (times, flows, _) in enumerate(_cashflows(coupons, notional), start=1):
        _, gradient = risk.cashflow_value(market.calibration, times, flows)
        matrix[1:, column] = risk.quote_sensitivity(market.calibration, gradient).per_unit
    return matrix


def _matrix(B):
    matrix = np.asarray(B, dtype=float)
    if matrix.shape != (6, 6) or not np.isfinite(matrix).all():
        raise ValueError("finite 6x6 spot/quote-by-hedge matrix required")
    return matrix


def _vector(values, name):
    result = np.asarray(values, dtype=float)
    if result.shape != (6,) or not np.isfinite(result).all():
        raise ValueError(f"six finite {name} values required")
    return result


def solve_hedge(B, g_quote):
    """Solve B h = -g with spot/1bp row units and explicit numerical rank checks.

    h contains shares and numbers of contracts at the declared rate notional.
    Rank failure is rejected, without pseudoinverse, ridge or condition-number
    cutoff. Multiplying B and g by the same row units preserves quantities.
    """
    matrix, gradient = _matrix(B), _vector(g_quote, "spot/quote Greek")
    normalized = matrix * RISK_STEPS[:, None]
    singular = np.linalg.svd(normalized, compute_uv=False)
    threshold = normalized.shape[0] * np.finfo(float).eps * singular[0]
    if np.sum(singular > threshold) != 6:
        raise ValueError("normalized hedge matrix is numerically rank deficient")
    try:
        quantities = np.linalg.solve(normalized, -gradient * RISK_STEPS)
    except np.linalg.LinAlgError as exc:
        raise ValueError("singular normalized hedge solve") from exc
    if not np.isfinite(quantities).all():
        raise ValueError("hedge solve produced nonfinite quantities")
    return quantities


def entry_cost(h, B, spot, *, rate_halfspread_bp, stock_halfspread_bp):
    """Return educational entry cost, separate from shock revaluation residual.

    Rate cost is absolute own-bucket PV01 times its halfspread in bp and
    absolute contract quantity. Stock cost is spot times halfspread in bp
    times absolute shares. These spreads are stress inputs, not market fits.
    """
    quantities, matrix = _vector(h, "hedge quantity"), _matrix(B)
    spot = float(spot)
    spreads = np.asarray([rate_halfspread_bp, stock_halfspread_bp], dtype=float)
    if not np.isfinite(spot) or spot <= 0:
        raise ValueError("positive finite spot required for stock entry cost")
    if not np.isfinite(spreads).all() or np.any(spreads < 0):
        raise ValueError("finite nonnegative halfspreads in bp required")
    unit_costs = np.r_[spot * spreads[1] * 1e-4, np.abs(np.diag(matrix)[1:]) * 1e-4 * spreads[0]]
    return float(np.abs(quantities) @ unit_costs)
