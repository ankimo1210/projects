"""Compare the §28.1 API with independent real-world quadrature, examples and MC."""

import argparse
import copy
import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

from hullkit import bsm
from hullkit import market_price_of_risk as mpr

try:
    from . import build_market_price_of_risk_reference as reference
except ImportError:
    import build_market_price_of_risk_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-28-1/"
OUT = PROJECT / BASE / "numerical-check.json"
TOLERANCE = 1e-8


def _finite(value):
    if not math.isfinite(value):
        raise ValueError("market price of risk API produced a nonfinite value")
    return value


def _greeks(row):
    """Analytic production Greeks for the claims hullkit prices directly."""
    s, k, r, sigma, t = row["S"], row["K"], row["r"], row["sigma"], row["T"]
    if row["kind"] == "stock":
        return s, 0.0, 1.0, 0.0
    if row["kind"] == "call":
        return (
            bsm.call_price(s, k, r, sigma, t),
            bsm.call_theta(s, k, r, sigma, t),
            bsm.call_delta(s, k, r, sigma, t),
            bsm.gamma(s, k, r, sigma, t),
        )
    if row["kind"] == "put":
        return (
            bsm.put_price(s, k, r, sigma, t),
            bsm.put_theta(s, k, r, sigma, t),
            bsm.put_delta(s, k, r, sigma, t),
            bsm.gamma(s, k, r, sigma, t),
        )
    return None


def verify(data):
    if data != reference.build():
        raise ValueError("saved §28.1 reference differs from independent recomputation")
    errors, ito, holdings, worlds = [], [], [], []
    ex1, ex2 = data["examples"]["example_28_1"], data["examples"]["example_28_2"]
    printed = (
        (_finite(mpr.market_price_of_risk(ex1["m"], ex1["s"], ex1["r"])), 0.2),
        (_finite(mpr.market_price_of_risk(ex2["m1"], ex2["s1"], ex2["r"])), -0.15),
        (_finite(mpr.required_growth(ex2["r"], -0.15, ex2["s2"])), 0.015),
    )
    for actual, pin in printed:
        if abs(actual - pin) > 1e-12:
            raise ValueError("printed Example 28.1/28.2 value differs from independent reference")
    for row in [*data["contracts"], *data["negative_contracts"]]:
        lam = (row["mu"] - row["r"]) / row["sigma"]
        errors.append(
            abs(_finite(mpr.market_price_of_risk(row["growth"], row["loading"], row["r"])) - lam)
        )
        errors.append(
            abs(_finite(mpr.required_growth(row["r"], lam, row["loading"])) - row["growth"])
        )
        greeks = _greeks(row)
        if greeks is not None:
            growth, loading = mpr.ito_growth_and_loading(*greeks, row["S"], row["mu"], row["sigma"])
            ito.extend(
                (abs(_finite(growth) - row["growth"]), abs(_finite(loading) - row["loading"]))
            )
    for row in data["riskless"]:
        one, two = row["first"], row["second"]
        n1, n2 = mpr.riskless_holdings(one["price"], one["loading"], two["price"], two["loading"])
        value = n1 * one["price"] + n2 * two["price"]
        diffusion = n1 * one["loading"] * one["price"] + n2 * two["loading"] * two["price"]
        drift = n1 * one["growth"] * one["price"] + n2 * two["growth"] * two["price"]
        holdings.extend(
            (
                abs(_finite(n1) - row["units"][0]) / abs(row["units"][0]),
                abs(_finite(n2) - row["units"][1]) / abs(row["units"][1]),
                abs(diffusion) / abs(value),
                abs(drift / value - one["r"]),
                abs(row["instantaneous_growth"] - one["r"]),
            )
        )
    for row in data["worlds"]:
        same = [w for w in data["worlds"] if w["kind"] == row["kind"]]
        worlds.append(max(abs(w["loading"] - row["loading"]) for w in same))
        worlds.append(
            abs(
                _finite(mpr.required_growth(row["r"], row["world_lambda"], row["loading"]))
                - row["growth"]
            )
        )
    c = data["consumption"]
    consumption_lambda = mpr.market_price_of_risk(
        c["derivative"]["growth"], c["derivative"]["loading"], c["r"]
    )
    errors.append(abs(_finite(consumption_lambda) - c["market_price_of_risk"]))
    naive = _finite(mpr.market_price_of_risk(c["spot_growth"], c["spot_volatility"], c["r"]))
    if (
        abs(naive - c["naive_spot_lambda"]) > TOLERANCE
        or abs(naive - c["market_price_of_risk"]) < 0.1
    ):
        raise ValueError("consumption-asset caveat differs from independent reference")
    z = []
    for row in data["mc"]["worlds"]:
        z.append(abs(row["direct_mean"] - row["analytic_mean"]) / row["direct_se"])
        z.append(abs(row["log_std"] - row["analytic_log_std"]) / row["log_std_se"])
        if row["weight_se"] > 0:
            z.append(abs(row["reweighted_mean"] - row["analytic_mean"]) / row["reweighted_se"])
            z.append(abs(row["weight_mean"] - 1) / row["weight_se"])
        elif abs(row["weight_mean"] - 1) > 1e-12:
            raise ValueError("identity likelihood ratio differs from one")
    call = data["mc"]["risk_neutral_call"]
    z.append(abs(call["reweighted_price"] - call["reference_price"]) / call["standard_error"])
    values = errors + ito + holdings + worlds + z
    if not all(math.isfinite(v) for v in values):
        raise ValueError("market price of risk diagnostics contain a nonfinite value")
    if max(errors + ito + holdings + worlds) > TOLERANCE:
        raise ValueError("market price of risk API differs from independent reference")
    if max(z) > 6:
        raise ValueError("market price of risk MC differs by over six standard errors")
    ratios = [r["residual_std_ratio"] for r in data["riskless"]]
    if any(a <= b for ratio in ratios for a, b in pairwise(ratio)):
        raise ValueError("riskless portfolio residual does not shrink with the step")
    return dict(
        claim_count=len(data["contracts"]) + len(data["negative_contracts"]),
        max_lambda_error=max(errors),
        max_ito_error=max(ito),
        max_riskless_error=max(holdings),
        max_world_error=max(worlds),
        max_mc_standard_errors=max(z),
        mc_paths=reference.MC_PATHS,
        example_28_1=printed[0][0],
        example_28_2_lambda=printed[1][0],
        example_28_2_growth=printed[2][0],
    )


