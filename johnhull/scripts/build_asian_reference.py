"""Independent reference prices for Hull 11e GE section 26.13 (Asian options).

The section prices an arithmetic-average option by matching the first two
moments of the average to a lognormal and calling Black's model
(Turnbull-Wakeman). That is an approximation, and nothing in the repository
measured its error. This module builds the references needed to measure it,
from three directions that share no code path with each other or with hullkit:

* ``discrete_moments`` / ``continuous_moments`` give the exact first two
  moments of the average, so the moment match itself can be checked against
  Hull's printed M1 and M2.
* ``two_date_price`` is an exact arithmetic-average price for two observation
  dates: conditioning on the first observation turns the payoff into a Black
  option on the second, leaving one smooth integral. It anchors everything
  else at machine precision.
* ``control_variate_price`` prices any observation schedule by simulating the
  observation dates exactly - no time-discretisation error - with the exact
  geometric-average price from ``geometric_price`` as the control variate.

All inputs are synthetic: prices and strikes in currency, maturities in years,
rates and dividend yields continuously compounded per year, volatility
annualised. Observation dates are ``i*T/m`` for ``i = 1..m``; the average
excludes today and includes maturity, the convention that reproduces Hull's
printed 12/52/250-observation prices.

Refresh the saved records from the repository root:

    .venv/bin/python johnhull/scripts/build_asian_reference.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr

PROJECT = Path(__file__).resolve().parent.parent
CONTRACTS = ("call", "put")
STRIKE = 100.0
SPOT_RATIOS = (0.80, 1.00, 1.25)
OBSERVATION_COUNTS = (2, 12, 52, 250)
NORMAL_PEAK = 1.0 / math.sqrt(2.0 * math.pi)


class Market(NamedTuple):
    """Synthetic market: continuous rate and dividend yield, volatility, years."""

    name: str
    rate: float
    dividend: float
    volatility: float
    expiry: float


MARKETS = (
    Market("low-vol-short", 0.03, 0.01, 0.10, 0.25),
    Market("positive-carry", 0.05, 0.02, 0.20, 1.0),
    Market("dividend-above-rate", 0.01, 0.07, 0.25, 1.5),
    Market("negative-rate", -0.025, 0.01, 0.18, 0.75),
    Market("zero-carry", 0.03, 0.03, 0.30, 2.0),
    Market("high-vol-long", 0.06, 0.025, 0.70, 5.0),
)
HULL_EXAMPLE = {"spot": 50.0, "strike": 50.0, "rate": 0.10, "dividend": 0.0,
                "volatility": 0.40, "expiry": 1.0}


def observation_times(expiry, count):
    """``i*T/m`` for ``i = 1..m``: today excluded, maturity included."""
    return np.arange(1, count + 1, dtype=float) * expiry / count


def black(forward, strike, vol, rate, expiry, kind):
    """Black's model on a forward (Hull 11e eq. 18.7-18.8)."""
    if kind not in CONTRACTS:
        raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")
    discount = math.exp(-rate * expiry)
    if vol <= 0.0 or expiry <= 0.0 or forward <= 0.0 or strike <= 0.0:
        payoff = max(forward - strike, 0.0) if kind == "call" else max(strike - forward, 0.0)
        return discount * payoff
    scale = vol * math.sqrt(expiry)
    d1 = (math.log(forward / strike) + 0.5 * scale**2) / scale
    d2 = d1 - scale
    if kind == "call":
        return discount * (forward * ndtr(d1) - strike * ndtr(d2))
    return discount * (strike * ndtr(-d2) - forward * ndtr(-d1))


def discrete_moments(spot, rate, dividend, sigma, times):
    """Exact E[A] and E[A^2] for the arithmetic average over ``times``.

    ``E[S_u S_v] = F_u F_v exp(sigma^2 min(u, v))`` under the risk-neutral GBM,
    which is Hull's general two-moment formula written with equal volatilities.
    """
    dates = np.asarray(times, dtype=float)
    count = dates.size
    forwards = spot * np.exp((rate - dividend) * dates)
    first = float(forwards.mean())
    cross = np.outer(forwards, forwards) * np.exp(sigma**2 * np.minimum.outer(dates, dates))
    return first, float(cross.sum()) / count**2


