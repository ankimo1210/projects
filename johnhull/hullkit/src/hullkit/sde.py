"""Stochastic-calculus primitives (A1 deep-dive — beyond Hull's tool-level use).

Graduate references: Shreve, *Stochastic Calculus for Finance II* (Ch.3-5);
Øksendal, *Stochastic Differential Equations*. These helpers power volume 13's
notebook and its Plotly figures, and underpin the risk-neutral pricing the Hull
volumes use without proof.

Key facts the tests pin (exact, not Monte-Carlo-noisy — they are telescoping
identities):

* left-point (Itô) Riemann sum of ∫ W dW  ==  ½(W_T² − [W]_T),
* midpoint (Stratonovich) sum               ==  ½ W_T²,

so their difference is exactly ½[W]_T → ½T: the Itô correction made visible.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def brownian_paths(T: float, n_steps: int, n_paths: int, rng=None) -> np.ndarray:
    """Standard Brownian motion paths W_t, shape ``(n_paths, n_steps + 1)``.

    Increments are iid ``N(0, dt)`` with ``dt = T / n_steps``; column ``j`` is
    ``W`` at time ``j*dt`` and column 0 is 0 (Shreve II §3.3).
    """
    if n_steps < 1 or n_paths < 1:
        raise ValueError("n_steps and n_paths must be >= 1")
    if rng is None:
        rng = np.random.default_rng(42)
    dt = T / n_steps
    dW = rng.standard_normal((n_paths, n_steps)) * np.sqrt(dt)
    W = np.zeros((n_paths, n_steps + 1))
    np.cumsum(dW, axis=1, out=W[:, 1:])
    return W


def quadratic_variation(W: np.ndarray) -> np.ndarray:
    """Realized quadratic variation Σ (ΔW)² per path; converges to T (Shreve II §3.4)."""
    dW = np.diff(W, axis=1)
    return np.sum(dW**2, axis=1)


def running_quadratic_variation(W: np.ndarray) -> np.ndarray:
    """Cumulative Σ (ΔW)² along each path, shape ``(n_paths, n_steps + 1)``.

    Used by the figure that shows the staircase hugging the diagonal y = t as
    the mesh is refined.
    """
    dW = np.diff(W, axis=1)
    out = np.zeros_like(W)
    np.cumsum(dW**2, axis=1, out=out[:, 1:])
    return out


def ito_riemann_sum(W: np.ndarray, alpha: float = 0.0, f: Callable | None = None) -> np.ndarray:
    """Riemann-sum approximation of ∫ f(W) dW with evaluation point ``alpha``.

    ``alpha=0`` evaluates the integrand at the left node (the **Itô** choice),
    ``alpha=0.5`` at the midpoint (**Stratonovich**), ``alpha=1`` at the right.
    ``f`` defaults to the identity, i.e. ∫ W dW (Shreve II §4.2/§4.3).
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    g = f if f is not None else (lambda w: w)
    w_left, w_right = W[:, :-1], W[:, 1:]
    w_eval = (1.0 - alpha) * w_left + alpha * w_right
    return np.sum(g(w_eval) * (w_right - w_left), axis=1)


def euler_maruyama(
    drift: Callable,
    diffusion: Callable,
    x0: float,
    T: float,
    n_steps: int,
    n_paths: int,
    rng=None,
) -> np.ndarray:
    """Euler–Maruyama scheme for dX = a(X,t) dt + b(X,t) dW (Kloeden–Platen).

    ``drift(x, t)`` and ``diffusion(x, t)`` act elementwise on the state vector.
    Weak order 1, strong order 1/2: terminal moments converge as ``n_steps`` grows
    (the test pins E[X_T] for geometric Brownian motion).
    """
    if n_steps < 1 or n_paths < 1:
        raise ValueError("n_steps and n_paths must be >= 1")
    if rng is None:
        rng = np.random.default_rng(42)
    dt = T / n_steps
    sqrt_dt = np.sqrt(dt)
    x = np.full(n_paths, float(x0))
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = x
    for i in range(1, n_steps + 1):
        t = (i - 1) * dt
        dW = rng.standard_normal(n_paths) * sqrt_dt
        x = x + drift(x, t) * dt + diffusion(x, t) * dW
        paths[:, i] = x
    return paths


def girsanov_weights(
    s_terminal: np.ndarray,
    S0: float,
    sigma: float,
    T: float,
    mu_from: float,
    mu_to: float,
) -> np.ndarray:
    """Radon–Nikodým weights that change the GBM drift from ``mu_from`` to ``mu_to``.

    With market price of risk ``λ = (mu_from − mu_to) / σ`` and ``W_T`` recovered
    from the terminal price, ``dQ/dP = exp(−λ W_T − ½ λ² T)`` (Shreve II §5.2-5.4).
    Then ``E^P[ weight · f(S_T) ] = E^Q[ f(S_T) ]`` and ``E^P[weight] = 1``; taking
    ``mu_to = r`` turns the real-world simulation into a risk-neutral price.
    """
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    lam = (mu_from - mu_to) / sigma
    w_t = (
        np.log(np.asarray(s_terminal, dtype=float) / S0) - (mu_from - 0.5 * sigma**2) * T
    ) / sigma
    return np.exp(-lam * w_t - 0.5 * lam**2 * T)
