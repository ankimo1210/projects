"""Recompute independent §28.1 inputs and compare real APIs and RN weights."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-28-1/"
OUT = PROJECT / BASE / "numerical-check.json"
SOURCES = (
    "scripts/build_risk_premium_reference.py",
    "scripts/verify_risk_premium_numerics.py",
    "hullkit/src/hullkit/risk_premium.py",
    "hullkit/src/hullkit/sde.py",
)


def verify(data):
    try:
        from .build_risk_premium_reference import build
    except ImportError:
        from build_risk_premium_reference import build
    from hullkit import risk_premium as premium
    from hullkit.sde import girsanov_weights

    fresh = build()
    if data != fresh:
        raise ValueError("independent reference differs from saved inputs")
    errors = []

    def compare(actual, expected):
        actual, expected = np.asarray(actual), np.asarray(expected)
        if not np.all(np.isfinite(actual)):
            raise ValueError("API returned nonfinite independent output")
        error = float(np.max(np.abs(actual - expected), initial=0))
        errors.append(error)
        if error > 1e-10:
            raise ValueError("API differs from independent risk reference")

    for row in data["cases"]:
        compare(
            premium.market_price_of_risk(row["mu"], row["r"], row["loading"]), row["risk_price"]
        )
        compare(premium.required_return(row["r"], row["risk_price"], row["loading"]), row["mu"])
        compare(
            premium.market_price_of_risk(row["mu"], row["r"], -row["loading"]), -row["risk_price"]
        )
    for row in data["powers"]:
        compare(premium.required_return(row["r"], row["risk_price"], row["loading"]), row["drift"])
        if row["loading"]:
            compare(premium.market_price_of_risk(row["drift"], row["r"], row["loading"]), 0.25)
    compare(
        premium.market_price_of_risk(0.12, 0.08, 0.2), data["printed_pins"]["example_28_1_lambda"]
    )
    compare(
        premium.market_price_of_risk(0.03, 0.06, 0.2), data["printed_pins"]["example_28_2_lambda"]
    )
    compare(premium.required_return(0.06, -0.15, 0.3), data["printed_pins"]["example_28_2_return"])
    hedge = data["figure"]["hedge"]
    portfolio_error = max(abs(sum(hedge["risk"])), abs(sum(hedge["returns"]) - hedge["r"]))
    density = data["figure"]["density"]
    density_error = float(np.max(np.abs(np.array(density["q"]) - density["weighted_p"])))
    if portfolio_error > 1e-10 or density_error > 1e-10:
        raise ValueError("independent portfolio or measure density failed")
    z = np.random.default_rng(data["seed"]).standard_normal(data["mc_paths"])
    standardized, normalization_errors, production_errors = [], [], []
    for row in data["mc"]:
        r, lam, s, t = (row[key] for key in ("r", "risk_price", "loading", "T"))
        terminal = row["f0"] * np.exp((r + lam * s - 0.5 * s * s) * t + s * math.sqrt(t) * z)
        weights = girsanov_weights(terminal, row["f0"], abs(s), t, r + lam * s, r)
        estimate = float(np.mean(math.exp(-r * t) * weights * terminal))
        production_errors.append(abs(estimate - row["weighted_price"]))
        compare(estimate, row["weighted_price"])
        for actual, expected, se in (
            (row["weighted_price"], 100, row["weighted_se"]),
            (row["direct_price"], 100, row["direct_se"]),
            (row["weight_mean"], 1, row["weight_se"]),
            (row["paired_difference"], 0, row["paired_se"]),
        ):
            standardized.append(abs(actual - expected) / se if se else abs(actual - expected))
        normalization_errors.append(abs(row["reference_weight"] - 1))
        if abs(row["reference_price"] - 100) > 1e-8:
            raise ValueError("independent weighted Gaussian integral failed")
    if max(standardized) > 6 or max(normalization_errors) > 1e-10:
        raise ValueError("independent MC or raw RN normalization failed")
    return dict(
        case_count=len(data["cases"]),
        power_count=len(data["powers"]),
        printed_pins=data["printed_pins"],
        max_api_error=max(errors),
        max_portfolio_error=portfolio_error,
        max_density_error=density_error,
        max_weight_normalization_error=max(normalization_errors),
        max_production_weight_error=max(production_errors),
        max_quadrature_error=max(row["quadrature_error"] for row in data["powers"] + data["mc"]),
        max_mc_standard_errors=max(standardized),
        mc_paths=data["mc_paths"],
    )


def negative_controls(data):
    controls = []
    for name in ("printed pin", "power drift", "RN normalization", "measure density"):
        changed = copy.deepcopy(data)
        if name == "printed pin":
            changed["printed_pins"]["example_28_2_return"] += 0.001
        elif name == "power drift":
            changed["powers"][0]["drift"] += 0.01
        elif name == "RN normalization":
            changed["mc"][0]["weight_mean"] = 1.0
        else:
            changed["figure"]["density"]["weighted_p"][65] += 0.05
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        controls.append(dict(mutation=name, rejected=rejected))
    return controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((PROJECT / BASE / "reference.json").read_text(encoding="utf-8"))
    record = dict(
        section="28.1",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCES
        },
        artifact_sha256=hashlib.sha256(
            (PROJECT / BASE / "reference.json").read_bytes()
        ).hexdigest(),
    )
    if any(not row["rejected"] for row in record["negative_controls"]):
        raise ValueError("risk premium negative control accepted")
    payload = (
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("risk premium numerical record missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §28.1 signed risk premiums, portfolio, densities and raw paired MC")


if __name__ == "__main__":
    main()
