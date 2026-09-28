"""Independent §26.1 reference: packages, zero-cost range forwards and deferred payment.

No hullkit imports. Option values use the Black–Scholes–Merton formulas written
with ``math.erfc`` and are re-derived by integrating the payoff against the
risk-neutral lognormal density with ``scipy.integrate.quad``. The call strike
of a zero-cost range forward is found by bisection on ``c(K2) - p(K1)``. Each
package is built leg by leg (call, put, forward, cash) so payoff and present
value are sums of the legs. A seeded antithetic simulation checks the present
value of every product and the loss probabilities.
"""

import argparse
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy import integrate

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-1/reference.json"
ANCHOR = {"spot": 1.32, "rate": 0.02, "yield": 0.02, "sigma": 0.14, "maturity": 0.25}
CASES = (
    ("hull_17_2", ANCHOR),
    ("equity_1y", {"spot": 100.0, "rate": 0.05, "yield": 0.02, "sigma": 0.20, "maturity": 1.0}),
    ("high_yield_2y", {"spot": 100.0, "rate": 0.01, "yield": 0.06, "sigma": 0.35, "maturity": 2.0}),
    ("zero_rate_6m", {"spot": 50.0, "rate": 0.0, "yield": 0.0, "sigma": 0.10, "maturity": 0.5}),
)
PUT_FRACTIONS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.999)
CURVE_FRACTIONS = tuple(round(0.30 + 0.01 * i, 2) for i in range(70))
SLOPE_GAPS = (1e-2, 1e-3, 1e-4, 1e-5, 1e-6)
DEFERRED_FRACTIONS = (0.9, 1.0, 1.1)
PAYOFF_GRID_POINTS = 41
FIGURE_RANGE = (1.12, 1.52)
FIGURE_POINTS = 141
ANCHOR_PUT_STRIKE = 1.30
PRINTED = {"call_strike": 1.3414, "premium": 0.0273}
MC_SEED = 20260926
MC_PAIRS = 1 << 19
Z_LIMIT = 16.0


def _ncdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d1_d2(p, strike):
    vol = p["sigma"] * math.sqrt(p["maturity"])
    d1 = (
        math.log(p["spot"] / strike)
        + (p["rate"] - p["yield"] + 0.5 * p["sigma"] ** 2) * p["maturity"]
    ) / vol
    return d1, d1 - vol


def call(p, strike):
    d1, d2 = _d1_d2(p, strike)
    return p["spot"] * math.exp(-p["yield"] * p["maturity"]) * _ncdf(d1) - strike * math.exp(
        -p["rate"] * p["maturity"]
    ) * _ncdf(d2)


def put(p, strike):
    d1, d2 = _d1_d2(p, strike)
    return strike * math.exp(-p["rate"] * p["maturity"]) * _ncdf(-d2) - p["spot"] * math.exp(
        -p["yield"] * p["maturity"]
    ) * _ncdf(-d1)


def forward_price(p):
    return p["spot"] * math.exp((p["rate"] - p["yield"]) * p["maturity"])


def prob_above(p, level):
    """Risk-neutral P(S_T > level)."""
    return _ncdf(_d1_d2(p, level)[1])


def expectation(p, payoff, kinks=()):
    """Risk-neutral E[payoff(S_T)] by quadrature over the standard normal, split at the kinks."""
    forward = forward_price(p)
    vol = p["sigma"] * math.sqrt(p["maturity"])

    def price(z):
        return forward * math.exp(-0.5 * vol * vol + vol * z)

    edges = sorted((math.log(k / forward) + 0.5 * vol * vol) / vol for k in kinks)
    if any(abs(e) >= Z_LIMIT for e in edges):
        raise ValueError("kink lies beyond the quadrature range")
    bounds = [-Z_LIMIT, *edges, Z_LIMIT]
    total = 0.0
    error = 0.0
    for lo, hi in pairwise(bounds):
        value, err = integrate.quad(
            lambda z: payoff(price(z)) * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi),
            lo,
            hi,
            epsabs=1e-15,
            epsrel=1e-13,
            limit=400,
        )
        total += value
        error += err
    return total, error


def present_value(p, payoff, kinks=()):
    value, error = expectation(p, payoff, kinks)
    discount = math.exp(-p["rate"] * p["maturity"])
    return value * discount, error * discount


