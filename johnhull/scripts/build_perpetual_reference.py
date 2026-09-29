"""Independent §26.2 reference for perpetual American calls and puts.

The characteristic roots and optimal first-passage exercise levels follow Hull
11e pp.615–616. A finite-maturity American CRR lattice, rolled back directly
from terminal payoffs without importing hullkit, independently checks prices
as maturity grows. All rates, yields and volatilities are annual continuous.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-2/reference.json"
CASES = (
    ("symmetric", {"spot": 100.0, "strike": 100.0, "rate": 0.04, "yield": 0.04, "sigma": 0.20}),
    (
        "standard_dividend",
        {"spot": 100.0, "strike": 100.0, "rate": 0.05, "yield": 0.03, "sigma": 0.20},
    ),
    (
        "dividend_stock",
        {"spot": 110.0, "strike": 100.0, "rate": 0.05, "yield": 0.03, "sigma": 0.25},
    ),
    (
        "high_yield_call_exercise",
        {"spot": 170.0, "strike": 100.0, "rate": 0.04, "yield": 0.08, "sigma": 0.25},
    ),
    (
        "high_vol_put_exercise",
        {"spot": 40.0, "strike": 100.0, "rate": 0.06, "yield": 0.03, "sigma": 0.35},
    ),
    ("zero_yield", {"spot": 100.0, "strike": 100.0, "rate": 0.05, "yield": 0.0, "sigma": 0.20}),
)
MATURITIES = (20.0, 40.0, 80.0, 160.0)
STEPS_PER_YEAR = 10


def _validate_market(p):
    for key in ("spot", "strike", "rate", "yield", "sigma"):
        value = p[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{key} must be finite")
    if p["spot"] <= 0 or p["strike"] <= 0:
        raise ValueError("spot and strike must be positive")
    if p["rate"] <= 0 or p["yield"] < 0 or p["sigma"] <= 0:
        raise ValueError("supported domain: rate > 0, yield >= 0, sigma > 0")


def _characteristic(exponent, p):
    """Residual of (r-q)a + sigma² a(a-1)/2 = r."""
    return (
        (p["rate"] - p["yield"]) * exponent
        + 0.5 * p["sigma"] ** 2 * exponent * (exponent - 1.0)
        - p["rate"]
    )


def analytic_case(label, parameters):
    """Build Hull's roots, exercise levels, values and boundary identities."""
    p = dict(parameters)
    _validate_market(p)
    spot, strike, rate, dividend, sigma = (
        p["spot"],
        p["strike"],
        p["rate"],
        p["yield"],
        p["sigma"],
    )
    variance = sigma * sigma
    if not math.isfinite(variance) or variance == 0.0:
        raise ValueError("sigma squared must be positive and finite")
    w = rate - dividend - variance / 2.0
    root = math.sqrt(w * w + 2.0 * variance * rate)
    if not math.isfinite(root):
        raise ValueError("characteristic root is outside floating-point range")

    # The direct Hull formulas are (root-w)/variance and (root+w)/variance.
    # Rationalization avoids cancellation; a1-1 uses the q identity to keep
    # the zero-dividend limit explicit and avoid dividing by a rounded zero.
    a2 = 2.0 * rate / (root - w) if w < 0 else (root + w) / variance
    if not math.isfinite(a2) or a2 <= 0.0:
        raise ValueError("put exponent is outside floating-point range")
    if dividend == 0.0:
        a1 = 1.0
        call = {
            "boundary_kind": "infinite",
            "boundary": None,
            "value": spot,
            "boundary_continuation_value": None,
            "boundary_intrinsic": None,
            "matching_residual": None,
            "continuation_delta_at_boundary": None,
            "intrinsic_delta": 1.0,
            "smooth_pasting_residual": None,
        }
    else:
        denominator = root + w + variance
        if not math.isfinite(denominator) or denominator <= 0.0:
            raise ValueError("call exponent is outside floating-point range")
        excess = 2.0 * dividend / denominator
        if not math.isfinite(excess) or excess <= 0.0:
            raise ValueError("yield is too small to resolve a finite call boundary")
        a1 = 1.0 + excess
        h1 = strike * (1.0 + excess) / excess
        if not math.isfinite(h1):
            raise ValueError("call boundary exceeds finite floating-point range")
        payoff = h1 - strike
        at_boundary = payoff * (h1 / h1) ** a1
        delta = a1 * payoff / h1
        call = {
            "boundary_kind": "finite",
            "boundary": h1,
            "value": payoff * (spot / h1) ** a1 if spot < h1 else spot - strike,
            "boundary_continuation_value": at_boundary,
            "boundary_intrinsic": payoff,
            "matching_residual": at_boundary - payoff,
            "continuation_delta_at_boundary": delta,
            "intrinsic_delta": 1.0,
            "smooth_pasting_residual": delta - 1.0,
        }

    h2 = strike * a2 / (a2 + 1.0)
    if not math.isfinite(h2) or h2 <= 0.0:
        raise ValueError("put boundary is outside floating-point range")
    put_payoff = strike - h2
    at_put_boundary = put_payoff * (h2 / h2) ** (-a2)
    put_delta = -a2 * put_payoff / h2
    put = {
        "boundary_kind": "finite",
        "boundary": h2,
        "value": put_payoff * (spot / h2) ** (-a2) if spot > h2 else strike - spot,
        "boundary_continuation_value": at_put_boundary,
        "boundary_intrinsic": put_payoff,
        "matching_residual": at_put_boundary - put_payoff,
        "continuation_delta_at_boundary": put_delta,
        "intrinsic_delta": -1.0,
        "smooth_pasting_residual": put_delta + 1.0,
    }
    return {
        "label": label,
        "parameters": p,
        "w": w,
        "a1": a1,
        "a2": a2,
        "characteristic_residuals": {
            "positive": _characteristic(a1, p),
            "negative": _characteristic(-a2, p),
        },
        "call": call,
        "put": put,
    }


