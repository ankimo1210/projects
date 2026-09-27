"""Cross-check Hull §27.5 average-state tree with printed and exact values."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_path_dependent_reference import build
from hullkit.path_dependent_tree import arithmetic_average_call_tree

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-5/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_path_dependent_reference.py",
    "scripts/verify_path_dependent_numerics.py",
    "hullkit/src/hullkit/path_dependent_tree.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate():
    """Recompute printed pins, exhaustive small trees and a linear-payoff identity."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent computation")
    p = reference["parameters"]
    errors = {}
    for label in ("coarse", "fine"):
        row = reference["printed"][label]
        for american, kind in ((False, "european"), (True, "american")):
            tree = arithmetic_average_call_tree(
                **p, steps=row["steps"], average_points=row["average_points"], american=american
            )
            errors[f"{label}_{kind}"] = abs(tree.price - row[kind])
    if max(errors.values()) >= 0.01:
        raise AssertionError("public tree does not reproduce the four printed prices")

    coarse = arithmetic_average_call_tree(**p, steps=20, average_points=4)
    x_node = coarse.average_grids[4][2]
    x_values = coarse.value_grids[4][2]
    figure = reference["figure_27_3"]
    grid_error = max(abs(a - b) for a, b in zip(x_node, figure["X"]["averages"], strict=True))
    x_value_error = abs(x_values[2] - figure["X"]["values"][2])
    if grid_error >= 0.01 or x_value_error >= 0.01:
        raise AssertionError("Figure 27.3 node X mismatch")

    exact_errors = []
    for row in reference["exact_small_trees"]:
        for american, kind in ((False, "european"), (True, "american")):
            found = arithmetic_average_call_tree(
                **p, steps=row["steps"], average_points=100, american=american
            ).price
            exact_errors.append(abs(found - row[kind]))
    if max(exact_errors) >= 0.02:
        raise AssertionError("representative average tree differs from exhaustive path tree")

    steps = 12
    linear = arithmetic_average_call_tree(
        **dict(p, strike=0.0), steps=steps, average_points=4
    ).price
    dt = p["maturity"] / steps
    expected_average = sum(
        p["spot"] * math.exp((p["rate"] - p["dividend_yield"]) * i * dt) for i in range(steps + 1)
    ) / (steps + 1)
    moment = math.exp(-p["rate"] * p["maturity"]) * expected_average
    moment_error = abs(linear - moment)
    if moment_error >= 1e-10:
        raise AssertionError("linear average payoff moment identity failed")
    return {
        "section": "27.5",
        "status": "PASS",
        "method": "printed Figure 27.3, exact non-recombining path enumeration, linear-average moment",
        "tolerances": {
            "printed_currency": 0.01,
            "exact_small_currency": 0.02,
            "average_moment_currency": 1e-10,
        },
        "measured": {
            "printed_errors": errors,
            "max_figure_grid_error": grid_error,
            "x_value_error": x_value_error,
            "exact_paths": len(exact_errors),
            "max_exact_path_error": max(exact_errors),
            "moment_error": moment_error,
        },
        "source_sha256": {name: sha(PROJECT / name) for name in SOURCES},
        "artifact_sha256": sha(REF),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(evaluate(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.5 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.5 printed prices, exact paths and average moment")


if __name__ == "__main__":
    main()
