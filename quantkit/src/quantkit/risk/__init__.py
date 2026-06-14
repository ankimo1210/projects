"""quantkit.risk — portfolio risk decomposition and statistical risk factors.

Two complementary views of where risk lives:
  * :mod:`quantkit.risk.decomposition` — Euler component/marginal contributions to
    portfolio volatility (the parts add up to the whole);
  * :mod:`quantkit.risk.factor` — PCA risk factors of the return covariance and the
    effective number of independent bets.
"""

from __future__ import annotations

from .decomposition import component_risk, marginal_risk, portfolio_vol
from .factor import PCAFactors, effective_n_bets, pca_factors

__all__ = [
    "PCAFactors",
    "component_risk",
    "effective_n_bets",
    "marginal_risk",
    "pca_factors",
    "portfolio_vol",
]