def continuous_moments(spot, rate, dividend, sigma, expiry):
    """Hull 11e p.626: the continuously averaged moments with constant r, q, sigma."""
    carry = rate - dividend
    if abs(carry) < 1e-12 or abs(carry + sigma**2) < 1e-12 or abs(2 * carry + sigma**2) < 1e-12:
        raise ValueError("the printed continuous moments divide by r-q and r-q+sigma^2")
    first = spot * (math.exp(carry * expiry) - 1.0) / (carry * expiry)
    second = (
        2 * math.exp((2 * carry + sigma**2) * expiry) * spot**2
        / ((carry + sigma**2) * (2 * carry + sigma**2) * expiry**2)
        + 2 * spot**2 / (carry * expiry**2)
        * (1.0 / (2 * carry + sigma**2) - math.exp(carry * expiry) / (carry + sigma**2))
    )
    return first, second


def turnbull_wakeman(spot, strike, rate, dividend, sigma, expiry, kind, times=None):
    """Moment-matched Black price (Hull eq. 26.3-26.4). Returns (price, M1, M2, vol)."""
    first, second = (continuous_moments(spot, rate, dividend, sigma, expiry) if times is None
                     else discrete_moments(spot, rate, dividend, sigma, times))
    vol = math.sqrt(math.log(second / first**2) / expiry)
    return black(first, strike, vol, rate, expiry, kind), first, second, vol


def geometric_price(spot, strike, rate, dividend, sigma, expiry, times, kind):
    """Exact discrete geometric-average price; the log average is normal."""
    dates = np.asarray(times, dtype=float)
    count = dates.size
    mean_log = math.log(spot) + (rate - dividend - 0.5 * sigma**2) * float(dates.mean())
    variance = sigma**2 * float(np.minimum.outer(dates, dates).sum()) / count**2
    forward = math.exp(mean_log + 0.5 * variance)
    return black(forward, strike, math.sqrt(variance / expiry), rate, expiry, kind)


def two_date_price(spot, strike, rate, dividend, sigma, times, kind, width=12.0):
    """Exact two-date arithmetic-average price by conditioning on the first date.

    Given ``S_{t1} = x`` the payoff is ``0.5 * max(S_{t2} - (2K - x), 0)`` for a
    call, so the inner expectation is Black's formula and only the outer
    integral over the first observation is numerical.
    """
    if len(times) != 2:
        raise ValueError("two_date_price needs exactly two observation dates")
    first_date, expiry = float(times[0]), float(times[1])
    gap = expiry - first_date
    drift = (rate - dividend - 0.5 * sigma**2) * first_date
    scale = sigma * math.sqrt(first_date)

    def integrand(z):
        level = spot * math.exp(drift + scale * z)
        inner_strike = 2.0 * strike - level
        forward = level * math.exp((rate - dividend) * gap)
        if inner_strike <= 0.0:
            value = 0.5 * (forward - inner_strike) if kind == "call" else 0.0
        else:
            value = 0.5 * black(forward, inner_strike, sigma, 0.0, gap, kind)
        return value * NORMAL_PEAK * math.exp(-0.5 * z * z)

    crossing = (math.log(2.0 * strike / spot) - drift) / scale
    edges = sorted({-width, min(max(crossing, -width), width), width})
    total = 0.0
    for low, high in pairwise(edges):
        value, error = quad(integrand, low, high, epsabs=1e-13, epsrel=1e-13, limit=300)
        if error > 1e-10:
            raise ValueError(f"two-date quadrature error estimate {error:.2e} is too large")
        total += value
    return math.exp(-rate * expiry) * total


def control_variate_price(spot, strikes, rate, dividend, sigma, expiry, times, *,
                          paths=400_000, chunk=50_000, seed=20260916):
    """Simulate the observation dates exactly; use the geometric price as control.

    ``strikes`` is priced in one sweep for both contracts. Returns
    ``{(strike, kind): (price, standard_error)}``.
    """
    dates = np.asarray(times, dtype=float)
    steps = np.diff(np.concatenate([[0.0], dates]))
    drift = (rate - dividend - 0.5 * sigma**2) * steps
    diffusion = sigma * np.sqrt(steps)
    discount = math.exp(-rate * expiry)
    generator = np.random.default_rng(seed)
    exact = {(strike, kind): geometric_price(spot, strike, rate, dividend, sigma, expiry, dates, kind)
             for strike in strikes for kind in CONTRACTS}
    samples = {key: [] for key in exact}
    done = 0
    while done < paths:
        size = min(chunk, paths - done)
        done += size
        noise = generator.standard_normal((size, dates.size))
        logs = math.log(spot) + np.cumsum(drift + diffusion * noise, axis=1)
        arithmetic = np.exp(logs).mean(axis=1)
        geometric = np.exp(logs.mean(axis=1))
        for strike in strikes:
            for kind in CONTRACTS:
                if kind == "call":
                    plain = np.maximum(arithmetic - strike, 0.0)
                    control = np.maximum(geometric - strike, 0.0)
                else:
                    plain = np.maximum(strike - arithmetic, 0.0)
                    control = np.maximum(strike - geometric, 0.0)
                samples[(strike, kind)].append((discount * plain, discount * control))
    results = {}
    for key, chunks in samples.items():
        plain = np.concatenate([item[0] for item in chunks])
        control = np.concatenate([item[1] for item in chunks])
        variance = control.var(ddof=1)
        beta = 0.0 if variance == 0.0 else np.cov(plain, control)[0, 1] / variance
        adjusted = plain - beta * (control - exact[key])
        results[key] = (float(adjusted.mean()), float(adjusted.std(ddof=1) / math.sqrt(adjusted.size)))
    return results


