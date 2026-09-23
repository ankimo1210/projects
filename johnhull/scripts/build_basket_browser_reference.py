"""Independent browser oracle for §26.15; no hullkit or lesson imports.

Recompute payoffs, GBM double-loop moments and the Black proxy from literal
market inputs / frozen reference contracts. MC and conditional references are
read from M7a; plotting arrays and lesson-data are never read.
"""

import hashlib
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-15"
SOURCES = (
    "scripts/build_basket_browser_reference.py",
    "scripts/build_basket_reference.py",
    "docs/validation/section-26-15/prices.json",
    "docs/validation/section-26-15/numerical-check.json",
)


def moments(row):
    forwards = [
        w * s * math.exp((row["r"] - q) * row["T"])
        for s, w, q in zip(row["spots"], row["weights"], row["dividends"], strict=True)
    ]
    second = 0.0
    for i, fi in enumerate(forwards):
        for j, fj in enumerate(forwards):
            second += (
                fi
                * fj
                * math.exp(
                    row["correlation"][i][j]
                    * row["volatilities"][i]
                    * row["volatilities"][j]
                    * row["T"]
                )
            )
    first = math.fsum(forwards)
    return first, second, math.sqrt(math.log(second / first**2) / row["T"])


def proxy(row):
    first, _, sigma = moments(row)
    scale = sigma * math.sqrt(row["T"])
    sign = 1 if row["kind"] == "call" else -1
    discount = math.exp(-row["r"] * row["T"])
    if scale == 0:
        return discount * max(sign * (first - row["K"]), 0)

    def cdf(x):
        return math.erfc(-x / math.sqrt(2)) / 2

    d1 = math.log(first / row["K"]) / scale + scale / 2
    return discount * sign * (first * cdf(sign * d1) - row["K"] * cdf(sign * (d1 - scale)))


def build():
    frozen = json.loads((VALIDATION / "prices.json").read_text())
    rows = frozen["rows"]

    def pick(market, strike=100.0, kind="call"):
        return next(r for r in rows if (r["market"], r["K"], r["kind"]) == (market, strike, kind))

    weights, strike = [0.6, 0.5], 100.0
    terminals = [[90.0, 60.0], [100.0, 80.0], [115.0, 90.0], [120.0, 120.0]]
    baskets = [sum(w * s for w, s in zip(weights, ts, strict=True)) for ts in terminals]
    payoff = {
        "weights": weights,
        "strike": strike,
        "terminals": terminals,
        "labels": [f"S₁(T)={ts[0]:.0f}, S₂(T)={ts[1]:.0f}" for ts in terminals],
        "basket": baskets,
        "call": [max(b - strike, 0) for b in baskets],
        "put": [max(strike - b, 0) for b in baskets],
    }
    correlation = []
    for name in ("negative-correlation", "baseline", "high-correlation"):
        row = pick(name)
        first, second, sigma = moments(row)
        f = [
            w * s * math.exp((row["r"] - q) * row["T"])
            for w, s, q in zip(row["weights"], row["spots"], row["dividends"], strict=True)
        ]
        covariance = (
            2
            * f[0]
            * f[1]
            * math.expm1(
                row["correlation"][0][1]
                * row["volatilities"][0]
                * row["volatilities"][1]
                * row["T"]
            )
        )
        correlation.append(
            {
                "market": name,
                "rho": row["correlation"][0][1],
                "M1": first,
                "M2": second,
                "sigma_percent": 100 * sigma,
                "cross_covariance": covariance,
            }
        )
    comparison = {}
    for state, market, kind in (
        ("baseline-call", "baseline", "call"),
        ("long-high-volatility-call", "long-high-volatility", "call"),
        ("baseline-put", "baseline", "put"),
    ):
        comparison[state] = [
            {
                "K": k,
                "approximation": proxy(pick(market, k, kind)),
                "reference": pick(market, k, kind)["reference"],
                "mc": pick(market, k, kind)["mc"],
                "four_se": 4 * pick(market, k, kind)["standard_error"],
            }
            for k in (80.0, 100.0, 120.0)
        ]
    error = {}
    for kind in ("call", "put"):
        error[kind] = []
        for name in (
            "baseline",
            "long-high-volatility",
            "three-diversified",
            "three-high-volatility",
        ):
            row = pick(name, kind=kind)
            gap = abs(proxy(row) - row["reference"])
            reference_uncertainty = (
                4 * row["standard_error"]
                if row["reference_method"] == "mc"
                else row["reference_uncertainty"]
            )
            error[kind].append(
                {
                    "market": name,
                    "reference_method": row["reference_method"],
                    "gap": gap,
                    "four_se": 4 * row["standard_error"],
                    "gap_percent": 100 * gap / abs(row["reference"]),
                    "four_se_percent": 400 * row["standard_error"] / abs(row["reference"]),
                    "sign_established": gap > reference_uncertainty,
                }
            )
    baseline = pick("baseline")
    first, second, sigma = moments(baseline)
    relative = [
        abs(proxy(r) - r["reference"]) / abs(r["reference"])
        for r in rows
        if abs(r["reference"]) >= frozen["price_floor"]
    ]
    counterexamples = [
        r
        for r in rows
        if r["reference_method"] == "conditional_quadrature"
        and abs(proxy(r) - r["reference"]) < 4 * r["standard_error"]
    ]
    counter = next(
        r for r in counterexamples if abs(proxy(r) - r["reference"]) > r["reference_uncertainty"]
    )
    return {
        "method": "Independent payoff algebra, direct-loop GBM moments and Black proxy; frozen M7a conditional/MC prices. No lesson or hullkit imports.",
        "source_sha256": {
            p: hashlib.sha256((PROJECT / p).read_bytes()).hexdigest() for p in SOURCES
        },
        "payoff": payoff,
        "correlation": correlation,
        "comparison": comparison,
        "error": error,
        "notebook": {
            "M1": first,
            "M2": second,
            "sigma": sigma,
            "call": proxy(baseline),
            "put": proxy(pick("baseline", kind="put")),
            "parity": math.exp(-baseline["r"] * baseline["T"]) * (first - baseline["K"]),
        },
        "summary": {
            "rows": len(rows),
            "relative_rows": len(relative),
            "price_floor": frozen["price_floor"],
            "max_relative_percent": 100 * max(relative),
            "max_absolute": max(abs(proxy(r) - r["reference"]) for r in rows),
        },
        "deterministic_sign_inside_mc_bar": {
            "market": counter["market"],
            "K": counter["K"],
            "kind": counter["kind"],
            "gap": abs(proxy(counter) - counter["reference"]),
            "reference_uncertainty": counter["reference_uncertainty"],
            "four_se": 4 * counter["standard_error"],
            "explanation": "MC uncertainty belongs to the sampled estimate. A conditional or analytic reference uses its own numerical error and can establish a sign inside the MC bar.",
        },
    }


def main():
    result = build()
    path = VALIDATION / "browser-reference.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"wrote {path.relative_to(PROJECT)}")
    print(result["notebook"])
    print(result["deterministic_sign_inside_mc_bar"])


if __name__ == "__main__":
    main()
