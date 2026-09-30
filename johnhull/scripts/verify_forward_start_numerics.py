"""Compare Hull §26.5 pricing with independent two-time payoff references."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from hullkit import forward_start

try:
    from . import build_forward_start_reference as reference
except ImportError:
    import build_forward_start_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-26-5/"
OUT = PROJECT / BASE / "numerical-check.json"


def _market(row):
    return {key: row[key] for key in ("S", "r", "sigma", "T1", "T2", "q")}


def verify(data):
    if data != reference.build():
        raise ValueError("saved §26.5 reference differs from independent recomputation")
    differences = [
        abs(forward_start.forward_start_call(**_market(row)) - row["price"])
        for row in [*data["cases"], data["example"]]
    ]
    if max(differences) > 1e-9:
        raise ValueError("forward-start API differs from independent payoff integral")
    figure = data["figure"]
    row = figure["homogeneity"]
    market = _market(row["market"])
    actual = forward_start.forward_start_call(**{**market, "S": row["spot"]})
    differences.extend(np.abs(actual - np.array(row["price"])).tolist())
    for row in figure["delay"]:
        start = np.array(row["start"])
        actual = forward_start.forward_start_call(
            100, 0.05, 0.2, start, start + row["tenor"], row["q"]
        )
        differences.extend(np.abs(actual - np.array(row["price"])).tolist())
    for row in figure["fixed_expiry"]:
        actual = forward_start.forward_start_call(
            100, 0.05, 0.2, row["start"], row["expiry"], row["q"]
        )
        differences.extend(np.abs(actual - np.array(row["price"])).tolist())
    maximum = max(differences)
    if maximum > 1e-9:
        raise ValueError(f"forward-start API differs from independent payoff integral: {maximum}")
    mc_z = [
        abs(row["price"] - row["reference_price"]) / row["standard_error"] for row in data["mc"]
    ]
    if max(mc_z) > 6:
        raise ValueError("two-time Monte Carlo differs by over six standard errors")
    zero_yield = figure["delay"][0]["price"]
    invariant = max(zero_yield) - min(zero_yield)
    homogeneous_row = figure["homogeneity"]
    homogeneous = max(
        abs(p / s - homogeneous_row["price"][0] / homogeneous_row["spot"][0])
        for s, p in zip(figure["homogeneity"]["spot"], figure["homogeneity"]["price"], strict=True)
    )
    if invariant > 1e-10 or homogeneous > 1e-12:
        raise ValueError("same-life delay invariance or spot homogeneity failed")
    return dict(
        case_count=len(data["cases"]),
        max_price_error=maximum,
        max_quadrature_error=max(row["quadrature_error"] for row in data["cases"]),
        max_mc_standard_errors=max(mc_z),
        mc_paths=reference.MC_PATHS,
        same_life_zero_yield_error=invariant,
        homogeneity_error=homogeneous,
        example_price=data["example"]["price"],
        same_life_atm=data["example"]["same_life_atm"],
    )


def negative_controls(data):
    rows = []
    for mutation in ("price", "tenor", "fixing", "discount"):
        changed = copy.deepcopy(data)
        if mutation == "price":
            changed["cases"][8]["price"] += 0.25
        elif mutation == "tenor":
            changed["cases"][8]["T2"] += changed["cases"][8]["T1"]
        elif mutation == "fixing":
            market = _market(changed["mc"][1])
            changed["mc"][1]["price"] = reference.integrate_forward_start(**{**market, "T1": 0.0})[
                0
            ]
        else:
            changed["mc"][1]["price"] *= math.exp(changed["mc"][1]["r"] * changed["mc"][1]["T1"])
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        rows.append(dict(mutation=mutation, rejected=rejected))
    return rows


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((PROJECT / BASE / "reference.json").read_text())
    result = dict(
        section="26.5",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            name: digest(name)
            for name in (
                "scripts/build_forward_start_reference.py",
                "scripts/verify_forward_start_numerics.py",
                "hullkit/src/hullkit/forward_start.py",
                "hullkit/src/hullkit/bsm.py",
            )
        },
        artifact_sha256=digest(BASE + "reference.json"),
    )
    if any(not row["rejected"] for row in result["negative_controls"]):
        raise ValueError("negative control accepted")
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("numerical record missing or stale")
    else:
        OUT.write_text(payload)
    print("PASS: §26.5 integral, Monte Carlo, fixing, delay and homogeneity")


if __name__ == "__main__":
    main()
