"""Cross-check Hull §27.7 two-asset trees with the independent §27.7 reference."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from build_two_asset_reference import METHODS, build
from hullkit.exotics import exchange_option
from hullkit.two_asset_tree import two_asset_lattice, two_asset_tree

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-7/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_two_asset_reference.py",
    "scripts/verify_two_asset_numerics.py",
    "hullkit/src/hullkit/two_asset_tree.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payoff(kind, strike):
    if kind == "max_call":
        return lambda s1, s2: np.maximum(np.maximum(s1, s2) - strike, 0.0)
    if kind == "min_put":
        return lambda s1, s2: np.maximum(strike - np.minimum(s1, s2), 0.0)
    return lambda s1, s2: np.maximum(s1 - s2, 0.0)


def _price(p, kind, method, steps, *, rho=None, exercise="european"):
    return two_asset_tree(
        tuple(p["spots"]),
        _payoff(kind, p["strike"]),
        p["rate"],
        tuple(p["volatilities"]),
        p["correlation"] if rho is None else rho,
        p["maturity"],
        steps,
        method=method,
        exercise=exercise,
        dividend_yields=tuple(p["dividend_yields"]),
    ).price


def _oscillates(errors):
    """True when a doubling does not roughly halve the error (ratio outside 0.4–0.6)."""
    return any(not 0.4 <= abs(b / a) <= 0.6 for a, b in itertools.pairwise(errors))


def evaluate():
    """Tie the public trees to forward induction, the formulas and Hull's factors."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent computation")
    p = reference["parameters"]
    analytic = reference["analytic"]
    (s1, s2), (q1, q2), (v1, v2) = p["spots"], p["dividend_yields"], p["volatilities"]
    formula_error = abs(
        exchange_option(s2, s1, v2, v1, p["correlation"], p["maturity"], q_u=q2, q_v=q1)
        - analytic["exchange"]
    )
    if formula_error >= 1e-12 or abs(analytic["max_call"]["difference"]) >= 1e-9:
        raise AssertionError("European two-asset formulas disagree")

    lattice_error = 0.0
    dense = reference["convergence"]
    for index, steps in enumerate(dense["steps"]):
        for method in METHODS:
            found = (
                _price(p, "exchange", method, steps),
                _price(p, "exchange", method, steps, exercise="american"),
            )
            expected = (dense["european"][method][index], dense["american"][method][index])
            lattice_error = max(
                lattice_error, *(abs(a - b) for a, b in zip(found, expected, strict=True))
            )
    errors = reference["errors"]
    for index, steps in enumerate(errors["steps"]):
        for method in METHODS:
            for kind, base in (
                ("max_call", analytic["max_call"]["stulz"]),
                ("exchange", analytic["exchange"]),
            ):
                found = _price(p, kind, method, steps) - base
                lattice_error = max(lattice_error, abs(found - errors[f"{method}_{kind}"][index]))
    sweep = reference["correlation"]
    for index, rho in enumerate(sweep["rho"]):
        for method in METHODS:
            found = _price(p, "max_call", method, sweep["steps"], rho=rho)
            expected = sweep["reference"][index] + sweep[method][index]
            lattice_error = max(lattice_error, abs(found - expected))
    for case in reference["cases"]:
        found = _price(p, case["payoff"], case["method"], case["steps"], rho=case["correlation"])
        lattice_error = max(lattice_error, abs(found - case["tree"]))
    american_max = reference["american_max_call"]
    for index, steps in enumerate(american_max["steps"]):
        for method in METHODS:
            found = _price(p, "max_call", method, steps, exercise="american")
            lattice_error = max(lattice_error, abs(found - american_max[method][index]))
    if lattice_error >= 1e-10:
        raise AssertionError("backward trees differ from the independent lattice computation")

    hand = reference["hand_example"]
    hand_error = 0.0
    for method in METHODS:
        lattice = two_asset_lattice(
            p["rate"],
            tuple(p["volatilities"]),
            p["correlation"],
            hand["dt"],
            method=method,
            dividend_yields=tuple(p["dividend_yields"]),
        )
        moves, probabilities = zip(*lattice.branches(), strict=True)
        mean, covariance = lattice.log_moments()
        hand_error = max(
            hand_error,
            float(np.max(np.abs(np.array(moves) - hand[method]["moves"]))),
            float(np.max(np.abs(np.array(probabilities) - hand[method]["probabilities"]))),
            float(np.max(np.abs(mean - hand["target"]["mean"]))),
            float(np.max(np.abs(covariance - np.array(hand["target"]["covariance"])))),
        )
    table = two_asset_lattice(0.05, (0.2, 0.3), 0.5, 0.01, method="adjusted").probabilities
    if hand_error >= 1e-15 or table != (0.375, 0.125, 0.125, 0.375):
        raise AssertionError("Hull §27.7 factors, Table 27.3 or one-step moments mismatch")

    transform = errors["transform_max_call"]
    order = errors["transform_max_call_order"]
    smooth = all(e > 0 for e in transform) and not _oscillates(transform)
    wobbly = {m: _oscillates(errors[f"{m}_max_call"]) for m in ("rubinstein", "adjusted")}
    final = {
        f"{m}_{kind}": abs(errors[f"{m}_{kind}"][-1])
        for m in METHODS
        for kind in ("max_call", "exchange")
    }
    if not smooth or not all(wobbly.values()) or not 0.9 <= order <= 1.1:
        raise AssertionError("convergence pattern of the three trees changed")
    if max(final.values()) >= 0.0015:
        raise AssertionError("800-step European errors are too large")

    american_ref = analytic["american_exchange"]
    premium = american_ref["value"] - analytic["exchange"]
    last_american = {m: dense["american"][m][-1] - american_ref["value"] for m in METHODS}
    if american_ref["half_spread"] >= 2.5e-5 or premium <= 0.4:
        raise AssertionError("1-D American exchange reference is not sharp enough")
    if max(abs(e) for e in last_american.values()) >= 0.005:
        raise AssertionError("200-step American exchange trees miss the 1-D reference")

    coincide = {}
    for rho in (-1.0, 0.0, 1.0):
        index = sweep["rho"].index(rho)
        coincide[str(rho)] = abs(sweep["rubinstein"][index] - sweep["adjusted"][index])
    apart = abs(
        sweep["rubinstein"][sweep["rho"].index(0.5)] - sweep["adjusted"][sweep["rho"].index(0.5)]
    )
    if max(coincide.values()) >= 1e-12 or apart <= 1e-4:
        raise AssertionError("Rubinstein and adjusted trees coincide at the wrong correlations")

    raw = [american_max[m][-1] for m in METHODS]
    controlled = [american_max[f"{m}_control_variate"][-1] for m in METHODS]
    spreads = {"raw": max(raw) - min(raw), "control_variate": max(controlled) - min(controlled)}
    if spreads["control_variate"] >= 5e-4 or spreads["control_variate"] >= spreads["raw"]:
        raise AssertionError("control variate does not tighten the American max-call trees")

    return {
        "section": "27.7",
        "status": "PASS",
        "method": (
            "forward lattice induction and a separately written backward induction on Hull's "
            "printed factors, Stulz and Margrabe formulas, 1-D American exchange reduction"
        ),
        "tolerances": {
            "lattice_currency": 1e-10,
            "formula_currency": 1e-12,
            "stulz_integration_currency": 1e-9,
            "hand_factors": 1e-15,
            "transform_order": [0.9, 1.1],
            "final_european_currency_800_steps": 0.0015,
            "american_exchange_currency_200_steps": 0.005,
            "one_dimensional_half_spread": 2.5e-5,
            "control_variate_spread_800_steps": 5e-4,
        },
        "measured": {
            "max_lattice_error": lattice_error,
            "formula_error": formula_error,
            "stulz_integration_difference": analytic["max_call"]["difference"],
            "hand_error": hand_error,
            "transform_max_call_order": order,
            "transform_smooth": smooth,
            "oscillating": wobbly,
            "final_errors_800_steps": final,
            "american_exchange_reference": american_ref["value"],
            "american_exchange_half_spread": american_ref["half_spread"],
            "early_exercise_premium": premium,
            "american_exchange_errors_200_steps": last_american,
            "rubinstein_adjusted_gap": {**coincide, "0.5": apart},
            "american_max_call_800_steps": {"raw": raw, "control_variate": controlled},
            "american_max_call_spreads": spreads,
            "lattice_cases": len(reference["cases"]),
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
            raise SystemExit("FAIL: §27.7 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.7 lattices, formulas, Hull factors and the 1-D American reduction")


if __name__ == "__main__":
    main()
