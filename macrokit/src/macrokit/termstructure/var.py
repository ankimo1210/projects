"""VAR(1) estimation, residual bootstrap, and expected short-rate averages."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Var1:
    mu: np.ndarray  # (K,)
    phi: np.ndarray  # (K, K)
    resid: np.ndarray  # (T-1, K), mean zero because of the intercept

    @property
    def sigma(self) -> np.ndarray:
        return self.resid.T @ self.resid / len(self.resid)


def fit_var1(x: np.ndarray) -> Var1:
    """OLS of x_{t+1} = mu + phi x_t + v_{t+1}."""
    z = np.column_stack([np.ones(len(x) - 1), x[:-1]])
    coef, *_ = np.linalg.lstsq(z, x[1:], rcond=None)
    return Var1(mu=coef[0], phi=coef[1:].T, resid=x[1:] - z @ coef)


def fit_var1_batch(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS VAR(1) for every path of a (B, T, K) array: mu (B, K), phi (B, K, K)."""
    lagged, lead = x[:, :-1], x[:, 1:]
    z = np.concatenate([np.ones((*lagged.shape[:2], 1)), lagged], axis=2)
    zz = np.einsum("btj,btk->bjk", z, z)
    zy = np.einsum("btj,btk->bjk", z, lead)
    coef = np.linalg.solve(zz, zy)
    return coef[:, 0], np.swapaxes(coef[:, 1:], 1, 2)


def simulate_var1_batch(
    mu: np.ndarray,
    phi: np.ndarray,
    resid: np.ndarray,
    x0: np.ndarray,
    n_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Residual-bootstrap paths of length len(resid) + 1 starting at x0: (n_paths, T, K)."""
    steps = len(resid)
    draws = resid[rng.integers(0, steps, size=(n_paths, steps))]
    out = np.empty((n_paths, steps + 1, len(x0)))
    out[:, 0] = x0
    for t in range(1, steps + 1):
        out[:, t] = mu + out[:, t - 1] @ phi.T + draws[:, t - 1]
    return out


def expected_average(
    mu: np.ndarray,
    phi: np.ndarray,
    delta0: float,
    delta1: np.ndarray,
    x: np.ndarray,
    horizon: int,
) -> np.ndarray:
    """Mean over h = 0..horizon-1 of delta0 + delta1 . E_t[x_{t+h}] under x' = mu + phi x.

    ``mu`` (..., K) and ``phi`` (..., K, K) may carry a leading batch axis; ``x`` is
    the (T, K) history. Returns (..., T) in the units of ``delta0``.
    """
    mu = np.asarray(mu)
    phi = np.asarray(phi)
    state = np.broadcast_to(x, mu.shape[:-1] + x.shape).copy()
    total = np.zeros(state.shape[:-1])
    phi_t = np.swapaxes(phi, -1, -2)
    for _ in range(horizon):
        total += delta0 + state @ delta1
        state = mu[..., None, :] + state @ phi_t
    return total / horizon


def max_abs_eig(phi: np.ndarray) -> float:
    return float(np.abs(np.linalg.eigvals(phi)).max())
