"""Independent Hull §26.7 conditional payoff integrals and seeded MC.

No hullkit or bivariate-normal CDF is imported. The inner vanilla expectation
uses an independent erfc implementation; the outer payoff is integrated
against the T1 lognormal density and discounted from T1.
"""

import argparse
import functools
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import ndtr

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-26-7/reference.json"
KINDS = ("call_on_call", "put_on_call", "call_on_put", "put_on_put")
MC_PATHS = 524288
MARKET = dict(S=100.0, K1=10.0, K2=100.0, r=0.05, sigma=0.2, T1=0.5, T2=1.0, q=0.02)


def vanilla(s, k, r, sigma, t, q, inner):
    """Independent scalar discounted vanilla expectation, with exact limits."""
    forward = s * math.exp(-q * t) - k * math.exp(-r * t)
    if sigma == 0 or t == 0:
        return max(forward if inner == "call" else -forward, 0)

    def n(x):
        return 0.5 * math.erfc(-x / math.sqrt(2))

    v = sigma * math.sqrt(t)
    d = (math.log(s / k) + (r - q + sigma * sigma / 2) * t) / v
    if inner == "call":
        return max(s * math.exp(-q * t) * n(d) - k * math.exp(-r * t) * n(d - v), 0)
    return max(k * math.exp(-r * t) * n(-d + v) - s * math.exp(-q * t) * n(-d), 0)


def critical(K1, K2, r, sigma, tau, q, inner):
    if K1 == 0 or (inner == "put" and K1 >= K2 * math.exp(-r * tau)):
        return None
    # This root is independent of the pricing implementation, in currency
    # spot rather than its normalized log-spot coordinates.
    hi = K2
    while (
        vanilla(hi, K2, r, sigma, tau, q, inner) > K1
        if inner == "put"
        else vanilla(hi, K2, r, sigma, tau, q, inner) < K1
    ):
        hi *= 2
    return brentq(
        lambda s: vanilla(s, K2, r, sigma, tau, q, inner) - K1,
        K2 * 1e-14,
        hi,
        xtol=1e-12,
        rtol=1e-14,
    )


def integrate_compound(S, K1, K2, r, sigma, T1, T2, q=0.0, kind="call_on_call"):
    outer, inner = kind.split("_on_")
    tau, discount = T2 - T1, math.exp(-r * T1)
    if K1 == 0:
        return (vanilla(S, K2, r, sigma, T2, q, inner) if outer == "call" else 0.0), 0.0
    if sigma == 0:
        value1 = vanilla(S * math.exp((r - q) * T1), K2, r, 0, tau, q, inner)
        return discount * max(value1 - K1 if outer == "call" else K1 - value1, 0), 0.0
    root = critical(K1, K2, r, sigma, tau, q, inner)
    vol = sigma * math.sqrt(T1)
    drift = (r - q - sigma * sigma / 2) * T1
    points = [-12.0, 12.0]
    if root is not None:
        z = (math.log(root / S) - drift) / vol
        if -12 < z < 12:
            points.append(z)
    # The inner vanilla has its own narrow transition near forward moneyness
    # zero. An outer exercise root alone can leave that transition invisible
    # to adaptive quadrature when tau << T1, despite a tiny error estimate.
    center = (math.log(K2 / S) - (r - q) * tau - drift) / vol
    width = math.sqrt(tau / T1)
    points.extend(center + n * width for n in (-10, -3, 0, 3, 10) if -12 < center + n * width < 12)
    points = sorted(set(points))

    def integrand(z):
        s1 = S * math.exp(drift + vol * z)
        value = vanilla(s1, K2, r, sigma, tau, q, inner)
        payoff = max(value - K1 if outer == "call" else K1 - value, 0)
        return discount * payoff * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    values = [
        quad(integrand, a, b, epsabs=2e-11, epsrel=2e-12, limit=200) for a, b in pairwise(points)
    ]
    return sum(value for value, _ in values), sum(error for _, error in values)


def _row(market, kind):
    price, error = integrate_compound(**market, kind=kind)
    return {**market, "kind": kind, "price": price, "quadrature_error": error}


