"""Build saved §26.16 variance-swap lesson data from the frozen M8a reference.

This script performs no quadrature or Monte Carlo. It reshapes the checked-in
independent reference and evaluates the closed-form payoff helpers of
``hullkit.variance_swaps`` for the shared Plotly lesson figures.
"""

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-16"
REFERENCE_PATH = VALIDATION / "reference.json"
SCHEMA_VERSION = 1
FAMILIES = ("payoff", "strip", "replication", "convexity")
SOURCE_PATHS = (
    "hullkit/src/hullkit/variance_swaps.py",
    "scripts/build_variance_swap_reference.py",
    "docs/validation/section-26-16/reference.json",
    "docs/validation/section-26-16/numerical-check.json",
    "scripts/build_variance_swap_lesson_data.py",
)
PAYOFF_VOL_NOTIONAL, PAYOFF_VOL_STRIKE = 100.0, 0.23
PAYOFF_GRID = tuple(round(0.10 + 0.01 * i, 2) for i in range(31))
LIMITATIONS = [
    "Hull's Examples 26.4-26.5 are printed; every other market is synthetic.",
    "Replication assumes continuous paths observed continuously; the daily contract is discrete.",
    "Measured errors describe the saved grids and are not universal bounds.",
]


def _family(data, method, hashes, units, limitations=()):
    return {
        "units": units,
        "method": method,
        "limitations": LIMITATIONS + list(limitations),
        "source_hashes": hashes,
        "data": data,
    }


def _payoff_rows():
    sys.path.insert(0, str(PROJECT / "hullkit/src"))
    from hullkit import variance_swaps

    variance_notional = variance_swaps.variance_notional(PAYOFF_VOL_NOTIONAL, PAYOFF_VOL_STRIKE)
    rows = []
    for sigma in PAYOFF_GRID:
        volatility = PAYOFF_VOL_NOTIONAL * (sigma - PAYOFF_VOL_STRIKE)
        variance = variance_notional * (sigma * sigma - PAYOFF_VOL_STRIKE**2)
        rows.append(
            {
                "realized_volatility": sigma,
                "volatility_payoff": volatility,
                "variance_payoff": variance,
                "difference": variance - volatility,
            }
        )
    return {
        "volatility_notional": PAYOFF_VOL_NOTIONAL,
        "volatility_strike": PAYOFF_VOL_STRIKE,
        "variance_notional": variance_notional,
        "variance_strike": PAYOFF_VOL_STRIKE**2,
        "rows": rows,
    }


def _strip_rows(reference):
    example = reference["example_26_4"]
    expiry = example["expiry"]
    return {
        "forward": example["forward"],
        "s_star": example["s_star"],
        "expiry": expiry,
        "boundary_terms": example["boundary_terms"],
        "strip_sum": example["strip_sum"],
        "variance_strip_sum": 2.0 / expiry * example["strip_sum"],
        "expected_variance": example["expected_variance"],
        "swap_value": example["swap_value"],
        "rows": [
            {
                "strike": row["strike"],
                "q": row["q"],
                "q_kind": row["q_kind"],
                "printed_q": row["printed_q"],
                "variance_contribution": 2.0 / expiry * row["contribution"],
            }
            for row in example["rows"]
        ],
    }


def _replication_rows(reference):
    block = reference["strip_convergence"]
    families = []
    for family in block["families"]:
        families.append(
            {
                "range": family["range"],
                "strike_low": family["strike_low"],
                "strike_high": family["strike_high"],
                "entries": [
                    {
                        "delta_k": row["delta_k"],
                        "strikes": row["strikes"],
                        "error": row["error"],
                        "relative_error_percent": 100.0 * row["error"] / block["exact"],
                    }
                    for row in family["rows"]
                ],
            }
        )
    flat = reference["flat_replication"]
    heston = reference["heston_replication"]
    plotted = next(row for row in heston["rows"] if row["market"] == block["market"])
    return {
        "market": block["market"],
        "expiry": block["expiry"],
        "forward": block["forward"],
        "exact": block["exact"],
        "families": families,
        "continuous_difference": plotted["difference"],
        "continuous_max_abs_difference": max(abs(row["difference"]) for row in heston["rows"]),
        "continuous_markets": len(heston["rows"]),
        "flat_s_star_max_abs_difference": max(abs(row["difference"]) for row in flat["rows"]),
    }


def _error_slopes(rows):
    """Local log-log slopes of |eq. 26.9 error| against xi between neighbouring grid points."""
    return [
        math.log(abs(b["approximation_error"]) / abs(a["approximation_error"]))
        / math.log(b["xi"] / a["xi"])
        for a, b in itertools.pairwise(rows)
    ]


def _convexity_rows(reference):
    block = reference["volatility_convexity"]
    slopes = _error_slopes(block["rows"])
    rows = []
    for row in block["rows"]:
        entry = {
            "xi": row["xi"],
            "expected_variance": row["expected_variance"],
            "variance_of_variance": row["variance_of_variance"],
            "exact": row["exact_expected_volatility"],
            "approximation": row["approximation"],
            "naive": row["naive"],
            "approximation_error": row["approximation_error"],
            "naive_error": row["naive_error"],
            "mc": None,
        }
        if row["mc"] is not None:
            entry["mc"] = {
                "estimate": row["mc"]["sqrt_mean"],
                "four_standard_errors": 4.0 * row["mc"]["sqrt_mean_se"],
            }
        rows.append(entry)
    return {
        "base": block["base"],
        "mc": block["mc"],
        "error_log_slope_min": min(slopes),
        "error_log_slope_max": max(slopes),
        "all_errors_negative": all(row["approximation_error"] < 0.0 for row in block["rows"]),
        "rows": rows,
    }


def build():
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    hashes = {
        path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS
    }
    money = {"payoff": "$ millions", "volatility": "annualized decimal", "time": "years"}
    variance = {"variance": "variance rate per year", "strike": "index points", "time": "years"}
    return {
        "schema_version": SCHEMA_VERSION,
        "section": "26.16",
        "payoff": _family(
            _payoff_rows(),
            "Undiscounted payoffs at T of Example 26.5's volatility swap and the variance swap "
            "with L_var = L_vol/(2 sigma_K)",
            hashes,
            money,
        ),
        "strip": _family(
            _strip_rows(reference),
            "Example 26.4 strip recomputed with the reference's own BSM; printed Q to 2 dp",
            hashes,
            variance,
        ),
        "replication": _family(
            _replication_rows(reference),
            "Eq. 26.8 strip minus the closed-form Heston E(V) that the continuous eq. 26.6 "
            "integral reproduces",
            hashes,
            variance,
        ),
        "convexity": _family(
            _convexity_rows(reference),
            "Eq. 26.9 and sqrt(E(V)) against the exact CIR-Laplace E[sqrt V] and exact-CIR MC ±4SE",
            hashes,
            {"volatility": "annualized decimal", "vol_of_vol": "xi per sqrt(year)"},
            ["Continuously monitored variance of one Heston/CIR market with v0 = theta."],
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
    print("menu states: payoff payoffs/difference; strip q/contribution")
    print("menu states: replication absolute/relative; convexity levels/error")


if __name__ == "__main__":
    main()