def negative_controls(data):
    rows = []
    for mutation in ("example", "loading_sign", "world_loading", "mc_error", "consumption"):
        changed = copy.deepcopy(data)
        if mutation == "example":
            changed["examples"]["example_28_2"]["m2"] = 0.105
        elif mutation == "loading_sign":
            row = next(r for r in changed["contracts"] if r["kind"] == "put")
            row["loading"] = abs(row["loading"])
        elif mutation == "world_loading":
            changed["worlds"][4]["loading"] *= 1.01
        elif mutation == "mc_error":
            changed["mc"]["worlds"][0]["direct_se"] /= 50
        else:
            changed["consumption"]["naive_spot_lambda"] = 0.2
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
    data = json.loads((PROJECT / BASE / "reference.json").read_text(encoding="utf-8"))
    result = dict(
        section="28.1",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            n: digest(n)
            for n in (
                "scripts/build_market_price_of_risk_reference.py",
                "scripts/verify_market_price_of_risk_numerics.py",
                "hullkit/src/hullkit/market_price_of_risk.py",
                "hullkit/src/hullkit/bsm.py",
            )
        },
        artifact_sha256=digest(BASE + "reference.json"),
    )
    if any(not r["rejected"] for r in result["negative_controls"]):
        raise ValueError("market price of risk negative control accepted")
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("market price of risk numerical record missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §28.1 examples, common lambda, riskless portfolio, worlds and Monte Carlo")


if __name__ == "__main__":
    main()
