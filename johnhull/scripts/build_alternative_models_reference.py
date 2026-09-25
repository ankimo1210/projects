"""Independent numerical reference for Hull 11e GE §27.1 (pp.641–646).

Uses a local-volatility PDE, original-Poisson conditional payoffs and a
gamma-density integral. No hullkit imports. All examples are synthetic.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.linalg import solve_banded
from scipy.optimize import brentq
from scipy.special import ndtr
from scipy.stats import gamma as gamma_dist
from scipy.stats import lognorm, poisson

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-1/reference.json"


def _black_call(spot, strike, rate, vol, expiry, dividend=0.0):
    width = vol * math.sqrt(expiry)
    d1 = (math.log(spot / strike) + (rate - dividend + vol * vol / 2) * expiry) / width
    return spot * math.exp(-dividend * expiry) * ndtr(d1) - strike * math.exp(
        -rate * expiry
    ) * ndtr(d1 - width)


def _implied(price, spot, strike, rate, expiry):
    return brentq(lambda vol: _black_call(spot, strike, rate, vol, expiry) - price, 0.001, 2.0)


def cev_pde(
    spot, strike, rate, vol_at_spot, expiry, beta, dividend=0.0, *, n_space=1000, n_time=800
):
    """Independent Crank–Nicolson local-volatility price, 0<beta<1."""
    upper = 4 * spot
    ds = upper / n_space
    dt = expiry / n_time
    x = np.linspace(0, upper, n_space + 1)
    sigma = vol_at_spot * spot ** (1 - beta)
    values = np.maximum(x - strike, 0.0)
    inner = x[1:-1]
    variance = (sigma * inner**beta) ** 2
    lower = (variance / ds**2 - (rate - dividend) * inner / ds) / 2
    diagonal = -variance / ds**2 - rate
    upper_coeff = (variance / ds**2 + (rate - dividend) * inner / ds) / 2
    left = -dt * lower / 2
    center = 1 - dt * diagonal / 2
    right = -dt * upper_coeff / 2
    band = np.zeros((3, n_space - 1))
    band[0, 1:] = right[:-1]
    band[1] = center
    band[2, :-1] = left[1:]
    for step in range(n_time):
        elapsed = (step + 1) * dt
        rhs = (1 + dt * diagonal / 2) * values[1:-1]
        rhs[1:] += dt * lower[1:] * values[1:-2] / 2
        rhs[:-1] += dt * upper_coeff[:-1] * values[2:-1] / 2
        right_boundary_old = upper * math.exp(-dividend * (elapsed - dt)) - strike * math.exp(
            -rate * (elapsed - dt)
        )
        right_boundary_new = upper * math.exp(-dividend * elapsed) - strike * math.exp(
            -rate * elapsed
        )
        rhs[-1] += dt * upper_coeff[-1] * (right_boundary_old + right_boundary_new) / 2
        values[1:-1] = solve_banded((1, 1), band, rhs, check_finite=False)
        values[-1] = right_boundary_new
    return float(np.interp(spot, x, values))


def merton_conditional(spot, strike, rate, sigma, expiry, intensity, mean, jump_vol):
    """Sum discounted original-Poisson conditional lognormal payoffs."""
    jump_pct = math.exp(mean + jump_vol * jump_vol / 2) - 1
    total = 0.0
    for count in range(60):
        width = math.sqrt(sigma * sigma * expiry + count * jump_vol * jump_vol)
        median = (
            math.log(spot)
            + (rate - intensity * jump_pct - sigma * sigma / 2) * expiry
            + count * mean
        )
        d2 = (median - math.log(strike)) / width
        conditional = math.exp(median + width * width / 2) * ndtr(d2 + width) - strike * ndtr(d2)
        total += poisson.pmf(count, intensity * expiry) * conditional
    return math.exp(-rate * expiry) * total


def vg_gamma_integral(spot, strike, rate, sigma, expiry, nu, theta):
    """Condition on gamma time, then integrate the lognormal call payoff."""
    omega = math.log(1 - theta * nu - sigma * sigma * nu / 2) / nu

    def integrand(clock):
        width = sigma * math.sqrt(clock)
        median = math.log(spot) + (rate + omega) * expiry + theta * clock
        d2 = (median - math.log(strike)) / width
        payoff = math.exp(median + width * width / 2) * ndtr(d2 + width) - strike * ndtr(d2)
        return payoff * gamma_dist.pdf(clock, a=expiry / nu, scale=nu)

    price, error = quad(integrand, 0, math.inf, epsabs=1e-9, epsrel=1e-9)
    if error > 1e-7:
        raise ArithmeticError(f"VG quadrature uncertainty {error}")
    return math.exp(-rate * expiry) * price


def build():
    """Return deterministic source-backed data for the four teaching figures."""
    spot, rate, sigma, expiry = 100.0, 0.05, 0.2, 0.5
    strikes = np.linspace(75, 125, 26)
    merton_prices = [
        merton_conditional(spot, float(k), rate, sigma, 0.25, 1.0, -0.1, 0.15) for k in strikes
    ]
    merton_iv = [
        _implied(p, spot, float(k), rate, 0.25) for p, k in zip(merton_prices, strikes, strict=True)
    ]
    vg_prices = [vg_gamma_integral(spot, float(k), 0.0, sigma, expiry, 0.5, 0.1) for k in strikes]
    vg_iv = [
        _implied(p, spot, float(k), 0.0, expiry) for p, k in zip(vg_prices, strikes, strict=True)
    ]
    local_spots = np.linspace(60, 140, 81)
    pde = {str(k): cev_pde(spot, k, rate, sigma, expiry, 0.8) for k in (80.0, 100.0, 120.0)}
    counts = np.arange(9)
    # VG Figure 27.1 parameters. Both processes use the same sigma=20%.
    rng = np.random.default_rng(2701)
    clocks = rng.gamma(shape=1.0, scale=0.5, size=400_000)
    omega = math.log(1 - 0.1 * 0.5 - 0.5 * sigma**2 * 0.5) / 0.5
    vg_returns = (
        omega * expiry + 0.1 * clocks + sigma * np.sqrt(clocks) * rng.standard_normal(len(clocks))
    )
    terminal_prices = spot * np.exp(vg_returns)
    edges = np.linspace(40, 200, 81)
    hist, _ = np.histogram(terminal_prices, bins=edges)
    hist = hist / (len(terminal_prices) * np.diff(edges))
    mids = (edges[:-1] + edges[1:]) / 2
    return {
        "section": "27.1",
        "source": "Hull 11e Global Edition pp.641–646, Table 27.1, Figure 27.1",
        "units": "prices in currency; time in years; rate/volatility annualized; terminal-stock-price densities per currency",
        "cev": {
            "spot": spot,
            "rate": rate,
            "expiry": expiry,
            "vol_at_spot": sigma,
            "spots": local_spots.tolist(),
            "local_vol": {
                str(beta): (sigma * (local_spots / spot) ** (beta - 1)).tolist()
                for beta in (0.7, 1.0, 1.3)
            },
            "pde_beta_0_8_calls": pde,
        },
        "merton": {
            "spot": spot,
            "rate": rate,
            "expiry": 0.25,
            "sigma": sigma,
            "intensity": 1.0,
            "jump_mean": -0.1,
            "jump_vol": 0.15,
            "strikes": strikes.tolist(),
            "prices": merton_prices,
            "implied_vol": merton_iv,
        },
        "poisson_table": {
            "intensity": 0.5,
            "expiry": 2.0,
            "counts": counts.tolist(),
            "probability": poisson.pmf(counts, 1.0).tolist(),
            "cumulative": poisson.cdf(counts, 1.0).tolist(),
        },
        "variance_gamma": {
            "spot": spot,
            "rate": 0.0,
            "expiry": expiry,
            "sigma": sigma,
            "nu": 0.5,
            "theta": 0.1,
            "strikes": strikes.tolist(),
            "prices": vg_prices,
            "implied_vol": vg_iv,
            "terminal_price_centers": mids.tolist(),
            "sample_density": hist.tolist(),
            "bsm_density": lognorm.pdf(
                mids, s=sigma * math.sqrt(expiry), scale=spot * math.exp(-(sigma**2) * expiry / 2)
            ).tolist(),
            "sample_size": len(clocks),
            "seed": 2701,
        },
        "limitations": "CEV PDE comparison is for beta=0.8 only. VG density is seeded Monte Carlo; price uses independent gamma integration. No calibration, transaction costs, or dynamic hedge study.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: alternative-model reference differs; regenerate and review")
        print(
            "PASS: alternative-model reference is reproducible",
            hashlib.sha256(payload.encode()).hexdigest(),
        )
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
