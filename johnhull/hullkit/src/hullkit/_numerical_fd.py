"""Private Hull21.8 uniform-S/log-S grids and numerical diagnostics.

American prices use post-step exercise projection, not an exact LCP solver.
``obstacle='source'`` reproduces Hull's comparison with K-S (or S-K), which
allows negative out-of-money prices on an unstable explicit grid. Ordinary
pricing projects against nonnegative payoff; the raw continuation and signed
transition weights remain available so instability is never hidden.
"""

import numpy as np
from scipy.linalg import solve_banded

from . import bsm


def fd_grid(
    spot,
    strike,
    rate,
    vol,
    maturity,
    space_steps,
    time_steps,
    *,
    s_max,
    s_min=None,
    space="spot",
    method="implicit",
    kind="call",
    american=False,
    yield_rate=0.0,
    obstacle="payoff",
):
    """Return the whole grid, with rows in increasing calendar time.

    On a spot grid the lower boundary is zero; on a log grid ``s_min`` is
    positive. Log endpoints use asymptotic vanilla boundary values, so domain
    refinement must be checked separately from spatial/time refinement.
    ``price`` interpolates in the grid coordinate; Greeks name their actual
    node rather than pretending the nearest node is the requested spot.

    Hull's explicit discount is 1/(1+r*dt), not exp(-r*dt). The CN scheme uses
    the average full PDE operator. Hopscotch alternates explicit/implicit node
    colors at each time level, applying exercise at each completed node.
    ``weights_nonnegative`` reports positivity of the explicit stencil only;
    it is not a general stability certificate for every scheme or grid.
    """
    data = np.asarray([spot, strike, rate, vol, maturity, s_max, yield_rate], dtype=float)
    if not np.isfinite(data).all() or spot < 0 or strike <= 0 or vol < 0 or maturity <= 0:
        raise ValueError("finite inputs, nonnegative spot/vol, positive strike/maturity required")
    if any(n < 1 or int(n) != n for n in (space_steps, time_steps)) or space_steps < 2:
        raise ValueError("space_steps >= 2 and time_steps >= 1 must be integers")
    if s_max <= max(spot, strike):
        raise ValueError("s_max must exceed spot and strike")
    if space not in ("spot", "log") or method not in ("implicit", "explicit", "cn", "hopscotch"):
        raise ValueError("unknown grid space or finite difference method")
    if kind not in ("call", "put") or obstacle not in ("payoff", "source"):
        raise ValueError("unknown option kind or exercise obstacle")
    m, n = int(space_steps), int(time_steps)
    dt = maturity / n
    if method in ("explicit", "hopscotch") and 1 + rate * dt <= 0:
        raise ValueError("explicit rational discount denominator must be positive")
    if space == "spot":
        if s_min not in (None, 0):
            raise ValueError("spot grid lower boundary must be zero")
        coordinate = np.linspace(0, s_max, m + 1)
        stock = coordinate.copy()
        j = np.arange(1, m)
        diffusion = vol**2 * j**2 / 2
        drift = (rate - yield_rate) * j / 2
        x_spot = spot
    else:
        s_min = spot / 100 if s_min is None else s_min
        if not np.isfinite(s_min) or not 0 < s_min < spot:
            raise ValueError("log grid requires 0 < s_min < spot")
        coordinate = np.linspace(np.log(s_min), np.log(s_max), m + 1)
        stock = np.exp(coordinate)
        dx = coordinate[1] - coordinate[0]
        diffusion = np.full(m - 1, vol**2 / (2 * dx**2))
        drift = np.full(m - 1, (rate - yield_rate - vol**2 / 2) / (2 * dx))
        x_spot = np.log(spot)
    lo, di, hi = diffusion - drift, -2 * diffusion, diffusion + drift
    weights = np.column_stack((dt * lo, 1 + dt * di, dt * hi))
    signed_intrinsic = stock - strike if kind == "call" else strike - stock
    payoff = np.maximum(signed_intrinsic, 0)
    exercise = signed_intrinsic if obstacle == "source" else payoff
    values = np.empty((n + 1, m + 1))
    continuation = np.empty_like(values)
    values[-1] = continuation[-1] = payoff

    theta = 0.5 if method == "cn" else 1.0
    band = np.zeros((3, m - 1))
    band[0, 1:] = -theta * dt * hi[:-1]
    band[1] = 1 - theta * dt * (di - rate)
    band[2, :-1] = -theta * dt * lo[1:]
    for i in range(n - 1, -1, -1):
        tau = (n - i) * dt
        pv_stock = stock * np.exp(-yield_rate * tau)
        pv_strike = strike * np.exp(-rate * tau)
        low = 0 if kind == "call" else max(pv_strike - pv_stock[0], 0)
        high = max(pv_stock[-1] - pv_strike, 0) if kind == "call" else 0
        if american:
            low, high = max(low, payoff[0]), max(high, payoff[-1])
        future = values[i + 1]
        current = np.empty(m + 1)
        current[0], current[-1] = low, high
        if method in ("implicit", "cn"):
            rhs = future[1:-1] + (1 - theta) * dt * (
                lo * future[:-2] + (di - rate) * future[1:-1] + hi * future[2:]
            )
            rhs[0] += theta * dt * lo[0] * low
            rhs[-1] += theta * dt * hi[-1] * high
            current[1:-1] = solve_banded((1, 1), band, rhs)
        else:
            explicit = (
                weights[:, 0] * future[:-2]
                + weights[:, 1] * future[1:-1]
                + weights[:, 2] * future[2:]
            ) / (1 + rate * dt)
            current[1:-1] = explicit
            if method == "hopscotch":
                explicit_nodes = (i + np.arange(1, m)) % 2 == 0
                raw = current.copy()
                if american:
                    current[1:-1][explicit_nodes] = np.maximum(
                        explicit[explicit_nodes], exercise[1:-1][explicit_nodes]
                    )
                for j in np.flatnonzero(~explicit_nodes) + 1:
                    current[j] = (
                        future[j]
                        + dt * lo[j - 1] * current[j - 1]
                        + dt * hi[j - 1] * current[j + 1]
                    ) / (1 - dt * (di[j - 1] - rate))
                    raw[j] = current[j]
                continuation[i] = raw
        if method != "hopscotch":
            continuation[i] = current
        if american:
            current[1:-1] = np.maximum(current[1:-1], exercise[1:-1])
        values[i] = current
    return {
        "price": float(np.interp(x_spot, coordinate, values[0])),
        "stock": stock,
        "coordinate": coordinate,
        "times": np.linspace(0, maturity, n + 1),
        "values": values,
        "continuation": continuation,
        "space": space,
        "method": method,
        "obstacle": obstacle,
        "dt": dt,
        "transition_weights": weights,
        "weights_nonnegative": bool(np.all(weights >= 0)),
    }


