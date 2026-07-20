"""Synthetic carbon-futures option models and risk-premium sensitivities.

Black-76 is the analytic baseline.  A full-truncation stochastic-variance
simulation is the challenger, with optional compensated lognormal jumps.  The
module uses synthetic inputs only; it neither embeds nor downloads allowance
market data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np

OptionKind = Literal["call", "put"]
CarbonModel = Literal["gbm", "heston", "sv_jump"]


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    value = float(value)
    valid = value >= 0.0 if allow_zero else value > 0.0
    if not np.isfinite(value) or not valid:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return value


def _option_kind(kind: OptionKind) -> OptionKind:
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")
    return kind


def black76_price(
    forward: float,
    strike: float,
    rate: float,
    volatility: float,
    maturity: float,
    *,
    kind: OptionKind = "call",
) -> float:
    """Black-76 European option price on a carbon allowance future."""

    forward = _positive(forward, "forward")
    strike = _positive(strike, "strike")
    volatility = _positive(volatility, "volatility", allow_zero=True)
    maturity = _positive(maturity, "maturity", allow_zero=True)
    kind = _option_kind(kind)
    discount = math.exp(-float(rate) * maturity)
    if maturity == 0.0 or volatility == 0.0:
        payoff = max(forward - strike, 0.0) if kind == "call" else max(strike - forward, 0.0)
        return float(discount * payoff)
    vol_sqrt_t = volatility * math.sqrt(maturity)
    d1 = math.log(forward / strike) / vol_sqrt_t + 0.5 * vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    normal = NormalDist()
    if kind == "call":
        value = forward * normal.cdf(d1) - strike * normal.cdf(d2)
    else:
        value = strike * normal.cdf(-d2) - forward * normal.cdf(-d1)
    return float(discount * value)


@dataclass(frozen=True)
class CarbonDynamics:
    """Annualized synthetic stochastic-variance and jump parameters."""

    v0: float = 0.09
    kappa: float = 2.0
    theta: float = 0.09
    vol_of_vol: float = 0.40
    rho: float = -0.40
    jump_intensity: float = 0.0
    jump_mean: float = -0.05
    jump_volatility: float = 0.10

    def __post_init__(self) -> None:
        for value, name in (
            (self.v0, "v0"),
            (self.kappa, "kappa"),
            (self.theta, "theta"),
            (self.vol_of_vol, "vol_of_vol"),
            (self.jump_intensity, "jump_intensity"),
            (self.jump_volatility, "jump_volatility"),
        ):
            _positive(value, name, allow_zero=True)
        if self.kappa == 0.0:
            raise ValueError("kappa must be positive")
        if not np.isfinite(self.rho) or not -1.0 <= self.rho <= 1.0:
            raise ValueError("rho must lie in [-1, 1]")
        if not np.isfinite(self.jump_mean):
            raise ValueError("jump_mean must be finite")


@dataclass(frozen=True)
class CarbonRiskPremia:
    """Independent annualized scenario shifts, not calibrated market facts."""

    return_premium: float = 0.0
    variance_premium: float = 0.0
    jump_intensity_premium: float = 0.0

    def __post_init__(self) -> None:
        for value, name in (
            (self.return_premium, "return_premium"),
            (self.variance_premium, "variance_premium"),
            (self.jump_intensity_premium, "jump_intensity_premium"),
        ):
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")


def simulate_terminal_futures(
    forward: float,
    maturity: float,
    *,
    model: CarbonModel = "heston",
    dynamics: CarbonDynamics | None = None,
    risk_premia: CarbonRiskPremia | None = None,
    n_steps: int = 64,
    n_paths: int = 20_000,
    seed: int = 0,
) -> np.ndarray:
    """Simulate terminal carbon futures under a transparent scenario measure.

    With zero ``return_premium`` and compensated jumps, the future is a
    martingale up to time-discretization error.  Variance and jump premia alter
    their respective dynamics independently.
    """

    forward = _positive(forward, "forward")
    maturity = _positive(maturity, "maturity", allow_zero=True)
    if not isinstance(n_steps, int) or n_steps < 1:
        raise ValueError("n_steps must be a positive integer")
    if not isinstance(n_paths, int) or n_paths < 2:
        raise ValueError("n_paths must be an integer >= 2")
    if model not in ("gbm", "heston", "sv_jump"):
        raise ValueError("model must be 'gbm', 'heston', or 'sv_jump'")
    dynamics = CarbonDynamics() if dynamics is None else dynamics
    premia = CarbonRiskPremia() if risk_premia is None else risk_premia
    theta = dynamics.theta + premia.variance_premium
    intensity = dynamics.jump_intensity + premia.jump_intensity_premium
    if theta < 0.0:
        raise ValueError("theta + variance_premium must be non-negative")
    if intensity < 0.0:
        raise ValueError("jump intensity after premium must be non-negative")
    if maturity == 0.0:
        return np.full(n_paths, forward)

    rng = np.random.default_rng(seed)
    dt = maturity / n_steps
    sqrt_dt = math.sqrt(dt)
    log_f = np.full(n_paths, math.log(forward))
    variance = np.full(n_paths, dynamics.v0)
    corr_scale = math.sqrt(max(0.0, 1.0 - dynamics.rho**2))
    jump_compensator = intensity * (
        math.exp(dynamics.jump_mean + 0.5 * dynamics.jump_volatility**2) - 1.0
    )

    for _ in range(n_steps):
        z_price = rng.standard_normal(n_paths)
        if model == "gbm":
            used_variance = np.full(n_paths, dynamics.v0)
        else:
            z_independent = rng.standard_normal(n_paths)
            z_variance = dynamics.rho * z_price + corr_scale * z_independent
            used_variance = np.maximum(variance, 0.0)
            variance = (
                variance
                + dynamics.kappa * (theta - used_variance) * dt
                + dynamics.vol_of_vol * np.sqrt(used_variance) * sqrt_dt * z_variance
            )

        drift = premia.return_premium - 0.5 * used_variance
        jump_sum = 0.0
        if model == "sv_jump" and intensity > 0.0:
            jump_count = rng.poisson(intensity * dt, n_paths)
            jump_sum = jump_count * dynamics.jump_mean + np.sqrt(
                jump_count
            ) * dynamics.jump_volatility * rng.standard_normal(n_paths)
            drift -= jump_compensator
        log_f += drift * dt + np.sqrt(used_variance) * sqrt_dt * z_price + jump_sum
    return np.exp(log_f)


@dataclass(frozen=True)
class CarbonOptionEstimate:
    """Monte Carlo carbon option price with standard error and normal 95% CI."""

    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    model: str
    seed: int


def carbon_option_mc(
    forward: float,
    strike: float,
    rate: float,
    maturity: float,
    *,
    kind: OptionKind = "call",
    model: CarbonModel = "heston",
    dynamics: CarbonDynamics | None = None,
    risk_premia: CarbonRiskPremia | None = None,
    n_steps: int = 64,
    n_paths: int = 20_000,
    seed: int = 0,
) -> CarbonOptionEstimate:
    """Monte Carlo price with standard error and a normal 95% interval."""

    strike = _positive(strike, "strike")
    kind = _option_kind(kind)
    terminal = simulate_terminal_futures(
        forward,
        maturity,
        model=model,
        dynamics=dynamics,
        risk_premia=risk_premia,
        n_steps=n_steps,
        n_paths=n_paths,
        seed=seed,
    )
    payoff = (
        np.maximum(terminal - strike, 0.0) if kind == "call" else np.maximum(strike - terminal, 0.0)
    )
    discounted = math.exp(-float(rate) * maturity) * payoff
    price = float(np.mean(discounted))
    standard_error = float(np.std(discounted, ddof=1) / math.sqrt(n_paths))
    return CarbonOptionEstimate(
        price=price,
        standard_error=standard_error,
        ci_low=price - 1.96 * standard_error,
        ci_high=price + 1.96 * standard_error,
        model=model,
        seed=seed,
    )


@dataclass(frozen=True)
class CarbonPremiumSensitivity:
    """Premium shifts from toggling return, variance, and jump risk premia one at a time."""

    baseline: float
    return_shifted: float
    variance_shifted: float
    jump_shifted: float

    @property
    def return_effect(self) -> float:
        """Premium shift attributable to the return risk premium alone."""
        return self.return_shifted - self.baseline

    @property
    def variance_effect(self) -> float:
        """Premium shift attributable to the variance risk premium alone."""
        return self.variance_shifted - self.baseline

    @property
    def jump_effect(self) -> float:
        """Premium shift attributable to the jump risk premium alone."""
        return self.jump_shifted - self.baseline


def risk_premium_sensitivity(
    forward: float,
    strike: float,
    rate: float,
    maturity: float,
    *,
    dynamics: CarbonDynamics | None = None,
    return_bump: float = 0.02,
    variance_bump: float = 0.01,
    jump_intensity_bump: float = 0.25,
    n_steps: int = 64,
    n_paths: int = 20_000,
    seed: int = 0,
) -> CarbonPremiumSensitivity:
    """One-at-a-time return, variance, and jump-premium sensitivity."""

    dynamics = CarbonDynamics(jump_intensity=0.20) if dynamics is None else dynamics

    def price(premia: CarbonRiskPremia) -> float:
        return carbon_option_mc(
            forward,
            strike,
            rate,
            maturity,
            model="sv_jump",
            dynamics=dynamics,
            risk_premia=premia,
            n_steps=n_steps,
            n_paths=n_paths,
            seed=seed,
        ).price

    return CarbonPremiumSensitivity(
        baseline=price(CarbonRiskPremia()),
        return_shifted=price(CarbonRiskPremia(return_premium=return_bump)),
        variance_shifted=price(CarbonRiskPremia(variance_premium=variance_bump)),
        jump_shifted=price(CarbonRiskPremia(jump_intensity_premium=jump_intensity_bump)),
    )
