"""Independent Hull GE §26.4 gap-option reference, without importing hullkit.

Three constructions are compared for every case: equations 26.1/26.2 with an
``erfc`` normal CDF, Gauss–Legendre quadrature of the payoff against the
lognormal density (the trigger is an interval endpoint, so the jump is never
inside a panel), and, for a subset, seeded antithetic Monte Carlo. Example 26.1
is checked against the printed $3,436, $1,896 and "about 45%".
"""

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-4/reference.json"
SEED = 20260930
PAIRS = 2**19
NODES, WEIGHTS = np.polynomial.legendre.leggauss(32)
PANELS = 96
TAIL = 16.0

MARKETS = {
    "base": dict(spot=100.0, r=0.05, sigma=0.25, T=1.0, q=0.02),
    "long_high_vol": dict(spot=100.0, r=0.03, sigma=0.40, T=2.0, q=0.0),
    "short_low_vol": dict(spot=50.0, r=0.01, sigma=0.15, T=0.5, q=0.03),
}
STRIKE_PAIRS = ((0.9, 1.0), (1.0, 1.0), (1.1, 1.0), (0.0, 1.0), (1.0, 0.8), (1.0, 1.2))
EXAMPLE = dict(spot=500_000.0, r=0.05, sigma=0.20, T=1.0, q=0.0)
PRINTED = {"regular_put": 3_436, "gap_put": 1_896, "reduction_percent": 45}


