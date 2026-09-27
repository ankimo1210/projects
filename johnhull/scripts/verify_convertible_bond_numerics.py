"""Cross-check the public §27.4 tree against independent recursion and limits."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_convertible_bond_reference import build
from hullkit.convertible_bond import convertible_bond_tree, defaultable_branch_probabilities
from scipy.stats import norm

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-4/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_convertible_bond_reference.py",
    "scripts/verify_convertible_bond_numerics.py",
    "hullkit/src/hullkit/convertible_bond.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate():
    """Recompute the independent reference, nodes, scenarios and closed forms."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent recursion")
    p = reference["parameters"]
    model = convertible_bond_tree(**p)
    positions = {
        "A": (0, 0),
        "B": (1, 1),
        "C": (1, 0),
        "D": (2, 2),
        "E": (2, 1),
        "F": (2, 0),
        "G": (3, 3),
        "H": (3, 2),
        "I": (3, 1),
        "J": (3, 0),
    }
    node_errors = []
    for name, (time, up) in positions.items():
        expected = reference["textbook"]["nodes"][name]
        node_errors.append(abs(model.bond_levels[time][up] - expected["value"]))
        if model.decisions[time][up] != expected["decision"]:
            raise AssertionError(f"node {name} decision differs from independent recursion")
    scenarios = reference["scenarios"]
    scenario_errors = []
    for key, override in (
        ("credit", "hazard_rate"),
        ("recovery", "recovery_value"),
        ("call", "call_price"),
        ("convergence", "steps"),
    ):
        for row in scenarios[key]:
            found = convertible_bond_tree(**dict(p, **{override: row[override]})).price
            scenario_errors.append(abs(found - row["price"]))
    probabilities = defaultable_branch_probabilities(0.05, 0, 0.3, 0.01, 0.25)
    ref_prob = reference["textbook"]["probabilities"]
    probability_error = max(
        abs(value - ref_prob[key])
        for value, key in zip(probabilities, ("up", "down", "default"), strict=True)
    )
    if max(node_errors + scenario_errors + [probability_error]) >= 1e-10:
        raise AssertionError("public tree differs from independent recursive reference")

    # No conversion/call: direct survival-weighted coupon, recovery and face cash flows.
    coupon_terms = dict(p, conversion_ratio=0.0, call_price=None, coupon_amount=2.0)
    bond = convertible_bond_tree(**coupon_terms).price
    dt = p["maturity"] / p["steps"]
    survive = math.exp(-p["hazard_rate"] * dt)
    discount = math.exp(-p["rate"] * dt)
    cashflows = (
        sum(
            discount**i
            * (survive**i * 2.0 + survive ** (i - 1) * (1 - survive) * p["recovery_value"])
            for i in range(1, p["steps"] + 1)
        )
        + (discount * survive) ** p["steps"] * p["face"]
    )
    coupon_error = abs(bond - cashflows)
    if coupon_error >= 1e-10:
        raise AssertionError("coupon/recovery cash-flow identity failed")

    # No default, dividend or call: face discount bond plus European call on shares.
    no_credit = dict(p, hazard_rate=0.0, call_price=None, steps=400)
    tree_limit = convertible_bond_tree(**no_credit).price
    strike = p["face"] / p["conversion_ratio"]
    vol_time = p["volatility"] * math.sqrt(p["maturity"])
    d1 = (
        math.log(p["spot"] / strike) + (p["rate"] + p["volatility"] ** 2 / 2) * p["maturity"]
    ) / vol_time
    d2 = d1 - vol_time
    call_value = p["spot"] * norm.cdf(d1) - strike * math.exp(
        -p["rate"] * p["maturity"]
    ) * norm.cdf(d2)
    closed_form = (
        p["face"] * math.exp(-p["rate"] * p["maturity"]) + p["conversion_ratio"] * call_value
    )
    limit_error = abs(tree_limit - closed_form)
    if limit_error >= 0.02:
        raise AssertionError("no-default/no-call BSM decomposition failed")
    return {
        "section": "27.4",
        "status": "PASS",
        "method": "independent memoized recursion, printed Figure 27.2, cash-flow identity, BSM limit",
        "tolerances": {
            "node_and_scenario_currency": 1e-10,
            "coupon_identity_currency": 1e-10,
            "bsm_limit_currency": 0.02,
        },
        "measured": {
            "textbook_price": model.price,
            "nodes": len(node_errors),
            "scenarios": len(scenario_errors),
            "max_node_error": max(node_errors),
            "max_scenario_error": max(scenario_errors),
            "probability_error": probability_error,
            "coupon_identity_error": coupon_error,
            "bsm_limit_error": limit_error,
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
            raise SystemExit("FAIL: §27.4 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.4 public tree, printed example, cash flows and BSM limit")


if __name__ == "__main__":
    main()
