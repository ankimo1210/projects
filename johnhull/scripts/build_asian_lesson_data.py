"""Build the saved §26.13 lesson numbers; never run during notebook builds.

Run from the workspace root with hullkit/src on PYTHONPATH. This generator may
import the independent reference engine; the lesson figures never do - they
read the saved JSON and refuse it when a source hash is stale.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build_asian_reference import (
    MARKETS,
    STRIKE,
    control_variate_price,
    discrete_moments,
    geometric_price,
    observation_times,
    turnbull_wakeman,
)
from hullkit import exotics

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-13"
SCHEMA_VERSION = 1
DISTRIBUTION_MARKETS = ("low-vol-short", "positive-carry", "high-vol-long")
DISTRIBUTION_PATHS = 200_000
DISTRIBUTION_BINS = 60
OBSERVATION_COUNTS = (12, 52, 250)
SOURCE_PATHS = (
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_asian_lesson_data.py",
    "scripts/build_asian_reference.py",
    "docs/validation/section-26-13/prices.json",
    "docs/validation/section-26-13/numerical-check.json",
)
LIMITATIONS = [
    "Synthetic constant-parameter GBM; positive S, K, T, sigma; continuous annual r and q.",
    "Observation dates are i*T/m: today excluded, maturity included.",
    "Moment matching is an approximation; the saved errors are measured, not bounds.",
    "Simulated references carry a standard error; only the two-date rows are exact.",
    "No cash dividends, nonconstant volatility, unequal observation spacing, T=0 or sigma=0.",
]
EXAMPLE_PATH = {
    "market": "positive-carry",
    "label": "定義した折れ線経路（GBM標本ではない）",
    "strike": 100.0,
    "prices": [100.0, 112.0, 94.0, 121.0, 90.0, 105.0, 84.0, 116.0, 108.0],
}


def _hashes():
    return {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
            for name in SOURCE_PATHS}


def _family(rows, method, hashes, limitations=()):
    return {
        "units": {"money": "currency", "time": "years", "rates": "continuous per year",
                  "volatility": "annualized", "observations": "averaging dates"},
        "method": method,
        "limitations": list(LIMITATIONS) + list(limitations),
        "source_hashes": hashes,
        "rows": rows,
    }


def _contract_rows():
    """Payoffs of the three §26.13 contracts on one defined polyline path."""
    prices = EXAMPLE_PATH["prices"]
    strike = EXAMPLE_PATH["strike"]
    observed = prices[1:]  # today is not an observation date
    average = sum(observed) / len(observed)
    terminal = prices[-1]
    return [{
        "path": prices,
        "observations": observed,
        "average": average,
        "terminal": terminal,
        "strike": strike,
        "payoffs": {
            "average_price_call": max(average - strike, 0.0),
            "average_price_put": max(strike - average, 0.0),
            "average_strike_call": max(terminal - average, 0.0),
            "average_strike_put": max(average - terminal, 0.0),
            "vanilla_call": max(terminal - strike, 0.0),
        },
    }]


def _distribution_rows():
    """Simulated law of the average against the fitted lognormal."""
    rows = []
    for name in DISTRIBUTION_MARKETS:
        market = next(item for item in MARKETS if item.name == name)
        times = observation_times(market.expiry, 52)
        steps = np.diff(np.concatenate([[0.0], times]))
        drift = (market.rate - market.dividend - 0.5 * market.volatility**2) * steps
        diffusion = market.volatility * np.sqrt(steps)
        generator = np.random.default_rng(20260918)
        noise = generator.standard_normal((DISTRIBUTION_PATHS, times.size))
        logs = math.log(STRIKE) + np.cumsum(drift + diffusion * noise, axis=1)
        average = np.exp(logs).mean(axis=1)
        first, second = discrete_moments(STRIKE, market.rate, market.dividend,
                                         market.volatility, times)
        matched_vol = math.sqrt(math.log(second / first**2) / market.expiry)
        low, high = np.quantile(average, [0.001, 0.999])
        edges = np.linspace(float(low), float(high), DISTRIBUTION_BINS + 1)
        counts, _ = np.histogram(average, bins=edges, density=True)
        centres = 0.5 * (edges[:-1] + edges[1:])
        scale = matched_vol * math.sqrt(market.expiry)
        location = math.log(first) - 0.5 * scale**2
        fitted = np.exp(-0.5 * ((np.log(centres) - location) / scale) ** 2) / (
            centres * scale * math.sqrt(2.0 * math.pi))
        rows.append({
            "market": market.name,
            "rate": market.rate,
            "dividend": market.dividend,
            "volatility": market.volatility,
            "expiry": market.expiry,
            "observations": 52,
            "moment_1": first,
            "moment_2": second,
            "matched_volatility": matched_vol,
            "centres": [float(x) for x in centres],
            "simulated_density": [float(x) for x in counts],
            "fitted_density": [float(x) for x in fitted],
            "simulated_skewness": float(((average - average.mean()) ** 3).mean()
                                        / average.std(ddof=0) ** 3),
            "fitted_skewness": float((math.exp(scale**2) + 2.0) * math.sqrt(math.expm1(scale**2))),
            "paths": DISTRIBUTION_PATHS,
        })
    return rows


def _observation_rows(paths):
    """Prices as the averaging grid is refined, plus the continuous formula."""
    rows = []
    for market in MARKETS:
        entries = []
        for count in OBSERVATION_COUNTS:
            times = observation_times(market.expiry, count)
            approximation, *_ = turnbull_wakeman(STRIKE, STRIKE, market.rate, market.dividend,
                                                 market.volatility, market.expiry, "call", times)
            estimates = control_variate_price(STRIKE, [STRIKE], market.rate, market.dividend,
                                              market.volatility, market.expiry, times,
                                              paths=paths)
            reference, error = estimates[(STRIKE, "call")]
            entries.append({
                "observations": count,
                "turnbull_wakeman": approximation,
                "reference": reference,
                "standard_error": error,
                "geometric": geometric_price(STRIKE, STRIKE, market.rate, market.dividend,
                                             market.volatility, market.expiry, times, "call"),
            })
        rows.append({
            "market": market.name,
            "rate": market.rate,
            "dividend": market.dividend,
            "volatility": market.volatility,
            "expiry": market.expiry,
            "continuous_turnbull_wakeman": (
                exotics.asian_average_price(STRIKE, STRIKE, market.rate, market.volatility,
                                            market.expiry, q=market.dividend)),
            "entries": entries,
        })
    return rows


def _error_rows(prices):
    """Measured relative error of the moment match, by moneyness and market."""
    rows = []
    for row in prices["rows"]:
        if row["observations"] != 52 or row["reference"] <= 0.5:
            continue
        rows.append({
            "market": row["market"],
            "contract": row["contract"],
            "spot_ratio": row["spot_ratio"],
            "volatility": row["volatility"],
            "expiry": row["expiry"],
            "scale": row["volatility"] * math.sqrt(row["expiry"]),
            "turnbull_wakeman": row["turnbull_wakeman"],
            "reference": row["reference"],
            "standard_error": row["standard_error"],
            "relative_error": (row["turnbull_wakeman"] - row["reference"]) / row["reference"],
        })
    return rows


def _seasoned_rows():
    """Hull's K* shift on one contract, including the certain-exercise branch."""
    market = next(item for item in MARKETS if item.name == "positive-carry")
    rows = []
    for observed in (80.0, 100.0, 120.0, 180.0):
        elapsed, remaining = 0.6, 0.4
        window = elapsed + remaining
        weight = remaining / window
        shifted = STRIKE / weight - observed * elapsed / remaining
        price = exotics.asian_seasoned_average_price(
            STRIKE, STRIKE, market.rate, market.volatility, elapsed, remaining, observed,
            q=market.dividend, kind="call")
        first, _ = exotics.asian_moments(STRIKE, market.rate, market.volatility, remaining,
                                         q=market.dividend)
        rows.append({
            "market": market.name,
            "observed_average": observed,
            "elapsed": elapsed,
            "remaining": remaining,
            "weight": weight,
            "shifted_strike": shifted,
            "certain_exercise": shifted <= 0.0,
            "price": price,
            "remaining_moment_1": first,
        })
    return rows


