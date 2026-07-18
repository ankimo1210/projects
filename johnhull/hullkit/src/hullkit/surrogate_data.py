"""Uncertainty-aware analytic, COS, and Monte-Carlo surrogate teachers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from . import bsm, fourier, heston, sabr, volatility


@dataclass(frozen=True)
class MonteCarloEstimate:
    estimate: float
    standard_error: float
    ci_lower: float
    ci_upper: float
    path_count: int
    method: str
    seed: int
    estimand: str = "price"
    path_stream_fingerprint: str | None = None

    def to_dict(self):
        return {
            "estimate": self.estimate,
            "standard_error": self.standard_error,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "path_count": self.path_count,
            "method": self.method,
            "seed": self.seed,
            "estimand": self.estimand,
            "path_stream_fingerprint": self.path_stream_fingerprint,
        }


@dataclass(frozen=True)
class MonteCarloCallEstimates:
    """Price and pathwise Greeks estimated from one common path stream."""

    price: MonteCarloEstimate
    delta: MonteCarloEstimate
    vega: MonteCarloEstimate
    common_random_numbers: bool = True

    def __post_init__(self):
        estimates = (self.price, self.delta, self.vega)
        if {item.estimand for item in estimates} != {"price", "delta", "vega"}:
            raise ValueError("price, delta and vega estimands are required")
        if len({(item.seed, item.path_count) for item in estimates}) != 1:
            raise ValueError("common-random-number estimates must share seed and path count")
        fingerprints = {item.path_stream_fingerprint for item in estimates}
        if self.common_random_numbers and (None in fingerprints or len(fingerprints) != 1):
            raise ValueError("common-random-number estimates must share one path stream")

    def to_dict(self):
        return {
            "price": self.price.to_dict(),
            "delta": self.delta.to_dict(),
            "vega": self.vega.to_dict(),
            "common_random_numbers": self.common_random_numbers,
        }


def analytic_bsm_rows(inputs):
    """Convert ``(x,tau,r,q,sigma)`` rows into the shared teacher schema."""
    inputs = np.asarray(inputs, dtype=float)
    if inputs.ndim != 2 or inputs.shape[1] != 5:
        raise ValueError("inputs must have shape (n, 5)")
    x, tau, rate, dividend, sigma = inputs.T
    price = bsm.call_price(x, 1.0, rate, sigma, tau, dividend)
    return {
        "inputs": inputs,
        "price": np.asarray(price),
        "delta": np.asarray(bsm.call_delta(x, 1.0, rate, sigma, tau, dividend)),
        "gamma": np.asarray(bsm.gamma(x, 1.0, rate, sigma, tau, dividend)),
        "vega": np.asarray(bsm.vega(x, 1.0, rate, sigma, tau, dividend)),
        "theta": np.asarray(bsm.call_theta(x, 1.0, rate, sigma, tau, dividend)),
        "rho": np.asarray(bsm.call_rho(x, 1.0, rate, sigma, tau, dividend)),
        "standard_error": np.zeros(len(inputs)),
        "ci_lower": np.asarray(price),
        "ci_upper": np.asarray(price),
        "method": "analytic_bsm",
    }


def _controlled_estimate(
    samples,
    controls,
    known_control,
    *,
    n_paths,
    method,
    seed,
    estimand,
    path_stream_fingerprint,
):
    samples = np.asarray(samples, dtype=float)
    controls = np.asarray(controls, dtype=float)
    variance = float(np.var(controls, ddof=1))
    beta = float(np.cov(samples, controls, ddof=1)[0, 1] / variance) if variance > 0 else 0.0
    adjusted = samples - beta * (controls - known_control)
    estimate = float(adjusted.mean())
    se = float(adjusted.std(ddof=1) / np.sqrt(n_paths))
    half_width = 1.959963984540054 * se
    return MonteCarloEstimate(
        estimate=estimate,
        standard_error=se,
        ci_lower=estimate - half_width,
        ci_upper=estimate + half_width,
        path_count=n_paths,
        method=method,
        seed=seed,
        estimand=estimand,
        path_stream_fingerprint=path_stream_fingerprint,
    )


def mc_black_scholes_call_estimates(
    S0,
    K,
    r,
    T,
    sigma,
    *,
    q=0.0,
    n_paths=100_000,
    seed=0,
    chunk_size=65_536,
):
    """Estimate call price, pathwise delta and vega on one CRN stream."""
    if min(S0, K, T, sigma) <= 0 or n_paths < 4 or chunk_size <= 0:
        raise ValueError("positive market inputs and at least four paths are required")
    rng = np.random.default_rng(seed)
    payoffs = []
    discounted_terminals = []
    pathwise_deltas = []
    delta_controls = []
    pathwise_vegas = []
    vega_controls = []
    stream_hash = hashlib.sha256()
    remaining = n_paths
    discount = np.exp(-r * T)
    root_maturity = np.sqrt(T)
    while remaining:
        count = min(remaining, chunk_size)
        half = (count + 1) // 2
        z = rng.standard_normal(half)
        z = np.concatenate((z, -z))[:count]
        stream_hash.update(np.asarray(z, dtype="<f8").tobytes())
        terminal = S0 * np.exp((r - q - 0.5 * sigma**2) * T + sigma * root_maturity * z)
        in_the_money = terminal > K
        discounted_terminal = discount * terminal
        terminal_vega = discounted_terminal * (root_maturity * z - sigma * T)
        payoffs.append(discount * np.maximum(terminal - K, 0.0))
        discounted_terminals.append(discounted_terminal)
        pathwise_deltas.append(in_the_money * discounted_terminal / S0)
        delta_controls.append(discounted_terminal / S0)
        pathwise_vegas.append(in_the_money * terminal_vega)
        vega_controls.append(terminal_vega)
        remaining -= count
    payoff = np.concatenate(payoffs)
    discounted_terminal = np.concatenate(discounted_terminals)
    fingerprint = f"sha256:{stream_hash.hexdigest()}"
    common = {
        "n_paths": n_paths,
        "seed": seed,
        "path_stream_fingerprint": fingerprint,
    }
    return MonteCarloCallEstimates(
        price=_controlled_estimate(
            payoff,
            discounted_terminal,
            S0 * np.exp(-q * T),
            method="mc_antithetic_control_variate",
            estimand="price",
            **common,
        ),
        delta=_controlled_estimate(
            np.concatenate(pathwise_deltas),
            np.concatenate(delta_controls),
            np.exp(-q * T),
            method="mc_antithetic_control_variate_pathwise_delta",
            estimand="delta",
            **common,
        ),
        vega=_controlled_estimate(
            np.concatenate(pathwise_vegas),
            np.concatenate(vega_controls),
            0.0,
            method="mc_antithetic_control_variate_pathwise_vega",
            estimand="vega",
            **common,
        ),
    )


def mc_black_scholes_call(
    S0,
    K,
    r,
    T,
    sigma,
    *,
    q=0.0,
    n_paths=100_000,
    seed=0,
    chunk_size=65_536,
):
    """Backward-compatible price view of the joint CRN estimator."""
    return mc_black_scholes_call_estimates(
        S0,
        K,
        r,
        T,
        sigma,
        q=q,
        n_paths=n_paths,
        seed=seed,
        chunk_size=chunk_size,
    ).price


def mc_bsm_rows(inputs, *, n_paths=20_000, seed=0, chunk_size=20_000):
    """Create uncertainty rows for MC price, pathwise delta and pathwise vega."""
    inputs = np.asarray(inputs, dtype=float)
    if inputs.ndim != 2 or inputs.shape[1] != 5:
        raise ValueError("inputs must have shape (n, 5)")
    estimates = [
        mc_black_scholes_call_estimates(
            row[0],
            1.0,
            row[2],
            row[1],
            row[4],
            q=row[3],
            n_paths=n_paths,
            seed=seed + index,
            chunk_size=chunk_size,
        )
        for index, row in enumerate(inputs)
    ]
    rows = {
        "inputs": inputs,
        "method": "mc_antithetic_control_variate_pathwise",
        "path_count": n_paths,
        "seed": seed,
        "row_seed": np.arange(seed, seed + len(inputs), dtype=np.int64),
        "common_random_numbers": True,
        "estimands": ("price", "delta", "vega"),
        "unsupported_greeks": ("gamma", "theta", "rho"),
        "path_stream_fingerprint": np.asarray(
            [item.price.path_stream_fingerprint for item in estimates]
        ),
    }
    for name in rows["estimands"]:
        values = [getattr(item, name) for item in estimates]
        rows[name] = np.asarray([item.estimate for item in values])
        rows[f"{name}_standard_error"] = np.asarray([item.standard_error for item in values])
        rows[f"{name}_ci_lower"] = np.asarray([item.ci_lower for item in values])
        rows[f"{name}_ci_upper"] = np.asarray([item.ci_upper for item in values])
    # Preserve the original price-uncertainty aliases for existing consumers.
    rows["standard_error"] = rows["price_standard_error"]
    rows["ci_lower"] = rows["price_ci_lower"]
    rows["ci_upper"] = rows["price_ci_upper"]
    return rows


def heston_cos_price(S0, K, r, T, *, v0, kappa, theta, xi, rho, N=256):
    """Stable Heston/COS teacher adapter."""

    def cf(u):
        return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)

    return fourier.cos_price(cf, S0, K, r, T, N=N)


def rbergomi_call_price(
    S0,
    K,
    r,
    T,
    *,
    xi0,
    eta,
    hurst,
    rho,
    n_steps=32,
    n_paths=20_000,
    seed=0,
):
    """Seeded rough-Bergomi Monte-Carlo call teacher with a Volterra kernel."""
    if (
        min(S0, K, T, xi0) <= 0
        or eta < 0
        or not 0 < hurst < 0.5
        or not -1 < rho < 1
        or n_steps < 2
        or n_paths < 100
    ):
        raise ValueError("invalid rough-Bergomi inputs")
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    half = (n_paths + 1) // 2
    z1 = rng.standard_normal((half, n_steps))
    z2 = rng.standard_normal((half, n_steps))
    z1 = np.concatenate([z1, -z1], axis=0)[:n_paths]
    z2 = np.concatenate([z2, -z2], axis=0)[:n_paths]
    d_w = np.sqrt(dt) * z1
    d_b = np.sqrt(dt) * (rho * z1 + np.sqrt(1 - rho**2) * z2)
    times = np.arange(1, n_steps + 1) * dt
    rough = np.zeros((n_paths, n_steps))
    normalizer = np.sqrt(2 * hurst)
    for index in range(n_steps):
        lags = (np.arange(index, -1, -1) + 1) * dt
        kernel = normalizer * lags ** (hurst - 0.5)
        rough[:, index] = d_w[:, : index + 1] @ kernel
    variance = xi0 * np.exp(eta * rough - 0.5 * eta**2 * times[np.newaxis, :] ** (2 * hurst))
    log_terminal = np.log(S0) + np.sum(
        (r - 0.5 * variance) * dt + np.sqrt(variance) * d_b,
        axis=1,
    )
    payoff = np.exp(-r * T) * np.maximum(np.exp(log_terminal) - K, 0.0)
    estimate = float(payoff.mean())
    se = float(payoff.std(ddof=1) / np.sqrt(n_paths))
    width = 1.959963984540054 * se
    return MonteCarloEstimate(
        estimate=estimate,
        standard_error=se,
        ci_lower=estimate - width,
        ci_upper=estimate + width,
        path_count=n_paths,
        method="rbergomi_mc_antithetic",
        seed=seed,
    )


def forward_surface_teacher(
    model,
    spot,
    strikes,
    maturities,
    rate,
    parameters,
    *,
    seed=0,
    n_paths=10_000,
):
    """Return price/IV surfaces from numerical Heston, SABR, or rBergomi teachers."""
    strikes = np.asarray(strikes, dtype=float)
    maturities = np.asarray(maturities, dtype=float)
    if (
        model not in {"heston", "sabr", "rbergomi"}
        or spot <= 0
        or strikes.ndim != 1
        or maturities.ndim != 1
        or np.any(strikes <= 0)
        or np.any(maturities <= 0)
    ):
        raise ValueError("invalid forward-surface teacher inputs")
    prices = np.empty((len(maturities), len(strikes)))
    standard_errors = np.zeros_like(prices)
    for maturity_index, maturity in enumerate(maturities):
        forward = spot * np.exp(rate * maturity)
        for strike_index, strike in enumerate(strikes):
            if model == "heston":
                prices[maturity_index, strike_index] = heston_cos_price(
                    spot,
                    strike,
                    rate,
                    maturity,
                    **parameters,
                )
            elif model == "sabr":
                implied = sabr.sabr_implied_vol(
                    forward,
                    strike,
                    maturity,
                    parameters["alpha"],
                    parameters["beta"],
                    parameters["rho"],
                    parameters["nu"],
                )
                prices[maturity_index, strike_index] = bsm.call_price(
                    spot,
                    strike,
                    rate,
                    implied,
                    maturity,
                )
            else:
                estimate = rbergomi_call_price(
                    spot,
                    strike,
                    rate,
                    maturity,
                    **parameters,
                    n_paths=n_paths,
                    seed=seed + maturity_index * len(strikes) + strike_index,
                )
                prices[maturity_index, strike_index] = estimate.estimate
                standard_errors[maturity_index, strike_index] = estimate.standard_error
    implied_volatility = np.empty_like(prices)
    for maturity_index, maturity in enumerate(maturities):
        for strike_index, strike in enumerate(strikes):
            implied_volatility[maturity_index, strike_index] = volatility.implied_vol(
                prices[maturity_index, strike_index],
                spot,
                strike,
                rate,
                maturity,
            )
    return {
        "model": model,
        "strikes": strikes,
        "maturities": maturities,
        "price": prices,
        "implied_volatility": implied_volatility,
        "standard_error": standard_errors,
        "method": {
            "heston": "heston_cos",
            "sabr": "hagan_sabr_to_bsm",
            "rbergomi": "rbergomi_mc_antithetic",
        }[model],
    }
