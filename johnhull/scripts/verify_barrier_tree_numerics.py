"""Cross-check Hull §27.6 barrier trees with the independent §27.6 reference."""

import argparse
import hashlib
import json
from pathlib import Path

from build_barrier_tree_reference import LATTICE_STEPS, build
from hullkit.barrier_tree import (
    barrier_log_spacing,
    binomial_barrier,
    interpolated_barrier,
    trinomial_barrier,
    trinomial_probabilities,
)
from hullkit.exotics import barrier_call

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-6/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_barrier_tree_reference.py",
    "scripts/verify_barrier_tree_numerics.py",
    "hullkit/src/hullkit/barrier_tree.py",
)
KEYS = ("binomial_simple", "trinomial_simple", "interpolated", "on_barrier")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public(p, steps):
    args = (
        p["spot"],
        p["strike"],
        p["barrier"],
        p["rate"],
        p["volatility"],
        p["maturity"],
        steps,
    )
    simple = trinomial_barrier(*args, method="simple")
    return {
        "binomial_simple": binomial_barrier(*args).price,
        "trinomial_simple": simple.price,
        "interpolated": interpolated_barrier(*args).price,
        "on_barrier": trinomial_barrier(*args, method="on_barrier").price,
        "outer_barrier": simple.tree_barrier,
    }