def grid_greeks(grid, node):
    """Centered delta/gamma and forward calendar theta at an interior node."""
    if int(node) != node or not 1 <= node < len(grid["stock"]) - 1:
        raise ValueError("Greek node must be an interior integer index")
    node = int(node)
    f, dx = grid["values"], grid["coordinate"][1] - grid["coordinate"][0]
    first = (f[0, node + 1] - f[0, node - 1]) / (2 * dx)
    second = (f[0, node + 1] - 2 * f[0, node] + f[0, node - 1]) / dx**2
    s = grid["stock"][node]
    delta = first if grid["space"] == "spot" else first / s
    gamma = second if grid["space"] == "spot" else (second - first) / s**2
    theta = (f[1, node] - f[0, node]) / grid["dt"]
    return {"stock": float(s), "delta": float(delta), "gamma": float(gamma), "theta": float(theta)}


def fd_vega(spot, strike, rate, vol, maturity, space_steps, time_steps, *, bump=1e-4, **kwargs):
    """Forward volatility bump with fixed domain and space/time grid counts."""
    if not np.isfinite(bump) or bump == 0 or vol + bump < 0:
        raise ValueError("nonzero finite bump and nonnegative bumped vol required")
    base = fd_grid(spot, strike, rate, vol, maturity, space_steps, time_steps, **kwargs)
    bumped = fd_grid(spot, strike, rate, vol + bump, maturity, space_steps, time_steps, **kwargs)
    vega = (bumped["price"] - base["price"]) / bump
    return {"vega": vega, "vega_per_point": vega / 100, "base": base, "bumped": bumped}


def fd_control_variate(spot, strike, rate, vol, maturity, space_steps, time_steps, **kwargs):
    """American + analytic European - same-grid European, using raw prices."""
    american = fd_grid(
        spot, strike, rate, vol, maturity, space_steps, time_steps, american=True, **kwargs
    )
    european = fd_grid(
        spot, strike, rate, vol, maturity, space_steps, time_steps, american=False, **kwargs
    )
    pricer = bsm.call_price if kwargs.get("kind", "call") == "call" else bsm.put_price
    analytic = float(pricer(spot, strike, rate, vol, maturity, kwargs.get("yield_rate", 0)))
    a, e = american["price"], european["price"]
    return {"american": a, "european": e, "analytic": analytic, "corrected": a + analytic - e}
