"""Independent density integration and log-price PDE for discrete barriers.

The contract is a dividend-free GBM up-and-out call, zero rebate, fixed K/H,
and monitoring at 0,T/m,...,T. A touch (S >= H) knocks out. These references
do not import the financial teacher or any hullkit implementation.
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import quad
from scipy.interpolate import CubicSpline
from scipy.linalg import solve_banded


def _contract(spot, maturity, strike, barrier, rate, sigma):
    stock = np.asarray(spot, dtype=float)
    values = np.asarray([maturity, strike, barrier, rate, sigma], dtype=float)
    if not np.isfinite(stock).all() or np.any(stock <= 0) or not np.isfinite(values).all():
        raise ValueError("finite positive spots and finite contract parameters required")
    if maturity <= 0 or strike <= 0 or barrier <= strike or sigma <= 0:
        raise ValueError("positive maturity/strike/volatility and barrier > strike required")
    return stock


def one_monitor_integral(
    spot,
    maturity,
    *,
    strike=100.0,
    barrier=120.0,
    rate=0.03,
    sigma=0.2,
    bump=1e-3,
    epsabs=1e-11,
    epsrel=1e-11,
):
    """Integrate the terminal normal density; Delta is a fixed-contract bump.

    The integral is over log(K) < log(S_T) < log(H), with cash discount
    exp(-rT). No closed-form option/CDF formula is called. Two central bump
    widths are retained; quadrature and bump differences are separate.
    At the initial contact S=H, price is zero and ordinary Delta is undefined.
    """
    stock = _contract(spot, maturity, strike, barrier, rate, sigma)
    if stock.ndim or not np.isfinite(bump) or bump <= 0:
        raise ValueError("a scalar spot and positive finite bump are required")
    stock = float(stock)
    if stock >= barrier:
        return {
            "price": 0.0,
            "delta": np.nan if stock == barrier else 0.0,
            "quadrature_price_error": 0.0,
            "quadrature_delta_error": 0.0,
            "delta_bump_difference": np.nan if stock == barrier else 0.0,
            "bump": None,
        }
    if stock - bump <= 0 or stock + bump >= barrier:
        raise ValueError("both fixed-contract bump spots must remain strictly below H")
    deviation = sigma * np.sqrt(maturity)
    discount = np.exp(-rate * maturity)
    lower, upper = np.log(strike), np.log(barrier)

    def integrate(value):
        mean = np.log(value) + (rate - 0.5 * sigma * sigma) * maturity

        def integrand(log_terminal):
            normal = (log_terminal - mean) / deviation
            density = np.exp(-0.5 * normal * normal) / (deviation * np.sqrt(2 * np.pi))
            return discount * (np.exp(log_terminal) - strike) * density

        return quad(integrand, lower, upper, epsabs=epsabs, epsrel=epsrel)

    price, error = integrate(stock)
    high, low = integrate(stock + bump), integrate(stock - bump)
    half_high, half_low = integrate(stock + bump / 2), integrate(stock - bump / 2)
    coarse = (high[0] - low[0]) / (2 * bump)
    fine = (half_high[0] - half_low[0]) / bump
    return {
        "price": price,
        "delta": fine,
        "delta_coarse": coarse,
        "quadrature_price_error": error,
        "quadrature_delta_error": (half_high[1] + half_low[1]) / bump,
        "delta_bump_difference": abs(fine - coarse),
        "bump": bump / 2,
    }


def pde_reference(
    spot,
    maturity,
    *,
    monitors=12,
    strike=100.0,
    barrier=120.0,
    rate=0.03,
    sigma=0.2,
    space_nodes=1200,
    steps_per_monitor=32,
    log_half_width=1.5,
    barrier_phase=0.5,
    bump=1e-3,
):
    """Solve a log-price CN PDE, killing only at the specified monitoring dates.

    Ito on x=log(S) gives dx=(r-sigma²/2)dt+sigma dW. Consequently the
    discounted backward generator is (sigma²/2)d_xx+(r-sigma²/2)d_x-r.
    Central differences approximate that generator. Each monitoring interval
    has exactly steps_per_monitor time steps, with the first two replaced by
    four implicit half steps (Rannacher damping after every new jump).

    Both remote boundaries are zero, and H lies inside the domain, not at an
    absorbing PDE boundary. At barrier_phase=.5 H is between two nodes: the
    quadrature implicit in the grid sees the monitor jump at a cell midpoint.
    barrier_phase=0 deliberately exposes the first-order node-jump bias.
    No value clipping is applied. Domain/space/time/phase convergence must be
    checked separately before regarding a result as a numerical reference.

    The final grid is the pre-t0 continuation. Initial KO is applied only to
    queried spots, retaining the generally positive left limit at H. Delta
    bumps the same interpolated price with fixed K/H/T/m and stays below H.
    """
    stock = _contract(spot, maturity, strike, barrier, rate, sigma)
    if (
        int(monitors) != monitors
        or monitors < 1
        or int(space_nodes) != space_nodes
        or space_nodes < 20
        or space_nodes % 2
        or int(steps_per_monitor) != steps_per_monitor
        or steps_per_monitor < 2
    ):
        raise ValueError(
            "positive integer monitoring/steps and an even spatial interval count required"
        )
    if (
        not np.isfinite([log_half_width, barrier_phase, bump]).all()
        or log_half_width <= 0
        or not 0 <= barrier_phase < 1
        or bump <= 0
    ):
        raise ValueError("positive domain/bump and barrier_phase in [0,1) required")
    monitors, space_nodes, steps_per_monitor = (
        int(monitors),
        int(space_nodes),
        int(steps_per_monitor),
    )
    dx = 2 * log_half_width / space_nodes
    log_h = np.log(barrier)
    relative = (np.arange(space_nodes + 1) - space_nodes // 2 + barrier_phase) * dx
    grid = log_h + relative
    living = relative < 0
    if np.log(strike) <= grid[0]:
        raise ValueError("lower remote boundary must be below strike")
    active = stock < barrier
    if np.any(np.log(stock[active]) <= grid[0]):
        raise ValueError("queried living spots must lie inside the remote PDE domain")
    values = np.maximum(np.exp(grid) - strike, 0.0) * living
    values[[0, -1]] = 0.0
    drift = rate - 0.5 * sigma * sigma
    below = 0.5 * sigma * sigma / dx**2 - 0.5 * drift / dx
    diagonal = -sigma * sigma / dx**2 - rate
    above = 0.5 * sigma * sigma / dx**2 + 0.5 * drift / dx
    dt = maturity / (monitors * steps_per_monitor)
    minimum = float(values.min())
    matrices = {}

    def advance(current, step, theta):
        key = step, theta
        if key not in matrices:
            band = np.empty((3, space_nodes - 1))
            band[0] = -theta * step * above
            band[0, 0] = 0.0
            band[1] = 1 - theta * step * diagonal
            band[2] = -theta * step * below
            band[2, -1] = 0.0
            matrices[key] = band
        rhs = (
            (1 + (1 - theta) * step * diagonal) * current[1:-1]
            + (1 - theta) * step * below * current[:-2]
            + (1 - theta) * step * above * current[2:]
        )
        result = np.zeros_like(current)
        result[1:-1] = solve_banded((1, 1), matrices[key], rhs, check_finite=False)
        return result

    for interval in range(monitors):
        for index in range(steps_per_monitor):
            if index < 2:
                values = advance(values, dt / 2, 1.0)
                minimum = min(minimum, float(values.min()))
                values = advance(values, dt / 2, 1.0)
            else:
                values = advance(values, dt, 0.5)
            minimum = min(minimum, float(values.min()))
        if interval < monitors - 1:
            values[~living] = 0.0
    interpolator = CubicSpline(grid, values, extrapolate=False)
    query = np.log(stock)
    prices = np.where(active, interpolator(query), 0.0)
    widths = np.minimum(bump, np.minimum(stock / 4, np.maximum(barrier - stock, 0) / 4))
    safe_width = np.where(active, widths, bump)
    deltas = (
        interpolator(np.log(stock + safe_width)) - interpolator(np.log(stock - safe_width))
    ) / (2 * safe_width)
    deltas = np.where(active, deltas, np.where(stock == barrier, np.nan, 0.0))
    spline_delta = np.where(
        active, interpolator(query, 1) / stock, np.where(stock == barrier, np.nan, 0.0)
    )
    if stock.ndim == 0:
        prices, deltas, spline_delta = float(prices), float(deltas), float(spline_delta)
    return {
        "price": prices,
        "delta": deltas,
        "spline_delta": spline_delta,
        "x_grid": grid,
        "continuation_grid": values,
        "metadata": {
            "monitor_times": np.linspace(0.0, maturity, monitors + 1),
            "monitoring_count": monitors + 1,
            "space_intervals": space_nodes,
            "steps_per_monitor": steps_per_monitor,
            "dt": dt,
            "dx": dx,
            "log_lower": float(grid[0]),
            "log_upper": float(grid[-1]),
            "barrier_phase": barrier_phase,
            "log_drift": drift,
            "cash_discount_rate": rate,
            "remote_boundary": "zero at both ends",
            "minimum_unclipped_value": minimum,
            "rannacher": "two CN steps replaced by four implicit half steps after each monitor jump",
            "t0_kill": "query only; final continuation grid is not killed",
            "delta_bump_max": bump,
        },
    }
