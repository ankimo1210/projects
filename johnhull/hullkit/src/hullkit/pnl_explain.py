"""P&L explain: factor exposure aggregation, delta-gamma-vega Taylor P&L
attribution versus full revaluation, limit utilization, and a pure
desk-report assembler for a daily risk desk.

Shares P&L conventions with `hullkit.risk`: P&L amounts have gains
positive; limit "measures" and "limits" are positive risk-usage amounts.

`aggregate_exposures` rolls up per-position delta, gamma, and vega into
per-factor book exposures via `weights @ matrix`. **Cross-gammas are out
of scope**: `gamma_p` is the book's own-factor second derivative
`d^2V/dx_i^2` per risk factor `i`, not a full `(n_factors, n_factors)`
cross-gamma matrix. `delta_gamma_vega_pnl`'s Taylor approximation
therefore has no `d^2V/(dx_i dx_j)` (i != j) or vol-convexity
(`d^2V/dvol^2`, "vomma") terms; for a book with correlated spot and vol
moves the leftover unexplained P&L is dominated by those missing
cross/vol-convexity terms (see `test_pnl_explain.py` for a worked BSM
example showing the resulting ~quadratic shrinkage of the residual as
the move size halves, versus the ~linear shrinkage of a delta-only
residual).

`pnl_attribution` compares an explained (Taylor) P&L total against a
fully revalued P&L to quantify the unexplained residual and its share.
`limit_utilization` reports utilization ratios and breach flags against
desk limits. `desk_report` is a pure assembler -- no randomness, no I/O,
no wall-clock timestamp -- producing a nested, JSON-able dict for a
reproducible daily risk report.

FRTB-style P&L attribution eligibility testing (IMA vs. SA comparison,
risk-theoretical vs. hypothetical P&L) is out of scope; see ROADMAP.md
for the deferred vol 28 candidate.
"""

from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass

import numpy as np


def _validate_2d_matrix(name: str, matrix: np.ndarray, n_pos: int) -> None:
    if matrix.ndim != 2:
        raise ValueError(f"{name} must be a 2-D (n_pos, n_factors) array, got shape {matrix.shape}")
    if matrix.shape[0] != n_pos:
        raise ValueError(f"{name} must have {n_pos} rows (n_pos), got {matrix.shape[0]}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be finite")


def aggregate_exposures(weights, deltas, gammas, vegas):
    """Aggregate per-position delta/gamma/vega into per-factor book exposures.

    `weights` is `(n_pos,)`; `deltas`, `gammas`, `vegas` are each `(n_pos,
    n_factors)`. Returns `(delta_p, gamma_p, vega_p)`, each `(n_factors,)`,
    computed as `weights @ matrix`. **Cross-gammas are out of scope**:
    `gamma_p` is the book's own-factor curvature per risk factor, not a
    full cross-gamma matrix (see module docstring). Raises ValueError on
    an empty book, a shape/length mismatch among `weights`, `deltas`,
    `gammas`, `vegas`, or non-finite inputs.
    """
    w = np.asarray(weights, dtype=float)
    d = np.asarray(deltas, dtype=float)
    g = np.asarray(gammas, dtype=float)
    v = np.asarray(vegas, dtype=float)

    if w.ndim != 1:
        raise ValueError(f"weights must be a 1-D array, got shape {w.shape}")
    if w.size == 0:
        raise ValueError("weights/deltas/gammas/vegas must be non-empty")
    n_pos = w.size
    _validate_2d_matrix("deltas", d, n_pos)
    _validate_2d_matrix("gammas", g, n_pos)
    _validate_2d_matrix("vegas", v, n_pos)
    n_factors = d.shape[1]
    if g.shape[1] != n_factors or v.shape[1] != n_factors:
        raise ValueError(
            f"deltas, gammas, and vegas must share n_factors={n_factors}, "
            f"got gammas.shape[1]={g.shape[1]}, vegas.shape[1]={v.shape[1]}"
        )
    if not np.all(np.isfinite(w)):
        raise ValueError("weights must be finite")

    delta_p = w @ d
    gamma_p = w @ g
    vega_p = w @ v
    return delta_p, gamma_p, vega_p


def _validate_factor_vector(name: str, vec: np.ndarray, n_factors: int) -> None:
    if vec.shape != (n_factors,):
        raise ValueError(f"{name} must have shape ({n_factors},), got {vec.shape}")
    if not np.all(np.isfinite(vec)):
        raise ValueError(f"{name} must be finite")


