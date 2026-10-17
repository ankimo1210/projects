"""Adrian, Crump and Moench (2013) term structure by linear regression (design §4.1).

Log prices ln P^(n) = A_n + B_n' X_t with monthly periods and the one-month rate
r_t = y^(1)/1200. Gate G2 validates it against the NY Fed series on US data (the
2026-10-17 prototype reproduced it with correlation 0.99985).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .curve import ZeroPanel
from .decompose import GRID_MONTHS, Decomposition
from .var import Var1, expected_average, fit_var1, fit_var1_batch, max_abs_eig, simulate_var1_batch

FACTOR_MONTHS = GRID_MONTHS
RETURN_MONTHS = np.array([6, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120])
LONG_FACTOR_MONTHS = np.arange(3, 361, 3)
LONG_RETURN_MONTHS = np.concatenate([RETURN_MONTHS, [180, 240, 300, 360]])


def pricing_recursion(
    mu: np.ndarray,
    phi: np.ndarray,
    sigma: np.ndarray,
    sigma2: float,
    delta0: float,
    delta1: np.ndarray,
    n_max: int,
) -> tuple[np.ndarray, np.ndarray]:
    """ACM eq. (11) with (mu, phi) the pricing drift: the Q measure uses mu - lambda0, phi - lambda1."""
    k = len(mu)
    a = np.zeros(n_max + 1)
    b = np.zeros((n_max + 1, k))
    for n in range(1, n_max + 1):
        a[n] = a[n - 1] + b[n - 1] @ mu + 0.5 * (b[n - 1] @ sigma @ b[n - 1] + sigma2) - delta0
        b[n] = b[n - 1] @ phi - delta1
    return a, b


@dataclass(frozen=True)
class AcmFit:
    dates: tuple[date, ...]
    factors: np.ndarray  # (T, K) principal components of the yields
    var: Var1
    lambda0: np.ndarray
    lambda1: np.ndarray
    delta0: float
    delta1: np.ndarray
    sigma2: float

    def fitted_yield(self, n: int, risk_neutral: bool = False) -> np.ndarray:
        """Model yield (annual %). ``risk_neutral=True`` prices with zero risk prices (P drift)."""
        mu, phi = self.var.mu, self.var.phi
        if not risk_neutral:
            mu, phi = mu - self.lambda0, phi - self.lambda1
        a, b = pricing_recursion(mu, phi, self.var.sigma, self.sigma2, self.delta0, self.delta1, n)
        return -1200.0 / n * (a[n] + self.factors @ b[n])

    def expected(
        self, horizon: int, mu: np.ndarray | None = None, phi: np.ndarray | None = None
    ) -> np.ndarray:
        """Design §2.1 E_t (annual %): mean expected one-month rate, optionally with other P dynamics."""
        mu = self.var.mu if mu is None else mu
        phi = self.var.phi if phi is None else phi
        return 1200.0 * expected_average(mu, phi, self.delta0, self.delta1, self.factors, horizon)


def fit_acm(
    panel: ZeroPanel,
    k: int = 5,
    factor_months: np.ndarray = FACTOR_MONTHS,
    return_months: np.ndarray = RETURN_MONTHS,
) -> AcmFit:
    log_price = -(panel.months / 12.0) * panel.yields / 100.0
    short = panel.column(1) / 1200.0
    selected = panel.columns(factor_months)
    centered = selected - selected.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov(centered.T))
    factors = centered @ vectors[:, ::-1][:, :k]
    var = fit_var1(factors)
    steps = len(factors) - 1
    excess = np.column_stack(
        [log_price[1:, n - 2] - log_price[:-1, n - 1] - short[:-1] for n in return_months]
    )
    z = np.column_stack([np.ones(steps), var.resid, factors[:-1]])
    coef, *_ = np.linalg.lstsq(z, excess, rcond=None)
    a, beta, c = coef[0], coef[1 : 1 + k], coef[1 + k :].T
    errors = excess - z @ coef
    sigma2 = float((errors**2).sum() / errors.size)
    b_star = np.array([np.outer(beta[:, i], beta[:, i]).ravel() for i in range(beta.shape[1])])
    bb = beta @ beta.T
    lambda1 = np.linalg.solve(bb, beta @ c)
    lambda0 = np.linalg.solve(bb, beta @ (a + 0.5 * (b_star @ var.sigma.ravel() + sigma2)))
    zs = np.column_stack([np.ones(len(factors)), factors])
    d, *_ = np.linalg.lstsq(zs, short, rcond=None)
    return AcmFit(panel.dates, factors, var, lambda0, lambda1, float(d[0]), d[1:], sigma2)


def decompose_acm(
    panel: ZeroPanel,
    fit: AcmFit,
    maturity: int = 120,
    mu: np.ndarray | None = None,
    phi: np.ndarray | None = None,
    model: str = "acm",
) -> Decomposition:
    return Decomposition(
        model, panel.dates, panel.column(maturity), fit.expected(maturity, mu, phi)
    )


@dataclass(frozen=True)
class BiasCorrected:
    mu: np.ndarray
    phi: np.ndarray
    shrink: float  # share of the estimated bias removed (1 = all, 0 = none)


def shrink_to_stationary(phi: np.ndarray, bias: np.ndarray) -> tuple[np.ndarray, float]:
    """Kilian (1998): remove the bias, shrinking it in 0.01 steps until stationary."""
    for step in range(100, -1, -1):
        shrink = step / 100.0
        corrected = phi - shrink * bias
        if max_abs_eig(corrected) < 1.0:
            return corrected, shrink
    return phi, 0.0


def kilian_correct(
    x: np.ndarray,
    var: Var1,
    n_boot: int,
    rng: np.random.Generator,
    max_floats: int = 5_000_000,
) -> BiasCorrected:
    """Bootstrap bias correction of phi; mu keeps the sample mean (design §4.2)."""
    if max_abs_eig(var.phi) >= 1.0:
        return BiasCorrected(var.mu, var.phi, 0.0)
    chunk = max(1, max_floats // (len(x) * x.shape[1]))
    total = np.zeros_like(var.phi)
    done = 0
    while done < n_boot:
        size = min(chunk, n_boot - done)
        paths = simulate_var1_batch(var.mu, var.phi, var.resid, x[0], size, rng)
        total += fit_var1_batch(paths)[1].sum(axis=0)
        done += size
    bias = total / n_boot - var.phi
    phi, shrink = shrink_to_stationary(var.phi, bias)
    mu = (np.eye(len(var.mu)) - phi) @ x.mean(axis=0)
    return BiasCorrected(mu, phi, shrink)


def bootstrap_expected(
    fit: AcmFit,
    horizon: int,
    n_boot: int,
    rng: np.random.Generator,
    correction_boot: int = 0,
) -> np.ndarray:
    """E_t (annual %) under re-estimated P dynamics, Q held fixed (design §4.1–4.2).

    Residual-bootstrap factor paths, re-estimate (mu, phi), recompute E on the
    actual factor history. With ``correction_boot`` the bootstrap DGP is the
    bias-corrected VAR and every re-estimate is bias-corrected again.
    """
    if correction_boot:
        dgp = kilian_correct(fit.factors, fit.var, correction_boot, rng)
        dgp_mu, dgp_phi = dgp.mu, dgp.phi
    else:
        dgp_mu, dgp_phi = fit.var.mu, fit.var.phi
    paths = simulate_var1_batch(dgp_mu, dgp_phi, fit.var.resid, fit.factors[0], n_boot, rng)
    mus, phis = fit_var1_batch(paths)
    if correction_boot:
        for b in range(n_boot):
            corrected = kilian_correct(paths[b], fit_var1(paths[b]), correction_boot, rng)
            mus[b], phis[b] = corrected.mu, corrected.phi
    return 1200.0 * expected_average(mus, phis, fit.delta0, fit.delta1, fit.factors, horizon)