def _mc():
    z = np.random.default_rng(267).standard_normal(MC_PATHS)
    m = MARKET
    s1 = m["S"] * np.exp(
        (m["r"] - m["q"] - m["sigma"] ** 2 / 2) * m["T1"] + m["sigma"] * math.sqrt(m["T1"]) * z
    )
    tau = m["T2"] - m["T1"]
    vol = m["sigma"] * math.sqrt(tau)
    d = (np.log(s1 / m["K2"]) + (m["r"] - m["q"] + m["sigma"] ** 2 / 2) * tau) / vol
    call = s1 * np.exp(-m["q"] * tau) * ndtr(d) - m["K2"] * np.exp(-m["r"] * tau) * ndtr(d - vol)
    put = m["K2"] * np.exp(-m["r"] * tau) * ndtr(-d + vol) - s1 * np.exp(-m["q"] * tau) * ndtr(-d)
    rows = []
    for kind in KINDS:
        outer, inner = kind.split("_on_")
        value = call if inner == "call" else put
        payoff = np.exp(-m["r"] * m["T1"]) * np.maximum(
            value - m["K1"] if outer == "call" else m["K1"] - value, 0
        )
        se = float(payoff.std(ddof=1) / math.sqrt(MC_PATHS))
        price = float(payoff.mean())
        rows.append(
            {
                **m,
                "kind": kind,
                "price": price,
                "standard_error": se,
                "ci95": [price - 1.959963984540054 * se, price + 1.959963984540054 * se],
                "paths": MC_PATHS,
                "seed": 267,
                "reference_price": integrate_compound(**m, kind=kind)[0],
                "estimator": "T1 spot sampling with conditional inner vanilla value",
            }
        )
    return rows


@functools.lru_cache(maxsize=1)
def build():
    markets = [
        MARKET,
        dict(S=80.0, K2=90.0, r=-0.01, sigma=0.3, T1=0.25, T2=1.5, q=0.04),
        dict(S=120.0, K2=100.0, r=0.02, sigma=0.45, T1=1.0, T2=2.0, q=0.0),
        {**MARKET, "sigma": 0.0},
        {**MARKET, "T1": 0.9999},
        dict(S=100.0, K2=100.0, r=-0.02, sigma=0.12, T1=0.1, T2=2.0, q=-0.01),
    ]
    cases = [
        _row({**market, "K1": factor * market["K2"]}, kind)
        for market in markets
        for factor in (0, 0.05, 0.25, 1.1)
        for kind in KINDS
    ]
    bound = MARKET["K2"] * math.exp(-MARKET["r"] * (MARKET["T2"] - MARKET["T1"]))
    cases += [
        _row({**MARKET, "K1": bound * factor}, kind) for factor in (1, 1 - 1e-8) for kind in KINDS
    ]
    roots = {inner: critical(10, 100, 0.05, 0.2, 0.5, 0.02, inner) for inner in ("call", "put")}
    spots = np.linspace(20, 180, 81).tolist()
    threshold = dict(spot=spots, critical=roots, market=MARKET)
    for inner in ("call", "put"):
        values = [vanilla(s, 100, 0.05, 0.2, 0.5, 0.02, inner) for s in spots]
        threshold[inner] = values
        for outer in ("call", "put"):
            threshold[outer + "_on_" + inner] = [
                max(v - 10 if outer == "call" else 10 - v, 0) for v in values
            ]
    strikes = dict(K1=np.linspace(0, 110, 23).tolist(), market=MARKET, put_bound=bound)
    timing = dict(T1=[0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 0.9999], market=MARKET)
    for kind in KINDS:
        strikes[kind] = [
            integrate_compound(**{**MARKET, "K1": k}, kind=kind)[0] for k in strikes["K1"]
        ]
        timing[kind] = [
            integrate_compound(**{**MARKET, "T1": t}, kind=kind)[0] for t in timing["T1"]
        ]
    return dict(
        section="26.7",
        source="Hull GE pp.618–619; all numerical inputs synthetic",
        cases=cases,
        example={kind: _row(MARKET, kind) for kind in KINDS},
        mc=_mc(),
        figure=dict(threshold=threshold, strikes=strikes, timing=timing),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("compound independent reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.7 independent conditional integrals and seeded Monte Carlo")


if __name__ == "__main__":
    main()