def delta_gamma_vega_pnl(delta_p, gamma_p, vega_p, factor_moves, vol_moves) -> dict:
    """Per-factor delta-gamma-vega Taylor P&L from book exposures and moves.

    `delta = delta_p @ dx`; `gamma = 0.5 * gamma_p @ dx**2` (own-factor
    curvature only, elementwise square -- cross-gammas are out of scope,
    see module docstring); `vega = vega_p @ dvol`, where `dx =
    factor_moves` and `dvol = vol_moves`. Returns `{"delta", "gamma",
    "vega", "total"}` as plain floats with `total = delta + gamma +
    vega`. Raises ValueError if `delta_p` is empty or not 1-D, if
    `gamma_p`, `vega_p`, `factor_moves`, or `vol_moves` do not share
    `delta_p`'s length, or on non-finite inputs.
    """
    delta_p_arr = np.asarray(delta_p, dtype=float)
    if delta_p_arr.ndim != 1 or delta_p_arr.size == 0:
        raise ValueError(f"delta_p must be a non-empty 1-D array, got shape {delta_p_arr.shape}")
    if not np.all(np.isfinite(delta_p_arr)):
        raise ValueError("delta_p must be finite")
    n_factors = delta_p_arr.shape[0]

    gamma_p_arr = np.asarray(gamma_p, dtype=float)
    vega_p_arr = np.asarray(vega_p, dtype=float)
    dx = np.asarray(factor_moves, dtype=float)
    dvol = np.asarray(vol_moves, dtype=float)
    _validate_factor_vector("gamma_p", gamma_p_arr, n_factors)
    _validate_factor_vector("vega_p", vega_p_arr, n_factors)
    _validate_factor_vector("factor_moves", dx, n_factors)
    _validate_factor_vector("vol_moves", dvol, n_factors)

    delta = float(delta_p_arr @ dx)
    gamma = float(0.5 * gamma_p_arr @ dx**2)
    vega = float(vega_p_arr @ dvol)
    total = delta + gamma + vega
    return {"delta": delta, "gamma": gamma, "vega": vega, "total": total}


def pnl_attribution(full_pnl: float, explained_total: float) -> dict:
    """Compare an explained (Taylor) P&L total against a full revaluation.

    `explained = explained_total`; `unexplained = full_pnl -
    explained_total`; `unexplained_share = |unexplained| /
    max(|full_pnl|, 1e-12)` (the denominator is floored so the share
    stays finite when `full_pnl` is at or near zero). Raises ValueError
    if `full_pnl` or `explained_total` is non-finite.
    """
    full = float(full_pnl)
    explained = float(explained_total)
    if not (math.isfinite(full) and math.isfinite(explained)):
        raise ValueError(
            f"full_pnl and explained_total must be finite, got {full_pnl}, {explained_total}"
        )
    unexplained = full - explained
    unexplained_share = abs(unexplained) / max(abs(full), 1e-12)
    return {
        "explained": explained,
        "unexplained": unexplained,
        "unexplained_share": unexplained_share,
    }


def limit_utilization(measures, limits) -> dict:
    """Limit utilization ratios and breach flags for a set of risk measures.

    `measures` and `limits` are aligned, non-empty 1-D arrays (e.g. VaR
    usage or notional exposure against desk limits).
    `utilization = measures / limits`; `breached = measures > limits`
    (strict). Returns `{"utilization": np.ndarray, "breached":
    np.ndarray[bool]}`. Raises ValueError on a shape mismatch, empty
    input, non-finite entries, or any non-positive `limits` entry (a
    limit must be a strictly positive ceiling).
    """
    m = np.asarray(measures, dtype=float)
    lim = np.asarray(limits, dtype=float)
    if m.shape != lim.shape:
        raise ValueError(
            f"measures and limits must have the same shape, got {m.shape} vs {lim.shape}"
        )
    if m.ndim != 1 or m.size == 0:
        raise ValueError("measures/limits must be non-empty 1-D arrays")
    if not (np.all(np.isfinite(m)) and np.all(np.isfinite(lim))):
        raise ValueError("measures and limits must be finite")
    if np.any(lim <= 0.0):
        raise ValueError(f"limits must be strictly positive, got {lim.tolist()}")

    utilization = m / lim
    breached = m > lim
    return {"utilization": utilization, "breached": breached}


def _to_jsonable(obj):
    """Recursively convert numpy/dataclass values into plain JSON-able types."""
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj) and not isinstance(obj, type):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, np.ndarray):
        return _to_jsonable(obj.tolist())
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def desk_report(var, es, components, utilization, backtest) -> dict:
    """Assemble a reproducible daily risk-desk report as a nested JSON-able dict.

    Pure function of its inputs -- no randomness, no I/O, no wall-clock
    timestamp. `var` and `es` are cast to plain floats. `components`
    (e.g. a `delta_gamma_vega_pnl`/`pnl_attribution` result),
    `utilization` (e.g. a `limit_utilization` result), and `backtest`
    (e.g. a `hullkit.var_backtest` result) are recursively converted from
    numpy arrays/scalars and dataclasses into plain Python types so the
    returned dict round-trips through `json.dumps`. Calling `desk_report`
    twice with identical inputs returns equal dicts.
    """
    return {
        "var": float(var),
        "es": float(es),
        "components": _to_jsonable(components),
        "utilization": _to_jsonable(utilization),
        "backtest": _to_jsonable(backtest),
    }