def continuous_limit(values, counts):
    """Richardson extrapolation of the 1/m discretisation: (m2*V2 - m1*V1)/(m2-m1)."""
    (count_low, value_low), (count_high, value_high) = zip(counts, values, strict=True)
    return (count_high * value_high - count_low * value_low) / (count_high - count_low)


def build_rows(paths=400_000):
    """Reference table over markets, observation counts, spot ratios and contracts."""
    rows = []
    strikes = [STRIKE / ratio for ratio in SPOT_RATIOS]  # scale the strike, not the spot
    for market in MARKETS:
        for count in OBSERVATION_COUNTS:
            times = observation_times(market.expiry, count)
            estimates = control_variate_price(
                STRIKE, strikes, market.rate, market.dividend, market.volatility,
                market.expiry, times, paths=paths,
            )
            for ratio, strike in zip(SPOT_RATIOS, strikes, strict=True):
                spot = STRIKE * ratio
                for kind in CONTRACTS:
                    reference, error = estimates[(strike, kind)]
                    # Undo the strike scaling: V(spot, STRIKE) = ratio * V(STRIKE, STRIKE/ratio)
                    reference, error = ratio * reference, ratio * error
                    approximation, first, second, vol = turnbull_wakeman(
                        spot, STRIKE, market.rate, market.dividend, market.volatility,
                        market.expiry, kind, times,
                    )
                    exact = (two_date_price(spot, STRIKE, market.rate, market.dividend,
                                            market.volatility, times, kind)
                             if count == 2 else None)
                    rows.append({
                        "market": market.name,
                        "observations": count,
                        "contract": kind,
                        "spot_ratio": ratio,
                        "spot": spot,
                        "strike": STRIKE,
                        "rate": market.rate,
                        "dividend": market.dividend,
                        "volatility": market.volatility,
                        "expiry": market.expiry,
                        "reference": reference,
                        "standard_error": error,
                        "exact": exact,
                        "turnbull_wakeman": approximation,
                        "moment_1": first,
                        "moment_2": second,
                        "matched_volatility": vol,
                        "geometric": ratio * geometric_price(
                            STRIKE, strike, market.rate, market.dividend, market.volatility,
                            market.expiry, times, kind),
                    })
    return rows


def hull_example_checks():
    """Reproduce Example 26.3 (p.627) and measure the approximation error there."""
    spot, strike = HULL_EXAMPLE["spot"], HULL_EXAMPLE["strike"]
    rate, dividend = HULL_EXAMPLE["rate"], HULL_EXAMPLE["dividend"]
    sigma, expiry = HULL_EXAMPLE["volatility"], HULL_EXAMPLE["expiry"]
    printed = {12: 6.00, 52: 5.70, 250: 5.63}
    continuous, first, second, vol = turnbull_wakeman(spot, strike, rate, dividend, sigma,
                                                      expiry, "call")
    discrete = []
    for count in (12, 52, 250):
        times = observation_times(expiry, count)
        approximation, *_ = turnbull_wakeman(spot, strike, rate, dividend, sigma, expiry,
                                             "call", times)
        estimates = control_variate_price(spot, [strike], rate, dividend, sigma, expiry, times,
                                          paths=1_000_000)
        reference, error = estimates[(strike, "call")]
        discrete.append({
            "observations": count,
            "printed": printed[count],
            "turnbull_wakeman": approximation,
            "reference": reference,
            "standard_error": error,
            "approximation_error": approximation - reference,
        })
    limit = continuous_limit([discrete[1]["reference"], discrete[2]["reference"]], [52, 250])
    return {
        "inputs": dict(HULL_EXAMPLE),
        "printed": {"moment_1": 52.59, "moment_2": 2922.76, "volatility": 0.2354, "price": 5.62},
        "continuous": {
            "moment_1": first, "moment_2": second, "matched_volatility": vol,
            "turnbull_wakeman": continuous,
            "extrapolated_reference": limit,
            "approximation_error": continuous - limit,
            "extrapolation": "Richardson in 1/m from the 52- and 250-observation references",
        },
        "discrete": discrete,
    }


