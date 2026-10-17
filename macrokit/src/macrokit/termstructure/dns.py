"""Diebold-Li dynamic Nelson-Siegel with a VAR(1) on the factors (design §4.4).

Not arbitrage-free; it is the baseline. Factors are in annual %.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .curve import ZeroPanel
from .decompose import GRID_MONTHS, Decomposition
from .var import Var1, expected_average, fit_var1, fit_var1_batch, simulate_var1_batch

LAMBDA = 0.0609  # per month, Diebold and Li (2006)


def ns_loadings(months: np.ndarray, lam: float = LAMBDA) -> np.ndarray:
    """Nelson-Siegel loadings (level, slope, curvature) for maturities in months (> 0).

    lam is per month.
    """
    m = np.asarray(months, dtype=float)
    x = lam * m
    slope = -np.expm1(-x) / x
    return np.column_stack([np.ones_like(m), slope, slope - np.exp(-x)])


@dataclass(frozen=True)
class DnsFit:
    dates: tuple[date, ...]
    factors: np.ndarray  # (T, 3) level, slope, curvature
    var: Var1
    lam: float

    @property
    def short_loading(self) -> np.ndarray:
        return ns_loadings(np.array([1.0]), self.lam)[0]

    def expected(
        self, horizon: int, mu: np.ndarray | None = None, phi: np.ndarray | None = None
    ) -> np.ndarray:
        mu = self.var.mu if mu is None else mu
        phi = self.var.phi if phi is None else phi
        return expected_average(mu, phi, 0.0, self.short_loading, self.factors, horizon)


def fit_dns(panel: ZeroPanel, lam: float = LAMBDA, months: np.ndarray = GRID_MONTHS) -> DnsFit:
    load = ns_loadings(months, lam)
    factors = np.linalg.lstsq(load, panel.columns(months).T, rcond=None)[0].T
    return DnsFit(panel.dates, factors, fit_var1(factors), lam)


def decompose_dns(panel: ZeroPanel, fit: DnsFit, maturity: int = 120) -> Decomposition:
    return Decomposition("dns", panel.dates, panel.column(maturity), fit.expected(maturity))


def bootstrap_expected_dns(
    fit: DnsFit, horizon: int, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    paths = simulate_var1_batch(fit.var.mu, fit.var.phi, fit.var.resid, fit.factors[0], n_boot, rng)
    mus, phis = fit_var1_batch(paths)
    return expected_average(mus, phis, 0.0, fit.short_loading, fit.factors, horizon)