def option_value(kind, spot, case):
    """Exercise immediately outside the continuation region."""
    if not math.isfinite(spot) or spot <= 0:
        raise ValueError("spot must be positive and finite")
    strike = case["parameters"]["strike"]
    if kind == "call":
        h = case["call"]["boundary"]
        if h is None:
            return spot
        return spot - strike if spot >= h else (h - strike) * (spot / h) ** case["a1"]
    if kind == "put":
        h = case["put"]["boundary"]
        return strike - spot if spot <= h else (strike - h) * (spot / h) ** (-case["a2"])
    raise ValueError("kind must be call or put")


def crr_american(parameters, maturity, steps):
    """Independent finite-maturity American prices from direct CRR rollback."""
    p = dict(parameters)
    _validate_market(p)
    if (
        not math.isfinite(maturity)
        or maturity <= 0
        or isinstance(steps, bool)
        or not isinstance(steps, int)
        or steps < 1
    ):
        raise ValueError("maturity must be positive and steps a positive integer")
    dt = maturity / steps
    h = p["sigma"] * math.sqrt(dt)
    if not math.isfinite(h) or h <= 0.0:
        raise ValueError("CRR time step is outside floating-point range")
    try:
        up = math.exp(h)
        growth = math.exp((p["rate"] - p["yield"]) * dt)
    except OverflowError as exc:
        raise ValueError("CRR factors are outside floating-point range") from exc
    down = 1.0 / up
    spread = up - down
    if not math.isfinite(spread) or spread <= 0.0 or not math.isfinite(growth):
        raise ValueError("CRR factors are outside floating-point range")
    probability = (growth - down) / spread
    if not 0.0 < probability < 1.0:
        raise ValueError("CRR time step violates the risk-neutral probability bound")
    discount = math.exp(-p["rate"] * dt)
    indices = np.arange(steps + 1)
    spots = p["spot"] * np.exp((2 * indices - steps) * h)
    calls = np.maximum(spots - p["strike"], 0.0)
    puts = np.maximum(p["strike"] - spots, 0.0)
    for level in range(steps - 1, -1, -1):
        calls = discount * ((1.0 - probability) * calls[:-1] + probability * calls[1:])
        puts = discount * ((1.0 - probability) * puts[:-1] + probability * puts[1:])
        indices = np.arange(level + 1)
        spots = p["spot"] * np.exp((2 * indices - level) * h)
        calls = np.maximum(calls, spots - p["strike"])
        puts = np.maximum(puts, p["strike"] - spots)
    return {"call": float(calls[0]), "put": float(puts[0])}


def lattice_rows(case):
    p = case["parameters"]
    rows = []
    for maturity in MATURITIES:
        steps = int(maturity * STEPS_PER_YEAR)
        finite = crr_american(p, maturity, steps)
        rows.append(
            {
                "maturity": maturity,
                "steps": steps,
                "call": finite["call"],
                "put": finite["put"],
                "call_gap": case["call"]["value"] - finite["call"],
                "put_gap": case["put"]["value"] - finite["put"],
            }
        )
    return {"rows": rows}


def figure(case):
    spots = [float(i) for i in range(10, 331, 2)]
    strike = case["parameters"]["strike"]
    return {
        "label": case["label"],
        "spot_grid": spots,
        "call": [option_value("call", s, case) for s in spots],
        "put": [option_value("put", s, case) for s in spots],
        "call_intrinsic": [max(s - strike, 0.0) for s in spots],
        "put_intrinsic": [max(strike - s, 0.0) for s in spots],
        "call_boundary": case["call"]["boundary"],
        "put_boundary": case["put"]["boundary"],
    }


def build():
    cases = []
    for label, parameters in CASES:
        case = analytic_case(label, parameters)
        case["lattice"] = lattice_rows(case)
        cases.append(case)
    return {
        "section": "26.2",
        "source": "Hull 11e Global Edition pp.615–616",
        "units": "spot, strike, boundaries and values in currency units; maturity in years; annual continuously compounded rates, yields and volatilities",
        "domain": {
            "spot": "positive finite",
            "strike": "positive finite",
            "rate": "positive finite",
            "yield": "nonnegative finite",
            "sigma": "positive finite",
            "lattice": "CRR probability must lie strictly between zero and one",
        },
        "independent_method": "finite-maturity American CRR rollback from terminal intrinsic payoffs, with both call and put exercise at every node; maturity is increased at fixed 10 steps per year",
        "lattice_config": {
            "maturities_years": list(MATURITIES),
            "steps_per_year": STEPS_PER_YEAR,
            "note": "Finite maturity and discrete price/time grids approximate the perpetual continuous-exercise result; gaps are not exact error bounds.",
        },
        "cases": cases,
        "figure": figure(cases[0]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §26.2 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §26.2 perpetual roots, boundaries, pasting and independent long-maturity CRR")


if __name__ == "__main__":
    main()
