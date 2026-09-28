"""Cross-check Hull §26.1 packages with the independent §26.1 reference."""

import argparse
import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from build_packages_reference import (
    PRINTED,
    build,
    expectation,
    prob_above,
)
from hullkit import bsm, packages

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-26-1/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_packages_reference.py",
    "scripts/verify_packages_numerics.py",
    "hullkit/src/hullkit/packages.py",
)
STRIKE_RTOL = 1e-10
PREMIUM_RTOL = 1e-11
VALUE_ATOL = 1e-11
MC_SIGMAS = 4.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _market(p):
    return {
        "spot": p["spot"],
        "r": p["rate"],
        "sigma": p["sigma"],
        "T": p["maturity"],
        "q": p["yield"],
    }


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _check_anchor(reference):
    anchor = reference["anchor_17_2"]
    market = _market(reference["parameters"])
    result = packages.range_forward(anchor["put_strike"], **market)
    strike_error = abs(result.call_strike - anchor["call_strike"])
    _require(
        strike_error <= STRIKE_RTOL * anchor["forward"], "range forward root differs from bisection"
    )
    _require(
        round(anchor["call_strike"], 4) == PRINTED["call_strike"],
        "root does not reproduce Hull's 1.3414",
    )
    for name in ("put_at_printed_strikes", "call_at_printed_strikes"):
        _require(
            round(anchor[name], 4) == PRINTED["premium"], f"{name} does not round to Hull's 0.0273"
        )
    _require(abs(result.premium - anchor["premium"]) <= 1e-14, "anchor premium differs")
    return {
        "call_strike": anchor["call_strike"],
        "strike_error": strike_error,
        "printed_call_strike": PRINTED["call_strike"],
        "premium": anchor["premium"],
        "printed_premium": PRINTED["premium"],
    }


def _check_formulas(reference):
    formula_gap = 0.0
    quadrature_gap = 0.0
    for case in reference["cases"]:
        p, market = case["parameters"], _market(case["parameters"])
        for row in case["bsm_quadrature"]:
            quadrature_gap = max(
                quadrature_gap,
                abs(row["call"] - row["call_quadrature"]),
                abs(row["put"] - row["put_quadrature"]),
            )
            formula_gap = max(
                formula_gap,
                abs(
                    bsm.call_price(
                        p["spot"], row["strike"], p["rate"], p["sigma"], p["maturity"], p["yield"]
                    )
                    - row["call"]
                ),
                abs(
                    bsm.put_price(
                        p["spot"], row["strike"], p["rate"], p["sigma"], p["maturity"], p["yield"]
                    )
                    - row["put"]
                ),
            )
        _require(abs(market["spot"] - p["spot"]) == 0.0, "market mapping changed")
    _require(quadrature_gap <= VALUE_ATOL, "BSM prices disagree with the lognormal integral")
    _require(formula_gap <= 1e-12, "hullkit BSM differs from the reference formulas")
    return {"bsm_vs_quadrature": quadrature_gap, "hullkit_bsm_vs_reference": formula_gap}


def _check_range_forwards(reference):
    strike_gap = premium_gap = cost_gap = pv_gap = 0.0
    rows = 0
    for case in reference["cases"]:
        market = _market(case["parameters"])
        forward = case["forward"]
        previous = None
        for row in case["range_forwards"]:
            result = packages.range_forward(row["put_strike"], **market)
            strike_gap = max(
                strike_gap, abs(result.call_strike - row["call_strike"]) / row["call_strike"]
            )
            premium_gap = max(premium_gap, abs(result.premium - row["premium"]) / row["premium"])
            cost_gap = max(cost_gap, abs(result.cost) / row["premium"])
            pv_gap = max(pv_gap, abs(row["net_pv_quadrature"]))
            _require(
                row["put_strike"] < forward < row["call_strike"],
                "strikes do not bracket the forward",
            )
            _require(
                abs(row["call_value"] - row["put_value"]) <= 1e-10 * row["put_value"],
                "reference call and put differ",
            )
            if previous is not None:
                _require(row["call_strike"] < previous, "K2 must fall as K1 rises")
            previous = row["call_strike"]
            rows += 1
    _require(strike_gap <= STRIKE_RTOL, "range forward strikes differ from bisection")
    _require(premium_gap <= PREMIUM_RTOL, "range forward premiums differ")
    _require(cost_gap <= 1e-10, "range forward is not zero cost")
    _require(pv_gap <= VALUE_ATOL, "quadrature present value of a range forward is not zero")
    return {
        "rows": rows,
        "strike_relative_gap": strike_gap,
        "premium_relative_gap": premium_gap,
        "cost_relative_to_premium": cost_gap,
        "quadrature_net_pv": pv_gap,
    }