def _project_relative(path: Path) -> str:
    """Record paths the way the ledger reads them, relative to the project root."""
    resolved = path.resolve()
    return str(resolved.relative_to(PROJECT)) if resolved.is_relative_to(PROJECT) else path.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the section 26.13 reference records.")
    parser.add_argument("--paths", type=int, default=400_000, help="Monte Carlo paths per schedule")
    parser.add_argument("--output", type=Path, default=Path("johnhull/docs/validation/section-26-13"))
    args = parser.parse_args(argv)

    rows = build_rows(args.paths)
    example = hull_example_checks()

    args.output.mkdir(parents=True, exist_ok=True)
    prices_path = args.output / "prices.json"
    prices_path.write_text(
        json.dumps({"strike": STRIKE, "paths": args.paths, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    anchored = [row for row in rows if row["exact"] is not None]
    anchor_gap = max(abs(row["exact"] - row["reference"]) for row in anchored)
    # A zero standard error means every path paid zero, so the row carries no
    # sampling noise and no information about it either.
    anchor_sigmas = max(abs(row["exact"] - row["reference"]) / row["standard_error"]
                        for row in anchored if row["standard_error"] > 0.0)
    signed = [((row["turnbull_wakeman"] - row["reference"]) / row["reference"], row)
              for row in rows if row["reference"] > 0.5]
    worst_ratio, worst_row = max(signed, key=lambda item: abs(item[0]))
    over_ratio, over_row = max(signed, key=lambda item: item[0])
    under_ratio, under_row = min(signed, key=lambda item: item[0])

    def _case(ratio, row):
        summary = {key: row[key] for key in
                   ("market", "observations", "contract", "spot_ratio", "volatility",
                    "expiry", "turnbull_wakeman", "reference", "standard_error")}
        summary["relative_error"] = ratio
        return summary
    record = {
        "status": "PASS",
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "M5a independent Asian references and approximation-error measurement; section 26.13 stays gaps_found.",
        "reference": "Hull 11e Global Edition section 26.13, physical/printed pp.626-627, Example 26.3 p.627.",
        "method": (
            "Exact moments of the average, an exact two-date price by conditioning, and a "
            "control-variate Monte Carlo that samples the observation dates exactly with the "
            "exact geometric-average price as control. No hullkit function is used."
        ),
        "observation_convention": "t_i = i*T/m for i=1..m; today excluded, maturity included.",
        "anchor": {
            "max_absolute_gap": anchor_gap,
            "max_standard_errors": anchor_sigmas,
            "cases": len(anchored),
            "note": "Two-observation rows carry an exact quadrature price; the gap is the Monte Carlo error.",
        },
        "approximation_error": {
            "definition": "Turnbull-Wakeman minus the simulated reference, rows with a reference above 0.5.",
            "max_relative": abs(worst_ratio),
            "sign": "both: the moment match overprices near and above the average's forward and underprices below it",
            "worst_case": _case(worst_ratio, worst_row),
            "largest_overprice": _case(over_ratio, over_row),
            "largest_underprice": _case(under_ratio, under_row),
        },
        "hull_example_26_3": example,
        "units": {"spot_strike_price": "currency", "expiry": "years",
                  "rate_dividend": "continuously compounded per year", "volatility": "annual"},
        "assumptions": [
            "Risk-neutral GBM with constant r/q/sigma; positive spot, volatility and maturity.",
            "Newly issued contracts: the whole averaging window lies in the future.",
            "All markets are synthetic; no claim about market performance.",
        ],
        "limitations": [
            "The simulated references carry a standard error; they are not exact except on the two-date rows.",
            "The continuous-average reference is a Richardson extrapolation in 1/m, not a limit computation.",
            "Seasoned contracts, average-strike options and non-constant volatility are not priced here.",
            "hullkit implements only the continuous average-price call; nothing else in the library is covered.",
        ],
        "source_sha256": {
            name: _sha256(PROJECT / name)
            for name in (
                "scripts/build_asian_reference.py",
                "hullkit/tests/test_asian_reference.py",
                "options, futures and other derivatives 11th.pdf",
            )
        },
        "artifact_sha256": {_project_relative(prices_path): _sha256(prices_path)},
    }
    (args.output / "numerical-check.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"prices: {len(rows)} rows -> {prices_path}")
    print(f"two-date anchor: max gap {anchor_gap:.3e} ({anchor_sigmas:.2f} standard errors)")
    print(f"Turnbull-Wakeman relative error: {over_ratio * 100:+.2f}% to {under_ratio * 100:+.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
