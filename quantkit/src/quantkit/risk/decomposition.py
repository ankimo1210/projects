"""Portfolio risk decomposition — where the volatility actually comes from.

Total portfolio volatility ``sigma = sqrt(w'Σw)`` decomposes exactly (Euler's
theorem, since volatility is homogeneous of degree 1 in the weights) into additive
per-asset **component contributions** ``w_i * (Σw)_i / sigma`` that sum back to
``sigma``. The **marginal contribution** ``(Σw)_i / sigma`` is the sensitivity of
portfolio vol to a small increase in asset ``i``. This complements
:func:`quantkit.portfolio.risk_contributions` (which reports the *variance share*); here
the units are volatility, so the parts literally add up to the whole.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _align(weights: pd.Series, cov: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    w = weights.reindex(cov.index).fillna(0.0).to_numpy(dtype=float)
    return w, cov.to_numpy(dtype=float)


def portfolio_vol(weights: pd.Series, cov: pd.DataFrame) -> float:
    """Portfolio volatility ``sqrt(w'Σw)`` (same period units as ``cov``)."""
    w, sigma = _align(weights, cov)
    return float(np.sqrt(max(w @ sigma @ w, 0.0)))


def marginal_risk(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Marginal contribution to risk ``(Σw)_i / sigma`` for each asset."""
    w, sigma = _align(weights, cov)
    vol = np.sqrt(max(w @ sigma @ w, 0.0))
    if vol == 0.0:
        return pd.Series(0.0, index=cov.index)
    return pd.Series((sigma @ w) / vol, index=cov.index)


def component_risk(weights: pd.Series, cov: pd.DataFrame) -> pd.Series:
    """Per-asset component contribution to risk; sums to :func:`portfolio_vol`."""
    w, _ = _align(weights, cov)
    return pd.Series(w, index=cov.index) * marginal_risk(weights, cov)