def _check_curve_and_slope(reference):
    market = _market(reference["parameters"])
    curve = reference["strike_curve"]
    gap = 0.0
    previous = math.inf
    for point in curve["points"]:
        result = packages.range_forward(point["put_strike"], **market)
        gap = max(gap, abs(result.call_strike - point["call_strike"]) / point["call_strike"])
        _require(point["call_strike"] < previous, "strike curve is not decreasing in K1")
        previous = point["call_strike"]
    _require(gap <= STRIKE_RTOL, "strike curve differs from bisection")
    first, last = curve["points"][0], curve["points"][-1]
    _require(first["call_strike"] > 1.5 * curve["forward"], "K2 does not run away as K1 falls")
    _require(
        last["call_strike"] < 1.02 * curve["forward"], "K2 does not approach F as K1 approaches F"
    )
    slopes = []
    for case in reference["cases"]:
        local = case["local_slope"]
        errors = [abs(row["ratio"] - local["limit"]) / local["limit"] for row in local["rows"]]
        _require(errors[-1] <= 1e-5, "local slope does not reach N(vol/2)/N(-vol/2)")
        _require(
            all(b < a for a, b in pairwise(errors)), "local slope error does not fall with the gap"
        )
        _require(local["limit"] > 1.0, "K2 - F must exceed F - K1 near the forward")
        slopes.append({"label": case["label"], "limit": local["limit"], "final_error": errors[-1]})
    return {"curve_relative_gap": gap, "curve_points": len(curve["points"]), "local_slopes": slopes}


def _check_deferred_and_packages(reference):
    payoff_gap = amount_gap = pv_gap = premium_gap = 0.0
    packaged_gap = 0.0
    leg_value_gap = 0.0
    breakeven_gap = 0.0
    profit_gap = 0.0
    rows = 0
    for case in reference["cases"]:
        p, market = case["parameters"], _market(case["parameters"])
        for row in case["deferred"]:
            option = packages.deferred_option(row["kind"], row["strike"], **market)
            premium_gap = max(
                premium_gap,
                abs(option.premium - row["premium"]),
                abs(row["premium"] - row["premium_quadrature"]),
            )
            amount_gap = max(amount_gap, abs(option.amount - row["amount"]))
            grid = np.asarray(row["grid"])
            payoff_gap = max(
                payoff_gap, float(np.max(np.abs(option.payoff(grid) - np.asarray(row["payoff"]))))
            )
            pv_gap = max(pv_gap, abs(row["net_pv_quadrature"]))
            breakeven_gap = max(breakeven_gap, abs(option.breakeven - row["breakeven"]))
            _require(
                abs(option.max_loss - row["max_loss"]) <= 1e-12, "deferred maximum loss differs"
            )
            if row["kind"] == "call":
                indicator, _ = expectation(
                    p, lambda s, b=row["breakeven"]: float(s > b), (row["breakeven"],)
                )
            else:
                indicator, _ = expectation(
                    p, lambda s, b=row["breakeven"]: float(s < b), (row["breakeven"],)
                )
            profit_gap = max(profit_gap, abs(indicator - row["probability_of_profit"]))
            rows += 1
        forward = case["forward"]
        market_kwargs = market
        for name, built in case["packages"].items():
            grid = np.asarray(built["grid"])
            packaged_gap = max(
                packaged_gap,
                float(
                    np.max(
                        np.abs(
                            np.asarray(built["payoff"]) - np.asarray(built["closed_form_payoff"])
                        )
                    )
                ),
            )
            leg_value_gap = max(leg_value_gap, abs(built["value"]))
            if name == "break_forward":
                option = packages.break_forward(**market_kwargs)
                packaged_gap = max(
                    packaged_gap,
                    float(np.max(np.abs(option.payoff(grid) - np.asarray(built["payoff"])))),
                )
                _require(
                    abs(option.strike - forward) <= 1e-14 * forward,
                    "break forward is not struck at the forward",
                )
            if name == "range_forward":
                legs = built["legs"]
                k2, k1 = legs[0]["strike"], legs[1]["strike"]
                result = packages.range_forward(k1, **market_kwargs)
                packaged_gap = max(
                    packaged_gap,
                    float(np.max(np.abs(result.payoff(grid) - np.asarray(built["payoff"])))),
                )
                _require(
                    abs(result.call_strike - k2) <= STRIKE_RTOL * k2,
                    "packaged range forward strike differs",
                )
    scale = max(case["parameters"]["spot"] for case in reference["cases"])
    _require(premium_gap <= VALUE_ATOL, "deferred premiums differ")
    _require(amount_gap <= 1e-12, "deferred amounts differ")
    _require(payoff_gap <= 1e-12 * scale, "deferred payoffs differ")
    _require(pv_gap <= VALUE_ATOL, "a deferred option has non-zero present value")
    _require(breakeven_gap <= 1e-12, "deferred breakevens differ")
    _require(profit_gap <= 1e-9, "probability of profit differs from the integral")
    _require(
        packaged_gap <= 1e-12 * scale, "leg-by-leg package payoffs differ from the closed forms"
    )
    _require(leg_value_gap <= VALUE_ATOL, "a package has non-zero value")
    return {
        "deferred_rows": rows,
        "premium_gap": premium_gap,
        "amount_gap": amount_gap,
        "payoff_gap": payoff_gap,
        "quadrature_net_pv": pv_gap,
        "breakeven_gap": breakeven_gap,
        "probability_of_profit_gap": profit_gap,
        "package_payoff_gap": packaged_gap,
        "package_leg_value_sum": leg_value_gap,
    }


