"""Independent browser oracle for §26.16; no hullkit or lesson imports.

Payoffs are recomputed from the contract formulas; strip, replication and
convexity values are read from the M8a reference (never from lesson-data or
plotting arrays). The notebook's printed examples are recomputed here too.
"""

import hashlib
import itertools
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-16"
SOURCES = (
    "scripts/build_variance_swap_browser_reference.py",
    "scripts/build_variance_swap_reference.py",
    "docs/validation/section-26-16/reference.json",
    "docs/validation/section-26-16/numerical-check.json",
)
VOL_NOTIONAL, VOL_STRIKE = 100.0, 0.23


def build():
    reference = json.loads((VALIDATION / "reference.json").read_text(encoding="utf-8"))
    sigma = [round(0.10 + 0.01 * i, 2) for i in range(31)]
    var_notional = VOL_NOTIONAL / (2 * VOL_STRIKE)
    example = reference["example_26_4"]
    rows = example["rows"]
    expiry = 0.25
    convergence = reference["strip_convergence"]
    convexity = reference["volatility_convexity"]["rows"]
    mc_rows = [row for row in convexity if row["mc"] is not None]
    path = [100.0, 101.0, 99.0, 100.5, 102.0]
    squares = math.fsum(math.log(b / a) ** 2 for a, b in itertools.pairwise(path))
    example5 = reference["example_26_5"]
    vix = reference["vix"]["example_26_4"]
    return {
        "source_sha256": {
            source: hashlib.sha256((PROJECT / source).read_bytes()).hexdigest()
            for source in SOURCES
        },
        "payoff": {
            "sigma": sigma,
            "variance_notional": var_notional,
            "volatility": [VOL_NOTIONAL * (s - VOL_STRIKE) for s in sigma],
            "variance": [var_notional * (s * s - VOL_STRIKE**2) for s in sigma],
            "difference": [VOL_NOTIONAL * (s - VOL_STRIKE) ** 2 / (2 * VOL_STRIKE) for s in sigma],
        },
        "strip": {
            "forward": example["forward"],
            "s_star": example["s_star"],
            "boundary": example["boundary_terms"],
            "expected_variance": example["expected_variance"],
            "rows": [
                {
                    "K": row["strike"],
                    "kind": row["q_kind"],
                    "q": row["q"],
                    "printed": row["printed_q"],
                    "contribution": 2 / expiry * row["contribution"],
                }
                for row in rows
            ],
        },
        "replication": {
            "exact": convergence["exact"],
            "families": {
                family["range"]: {
                    "delta_k": [row["delta_k"] for row in family["rows"]],
                    "absolute": [row["error"] for row in family["rows"]],
                    "relative": [
                        100 * row["error"] / convergence["exact"] for row in family["rows"]
                    ],
                }
                for family in convergence["families"]
            },
        },
        "convexity": {
            "xi": [row["xi"] for row in convexity],
            "exact": [100 * row["exact_expected_volatility"] for row in convexity],
            "approximation": [100 * row["approximation"] for row in convexity],
            "naive": [100 * row["naive"] for row in convexity],
            "approximation_error": [100 * row["approximation_error"] for row in convexity],
            "naive_error": [100 * row["naive_error"] for row in convexity],
            "mc_xi": [row["xi"] for row in mc_rows],
            "mc": [100 * row["mc"]["sqrt_mean"] for row in mc_rows],
            "mc_four_se": [400 * row["mc"]["sqrt_mean_se"] for row in mc_rows],
        },
        "notebook": {
            "realized_n2": 252 * squares / 3,
            "realized_n1": 252 * squares / 4,
            "variance_notional": var_notional,
            "example_26_4_expected_variance": example["expected_variance"],
            "example_26_4_value": example["swap_value"],
            "example_26_5_expected_volatility": example5["expected_volatility"],
            "example_26_5_value": example5["swap_value"],
            "naive_volatility": math.sqrt(0.0621),
            "cumulative_26_6": vix["cumulative_variance_26_6"],
            "cumulative_26_10": vix["cumulative_variance_26_10"],
        },
    }


def main():
    result = build()
    path = VALIDATION / "browser-reference.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"wrote {path.relative_to(PROJECT)}")
    print(result["notebook"])


if __name__ == "__main__":
    main()
