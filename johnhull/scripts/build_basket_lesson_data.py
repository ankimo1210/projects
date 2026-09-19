"""Build saved §26.15 basket lesson data from the frozen M7a references.

This script performs no quadrature or Monte Carlo.  It reshapes checked-in
independent prices and exact moments for the shared Plotly lesson figures.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-15"
PRICES_PATH = VALIDATION / "prices.json"
SCHEMA_VERSION = 1
FAMILIES = ("payoff", "correlation", "comparison", "error")
SOURCE_PATHS = (
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_basket_reference.py",
    "docs/validation/section-26-15/prices.json",
    "docs/validation/section-26-15/numerical-check.json",
    "scripts/build_basket_lesson_data.py",
)
PAYOFF_WEIGHTS = (0.6, 0.5)
PAYOFF_STRIKE = 100.0
PAYOFF_TERMINALS = ((90.0, 60.0), (100.0, 80.0), (115.0, 90.0), (120.0, 120.0))
CORRELATION_MARKETS = ("negative-correlation", "baseline", "high-correlation")
COMPARISON_CASES = (
    ("baseline-call", "baseline", "call"),
    ("long-high-volatility-call", "long-high-volatility", "call"),
    ("baseline-put", "baseline", "put"),
)
ERROR_MARKETS = (
    "baseline",
    "long-high-volatility",
    "three-diversified",
    "three-high-volatility",
)
LIMITATIONS = [
    "Synthetic constant-parameter correlated-GBM markets; values are in currency.",
    "Moment matching is an approximation except for exact lognormal anchors.",
    "Recorded Monte Carlo uncertainty is four standard errors, not a universal bound.",
]


def _family(data, method, hashes, limitations=()):
    return {
        "units": {
            "money": "currency",
            "time": "years",
            "rates": "continuous per year",
            "volatility": "annualized",
        },
        "method": method,
        "limitations": LIMITATIONS + list(limitations),
        "source_hashes": hashes,
        "data": data,
    }


def _frozen(rows, market, strike, kind):
    return next(
        row
        for row in rows
        if row["market"] == market and row["K"] == strike and row["kind"] == kind
    )


def _payoff_rows():
    rows = []
    for terminal_assets in PAYOFF_TERMINALS:
        basket = math.fsum(
            weight * terminal
            for weight, terminal in zip(PAYOFF_WEIGHTS, terminal_assets, strict=True)
        )
        rows.append(
            {
                "terminal_assets": list(terminal_assets),
                "basket_terminal": basket,
                "call": max(basket - PAYOFF_STRIKE, 0.0),
                "put": max(PAYOFF_STRIKE - basket, 0.0),
            }
        )
    return {
        "weights": list(PAYOFF_WEIGHTS),
        "strike": PAYOFF_STRIKE,
        "rows": rows,
    }


def _correlation_rows(rows):
    entries = []
    for market in CORRELATION_MARKETS:
        row = _frozen(rows, market, 100.0, "call")
        rho = row["correlation"][0][1]
        forwards = [
            weight * spot * math.exp((row["r"] - dividend) * row["T"])
            for spot, weight, dividend in zip(
                row["spots"], row["weights"], row["dividends"], strict=True
            )
        ]
        cross_second_moment = (
            2.0
            * forwards[0]
            * forwards[1]
            * math.exp(rho * row["volatilities"][0] * row["volatilities"][1] * row["T"])
        )
        entries.append(
            {
                "market": market,
                "spots": row["spots"],
                "weights": row["weights"],
                "volatilities": row["volatilities"],
                "dividends": row["dividends"],
                "rate": row["r"],
                "expiry": row["T"],
                "rho": rho,
                "first_moment": row["M1"],
                "second_moment": row["M2"],
                "cross_second_moment": cross_second_moment,
                "cross_covariance_contribution": cross_second_moment
                - 2.0 * forwards[0] * forwards[1],
                "matched_volatility": math.sqrt(math.log(row["M2"] / row["M1"] ** 2) / row["T"]),
            }
        )
    return {"strike": 100.0, "kind": "call", "entries": entries}


def _comparison_rows(rows):
    families = []
    for scenario, market, kind in COMPARISON_CASES:
        entries = []
        for strike in (80.0, 100.0, 120.0):
            row = _frozen(rows, market, strike, kind)
            entries.append(
                {
                    "strike": strike,
                    "approximation": row["approximation"],
                    "independent_reference": row["reference"],
                    "reference_method": row["reference_method"],
                    "mc": row["mc"],
                    "standard_error": row["standard_error"],
                    "four_standard_errors": 4.0 * row["standard_error"],
                }
            )
        families.append(
            {
                "scenario": scenario,
                "market": market,
                "kind": kind,
                "entries": entries,
            }
        )
    return families


def _error_rows(rows):
    families = []
    for kind in ("call", "put"):
        entries = []
        for market in ERROR_MARKETS:
            row = _frozen(rows, market, 100.0, kind)
            absolute_gap = abs(row["approximation"] - row["reference"])
            four_se = 4.0 * row["standard_error"]
            entries.append(
                {
                    "market": market,
                    "strike": 100.0,
                    "kind": kind,
                    "approximation": row["approximation"],
                    "reference": row["reference"],
                    "reference_method": row["reference_method"],
                    "absolute_gap": absolute_gap,
                    "four_standard_errors": four_se,
                    "absolute_relative_error_percent": 100.0 * absolute_gap / abs(row["reference"]),
                    "four_se_relative_percent": 100.0 * four_se / abs(row["reference"]),
                    "error_sign_established": row["error_sign_established"],
                }
            )
        families.append({"scenario": kind, "strike": 100.0, "entries": entries})
    return families


def build():
    frozen = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    hashes = {
        path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS
    }
    rows = frozen["rows"]
    return {
        "schema_version": SCHEMA_VERSION,
        "section": "26.15",
        "payoff": _family(
            _payoff_rows(),
            "Literal two-asset terminal states and European basket call/put payoffs",
            hashes,
        ),
        "correlation": _family(
            _correlation_rows(rows),
            "Frozen otherwise-identical markets isolate rho in the cross covariance and matched volatility",
            hashes,
        ),
        "comparison": _family(
            _comparison_rows(rows),
            "Frozen lognormal proxy, conditional-quadrature reference and independent Monte Carlo with four-SE bars",
            hashes,
        ),
        "error": _family(
            _error_rows(rows),
            "Absolute relative proxy gap against four-SE uncertainty; unresolved signs stay unsigned",
            hashes,
            [
                "The sign is unresolved whenever the frozen gap is no larger than four standard errors."
            ],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=VALIDATION)
    options = parser.parse_args()
    options.output_dir.mkdir(parents=True, exist_ok=True)
    lesson = build()
    path = options.output_dir / "lesson-data.json"
    path.write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path}")
    print("menu states: payoff call/put; correlation all/covariance-only/volatility-only")
    print("menu states: comparison baseline-call/long-high-volatility-call/baseline-put")
    print("menu states: error call/put")


if __name__ == "__main__":
    main()