def _check_risk(reference):
    p = reference["parameters"]
    market = _market(p)
    risk = reference["risk_comparison"]
    mc = reference["monte_carlo"]
    result = packages.range_forward(risk["range_forward"]["strikes"]["put"], **market)
    _require(
        abs(result.call_strike - risk["range_forward"]["strikes"]["call"])
        <= STRIKE_RTOL * result.call_strike,
        "range forward strikes differ",
    )
    option = packages.break_forward(**market)
    _require(
        abs(option.amount - risk["break_forward"]["amount"]) <= 1e-12,
        "break forward amount differs",
    )
    balance = 0.0
    for name, row in risk.items():
        balance = max(
            balance, abs(row["net_pv"]), abs(row["gain_pv_quadrature"] - row["gain_pv_formula"])
        )
        _require(
            abs(row["gain_pv_quadrature"] - row["loss_pv_quadrature"]) <= VALUE_ATOL,
            f"{name}: gain and loss present values differ",
        )
        stats = mc[name]
        _require(
            abs(stats["pv"]) <= MC_SIGMAS * stats["pv_se"],
            f"{name}: simulated present value is not zero",
        )
        _require(
            abs(stats["loss_probability"] - row["probability_of_loss"])
            <= MC_SIGMAS * stats["loss_probability_se"],
            f"{name}: simulated loss probability differs",
        )
    _require(balance <= VALUE_ATOL, "expected gain and loss do not balance")
    gains = [risk[k]["gain_pv_quadrature"] for k in ("forward", "break_forward", "range_forward")]
    _require(
        gains[0] > gains[1] > gains[2] > 0.0,
        "expected loss should fall from forward to break forward to range forward",
    )
    losses = [risk[k]["probability_of_loss"] for k in ("range_forward", "forward", "break_forward")]
    _require(
        losses[0] < losses[1] < losses[2],
        "loss probability should rise from range forward to forward to break forward",
    )
    caps = {k: risk[k]["max_loss"] for k in risk}
    _require(
        caps["break_forward"] < caps["range_forward"] < caps["forward"],
        "maximum losses are not ordered as claimed",
    )
    _require(prob_above(p, p["spot"]) > 0.0, "reference probability helper failed")
    return {
        "balance": balance,
        "expected_gain_pv": {k: risk[k]["gain_pv_quadrature"] for k in risk},
        "probability_of_loss": {k: risk[k]["probability_of_loss"] for k in risk},
        "max_loss": caps,
        "monte_carlo": {
            k: {
                "pv_z": mc[k]["pv"] / mc[k]["pv_se"],
                "loss_probability_z": (mc[k]["loss_probability"] - risk[k]["probability_of_loss"])
                / mc[k]["loss_probability_se"],
            }
            for k in risk
        },
    }