def solve_call_strike(p, put_strike):
    """Bisection for K2 with c(K2) = p(K1), K2 > F."""
    forward = forward_price(p)
    target = put(p, put_strike)
    lo, hi = forward, forward * 1.5
    while call(p, hi) > target:
        lo, hi = hi, hi * 2.0
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if call(p, mid) > target:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-15 * forward:
            break
    return 0.5 * (lo + hi)


def leg_payoff(leg, s):
    kind, position = leg["type"], leg["position"]
    if kind == "call":
        return position * max(s - leg["strike"], 0.0)
    if kind == "put":
        return position * max(leg["strike"] - s, 0.0)
    if kind == "forward":
        return position * (s - leg["strike"])
    return position * leg["amount"]


def leg_value(p, leg):
    kind, position = leg["type"], leg["position"]
    discount = math.exp(-p["rate"] * p["maturity"])
    if kind == "call":
        return position * call(p, leg["strike"])
    if kind == "put":
        return position * put(p, leg["strike"])
    if kind == "forward":
        return position * (
            p["spot"] * math.exp(-p["yield"] * p["maturity"]) - leg["strike"] * discount
        )
    return position * leg["amount"] * discount


def package(p, legs, grid):
    return {
        "legs": legs,
        "leg_values": [leg_value(p, leg) for leg in legs],
        "value": sum(leg_value(p, leg) for leg in legs),
        "grid": grid,
        "payoff": [sum(leg_payoff(leg, s) for leg in legs) for s in grid],
    }


def payoff_grid(p, low=0.6, high=1.5):
    forward = forward_price(p)
    return [
        forward * (low + (high - low) * i / (PAYOFF_GRID_POINTS - 1))
        for i in range(PAYOFF_GRID_POINTS)
    ]


def bsm_by_quadrature(p):
    forward = forward_price(p)
    rows = []
    for fraction in (0.8, 0.9, 1.0, 1.1, 1.25):
        strike = fraction * forward
        c, c_err = present_value(p, lambda s, k=strike: max(s - k, 0.0), (strike,))
        v, v_err = present_value(p, lambda s, k=strike: max(k - s, 0.0), (strike,))
        rows.append(
            {
                "strike": strike,
                "call": call(p, strike),
                "call_quadrature": c,
                "put": put(p, strike),
                "put_quadrature": v,
                "quadrature_error": max(c_err, v_err),
            }
        )
    return rows


def range_rows(p):
    forward = forward_price(p)
    rows = []
    for fraction in PUT_FRACTIONS:
        k1 = fraction * forward
        k2 = solve_call_strike(p, k1)
        premium = put(p, k1)

        def net(s, k1=k1, k2=k2):
            return max(s - k2, 0.0) - max(k1 - s, 0.0)

        pv, pv_err = present_value(p, net, (k1, k2))
        rows.append(
            {
                "put_fraction": fraction,
                "put_strike": k1,
                "call_strike": k2,
                "premium": premium,
                "call_value": call(p, k2),
                "put_value": premium,
                "net_pv_quadrature": pv,
                "quadrature_error": pv_err,
            }
        )
    return rows


def curve(p):
    forward = forward_price(p)
    points = []
    for fraction in CURVE_FRACTIONS:
        k1 = fraction * forward
        points.append({"put_strike": k1, "call_strike": solve_call_strike(p, k1)})
    return {"forward": forward, "points": points}


def local_slope(p):
    forward = forward_price(p)
    vol = p["sigma"] * math.sqrt(p["maturity"])
    limit = _ncdf(vol / 2.0) / _ncdf(-vol / 2.0)
    rows = []
    for gap in SLOPE_GAPS:
        k1 = forward * (1.0 - gap)
        k2 = solve_call_strike(p, k1)
        rows.append({"relative_gap": gap, "ratio": (k2 - forward) / (forward - k1)})
    return {"limit": limit, "rows": rows}