def evaluate():
    """Tie the public trees to forward induction, the formulas and Hull's spacing rule."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent computation")
    p = reference["parameters"]
    analytic = reference["analytic"]["continuous"]
    formula_error = abs(
        barrier_call(
            p["spot"],
            p["strike"],
            p["barrier"],
            p["rate"],
            p["volatility"],
            p["maturity"],
            q=p["dividend_yield"],
            barrier="up-and-out",
        )
        - analytic
    )
    if formula_error >= 1e-12:
        raise AssertionError("hullkit §26.9 formula differs from the independent formula")

    dense = reference["convergence"]
    lattice_error = 0.0
    for index, steps in enumerate(dense["steps"]):
        row = _public(p, steps)
        for key in (*KEYS, "outer_barrier"):
            lattice_error = max(lattice_error, abs(row[key] - dense[key][index]))
    doubling = reference["errors"]
    for index, steps in enumerate(doubling["steps"]):
        row = _public(p, steps)
        for key in ("trinomial_simple", "interpolated", "on_barrier"):
            lattice_error = max(lattice_error, abs(row[key] - analytic - doubling[key][index]))
    for case in reference["cases"]:
        q = dict(p, barrier=case["barrier"], dividend_yield=case["dividend_yield"])
        args = (q["spot"], q["strike"], q["barrier"], q["rate"], q["volatility"], q["maturity"])
        options = dict(
            option=case["option"],
            barrier_type=case["barrier_type"],
            dividend_yield=case["dividend_yield"],
        )
        found = {
            "binomial_simple": binomial_barrier(*args, case["steps"], **options).price,
            "trinomial_simple": trinomial_barrier(*args, case["steps"], **options).price,
            "trinomial_inner": trinomial_barrier(
                *args, case["steps"], method="inner", **options
            ).price,
            "on_barrier": trinomial_barrier(
                *args, case["steps"], method="on_barrier", **options
            ).price,
        }
        for key, value in found.items():
            lattice_error = max(lattice_error, abs(value - case[key]))
    if lattice_error >= 1e-10:
        raise AssertionError("backward trees differ from forward lattice induction")

    monitoring = reference["monitoring"]
    bgk_error = 0.0
    for index, steps in enumerate(monitoring["steps"]):
        discrete = barrier_call(
            p["spot"],
            p["strike"],
            p["barrier"],
            p["rate"],
            p["volatility"],
            p["maturity"],
            q=p["dividend_yield"],
            barrier="up-and-out",
            n_observations=steps,
        )
        bgk_error = max(bgk_error, abs(discrete - analytic - monitoring["bgk_discrete"][index]))
        tree, bgk = monitoring["tree_on_barrier"][index], monitoring["bgk_discrete"][index]
        if not tree < 0 < bgk or abs(tree) >= bgk:
            raise AssertionError("tree monitoring behaves like discrete monitoring")
    if bgk_error >= 1e-12:
        raise AssertionError("BGK reference differs from hullkit.exotics")

    simple_error = max(abs(value - analytic) for value in dense["trinomial_simple"])
    late = [i for i, steps in enumerate(dense["steps"]) if steps >= 100]
    outer_gap = max(abs(dense["trinomial_simple"][i] - dense["outer_analytic"][i]) for i in late)
    if simple_error < 0.5 or outer_gap >= 0.05:
        raise AssertionError("simple tree is not explained by its outer barrier")
    order = doubling["on_barrier_order"]
    final = {key: abs(doubling[key][-1]) for key in ("interpolated", "on_barrier")}
    if not 0.9 <= order <= 1.1 or final["on_barrier"] >= 0.0015 or final["interpolated"] >= 0.001:
        raise AssertionError("barrier-aware trees do not converge at first order")

    hand = reference["hand_example"]
    dt = p["maturity"] / hand["steps"]
    levels, spacing = barrier_log_spacing(p["spot"], p["barrier"], p["volatility"], dt)
    branch = trinomial_probabilities(spacing, p["rate"], p["volatility"], dt)
    hand_error = max(
        abs(spacing - hand["log_spacing"]),
        *(
            abs(a - b)
            for a, b in zip(branch, (hand["p_up"], hand["p_middle"], hand["p_down"]), strict=True)
        ),
        abs(hand["mean"] - (p["rate"] - p["volatility"] ** 2 / 2) * dt),
        abs(hand["second_moment"] - p["volatility"] ** 2 * dt),
    )
    if levels != hand["levels"] or hand_error >= 1e-14:
        raise AssertionError("Hull §27.6 spacing or moment match failed")

    example = reference["lattice_example"]
    small = (
        p["spot"],
        p["strike"],
        p["barrier"],
        p["rate"],
        p["volatility"],
        p["maturity"],
        LATTICE_STEPS,
    )
    geometry_error = max(
        abs(trinomial_barrier(*small).tree_barrier - example["standard"]["outer_barrier"]),
        abs(
            trinomial_barrier(*small, method="inner").tree_barrier
            - example["standard"]["inner_barrier"]
        ),
        abs(
            trinomial_barrier(*small, method="on_barrier").log_spacing
            - example["on_barrier"]["log_spacing"]
        ),
    )
    if geometry_error >= 1e-12:
        raise AssertionError("Figure 27.4/27.5 lattice geometry mismatch")

    near = reference["near_barrier"]
    probability_error = 0.0
    for steps, curve in near["curves"].items():
        dt = p["maturity"] / int(steps)
        for index, barrier in enumerate(curve["barrier"]):
            found_levels, found = barrier_log_spacing(p["spot"], barrier, p["volatility"], dt)
            branch = trinomial_probabilities(found, p["rate"], p["volatility"], dt)
            expected = [curve[key][index] for key in ("p_up", "p_middle", "p_down")]
            if found_levels != curve["levels"][index]:
                raise AssertionError("near-barrier level mismatch")
            probability_error = max(
                probability_error, *(abs(a - b) for a, b in zip(branch, expected, strict=True))
            )
            if (branch[1] < 0) != (barrier < curve["negative_middle_below"]):
                raise AssertionError("negative middle branch threshold mismatch")
    if probability_error >= 1e-14:
        raise AssertionError("near-barrier probabilities mismatch")
    rejected = []
    for case in near["cases"]:
        try:
            trinomial_barrier(
                p["spot"],
                p["strike"],
                case["barrier"],
                p["rate"],
                p["volatility"],
                p["maturity"],
                case["steps"],
                method="on_barrier",
            )
            accepted = True
        except ValueError:
            accepted = False
        if accepted != (case["levels"] > 0 and case["p_middle"] >= 0):
            raise AssertionError(f"near-barrier case handled wrongly: {case}")
        if not accepted:
            rejected.append(f"H={case['barrier']}, N={case['steps']}")

    return {
        "section": "27.6",
        "status": "PASS",
        "method": (
            "forward lattice induction, §26.9 continuous formula, Crank–Nicolson PDE, "
            "Hull spacing and moment identities"
        ),
        "tolerances": {
            "lattice_currency": 1e-10,
            "formula_currency": 1e-12,
            "pde_currency": 1e-5,
            "on_barrier_order": [0.9, 1.1],
            "final_on_barrier_currency": 0.0015,
            "final_interpolated_currency": 0.001,
            "outer_barrier_gap_from_100_steps": 0.05,
        },
        "measured": {
            "max_lattice_error": lattice_error,
            "formula_error": formula_error,
            "pde_error": reference["analytic"]["pde"]["error"],
            "max_simple_trinomial_error": simple_error,
            "max_outer_barrier_gap_from_100_steps": outer_gap,
            "on_barrier_order": order,
            "final_errors_3200_steps": final,
            "hand_error": hand_error,
            "geometry_error": geometry_error,
            "near_probability_error": probability_error,
            "near_rejected": rejected,
            "lattice_cases": len(reference["cases"]),
            "bgk_error": bgk_error,
            "monitoring": monitoring,
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
            raise SystemExit("FAIL: §27.6 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.6 lattice, formula, PDE, spacing and near-barrier limits")


if __name__ == "__main__":
    main()
