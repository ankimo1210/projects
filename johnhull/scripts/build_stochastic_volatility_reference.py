"""Independent numerical reference for Hull 11e GE §27.2 (pp.646–649).

Uses a Crank–Nicolson PDE with a time-dependent volatility, Heston prices by
Gil-Pelaez integration of a separately written characteristic function, a
transcription of Hull's printed SABR formula and a SABR Monte Carlo
simulation. No hullkit imports. All markets are synthetic.
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

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-2/reference.json"

TERM = {"spot": 100.0, "rate": 0.05, "durations": [0.5, 0.5], "volatilities": [0.2, 0.3]}
HESTON = {
    "spot": 100.0,
    "rate": 0.05,
    "dividend_yield": 0.0,
    "expiry": 1.0,
    "v0": 0.04,
    "reversion": 1.5,
    "long_run": 0.04,
    "vol_of_variance": 0.6,
}
SABR = {"forward": 0.03, "expiry": 1.0, "beta": 0.5, "atm_lognormal_vol": 0.2}


def _call(spot, strike, rate, vol, expiry, dividend=0.0):
    width = vol * math.sqrt(expiry)
    d1 = (math.log(spot / strike) + (rate - dividend) * expiry) / width + width / 2
    return spot * math.exp(-dividend * expiry) * ndtr(d1) - strike * math.exp(
        -rate * expiry
    ) * ndtr(d1 - width)


def _implied(price, spot, strike, rate, expiry, dividend=0.0):
    return brentq(
        lambda vol: _call(spot, strike, rate, vol, expiry, dividend) - price,
        1e-6,
        5.0,
        xtol=1e-14,
    )


def term_structure_pde(spot, strike, rate, durations, volatilities, n_space=1600, n_time=1600):
    """Crank–Nicolson in log price with sigma(t) a step function of calendar time.

    Two fully implicit half steps start the scheme (Rannacher) to damp the
    payoff kink; the volatility switch falls on a grid time.
    """
    expiry = sum(durations)
    breaks = np.cumsum(durations)
    top_vol = max(volatilities)
    width = 8.0 * top_vol * math.sqrt(expiry)
    x = np.linspace(math.log(spot) - width, math.log(spot) + width, n_space + 1)
    dx = x[1] - x[0]
    values = np.maximum(np.exp(x) - strike, 0.0)
    dtau = expiry / n_time

    def sigma_at(calendar_time):
        index = int(np.searchsorted(breaks, calendar_time, side="right"))
        return volatilities[min(index, len(volatilities) - 1)]

    def operator(vol):
        diffusion = 0.5 * vol * vol / dx**2
        drift = (rate - 0.5 * vol * vol) / (2 * dx)
        return diffusion - drift, -2 * diffusion - rate, diffusion + drift

    def step(values, tau_new, vol, theta, dt):
        low, mid, up = operator(vol)
        interior = values[1:-1]
        explicit = interior + (1 - theta) * dt * (
            low * values[:-2] + mid * interior + up * values[2:]
        )
        lower_boundary = 0.0
        upper_boundary = math.exp(x[-1]) - strike * math.exp(-rate * tau_new)
        explicit[0] += theta * dt * low * lower_boundary
        explicit[-1] += theta * dt * up * upper_boundary
        size = len(interior)
        bands = np.zeros((3, size))
        bands[0, 1:] = -theta * dt * up
        bands[1, :] = 1 - theta * dt * mid
        bands[2, :-1] = -theta * dt * low
        updated = np.empty_like(values)
        updated[1:-1] = solve_banded((1, 1), bands, explicit)
        updated[0], updated[-1] = lower_boundary, upper_boundary
        return updated

    tau = 0.0
    for index in range(n_time):
        # calendar time at the middle of this backward step
        vol = sigma_at(expiry - (tau + dtau / 2))
        if index == 0:
            for _ in range(2):
                tau += dtau / 2
                values = step(values, tau, vol, 1.0, dtau / 2)
        else:
            tau += dtau
            values = step(values, tau, vol, 0.5, dtau)
    return float(np.interp(math.log(spot), x, values))


def heston_log_cf(u, spot, rate, dividend, expiry, v0, reversion, long_run, xi, rho):
    """E[exp(iu ln S_T)] for the correlated square-root model (trap-stable form)."""
    b = reversion - 1j * rho * xi * u
    d = np.sqrt(b * b + xi * xi * (1j * u + u * u))
    g = (b - d) / (b + d)
    decay = np.exp(-d * expiry)
    c = 1j * u * (math.log(spot) + (rate - dividend) * expiry) + reversion * long_run / xi**2 * (
        (b - d) * expiry - 2 * np.log((1 - g * decay) / (1 - g))
    )
    dterm = (b - d) / xi**2 * (1 - decay) / (1 - g * decay)
    return np.exp(c + dterm * v0)


def heston_gil_pelaez_call(strike, rho, market=HESTON):
    """European call from the two Gil-Pelaez exercise probabilities."""
    args = (
        market["spot"],
        market["rate"],
        market["dividend_yield"],
        market["expiry"],
        market["v0"],
        market["reversion"],
        market["long_run"],
        market["vol_of_variance"],
        rho,
    )
    log_k = math.log(strike)
    forward_cf = heston_log_cf(-1j, *args)

    def p1(u):
        return (np.exp(-1j * u * log_k) * heston_log_cf(u - 1j, *args) / (1j * u * forward_cf)).real

    def p2(u):
        return (np.exp(-1j * u * log_k) * heston_log_cf(u, *args) / (1j * u)).real

    settings = dict(limit=800, epsabs=1e-13, epsrel=1e-12)
    prob1 = 0.5 + quad(p1, 0.0, 250.0, **settings)[0] / math.pi
    prob2 = 0.5 + quad(p2, 0.0, 250.0, **settings)[0] / math.pi
    expiry = market["expiry"]
    return (
        market["spot"] * math.exp(-market["dividend_yield"] * expiry) * prob1
        - strike * math.exp(-market["rate"] * expiry) * prob2
    )


def hull_sabr_vol(forward, strike, expiry, sigma0, beta, rho, nu):
    """Hull 11e GE p.648 SABR implied volatility, transcribed term by term."""
    x = (forward * strike) ** ((1 - beta) / 2)
    y = (1 - beta) * math.log(forward / strike)
    a_term = sigma0 / (x * (1 + y * y / 24 + y**4 / 1920))
    b_term = (
        1
        + (
            (1 - beta) ** 2 * sigma0**2 / (24 * x * x)
            + rho * beta * nu * sigma0 / (4 * x)
            + (2 - 3 * rho * rho) / 24 * nu * nu
        )
        * expiry
    )
    if strike == forward:
        return sigma0 * b_term / forward ** (1 - beta)
    phi = nu * x / sigma0 * math.log(forward / strike)
    chi = math.log((math.sqrt(1 - 2 * rho * phi + phi * phi) + phi - rho) / (1 - rho))
    return a_term * b_term * phi / chi


def sabr_monte_carlo(forward, expiry, sigma0, beta, rho, nu, strikes, n_steps, n_paths, seed):
    """Undiscounted out-of-the-money option values from an Euler SABR simulation.

    The volatility is exactly lognormal; the forward uses Euler steps and is
    absorbed at zero. Puts are used below the forward and calls at or above.
    """
    rng = np.random.default_rng(seed)
    dt = expiry / n_steps
    root = math.sqrt(dt)
    level = np.full(n_paths, forward)
    vol = np.full(n_paths, sigma0)
    for _ in range(n_steps):
        z1 = rng.standard_normal(n_paths)
        z2 = rho * z1 + math.sqrt(1 - rho * rho) * rng.standard_normal(n_paths)
        level = np.maximum(level + vol * np.maximum(level, 0.0) ** beta * root * z1, 0.0)
        vol = vol * np.exp(nu * root * z2 - 0.5 * nu * nu * dt)
    rows = []
    for strike in strikes:
        payoff = (
            np.maximum(strike - level, 0.0) if strike < forward else np.maximum(level - strike, 0.0)
        )
        value = float(payoff.mean())
        error = float(payoff.std(ddof=1) / math.sqrt(n_paths))
        call = value + (forward - strike if strike < forward else 0.0)
        implied = _implied(call, forward, strike, 0.0, expiry)
        width = implied * math.sqrt(expiry)
        d1 = math.log(forward / strike) / width + width / 2
        vega = forward * math.sqrt(expiry) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
        rows.append(
            {
                "strike": float(strike),
                "option": "put" if strike < forward else "call",
                "value": value,
                "standard_error": error,
                "implied_vol": implied,
                "implied_vol_standard_error": error / vega,
            }
        )
    return {
        "rows": rows,
        "mean_terminal_forward": float(level.mean()),
        "absorbed_fraction": float(np.mean(level == 0.0)),
    }


def build():
    """Return the saved §27.2 reference payload."""
    # Eq. (27.1): step volatility and the average variance rate.
    durations, vols = TERM["durations"], TERM["volatilities"]
    expiry = sum(durations)
    average = sum(d * v * v for d, v in zip(durations, vols, strict=True)) / expiry
    strikes = [80.0, 100.0, 120.0]
    term_prices = {
        str(k): {
            "pde": term_structure_pde(TERM["spot"], k, TERM["rate"], durations, vols),
            "average_variance_bsm": _call(
                TERM["spot"], k, TERM["rate"], math.sqrt(average), expiry
            ),
            "arithmetic_vol_bsm": _call(
                TERM["spot"],
                k,
                TERM["rate"],
                sum(d * v for d, v in zip(durations, vols, strict=True)) / expiry,
                expiry,
            ),
        }
        for k in strikes
    }
    times = [round(0.01 * i, 2) for i in range(101)]

    def sigma_at(t):
        return vols[0] if t < durations[0] else vols[1]

    def remaining_rms(t):
        if t >= expiry:
            return vols[-1]
        first = max(durations[0] - t, 0.0)
        return math.sqrt(
            (first * vols[0] ** 2 + (expiry - t - first) * vols[1] ** 2) / (expiry - t)
        )

    term = {
        **TERM,
        "expiry": expiry,
        "average_variance": average,
        "average_volatility": math.sqrt(average),
        "arithmetic_volatility": sum(d * v for d, v in zip(durations, vols, strict=True)) / expiry,
        "prices": term_prices,
        "times": times,
        "sigma": [sigma_at(t) for t in times],
        "remaining_rms_vol": [remaining_rms(t) for t in times],
    }

    # Eqs. (27.2)-(27.3) with alpha=0.5: Hull–White (rho=0) and correlation.
    market = HESTON
    forward = market["spot"] * math.exp(
        (market["rate"] - market["dividend_yield"]) * market["expiry"]
    )
    heston_strikes = [60.0 + 4.0 * i for i in range(26)]
    scaled = market["reversion"] * market["expiry"]
    expected_average = (
        market["long_run"] + (market["v0"] - market["long_run"]) * (1 - math.exp(-scaled)) / scaled
    )
    flat = math.sqrt(expected_average)
    smiles = {}
    for rho in (-0.7, 0.0, 0.7):
        prices = [heston_gil_pelaez_call(k, rho) for k in heston_strikes]
        smiles[f"{rho:+.1f}"] = {
            "prices": prices,
            "implied_vol": [
                _implied(p, market["spot"], k, market["rate"], market["expiry"])
                for p, k in zip(prices, heston_strikes, strict=True)
            ],
        }
    flat_prices = [
        _call(market["spot"], k, market["rate"], flat, market["expiry"]) for k in heston_strikes
    ]
    symmetry = []
    for shift in (0.1, 0.2, 0.3, 0.4):
        up, down = forward * math.exp(shift), forward * math.exp(-shift)
        symmetry.append(
            {
                "log_forward_moneyness": shift,
                "upper_vol": _implied(
                    heston_gil_pelaez_call(up, 0.0), market["spot"], up, market["rate"], 1.0
                ),
                "lower_vol": _implied(
                    heston_gil_pelaez_call(down, 0.0), market["spot"], down, market["rate"], 1.0
                ),
            }
        )
    heston = {
        **market,
        "forward": forward,
        "strikes": heston_strikes,
        "expected_average_variance": expected_average,
        "flat_volatility": flat,
        "flat_prices": flat_prices,
        "smiles": smiles,
        "rho_zero_symmetry": symmetry,
    }

    # SABR (p.648) in Hull's notation, beta=0.5 as in rates practice.
    sigma0 = SABR["atm_lognormal_vol"] * SABR["forward"] ** (1 - SABR["beta"])
    sabr_strikes = [round(0.015 + 0.001 * i, 3) for i in range(36)]
    forward_rate, sabr_expiry, beta = SABR["forward"], SABR["expiry"], SABR["beta"]
    rho_group = {
        f"{rho:+.1f}": [
            hull_sabr_vol(forward_rate, k, sabr_expiry, sigma0, beta, rho, 0.4)
            for k in sabr_strikes
        ]
        for rho in (-0.6, 0.0, 0.6)
    }
    nu_group = {
        f"{nu:.1f}": [
            hull_sabr_vol(forward_rate, k, sabr_expiry, sigma0, beta, 0.0, nu) for k in sabr_strikes
        ]
        for nu in (0.2, 0.4, 0.8)
    }
    mc_strikes = [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05]
    mc = sabr_monte_carlo(
        SABR["forward"],
        SABR["expiry"],
        sigma0,
        SABR["beta"],
        0.0,
        0.4,
        mc_strikes,
        500,
        400_000,
        2702,
    )
    for row in mc["rows"]:
        row["hull_formula_vol"] = hull_sabr_vol(
            SABR["forward"], row["strike"], SABR["expiry"], sigma0, SABR["beta"], 0.0, 0.4
        )
    sabr = {
        **SABR,
        "sigma0": sigma0,
        "strikes": sabr_strikes,
        "rho_group_nu": 0.4,
        "rho_group": rho_group,
        "nu_group_rho": 0.0,
        "nu_group": nu_group,
        "atm": {
            "rho": 0.0,
            "nu": 0.4,
            "limit_vol": hull_sabr_vol(
                forward_rate, forward_rate, sabr_expiry, sigma0, beta, 0.0, 0.4
            ),
            "near_atm_vol": hull_sabr_vol(
                forward_rate, forward_rate * (1 + 1e-6), sabr_expiry, sigma0, beta, 0.0, 0.4
            ),
        },
        "monte_carlo": {
            "rho": 0.0,
            "nu": 0.4,
            "n_steps": 500,
            "n_paths": 400_000,
            "seed": 2702,
            **mc,
        },
    }
    return {
        "section": "27.2",
        "source": "Hull 11e Global Edition pp.646–649, equations (27.1)–(27.3) and the SABR formula",
        "units": "prices in currency (SABR values per unit forward notional, undiscounted); time in years; rates and volatilities annualized decimals",
        "term_structure": term,
        "heston": heston,
        "sabr": sabr,
        "limits": (
            "Synthetic markets. Heston prices use Gil-Pelaez quadrature; the SABR Monte Carlo "
            "has Euler and sampling error. Nothing here is calibrated to market data."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: stochastic-volatility reference differs; regenerate and review")
        print(
            "PASS: stochastic-volatility reference is reproducible",
            hashlib.sha256(payload.encode()).hexdigest(),
        )
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