def deferred_rows(p):
    forward = forward_price(p)
    grid = payoff_grid(p)
    rows = []
    for kind in ("call", "put"):
        for fraction in DEFERRED_FRACTIONS:
            strike = fraction * forward
            premium = call(p, strike) if kind == "call" else put(p, strike)
            amount = premium * math.exp(p["rate"] * p["maturity"])

            def leg(s, strike=strike, kind=kind):
                return max(s - strike, 0.0) if kind == "call" else max(strike - s, 0.0)

            def net(s, leg=leg, amount=amount):
                return leg(s) - amount

            pv, pv_err = present_value(p, net, (strike,))
            premium_quad, _ = present_value(p, leg, (strike,))
            breakeven = strike + amount if kind == "call" else strike - amount
            profit = prob_above(p, breakeven) if kind == "call" else 1.0 - prob_above(p, breakeven)
            rows.append(
                {
                    "kind": kind,
                    "strike_fraction": fraction,
                    "strike": strike,
                    "premium": premium,
                    "premium_quadrature": premium_quad,
                    "amount": amount,
                    "net_pv_quadrature": pv,
                    "quadrature_error": pv_err,
                    "breakeven": breakeven,
                    "max_loss": amount,
                    "probability_of_profit": profit,
                    "grid": grid,
                    "payoff": [leg(s) - amount for s in grid],
                }
            )
    return rows


def package_rows(p):
    """Leg-by-leg packages: range forward, break forward and a deferred call."""
    forward = forward_price(p)
    grid = payoff_grid(p)
    k1 = 0.95 * forward
    k2 = solve_call_strike(p, k1)
    amount_bf = put(p, forward) * math.exp(p["rate"] * p["maturity"])
    amount_dc = call(p, forward * 1.05) * math.exp(p["rate"] * p["maturity"])
    definitions = {
        "range_forward": [
            {"type": "call", "position": 1, "strike": k2},
            {"type": "put", "position": -1, "strike": k1},
        ],
        "break_forward": [
            {"type": "forward", "position": 1, "strike": forward},
            {"type": "put", "position": 1, "strike": forward},
            {"type": "cash", "position": -1, "amount": amount_bf},
        ],
        "deferred_call": [
            {"type": "call", "position": 1, "strike": 1.05 * forward},
            {"type": "cash", "position": -1, "amount": amount_dc},
        ],
    }
    closed = {
        "range_forward": lambda s: max(s - k2, 0.0) - max(k1 - s, 0.0),
        "break_forward": lambda s: max(s - forward, 0.0) - amount_bf,
        "deferred_call": lambda s: max(s - 1.05 * forward, 0.0) - amount_dc,
    }
    rows = {}
    for name, legs in definitions.items():
        built = package(p, legs, grid)
        built["closed_form_payoff"] = [closed[name](s) for s in grid]
        rows[name] = built
    return rows


def risk_comparison(p):
    """Forward, range forward and break forward: zero present value, different risk."""
    forward = forward_price(p)
    k1 = 0.95 * forward
    k2 = solve_call_strike(p, k1)
    amount = put(p, forward) * math.exp(p["rate"] * p["maturity"])
    products = {
        "forward": {
            "net": lambda s: s - forward,
            "kinks": (forward,),
            "gain_pv_formula": call(p, forward),
            "probability_of_loss": 1.0 - prob_above(p, forward),
            "max_loss": forward,
        },
        "range_forward": {
            "net": lambda s: max(s - k2, 0.0) - max(k1 - s, 0.0),
            "kinks": (k1, k2),
            "gain_pv_formula": call(p, k2),
            "probability_of_loss": 1.0 - prob_above(p, k1),
            "max_loss": k1,
        },
        "break_forward": {
            "net": lambda s: max(s - forward, 0.0) - amount,
            "kinks": (forward, forward + amount),
            "gain_pv_formula": call(p, forward + amount),
            "probability_of_loss": 1.0 - prob_above(p, forward + amount),
            "max_loss": amount,
        },
    }
    rows = {}
    for name, product in products.items():
        net = product["net"]
        gain, gain_err = present_value(p, lambda s, f=net: max(f(s), 0.0), product["kinks"])
        loss, loss_err = present_value(p, lambda s, f=net: max(-f(s), 0.0), product["kinks"])
        rows[name] = {
            "gain_pv_quadrature": gain,
            "loss_pv_quadrature": loss,
            "gain_pv_formula": product["gain_pv_formula"],
            "net_pv": gain - loss,
            "probability_of_loss": product["probability_of_loss"],
            "max_loss": product["max_loss"],
            "quadrature_error": max(gain_err, loss_err),
        }
    rows["range_forward"]["strikes"] = {"put": k1, "call": k2}
    rows["break_forward"]["amount"] = amount
    return rows