def build(paths):
    hashes = _hashes()
    prices = json.loads((VALIDATION / "prices.json").read_text(encoding="utf-8"))
    return {
        "schema_version": SCHEMA_VERSION,
        "strike": STRIKE,
        "contract": _family(_contract_rows(),
                            "One defined polyline path; payoffs of the three §26.13 contracts",
                            hashes,
                            ["The path is a defined example, not a GBM sample."]),
        "distribution": _family(_distribution_rows(),
                                "Simulated law of the average against the moment-matched lognormal",
                                hashes,
                                ["Histogram trimmed to the 0.1%-99.9% quantiles of the sample."]),
        "observations": _family(_observation_rows(paths),
                                "Turnbull-Wakeman and control-variate references at 12/52/250 dates",
                                hashes),
        "errors": _family(_error_rows(prices),
                          "Relative error of the moment match at 52 dates, from the saved table",
                          hashes),
        "seasoned": _family(_seasoned_rows(),
                            "Hull's K* shift, including the branch where the call is certain to pay",
                            hashes),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", type=int, default=400_000)
    parser.add_argument("--output-dir", type=Path, default=VALIDATION)
    options = parser.parse_args()
    lesson = build(options.paths)
    options.output_dir.mkdir(parents=True, exist_ok=True)
    (options.output_dir / "lesson-data.json").write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    for row in lesson["observations"]["rows"]:
        entries = ", ".join(f"m={item['observations']}: {item['turnbull_wakeman']:.4f}"
                            f" vs {item['reference']:.4f}" for item in row["entries"])
        print(f"{row['market']}: {entries}")


if __name__ == "__main__":
    main()