def _check_figure_payoffs(reference):
    p = reference["parameters"]
    market = _market(p)
    data = reference["figure_payoffs"]
    grid = np.asarray(data["grid"])
    forward = data["forward_price"]
    result = packages.range_forward(data["put_strike"], **market)
    option = packages.break_forward(**market)
    payoffs = {name: np.asarray(values) for name, values in data["payoffs"].items()}
    gaps = {
        "forward": float(np.max(np.abs(grid - forward - payoffs["forward"]))),
        "range_forward": float(np.max(np.abs(result.payoff(grid) - payoffs["range_forward"]))),
        "call": float(np.max(np.abs(np.maximum(grid - forward, 0.0) - payoffs["call"]))),
        "break_forward": float(np.max(np.abs(option.payoff(grid) - payoffs["break_forward"]))),
    }
    _require(max(gaps.values()) <= 1e-13, "payoff diagram data differ from the public API")
    _require(
        abs(result.call_strike - data["call_strike"]) <= STRIKE_RTOL * forward,
        "diagram call strike differs",
    )
    _require(abs(option.amount - data["amount"]) <= 1e-12, "diagram deferred amount differs")
    _require(abs(option.breakeven - data["breakeven"]) <= 1e-12, "diagram breakeven differs")
    _require(
        abs(payoffs["break_forward"].min() + data["amount"]) <= 1e-13
        and abs(payoffs["range_forward"][0] - (-(data["put_strike"] - grid[0]))) <= 1e-13,
        "diagram floors differ from the maximum loss and the put leg",
    )
    return {"payoff_gaps": gaps, "grid_points": len(grid)}


def _check_rejections():
    market = {"spot": 1.32, "r": 0.02, "sigma": 0.14, "T": 0.25, "q": 0.02}
    rejected = 0
    for call in (
        lambda: packages.range_forward(1.33, **market),
        lambda: packages.range_forward(0.0, **market),
        lambda: packages.range_forward(1.30, **{**market, "sigma": 0.0}),
        lambda: packages.deferred_option("straddle", 1.32, **market),
        lambda: packages.deferred_option("call", -1.0, **market),
    ):
        try:
            call()
        except ValueError:
            rejected += 1
    _require(rejected == 5, "invalid inputs are not rejected")
    return {"rejected_inputs": rejected}


def evaluate():
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent computation")
    measured = {
        "anchor_17_2": _check_anchor(reference),
        "formulas": _check_formulas(reference),
        "range_forwards": _check_range_forwards(reference),
        "curve_and_slope": _check_curve_and_slope(reference),
        "deferred_and_packages": _check_deferred_and_packages(reference),
        "risk": _check_risk(reference),
        "figure_payoffs": _check_figure_payoffs(reference),
        "rejections": _check_rejections(),
    }
    return {
        "section": "26.1",
        "status": "PASS",
        "method": (
            "range forward call strike by bisection on c(K2) - p(K1), leg-by-leg package payoffs and values, "
            "lognormal quadrature of every present value, N(vol/2)/N(-vol/2) limit of (K2 - F)/(F - K1), "
            "seeded antithetic simulation of present values and loss probabilities"
        ),
        "tolerances": {
            "strike_relative": STRIKE_RTOL,
            "premium_relative": PREMIUM_RTOL,
            "quadrature_currency": VALUE_ATOL,
            "hullkit_bsm_currency": 1e-12,
            "deferred_amount_currency": 1e-12,
            "probability_of_profit": 1e-9,
            "local_slope_relative_at_1e-6": 1e-5,
            "monte_carlo_sigmas": MC_SIGMAS,
        },
        "measured": measured,
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
            raise SystemExit("FAIL: §26.1 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.1 range forwards, deferred payment, break forwards and package risk")


if __name__ == "__main__":
    main()