def monte_carlo(p):
    forward = forward_price(p)
    vol = p["sigma"] * math.sqrt(p["maturity"])
    discount = math.exp(-p["rate"] * p["maturity"])
    rng = np.random.default_rng(MC_SEED)
    z = rng.standard_normal(MC_PAIRS)
    k1 = 0.95 * forward
    k2 = solve_call_strike(p, k1)
    amount = put(p, forward) * math.exp(p["rate"] * p["maturity"])

    def stats(net):
        up = net(forward * np.exp(-0.5 * vol * vol + vol * z))
        down = net(forward * np.exp(-0.5 * vol * vol - vol * z))
        pair = 0.5 * (up + down)
        loss = 0.5 * ((up < 0.0).astype(float) + (down < 0.0).astype(float))
        n = len(z)
        return {
            "pv": float(discount * pair.mean()),
            "pv_se": float(discount * pair.std(ddof=1) / math.sqrt(n)),
            "loss_probability": float(loss.mean()),
            "loss_probability_se": float(loss.std(ddof=1) / math.sqrt(n)),
        }

    return {
        "seed": MC_SEED,
        "antithetic_pairs": MC_PAIRS,
        "forward": stats(lambda s: s - forward),
        "range_forward": stats(lambda s: np.maximum(s - k2, 0.0) - np.maximum(k1 - s, 0.0)),
        "break_forward": stats(lambda s: np.maximum(s - forward, 0.0) - amount),
    }


def anchor():
    p = ANCHOR
    k2 = solve_call_strike(p, ANCHOR_PUT_STRIKE)
    return {
        "put_strike": ANCHOR_PUT_STRIKE,
        "call_strike": k2,
        "premium": put(p, ANCHOR_PUT_STRIKE),
        "put_at_printed_strikes": put(p, ANCHOR_PUT_STRIKE),
        "call_at_printed_strikes": call(p, PRINTED["call_strike"]),
        "printed": PRINTED,
        "forward": forward_price(p),
    }


def figure_payoffs(p):
    """Maturity payoffs at the §17.2 strikes for the payoff diagrams, summed from legs."""
    forward = forward_price(p)
    k2 = solve_call_strike(p, ANCHOR_PUT_STRIKE)
    amount = put(p, forward) * math.exp(p["rate"] * p["maturity"])
    grid = [
        FIGURE_RANGE[0] + (FIGURE_RANGE[1] - FIGURE_RANGE[0]) * i / (FIGURE_POINTS - 1)
        for i in range(FIGURE_POINTS)
    ]
    legs = {
        "forward": [{"type": "forward", "position": 1, "strike": forward}],
        "range_forward": [
            {"type": "call", "position": 1, "strike": k2},
            {"type": "put", "position": -1, "strike": ANCHOR_PUT_STRIKE},
        ],
        "call": [{"type": "call", "position": 1, "strike": forward}],
        "break_forward": [
            {"type": "call", "position": 1, "strike": forward},
            {"type": "cash", "position": -1, "amount": amount},
        ],
    }
    return {
        "grid": grid,
        "forward_price": forward,
        "put_strike": ANCHOR_PUT_STRIKE,
        "call_strike": k2,
        "premium": call(p, forward),
        "amount": amount,
        "breakeven": forward + amount,
        "payoffs": {name: package(p, spec, grid)["payoff"] for name, spec in legs.items()},
    }


def build():
    cases = []
    for label, p in CASES:
        cases.append(
            {
                "label": label,
                "parameters": p,
                "forward": forward_price(p),
                "bsm_quadrature": bsm_by_quadrature(p),
                "range_forwards": range_rows(p),
                "local_slope": local_slope(p),
                "deferred": deferred_rows(p),
                "packages": package_rows(p),
            }
        )
    return {
        "section": "26.1",
        "source": "Hull 11e Global Edition pp.614–615; range forward of §17.2 p.388",
        "units": "prices and strikes in the underlying's currency; maturity in years; annual continuous rates, yields and volatilities",
        "parameters": ANCHOR,
        "anchor_17_2": anchor(),
        "strike_curve": curve(ANCHOR),
        "risk_comparison": risk_comparison(ANCHOR),
        "figure_payoffs": figure_payoffs(ANCHOR),
        "monte_carlo": monte_carlo(ANCHOR),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §26.1 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print(
        "PASS: §26.1 range forward root, leg-by-leg packages, deferred payment, quadrature and simulation"
    )


if __name__ == "__main__":
    main()
