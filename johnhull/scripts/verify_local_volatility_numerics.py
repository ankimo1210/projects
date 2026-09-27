"""Verify Hull §27.3 Dupire inversion against an independent analytic mixture."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build_local_volatility_reference import build, mixture_call
from hullkit import bsm
from hullkit.local_volatility import dupire_local_vol

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-3/numerical-check.json"
REF = OUT.with_name("reference.json")
TOLERANCES = {
    "local_vol_absolute": 2e-4,
    "pde_repricing_currency": 0.005,
    "flat_bsm_vol_absolute": 2e-4,
    "term_carry_vol_absolute": 2e-4,
}
SOURCES = (
    "scripts/build_local_volatility_reference.py",
    "scripts/verify_local_volatility_numerics.py",
    "hullkit/src/hullkit/local_volatility.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate():
    """Recompute the reference and all public-model comparisons before PASS."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise ValueError("saved independent reference differs from fresh computation")
    p = reference["parameters"]
    errors = []
    for t in reference["maturities"]:
        for k, exact in zip(
            reference["strikes"], reference["slices"][str(t)]["local_vols"], strict=True
        ):
            estimate = dupire_local_vol(
                mixture_call,
                k,
                t,
                p["rate"],
                p["dividend_yield"],
                strike_step=0.05,
                maturity_step=0.001,
            )
            errors.append(abs(estimate - exact))
    pde_errors = [
        abs(row["local_vol_pde_call"] - row["market_call"]) for row in reference["pde_repricing"]
    ]

    def flat(k, t):
        return float(bsm.call_price(100, k, 0.04, 0.23, t, 0.015))

    flat_errors = [
        abs(dupire_local_vol(flat, k, t, 0.04, 0.015, strike_step=0.05, maturity_step=0.001) - 0.23)
        for k in (75.0, 100.0, 125.0)
        for t in (0.5, 1.0, 2.0)
    ]

    def varying_carry(k, t):
        return float(bsm.call_price(100, k, 0.02 + 0.005 * t, 0.2, t, 0.01 + 0.002 * t))

    term_error = abs(
        dupire_local_vol(varying_carry, 105, 1, 0.03, 0.014, strike_step=0.05, maturity_step=0.001)
        - 0.2
    )
    if max(errors) >= TOLERANCES["local_vol_absolute"]:
        raise AssertionError("Dupire inversion does not match the analytic mixture")
    if max(pde_errors) >= TOLERANCES["pde_repricing_currency"]:
        raise AssertionError("backward local-vol PDE does not reprice mixture calls")
    if (
        max(flat_errors) >= TOLERANCES["flat_bsm_vol_absolute"]
        or term_error >= TOLERANCES["term_carry_vol_absolute"]
    ):
        raise AssertionError("flat-vol or varying-carry limit failed")
    if not all(math.isfinite(v) for v in errors + pde_errors + flat_errors + [term_error]):
        raise AssertionError("nonfinite comparison")

    for t in reference["maturities"]:
        slice_ = reference["slices"][str(t)]
        calls = np.asarray(slice_["calls"])
        if not (np.all(np.diff(calls) < 0) and np.all(np.diff(calls, n=2) > 0)):
            raise AssertionError("synthetic price slice is not decreasing and convex")
        vols = slice_["local_vols"]
        if not all(
            min(p["component_volatilities"]) < vol < max(p["component_volatilities"])
            for vol in vols
        ):
            raise AssertionError("conditional local volatility left the mixture component bounds")
    paths = reference["two_date_models"]
    marginal_z = [
        abs(paths[key]["paired_difference"]) / paths[key]["paired_standard_error"]
        for key in ("half_year_up", "one_year_up")
    ]
    joint_z = (
        abs(paths["both_dates_up"]["paired_difference"])
        / paths["both_dates_up"]["paired_standard_error"]
    )
    if max(marginal_z) >= 3 or joint_z <= 5:
        raise AssertionError("one-date marginals or two-date joint contrast failed")

    return {
        "section": "27.3",
        "status": "PASS",
        "method": "independent analytic latent-volatility mixture, Dupire finite differences, backward spot PDE",
        "tolerances": TOLERANCES,
        "measured": {
            "points": len(errors),
            "max_local_vol_absolute_error": max(errors),
            "max_pde_repricing_currency_error": max(pde_errors),
            "max_flat_bsm_vol_error": max(flat_errors),
            "varying_carry_vol_error": term_error,
            "latent_vs_local_one_date_max_paired_z": max(marginal_z),
            "latent_vs_local_two_date_paired_z": joint_z,
            "latent_vs_local_two_date_probability_gap": paths["both_dates_up"]["paired_difference"],
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
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.3 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.3 independent Dupire inversion and backward PDE repricing")


if __name__ == "__main__":
    main()
