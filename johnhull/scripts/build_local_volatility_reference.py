"""Independent synthetic §27.3 reference: analytic mixture and backward PDE.

No hullkit imports. A latent two-volatility lognormal mixture gives a smooth,
arbitrage-free call surface. Its exact Dupire coefficient is a density-weighted
conditional variance; the backward PDE checks vanilla repricing independently.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import solve_banded
from scipy.optimize import brentq
from scipy.special import logsumexp
from scipy.stats import norm

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-3/reference.json"
SPOT, RATE, DIVIDEND = 100.0, 0.03, 0.01
WEIGHTS, SIGMAS = (0.7, 0.3), (0.15, 0.35)
STRIKES = tuple(float(k) for k in range(75, 126, 5))
MATURITIES = (0.5, 1.0, 2.0)


def black_scholes_call(spot, strike, maturity, sigma):
    """Closed-form call for a constant-vol component; independent of hullkit."""
    root_t = math.sqrt(maturity)
    d1 = (np.log(spot / strike) + (RATE - DIVIDEND + 0.5 * sigma**2) * maturity) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    return spot * math.exp(-DIVIDEND * maturity) * norm.cdf(d1) - strike * math.exp(
        -RATE * maturity
    ) * norm.cdf(d2)


def mixture_call(strike, maturity):
    """Arbitrage-free European call surface from an inception-time volatility draw."""
    return sum(
        w * black_scholes_call(SPOT, strike, maturity, s)
        for w, s in zip(WEIGHTS, SIGMAS, strict=True)
    )


def component_density(strike, maturity, sigma):
    """Strike butterfly divided by discount factor, for one BSM component."""
    d2 = (np.log(SPOT / strike) + (RATE - DIVIDEND - 0.5 * sigma**2) * maturity) / (
        sigma * np.sqrt(maturity)
    )
    return norm.pdf(d2) / (strike * sigma * np.sqrt(maturity))


def exact_local_vol(strike, maturity):
    """Conditional second moment of the latent volatility given S_t=K."""
    k = np.asarray(strike, dtype=float)
    logs = []
    for weight, sigma in zip(WEIGHTS, SIGMAS, strict=True):
        d2 = (np.log(SPOT / k) + (RATE - DIVIDEND - 0.5 * sigma**2) * maturity) / (
            sigma * np.sqrt(maturity)
        )
        logs.append(math.log(weight) + norm.logpdf(d2) - np.log(k * sigma * np.sqrt(maturity)))
    probabilities = np.exp(np.stack(logs) - logsumexp(np.stack(logs), axis=0))
    return np.sqrt(sum(probabilities[i] * sigma**2 for i, sigma in enumerate(SIGMAS)))


def implied_vol(strike, maturity):
    """Invert the mixture call into a BSM smile without using hullkit."""
    target = mixture_call(strike, maturity)
    return brentq(lambda vol: black_scholes_call(SPOT, strike, maturity, vol) - target, 0.01, 1.0)


def backward_pde_call(strike, maturity, *, ds=0.5, steps_per_year=400):
    """Crank–Nicolson price with the analytic local vol in the *spot* operator."""
    smax = 400.0
    grid = np.arange(0.0, smax + ds / 2, ds)
    interior = grid[1:-1]
    n_steps = round(maturity * steps_per_year)
    dt = maturity / n_steps
    value = np.maximum(grid - strike, 0.0)
    for step in range(n_steps - 1, -1, -1):
        time = (step + 0.5) * dt
        volatility = exact_local_vol(interior, time)
        diffusion = 0.5 * volatility**2 * interior**2
        drift = (RATE - DIVIDEND) * interior
        low = diffusion / ds**2 - drift / (2 * ds)
        diagonal = -2 * diffusion / ds**2 - RATE
        high = diffusion / ds**2 + drift / (2 * ds)
        rhs = value[1:-1] + 0.5 * dt * (
            low * value[:-2] + diagonal * value[1:-1] + high * value[2:]
        )
        old_upper = smax * math.exp(-DIVIDEND * (maturity - step * dt)) - strike * math.exp(
            -RATE * (maturity - step * dt)
        )
        rhs[-1] += 0.5 * dt * high[-1] * old_upper
        bands = np.zeros((3, len(interior)))
        bands[0, 1:] = -0.5 * dt * high[:-1]
        bands[1] = 1 - 0.5 * dt * diagonal
        bands[2, :-1] = -0.5 * dt * low[1:]
        value[1:-1] = solve_banded((1, 1), bands, rhs)
        value[-1] = old_upper
    return float(np.interp(SPOT, grid, value))


def two_date_model_comparison():
    """Common-random-number joint digital under latent and local-vol paths.

    The latent process draws one constant volatility at inception. The local
    process uses its exact conditional variance coefficient but Euler log
    steps. Both have the same continuous-time European call surface; the MC
    result quantifies a genuinely path-dependent difference for this example.
    """
    seed, paths, steps = 273, 150_000, 200
    rng = np.random.default_rng(seed)
    dt = 1.0 / steps
    latent_sigma = np.where(rng.random(paths) < WEIGHTS[0], SIGMAS[0], SIGMAS[1])
    latent = np.full(paths, SPOT)
    local = np.full(paths, SPOT)
    for step in range(steps):
        z = rng.standard_normal(paths)
        time = (step + 0.5) * dt
        sigma_local = exact_local_vol(local, time)
        latent *= np.exp(
            (RATE - DIVIDEND - 0.5 * latent_sigma**2) * dt + latent_sigma * math.sqrt(dt) * z
        )
        local *= np.exp(
            (RATE - DIVIDEND - 0.5 * sigma_local**2) * dt + sigma_local * math.sqrt(dt) * z
        )
        if step == steps // 2 - 1:
            latent_half = latent.copy()
            local_half = local.copy()

    def event(a, b):
        baseline, modeled = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
        paired = modeled.astype(float) - baseline.astype(float)
        return {
            "latent_probability": float(baseline.mean()),
            "local_probability": float(modeled.mean()),
            "paired_difference": float(paired.mean()),
            "paired_standard_error": float(paired.std(ddof=1) / math.sqrt(paths)),
        }

    return {
        "seed": seed,
        "paths": paths,
        "steps": steps,
        "threshold": SPOT,
        "half_year_up": event(latent_half > SPOT, local_half > SPOT),
        "one_year_up": event(latent > SPOT, local > SPOT),
        "both_dates_up": event(
            (latent_half > SPOT) & (latent > SPOT), (local_half > SPOT) & (local > SPOT)
        ),
    }


def build():
    """Return deterministic reference values for §27.3 figures and checks."""
    prices = []
    for maturity in MATURITIES:
        row = []
        for strike in (80.0, 100.0, 120.0):
            row.append(
                {
                    "maturity": maturity,
                    "strike": strike,
                    "market_call": float(mixture_call(strike, maturity)),
                    "local_vol_pde_call": backward_pde_call(strike, maturity),
                }
            )
        prices.extend(row)
    return {
        "section": "27.3",
        "source": "Hull 11e GE pp.649–650, eq. (27.4); synthetic latent-volatility mixture",
        "units": "spot/strike/call in currency; maturity in years; rates and volatilities annual decimals",
        "parameters": {
            "spot": SPOT,
            "rate": RATE,
            "dividend_yield": DIVIDEND,
            "weights": list(WEIGHTS),
            "component_volatilities": list(SIGMAS),
        },
        "strikes": list(STRIKES),
        "maturities": list(MATURITIES),
        "slices": {
            str(t): {
                "calls": [float(mixture_call(k, t)) for k in STRIKES],
                "implied_vols": [float(implied_vol(k, t)) for k in STRIKES],
                "local_vols": [float(exact_local_vol(k, t)) for k in STRIKES],
                "component_densities": [
                    [float(component_density(k, t, s)) for k in STRIKES] for s in SIGMAS
                ],
            }
            for t in MATURITIES
        },
        "pde_repricing": prices,
        "two_date_models": two_date_model_comparison(),
        "pde_grid": {"spot_step": 0.5, "steps_per_year": 400, "spot_max": 400},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: independent §27.3 reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.3 independent analytic mixture and backward PDE reference")


if __name__ == "__main__":
    main()