def norm_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d(spot, K2, r, sigma, T, q):
    d1 = (math.log(spot / K2) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def closed_form(kind, spot, K1, K2, r, sigma, T, q):
    """Hull eq. 26.1 (call) and 26.2 (put): d1, d2 at the trigger, K1 in the cash leg."""
    d1, d2 = _d(spot, K2, r, sigma, T, q)
    if kind == "call":
        return spot * math.exp(-q * T) * norm_cdf(d1) - K1 * math.exp(-r * T) * norm_cdf(d2)
    return K1 * math.exp(-r * T) * norm_cdf(-d2) - spot * math.exp(-q * T) * norm_cdf(-d1)


def _terminal(spot, r, sigma, T, q, z):
    return spot * np.exp((r - q - 0.5 * sigma * sigma) * T + sigma * math.sqrt(T) * z)


def _trigger_z(spot, K2, r, sigma, T, q):
    return (math.log(K2 / spot) - (r - q - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))


def _integrate(function, low, high):
    if high <= low:
        return 0.0
    edges = np.linspace(low, high, PANELS + 1)
    total = 0.0
    for a, b in itertools.pairwise(edges):
        z = 0.5 * (b - a) * NODES + 0.5 * (a + b)
        total += 0.5 * (b - a) * float(np.dot(WEIGHTS, function(z)))
    return float(total)


def _density(z):
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _region(kind, spot, K2, r, sigma, T, q):
    star = _trigger_z(spot, K2, r, sigma, T, q)
    upper = TAIL + sigma * math.sqrt(T)
    if kind == "call":
        return max(star, -upper), upper
    return -upper, min(star, upper)


def quadrature(kind, spot, K1, K2, r, sigma, T, q):
    """Discounted expected payoff integrated over the trigger region only."""
    low, high = _region(kind, spot, K2, r, sigma, T, q)
    sign = 1.0 if kind == "call" else -1.0

    def payoff(z):
        return sign * (_terminal(spot, r, sigma, T, q, z) - K1) * _density(z)

    return math.exp(-r * T) * _integrate(payoff, low, high)


def trigger_probability(kind, spot, K2, r, sigma, T, q):
    low, high = _region(kind, spot, K2, r, sigma, T, q)
    return _integrate(_density, low, high)


def conditional_mean(kind, spot, K2, r, sigma, T, q):
    """Risk-neutral mean of S_T given the trigger: the K1 that prices the gap at zero."""
    low, high = _region(kind, spot, K2, r, sigma, T, q)
    mass = _integrate(lambda z: _terminal(spot, r, sigma, T, q, z) * _density(z), low, high)
    return mass / trigger_probability(kind, spot, K2, r, sigma, T, q)


def monte_carlo(kind, spot, K1, K2, r, sigma, T, q, seed=SEED, pairs=PAIRS):
    """Antithetic pairs; the standard error uses the pair averages."""
    z = np.random.default_rng(seed).standard_normal(pairs)
    values = []
    for draw in (z, -z):
        s = _terminal(spot, r, sigma, T, q, draw)
        hit = s > K2 if kind == "call" else s < K2
        values.append(np.where(hit, (s - K1) if kind == "call" else (K1 - s), 0.0))
    pair = 0.5 * (values[0] + values[1]) * math.exp(-r * T)
    return float(pair.mean()), float(pair.std(ddof=1) / math.sqrt(pairs))


def _case(label, kind, market, K1, K2, seed=None):
    closed = closed_form(kind, K1=K1, K2=K2, **market)
    quad = quadrature(kind, K1=K1, K2=K2, **market)
    regular = closed_form(kind, K1=K2, K2=K2, **market)
    _, d2 = _d(market["spot"], K2, market["r"], market["sigma"], market["T"], market["q"])
    probability = norm_cdf(d2) if kind == "call" else norm_cdf(-d2)
    sign = 1.0 if kind == "call" else -1.0
    adjustment = sign * (K2 - K1) * math.exp(-market["r"] * market["T"]) * probability
    row = {
        "label": label,
        "kind": kind,
        **market,
        "K1": K1,
        "K2": K2,
        "price": closed,
        "quadrature_price": quad,
        "regular_price": regular,
        "trigger_adjustment": adjustment,
        "trigger_probability": probability,
        "quadrature_trigger_probability": trigger_probability(kind, K2=K2, **market),
    }
    if abs(closed - quad) > 1e-10 * max(1.0, abs(closed)):
        raise AssertionError(f"closed form and quadrature differ: {label}")
    if abs(closed - (regular + adjustment)) > 1e-10 * max(1.0, abs(closed)):
        raise AssertionError(f"regular plus adjustment differs: {label}")
    if seed is not None:
        mean, error = monte_carlo(kind, K1=K1, K2=K2, **market, seed=seed)
        row["monte_carlo"] = {
            "seed": seed,
            "mean": mean,
            "standard_error": error,
            "z": (mean - closed) / error,
        }
        if abs(row["monte_carlo"]["z"]) > 4.0:
            raise AssertionError(f"Monte Carlo outside four standard errors: {label}")
    return row


def _cases():
    """Monte Carlo cases get their own seed so their z-scores are independent."""
    rows = []
    seeds = iter(range(SEED, SEED + 100))
    for name, market in MARKETS.items():
        for index, (k1, k2) in enumerate(STRIKE_PAIRS):
            for kind in ("call", "put"):
                K1, K2 = k1 * market["spot"], k2 * market["spot"]
                label = f"{name}_{kind}_K1_{K1:g}_K2_{K2:g}"
                seed = next(seeds) if name == "base" and index < 4 else None
                rows.append(_case(label, kind, market, K1, K2, seed))
    for K1, K2 in ((400_000.0, 400_000.0), (400_000.0, 350_000.0)):
        label = f"example_26_1_put_K1_{K1:g}_K2_{K2:g}"
        rows.append(_case(label, "put", EXAMPLE, K1, K2, next(seeds)))
    return rows


def _parity(rows):
    by_key = {
        (r["spot"], r["r"], r["sigma"], r["T"], r["q"], r["K1"], r["K2"], r["kind"]): r
        for r in rows
    }
    worst = 0.0
    count = 0
    for key, row in by_key.items():
        if key[-1] != "call" or (put := by_key.get((*key[:-1], "put"))) is None:
            continue
        spot, r, _, T, q, K1, _ = key[:-1]
        target = spot * math.exp(-q * T) - K1 * math.exp(-r * T)
        worst = max(worst, abs(row["price"] - put["price"] - target))
        count += 1
    if worst > 1e-10:
        raise AssertionError("gap call minus gap put parity failed")
    return {"pairs": count, "max_error": worst}


def _example():
    regular = closed_form("put", K1=400_000.0, K2=400_000.0, **EXAMPLE)
    insurer = closed_form("put", K1=400_000.0, K2=350_000.0, **EXAMPLE)
    policyholder = closed_form("put", K1=350_000.0, K2=350_000.0, **EXAMPLE)
    _, d2 = _d(
        EXAMPLE["spot"], 350_000.0, EXAMPLE["r"], EXAMPLE["sigma"], EXAMPLE["T"], EXAMPLE["q"]
    )
    probability = norm_cdf(-d2)
    transfer = 50_000.0 * math.exp(-EXAMPLE["r"] * EXAMPLE["T"]) * probability
    reduction = 1.0 - insurer / regular
    if round(regular) != PRINTED["regular_put"] or round(insurer) != PRINTED["gap_put"]:
        raise AssertionError("Example 26.1 printed prices not reproduced")
    if round(100.0 * reduction) != PRINTED["reduction_percent"]:
        raise AssertionError("Example 26.1 reduction not about 45%")
    if abs(insurer - policyholder - transfer) > 1e-9:
        raise AssertionError("insurer cost is not policyholder value plus transfer cost")
    return {
        **EXAMPLE,
        "K1": 400_000.0,
        "K2": 350_000.0,
        "transfer_cost": 50_000.0,
        "printed": PRINTED,
        "regular_put": regular,
        "insurer_gap_put": insurer,
        "insurer_gap_put_quadrature": quadrature("put", K1=400_000.0, K2=350_000.0, **EXAMPLE),
        "policyholder_put": policyholder,
        "transfer_cost_present_value": transfer,
        "claim_probability": probability,
        "reduction": reduction,
    }


def _conditional_means():
    market = MARKETS["base"]
    rows = {}
    for kind in ("call", "put"):
        d1, d2 = _d(market["spot"], 100.0, market["r"], market["sigma"], market["T"], market["q"])
        sign = 1.0 if kind == "call" else -1.0
        forward = market["spot"] * math.exp((market["r"] - market["q"]) * market["T"])
        closed = forward * norm_cdf(sign * d1) / norm_cdf(sign * d2)
        quad = conditional_mean(kind, K2=100.0, **market)
        if abs(closed - quad) > 1e-10 * closed:
            raise AssertionError(f"conditional mean differs: {kind}")
        price = closed_form(kind, K1=closed, K2=100.0, **market)
        if abs(price) > 1e-12:
            raise AssertionError(f"conditional-mean settlement does not price at zero: {kind}")
        rows[kind] = {"closed_form": closed, "quadrature": quad, "price_at_level": price}
    return rows


def _figures():
    market = MARKETS["base"]
    grid = [round(60.0 + 0.5 * i, 10) for i in range(161)]

    def payoff(kind, K1, K2, s):
        if kind == "call":
            return s - K1 if s > K2 else 0.0
        return K1 - s if s < K2 else 0.0

    settlement = [round(60.0 + i, 10) for i in range(81)]
    lines = {
        kind: [closed_form(kind, K1=k1, K2=100.0, **market) for k1 in settlement]
        for kind in ("call", "put")
    }
    _, d2 = _d(market["spot"], 100.0, market["r"], market["sigma"], market["T"], market["q"])
    insurance_grid = [200_000.0 + 2_500.0 * i for i in range(121)]
    costs = [5_000.0 * i for i in range(31)]
    regular = closed_form("put", K1=400_000.0, K2=400_000.0, **EXAMPLE)
    transfer_rows = []
    for cost in costs:
        trigger = 400_000.0 - cost
        insurer = closed_form("put", K1=400_000.0, K2=trigger, **EXAMPLE)
        holder = closed_form("put", K1=trigger, K2=trigger, **EXAMPLE)
        _, dt2 = _d(
            EXAMPLE["spot"], trigger, EXAMPLE["r"], EXAMPLE["sigma"], EXAMPLE["T"], EXAMPLE["q"]
        )
        pv = cost * math.exp(-EXAMPLE["r"] * EXAMPLE["T"]) * norm_cdf(-dt2)
        if abs(insurer - holder - pv) > 1e-9:
            raise AssertionError("transfer-cost identity failed")
        transfer_rows.append(
            {
                "transfer_cost": cost,
                "insurer_cost": insurer,
                "policyholder_value": holder,
                "transfer_cost_present_value": pv,
                "reduction": 1.0 - insurer / regular,
            }
        )
    return {
        "payoff": {
            "market": market,
            "K2": 100.0,
            "grid": grid,
            "regular_call": [payoff("call", 100.0, 100.0, s) for s in grid],
            "gap_call_K1_90": [payoff("call", 90.0, 100.0, s) for s in grid],
            "gap_call_K1_110": [payoff("call", 110.0, 100.0, s) for s in grid],
        },
        "settlement_line": {
            "market": market,
            "K2": 100.0,
            "K1": settlement,
            "call": lines["call"],
            "put": lines["put"],
            "call_slope": -math.exp(-market["r"] * market["T"]) * norm_cdf(d2),
            "put_slope": math.exp(-market["r"] * market["T"]) * norm_cdf(-d2),
        },
        "insurance": {
            "grid": insurance_grid,
            "regular_put": [payoff("put", 400_000.0, 400_000.0, s) for s in insurance_grid],
            "insurer_gap_put": [payoff("put", 400_000.0, 350_000.0, s) for s in insurance_grid],
            "policyholder_net": [payoff("put", 350_000.0, 350_000.0, s) for s in insurance_grid],
        },
        "transfer_cost": {"regular_put": regular, "rows": transfer_rows},
    }


def build():
    """Save cross-checked prices, Example 26.1 and the four figure datasets."""
    rows = _cases()
    return {
        "section": "26.4",
        "source": "Hull 11e Global Edition p.617, equations 26.1-26.2 and Example 26.1",
        "note": (
            "Only Example 26.1 (S0=500,000, K1=400,000, K2=350,000, r=5%, sigma=20%, T=1, "
            "q=0 and the regular put at 400,000) is printed; every other market is synthetic."
        ),
        "method": {
            "normal_cdf": "0.5*erfc(-x/sqrt(2))",
            "quadrature": f"Gauss-Legendre {len(NODES)} nodes x {PANELS} panels over the trigger region, +/-{TAIL:g} sd",
            "monte_carlo": f"seeds {SEED}+i per case, {PAIRS} antithetic pairs, |z| <= 4",
        },
        "cases": rows,
        "parity": _parity(rows),
        "example_26_1": _example(),
        "conditional_mean": _conditional_means(),
        "figure": _figures(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("missing or stale §26.4 independent reference")
        print("PASS: §26.4 closed form, quadrature and Monte Carlo reference")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(expected, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
