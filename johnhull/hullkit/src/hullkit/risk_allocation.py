"""Risk decomposition: analytic-normal marginal/component VaR, historical
incremental VaR, and simulation-based Euler ES components.

Shares P&L/VaR conventions with `hullkit.risk`: P&L arrays have gains
positive, VaR/ES are positive loss amounts, and `alpha` is the coverage
level (default 0.99).

Analytic marginal/component VaR reuse `hullkit.risk.portfolio_sigma`'s
dollar-sigma construction (`C = corr * outer(vols, vols)`,
`sigma_P = sqrt(a^T C a)`) and Euler's theorem for the homogeneous-degree-1
`sigma_P`:

    dVaR/da_i = z_alpha * (C a)_i / sigma_P
    CVaR_i = a_i * dVaR/da_i
    sum_i CVaR_i = z_alpha * sigma_P = VaR  (exact identity)

Historical incremental VaR and simulation Euler ES components reuse
`hullkit.risk.historical_var_es`'s tail-selection convention
(`k = max(1, ceil((1-alpha)*n - 1e-9))`, worst-k scenarios by total P&L) so
that simulation-based additivity is exact by construction: the Euler ES
components are computed on the *same* scenario set selected for the total
portfolio's tail, with ties resolved deterministically via a stable
argsort of total P&L.

References: Tasche (1999), *Risk contributions and performance
measurement*; Tasche (2008), *Capital allocation for credit portfolios
with kernel estimators*.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from . import risk


def _validate_alpha(alpha: float) -> None:
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")


def _validate_book(amounts: np.ndarray, vols: np.ndarray, corr: np.ndarray) -> None:
    if amounts.ndim != 1 or vols.ndim != 1:
        raise ValueError("amounts and vols must be 1-D arrays")
    if amounts.shape != vols.shape:
        raise ValueError("amounts and vols must have the same length")
    if amounts.size == 0:
        raise ValueError("amounts/vols/corr must be non-empty")
    n = amounts.size
    if corr.shape != (n, n):
        raise ValueError(f"corr must have shape ({n}, {n}), got {corr.shape}")
    if not (
        np.all(np.isfinite(amounts)) and np.all(np.isfinite(vols)) and np.all(np.isfinite(corr))
    ):
        raise ValueError("amounts, vols, and corr must be finite")


def _validate_pnl_matrix(pnl_matrix: np.ndarray) -> None:
    if pnl_matrix.ndim != 2:
        raise ValueError(
            "pnl_matrix must be a 2-D (n_scenarios, n_positions) array, "
            f"got shape {pnl_matrix.shape}"
        )
    if pnl_matrix.shape[0] == 0 or pnl_matrix.shape[1] == 0:
        raise ValueError("pnl_matrix must be non-empty in both dimensions")
    if not np.all(np.isfinite(pnl_matrix)):
        raise ValueError("pnl_matrix must be finite")


def marginal_var_normal(amounts, vols, corr, alpha: float = 0.99) -> np.ndarray:
    """Analytic-normal marginal VaR `dVaR/da_i` (Tasche 1999, Euler allocation).

    `dVaR/da_i = z_alpha * (C a)_i / sigma_P`, with `C = corr * outer(vols,
    vols)` and `sigma_P = hullkit.risk.portfolio_sigma(amounts, vols,
    corr)` -- the same dollar-sigma construction as `hullkit.risk`. Raises
    ValueError on a shape mismatch, an empty book, non-finite inputs, or a
    non-positive portfolio sigma (degenerate book).
    """
    a = np.asarray(amounts, dtype=float)
    v = np.asarray(vols, dtype=float)
    c = np.asarray(corr, dtype=float)
    _validate_book(a, v, c)
    _validate_alpha(alpha)

    sigma_p = risk.portfolio_sigma(a, v, c)
    if not (math.isfinite(sigma_p) and sigma_p > 0.0):
        raise ValueError(f"portfolio sigma must be finite and positive, got {sigma_p}")

    cov = c * np.outer(v, v)
    z = float(norm.ppf(alpha))
    return z * (cov @ a) / sigma_p


def component_var_normal(amounts, vols, corr, alpha: float = 0.99) -> np.ndarray:
    """Analytic-normal component VaR `CVaR_i = a_i * dVaR/da_i` (Euler allocation).

    Sums exactly to `hullkit.risk.normal_var(portfolio_sigma(amounts,
    vols, corr), alpha)` by Euler's theorem for the homogeneous-degree-1
    `sigma_P`. Raises ValueError under the same conditions as
    `marginal_var_normal`.
    """
    a = np.asarray(amounts, dtype=float)
    marginal = marginal_var_normal(a, vols, corr, alpha=alpha)
    return a * marginal


def incremental_var(pnl_matrix, position_index: int, alpha: float = 0.99) -> float:
    """Historical incremental VaR of dropping one position from the book.

    `VaR(all positions) - VaR(all except position_index)`, both computed
    via `hullkit.risk.historical_var_es` on the row-summed P&L of
    `pnl_matrix` (n_scenarios, n_positions), gains positive. Raises
    ValueError on an empty or non-2-D `pnl_matrix`, non-finite entries, or
    an out-of-range `position_index`.
    """
    m = np.asarray(pnl_matrix, dtype=float)
    _validate_pnl_matrix(m)
    _validate_alpha(alpha)
    n_positions = m.shape[1]
    if not (0 <= position_index < n_positions):
        raise ValueError(f"position_index must be in [0, {n_positions}), got {position_index}")

    var_all, _ = risk.historical_var_es(m.sum(axis=1), alpha=alpha)
    keep = np.ones(n_positions, dtype=bool)
    keep[position_index] = False
    var_without, _ = risk.historical_var_es(m[:, keep].sum(axis=1), alpha=alpha)
    return float(var_all - var_without)


def euler_es_components(pnl_matrix, alpha: float = 0.99) -> np.ndarray:
    """Simulation-based Euler ES components (per-position contribution to total ES).

    Selects the vol 08 tail set `T` of the total P&L (row sum of
    `pnl_matrix`) using `hullkit.risk.historical_var_es`'s convention
    (`k = max(1, ceil((1-alpha)*n - 1e-9))`, worst-k scenarios), with ties
    resolved via a stable argsort of total P&L. `CES_i = mean_{s in
    T}(-pnl_matrix[s, i])`; by linearity `sum_i CES_i` equals
    `hullkit.risk.historical_var_es(pnl_matrix.sum(axis=1))[1]` exactly.
    Raises ValueError on an empty or non-2-D `pnl_matrix` or non-finite
    entries.
    """
    m = np.asarray(pnl_matrix, dtype=float)
    _validate_pnl_matrix(m)
    _validate_alpha(alpha)

    total = m.sum(axis=1)
    n = total.size
    k = max(1, math.ceil((1.0 - alpha) * n - 1e-9))
    order = np.argsort(total, kind="stable")
    tail = order[:k]
    return -m[tail].mean(axis=0)
