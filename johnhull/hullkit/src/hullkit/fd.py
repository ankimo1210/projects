"""Finite-difference pricing on a uniform ln-S grid (Hull 11e, Ch.21).

Theta scheme: theta=1 (implicit, unconditionally stable) or theta=0.5
(Crank-Nicolson, second-order). American exercise via post-step projection
f = max(f, intrinsic) — simple and adequate for a learning kit.
"""

import numpy as np
from scipy.linalg import solve_banded


def fd_vanilla(
    S0,
    K,
    r,
    sigma,
    T,
    q=0.0,
    kind="call",
    american=False,
    method="cn",
    n_s=200,
    n_t=200,
    s_max_mult=4.0,
    return_boundary=False,
    return_greeks=False,
):
    """Theta-scheme FD price of a vanilla option; ln S0 is a grid node.

    With return_boundary=True (American puts), also returns (taus, boundary)
    — the early-exercise boundary S*(tau) read off the grid at each step.

    With return_greeks=True (and return_boundary=False), returns
    (price, delta, gamma) read from the solved grid.  Delta and gamma are
    computed via the chain rule on the uniform ln-S grid:
      delta = dV/dS = (1/S) * dV/dx
      gamma = d2V/dS2 = (1/S^2) * (d2V/dx2 - dV/dx)
    where x = ln S.  return_greeks is ignored when return_boundary=True.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if method not in ("implicit", "cn"):
        raise ValueError(f"method must be 'implicit' or 'cn', got {method!r}")
    theta = 1.0 if method == "implicit" else 0.5

    x = np.linspace(np.log(S0 / s_max_mult), np.log(S0 * s_max_mult), n_s + 1)
    s_grid = np.exp(x)
    dx = x[1] - x[0]
    dt = T / n_t
    drift = r - q - 0.5 * sigma**2

    payoff = np.maximum(s_grid - K, 0.0) if kind == "call" else np.maximum(K - s_grid, 0.0)
    f = payoff.copy()

    # interior operator L f = drift f_x + (sigma^2/2) f_xx - r f
    a_coef = 0.5 * sigma**2 / dx**2
    b_coef = drift / (2.0 * dx)
    lo = a_coef - b_coef
    di = -2.0 * a_coef - r
    up = a_coef + b_coef

    n_int = n_s - 1
    ab = np.zeros((3, n_int))
    ab[0, 1:] = -theta * dt * up
    ab[1, :] = 1.0 - theta * dt * di
    ab[2, :-1] = -theta * dt * lo

    taus, boundary = [], []
    for step in range(1, n_t + 1):
        tau = step * dt
        rhs = f[1:-1] + (1.0 - theta) * dt * (lo * f[:-2] + di * f[1:-1] + up * f[2:])
        if kind == "call":
            f_lo = 0.0
            f_hi = s_grid[-1] * np.exp(-q * tau) - K * np.exp(-r * tau)
        else:
            f_lo = K * np.exp(-r * tau) - s_grid[0] * np.exp(-q * tau)
            f_hi = 0.0
        rhs[0] += theta * dt * lo * f_lo
        rhs[-1] += theta * dt * up * f_hi
        new_int = solve_banded((1, 1), ab, rhs)
        f = np.concatenate([[f_lo], new_int, [f_hi]])
        if american:
            f = np.maximum(f, payoff)
            if return_boundary:
                mask = (np.abs(f - payoff) < 1e-10) & (payoff > 0.0)
                if mask.any():
                    taus.append(tau)
                    boundary.append(
                        float(s_grid[mask].max() if kind == "put" else s_grid[mask].min())
                    )

    price = float(np.interp(np.log(S0), x, f))
    if return_boundary:
        return price, taus, boundary
    if return_greeks:
        j = int(np.argmin(np.abs(x - np.log(S0))))
        j = max(1, min(j, len(x) - 2))
        dfdx = (f[j + 1] - f[j - 1]) / (2.0 * dx)
        d2fdx2 = (f[j + 1] - 2.0 * f[j] + f[j - 1]) / dx**2
        s_j = s_grid[j]
        delta = dfdx / s_j
        gamma = (d2fdx2 - dfdx) / s_j**2
        return price, float(delta), float(gamma)
    return price
