"""One-factor copula valuation of CDO tranches and basket CDS (Hull 11e, §25.6–25.11).

The standard market model (Gaussian copula, Gauss–Hermite quadrature over the
common factor, eqs. 25.5–25.12), kth-to-default swaps, compound and base
correlations (Table 25.8), the double-t copula and the heterogeneous
Andersen–Sidenius–Basu recursion (§25.11).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.special import gammaln
from scipy.stats import norm
from scipy.stats import t as student_t

# --- factor quadrature -----------------------------------------------------


def gauss_hermite_factor(m: int = 60):
    """Nodes/weights approximating E[g(F)], F ~ N(0,1) (Hull eq. 25.12).

    With ``m=60`` the nodes nearest the origin are ±0.2020, −0.6060, −1.0104 with
    weights 0.1579, 0.1342, 0.0969 — the columns printed in Hull Table 25.7.
    """
    if int(m) != m or m < 1:
        raise ValueError("m must be a positive integer")
    x, w = np.polynomial.hermite.hermgauss(int(m))
    return np.sqrt(2.0) * x, w / np.sqrt(np.pi)


def standardized_t_cdf(x, nu: float):
    """CDF of a Student-t(ν) variable scaled to unit variance."""
    _check_nu(nu)
    return student_t.cdf(np.asarray(x, dtype=float) / math.sqrt((nu - 2.0) / nu), nu)


def standardized_t_ppf(u, nu: float):
    """Quantile of a unit-variance Student-t(ν) variable."""
    _check_nu(nu)
    return student_t.ppf(np.asarray(u, dtype=float), nu) * math.sqrt((nu - 2.0) / nu)


def double_t_factor_quadrature(nu: float, m: int = 60):
    """Nodes/weights for E[g(F)] with F a unit-variance t(ν): Gauss–Legendre in CDF space."""
    if int(m) != m or m < 1:
        raise ValueError("m must be a positive integer")
    x, w = np.polynomial.legendre.leggauss(int(m))
    u = 0.5 * (x + 1.0)
    return standardized_t_ppf(u, nu), 0.5 * w


def _factor_quadrature(copula: str, nu: float, m: int):
    if copula == "gaussian":
        return gauss_hermite_factor(m)
    if copula == "double_t":
        return double_t_factor_quadrature(nu, m)
    raise ValueError("copula must be 'gaussian' or 'double_t'")


# --- conditional default probabilities --------------------------------------


def conditional_default_prob(q, rho: float, factor):
    """Q(t | F) = N((N⁻¹(Q) − √ρ F)/√(1−ρ)) (Hull eq. 25.5), broadcasting over inputs."""
    _check_rho(rho)
    q = np.asarray(q, dtype=float)
    f = np.asarray(factor, dtype=float)
    return norm.cdf((norm.ppf(q) - math.sqrt(rho) * f) / math.sqrt(1.0 - rho))


def double_t_threshold(q: float, rho: float, nu: float, m: int = 200) -> float:
    """Default threshold x* with P(√ρF + √(1−ρ)Z ≤ x*) = q for unit-variance t(ν) factors."""
    _check_rho(rho)
    _check_nu(nu)
    if not 0.0 < q < 1.0:
        raise ValueError("q must lie in (0, 1)")
    nodes, weights = double_t_factor_quadrature(nu, m)
    scale = math.sqrt(1.0 - rho)

    def cdf(x: float) -> float:
        return float(weights @ standardized_t_cdf((x - math.sqrt(rho) * nodes) / scale, nu)) - q

    return float(brentq(cdf, -60.0, 60.0, xtol=1e-13))


def double_t_conditional_prob(q, rho: float, factor, nu: float, m: int = 200):
    """Q(t | F) under the double-t copula: T_std((x*(q) − √ρF)/√(1−ρ)) (Hull & White 2004)."""
    q = np.asarray(q, dtype=float)
    f = np.asarray(factor, dtype=float)
    thresholds = np.vectorize(lambda value: double_t_threshold(float(value), rho, nu, m))(q)
    return standardized_t_cdf((thresholds - math.sqrt(rho) * f) / math.sqrt(1.0 - rho), nu)


def _conditional_probs(q, rho: float, nodes: np.ndarray, copula: str, nu: float):
    """Conditional default probabilities with shape (M,) + q.shape."""
    q = np.asarray(q, dtype=float)
    f = nodes.reshape((-1,) + (1,) * q.ndim)
    if copula == "gaussian":
        return conditional_default_prob(q[None, ...], rho, f)
    return double_t_conditional_prob(q[None, ...], rho, f, nu)


# --- default-count distributions ---------------------------------------------


def binomial_pmf(n: int, p):
    """P(k defaults | p) for k = 0..n along a new trailing axis (Hull eq. 25.7), stable at p→0, 1."""
    if int(n) != n or n < 1:
        raise ValueError("n must be a positive integer")
    p = np.clip(np.asarray(p, dtype=float), 1e-300, 1.0 - 1e-16)[..., None]
    k = np.arange(n + 1, dtype=float)
    log_choose = gammaln(n + 1.0) - gammaln(k + 1.0) - gammaln(n - k + 1.0)
    return np.exp(log_choose + k * np.log(p) + (n - k) * np.log1p(-p))


def heterogeneous_default_pmf(cond_probs):
    """Default-count pmf for names with different conditional PDs (Andersen–Sidenius–Basu).

    ``cond_probs`` has the names on its last axis; the result has k = 0..n on its last
    axis. With equal probabilities the recursion reproduces the binomial distribution.
    """
    p = np.asarray(cond_probs, dtype=float)
    if p.ndim == 0 or p.shape[-1] < 1:
        raise ValueError("cond_probs must have at least one name on its last axis")
    n = p.shape[-1]
    pmf = np.zeros((*p.shape[:-1], n + 1))
    pmf[..., 0] = 1.0
    for i in range(n):
        p_i = p[..., i][..., None]
        shifted = np.concatenate([np.zeros_like(pmf[..., :1]), pmf[..., :-1]], axis=-1)
        pmf = pmf * (1.0 - p_i) + shifted * p_i
    return pmf


def _default_count_pmf(
    hazard, times: np.ndarray, rho: float, nodes: np.ndarray, n_names: int, copula: str, nu: float
):
    """Return the (M, len(times), n+1) default-count pmf for constant or per-name hazards."""
    hazard = np.asarray(hazard, dtype=float)
    if np.any(hazard < 0.0):
        raise ValueError("hazard must be >= 0")
    if hazard.ndim == 0:
        q = 1.0 - np.exp(-float(hazard) * times)
        return binomial_pmf(n_names, _conditional_probs(q, rho, nodes, copula, nu))
    if hazard.shape != (n_names,):
        raise ValueError("hazard must be a scalar or an array of length n_names")
    q = 1.0 - np.exp(-hazard[None, :] * times[:, None])
    return heterogeneous_default_pmf(_conditional_probs(q, rho, nodes, copula, nu))


# --- tranche principal --------------------------------------------------------


def smallest_integer_above(x: float) -> int:
    """m(x): the smallest integer strictly greater than x (Hull §25.10)."""
    return math.floor(x) + 1


def tranche_principal_by_defaults(n_names: int, recovery: float, attach: float, detach: float):
    """Tranche principal (initial = 1) after k defaults, k = 0..n (Hull eq. 25.8 pieces)."""
    _check_tranche(attach, detach)
    _check_recovery(recovery)
    n_low = attach * n_names / (1.0 - recovery)
    n_high = detach * n_names / (1.0 - recovery)
    m_low, m_high = smallest_integer_above(n_low), smallest_integer_above(n_high)
    k = np.arange(n_names + 1)
    partial = (detach - k * (1.0 - recovery) / n_names) / (detach - attach)
    return np.where(k < m_low, 1.0, np.where(k >= m_high, 0.0, np.clip(partial, 0.0, 1.0)))


@dataclass(frozen=True)
class TrancheValuation:
    """Conditional and unconditional tranche legs (Hull eqs. 25.9–25.12); principal 1, spread 1."""

    payment_times: np.ndarray
    factor_nodes: np.ndarray
    factor_weights: np.ndarray
    expected_principal: np.ndarray
    annuity_by_factor: np.ndarray
    accrual_by_factor: np.ndarray
    protection_by_factor: np.ndarray

    @property
    def annuity(self) -> float:
        """A = E_F[A(F)]."""
        return float(self.factor_weights @ self.annuity_by_factor)

    @property
    def accrual(self) -> float:
        """B = E_F[B(F)]."""
        return float(self.factor_weights @ self.accrual_by_factor)

    @property
    def protection(self) -> float:
        """C = E_F[C(F)] — PV of expected tranche loss per unit tranche principal."""
        return float(self.factor_weights @ self.protection_by_factor)

    @property
    def spread(self) -> float:
        """Breakeven spread s = C/(A+B) (Hull eq. 25.4)."""
        return self.protection / (self.annuity + self.accrual)

    def upfront(self, fixed_spread: float) -> float:
        """Upfront payment as a fraction of tranche principal: C − s*(A+B)."""
        return self.protection - fixed_spread * (self.annuity + self.accrual)


def _payment_grid(maturity: float, freq: int):
    if int(freq) != freq or freq < 1:
        raise ValueError("freq must be a positive integer")
    n = round(maturity * freq)
    if n <= 0 or abs(n / freq - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of payment periods")
    times = np.arange(1, n + 1) / freq
    previous = times - 1.0 / freq
    return times, previous, 0.5 * (times + previous)


def cdo_tranche_valuation(
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    attach: float,
    detach: float,
    n_names: int,
    rho: float,
    freq: int = 4,
    m: int = 60,
    copula: str = "gaussian",
    nu: float = 4.0,
) -> TrancheValuation:
    """Standard market model for a synthetic CDO tranche (Hull §25.10, Example 25.2).

    ``hazard`` is a constant (homogeneous, binomial conditional counts) or an array of
    per-name hazards (heterogeneous, ASB recursion). ``copula`` selects the Gaussian
    or double-t one-factor copula. Returns conditional legs on the factor grid.
    """
    if int(n_names) != n_names or n_names < 1:
        raise ValueError("n_names must be a positive integer")
    _check_rho(rho)
    times, _previous, mid = _payment_grid(maturity, freq)
    nodes, weights = _factor_quadrature(copula, nu, m)
    pmf = _default_count_pmf(hazard, times, rho, nodes, int(n_names), copula, nu)
    principal = tranche_principal_by_defaults(int(n_names), recovery, attach, detach)
    expected = np.concatenate([np.ones((nodes.size, 1)), pmf @ principal], axis=1)
    dt = np.diff(np.concatenate([[0.0], times]))
    discount = np.exp(-r * times)
    discount_mid = np.exp(-r * mid)
    loss = expected[:, :-1] - expected[:, 1:]
    annuity = (dt * expected[:, 1:] * discount).sum(axis=1)
    accrual = (0.5 * dt * loss * discount_mid).sum(axis=1)
    protection = (loss * discount_mid).sum(axis=1)
    return TrancheValuation(times, nodes, weights, expected, annuity, accrual, protection)


def cdo_tranche_spread(
    hazard,
    recovery,
    r,
    maturity,
    attach,
    detach,
    n_names,
    rho,
    freq=4,
    m=60,
    copula="gaussian",
    nu=4.0,
) -> float:
    """Breakeven tranche spread C/(A+B) (Hull Example 25.2: 348 bp)."""
    return cdo_tranche_valuation(
        hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m, copula, nu
    ).spread


def cdo_upfront(
    hazard,
    recovery,
    r,
    maturity,
    attach,
    detach,
    n_names,
    rho,
    freq=4,
    m=60,
    copula="gaussian",
    nu=4.0,
    fixed_spread=0.05,
) -> float:
    """Upfront payment C − s*(A+B) for a tranche quoted with a fixed running spread."""
    return cdo_tranche_valuation(
        hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m, copula, nu
    ).upfront(fixed_spread)


# --- kth-to-default ------------------------------------------------------------


@dataclass(frozen=True)
class KthToDefaultValuation:
    """Conditional/unconditional legs of a kth-to-default CDS (Hull §25.10, Example 25.3)."""

    payment_times: np.ndarray
    factor_nodes: np.ndarray
    factor_weights: np.ndarray
    cumulative_prob: np.ndarray
    payoff_by_factor: np.ndarray
    annuity_by_factor: np.ndarray
    accrual_by_factor: np.ndarray

    @property
    def payoff(self) -> float:
        """PV of expected payoff, per unit notional."""
        return float(self.factor_weights @ self.payoff_by_factor)

    @property
    def annuity(self) -> float:
        """PV of regular payments per unit spread."""
        return float(self.factor_weights @ self.annuity_by_factor)

    @property
    def accrual(self) -> float:
        """PV of accrual payments per unit spread."""
        return float(self.factor_weights @ self.accrual_by_factor)

    @property
    def spread(self) -> float:
        """Breakeven spread payoff/(annuity + accrual)."""
        return self.payoff / (self.annuity + self.accrual)


def kth_to_default_valuation(
    k: int,
    n_names: int,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    rho: float,
    freq: int = 1,
    m: int = 60,
    copula: str = "gaussian",
    nu: float = 4.0,
) -> KthToDefaultValuation:
    """Value a kth-to-default CDS by conditioning on the factor (Hull Example 25.3: 153 bp).

    The kth default falls in (t_{j-1}, t_j] with conditional probability
    P(≥k by t_j | F) − P(≥k by t_{j-1} | F); settlement at the midpoint, accrual half
    a period.
    """
    if int(k) != k or int(n_names) != n_names or not 1 <= k <= n_names:
        raise ValueError("k must be an integer in [1, n_names]")
    _check_rho(rho)
    _check_recovery(recovery)
    times, _previous, mid = _payment_grid(maturity, freq)
    nodes, weights = _factor_quadrature(copula, nu, m)
    pmf = _default_count_pmf(hazard, times, rho, nodes, int(n_names), copula, nu)
    at_least_k = np.concatenate(
        [np.zeros((nodes.size, 1)), pmf[:, :, int(k) :].sum(axis=2)], axis=1
    )
    dt = np.diff(np.concatenate([[0.0], times]))
    discount = np.exp(-r * times)
    discount_mid = np.exp(-r * mid)
    trigger = at_least_k[:, 1:] - at_least_k[:, :-1]
    payoff = ((1.0 - recovery) * trigger * discount_mid).sum(axis=1)
    annuity = (dt * (1.0 - at_least_k[:, 1:]) * discount).sum(axis=1)
    accrual = (0.5 * dt * trigger * discount_mid).sum(axis=1)
    return KthToDefaultValuation(times, nodes, weights, at_least_k, payoff, annuity, accrual)


def kth_to_default_spread(
    k, n_names, hazard, recovery, r, maturity, rho, freq=1, m=60, copula="gaussian", nu=4.0
) -> float:
    """Breakeven spread of a kth-to-default CDS."""
    return kth_to_default_valuation(
        k, n_names, hazard, recovery, r, maturity, rho, freq, m, copula, nu
    ).spread


# --- implied correlations -------------------------------------------------------


def compound_correlation(
    quote: float,
    attach: float,
    detach: float,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    n_names: int,
    freq: int = 4,
    m: int = 60,
    quote_kind: str = "spread",
    fixed_spread: float = 0.05,
    bracket: tuple[float, float] = (1e-6, 0.999),
) -> float:
    """Copula correlation at which the model reproduces one tranche quote (Hull §25.10)."""
    if quote_kind not in ("spread", "upfront"):
        raise ValueError("quote_kind must be 'spread' or 'upfront'")

    def gap(rho: float) -> float:
        valuation = cdo_tranche_valuation(
            hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m
        )
        model = valuation.spread if quote_kind == "spread" else valuation.upfront(fixed_spread)
        return model - quote

    try:
        return float(brentq(gap, bracket[0], bracket[1], xtol=1e-12))
    except ValueError as exc:
        raise ValueError(
            "compound_correlation: no correlation in the bracket reproduces the quote"
        ) from exc


@dataclass(frozen=True)
class BaseCorrelationResult:
    """Compound and base correlations with the expected-loss bookkeeping behind them."""

    attachments: np.ndarray
    detachments: np.ndarray
    compound: np.ndarray
    base: np.ndarray
    tranche_expected_loss: np.ndarray
    cumulative_expected_loss: np.ndarray


def base_correlations(
    quotes,
    attachments,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    n_names: int,
    freq: int = 4,
    m: int = 60,
    equity_fixed_spread: float = 0.05,
) -> BaseCorrelationResult:
    """Hull's four-step base-correlation bootstrap (Table 25.8).

    ``attachments`` are the tranche boundaries a_0=0 < a_1 < …; ``quotes[0]`` is the
    equity upfront fraction (running ``equity_fixed_spread``), the rest are spreads.
    Step 1 compound correlations; step 2 C_q per tranche; step 3 cumulative expected
    loss on 0–a_q as a fraction of portfolio principal; step 4 the ρ that prices 0–a_q.
    """
    bounds = np.asarray(attachments, dtype=float)
    quotes = np.asarray(quotes, dtype=float)
    if (
        bounds.ndim != 1
        or bounds.size != quotes.size + 1
        or bounds[0] != 0.0
        or np.any(np.diff(bounds) <= 0.0)
    ):
        raise ValueError(
            "attachments must start at 0, be strictly increasing, and have len(quotes)+1 entries"
        )
    lows, highs = bounds[:-1], bounds[1:]
    compound = np.empty(quotes.size)
    tranche_loss = np.empty(quotes.size)
    for i, (lo, hi, quote) in enumerate(zip(lows, highs, quotes, strict=True)):
        kind = "upfront" if i == 0 else "spread"
        compound[i] = compound_correlation(
            float(quote),
            float(lo),
            float(hi),
            hazard,
            recovery,
            r,
            maturity,
            n_names,
            freq,
            m,
            kind,
            equity_fixed_spread,
        )
        tranche_loss[i] = cdo_tranche_valuation(
            hazard, recovery, r, maturity, float(lo), float(hi), n_names, compound[i], freq, m
        ).protection
    cumulative = np.cumsum(tranche_loss * (highs - lows))
    base = np.empty(quotes.size)
    for i, hi in enumerate(highs):
        target = cumulative[i] / hi

        def gap(rho: float, hi: float = float(hi), target: float = float(target)) -> float:
            protection = cdo_tranche_valuation(
                hazard, recovery, r, maturity, 0.0, hi, n_names, rho, freq, m
            ).protection
            return protection - target

        try:
            base[i] = brentq(gap, 1e-6, 0.999, xtol=1e-12)
        except ValueError as exc:
            raise ValueError(
                f"base_correlations: no correlation prices the 0-{hi:.0%} tranche"
            ) from exc
    return BaseCorrelationResult(lows, highs, compound, base, tranche_loss, cumulative)


def expected_loss_curve(
    detachments,
    base_correlations,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    n_names: int,
    freq: int = 4,
    m: int = 60,
):
    """PV of expected loss on the 0–X% tranche as a fraction of portfolio principal (Fig. 25.3)."""
    detachments = np.asarray(detachments, dtype=float)
    rhos = np.asarray(base_correlations, dtype=float)
    if detachments.shape != rhos.shape:
        raise ValueError("detachments and base_correlations must have equal length")
    values = []
    for x, rho in zip(detachments, rhos, strict=True):
        valuation = cdo_tranche_valuation(
            hazard, recovery, r, maturity, 0.0, float(x), n_names, float(rho), freq, m
        )
        values.append(valuation.protection * float(x))
    return np.asarray(values)


# --- validation helpers ------------------------------------------------------------


def _check_rho(rho: float) -> None:
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")


def _check_recovery(recovery: float) -> None:
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")


def _check_tranche(attach: float, detach: float) -> None:
    if not 0.0 <= attach < detach <= 1.0:
        raise ValueError("tranche must satisfy 0 <= attach < detach <= 1")


def _check_nu(nu: float) -> None:
    if not nu > 2.0:
        raise ValueError("nu must exceed 2 so the t distribution has finite variance")
