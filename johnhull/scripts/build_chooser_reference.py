"""Independent T1 density integrals of max(call1,put1), without hullkit."""

import argparse
import functools
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-26-8/reference.json"
MARKET = dict(S=100.0, K=100.0, r=0.05, sigma=0.2, T1=0.5, T2=1.0, q=0.02)
MC_PATHS = 524288


def vanilla(s, k, r, sigma, t, q, kind):
    """Own scalar erfc BSM expectation, including deterministic limits."""
    forward = s * math.exp(-q * t) - k * math.exp(-r * t)
    if sigma == 0 or t == 0:
        return max(forward if kind == "call" else -forward, 0.0)
    v = sigma * math.sqrt(t)
    d = (math.log(s / k) + (r - q + sigma * sigma / 2) * t) / v

    def n(x):
        return 0.5 * math.erfc(-x / math.sqrt(2))

    if kind == "call":
        return max(s * math.exp(-q * t) * n(d) - k * math.exp(-r * t) * n(d - v), 0.0)
    return max(k * math.exp(-r * t) * n(-d + v) - s * math.exp(-q * t) * n(-d), 0.0)


def integrate_chooser(S, K, r, sigma, T1, T2, q=0.0):
    """Discount the conditional selected value; never use the replication price."""
    tau = T2 - T1
    if T1 == 0:
        return max(vanilla(S, K, r, sigma, T2, q, k) for k in ("call", "put")), 0.0
    if sigma == 0:
        s1 = S * math.exp((r - q) * T1)
        return math.exp(-r * T1) * max(
            vanilla(s1, K, r, 0, tau, q, k) for k in ("call", "put")
        ), 0.0
    v = sigma * math.sqrt(T1)
    drift = (r - q - sigma * sigma / 2) * T1
    center = (math.log(K / S) - (r - q) * tau - drift) / v
    width = math.sqrt(tau / T1)
    # Split both the choice kink and narrow inner-vanilla transition, even
    # near T1=T2 where adaptive integration can underreport its true error.
    points = sorted(
        set(
            [-12.0, 12.0]
            + [center + n * width for n in (-10, -3, 0, 3, 10) if -12 < center + n * width < 12]
        )
    )

    def f(z):
        s1 = S * math.exp(drift + v * z)
        chosen = max(vanilla(s1, K, r, sigma, tau, q, k) for k in ("call", "put"))
        return math.exp(-r * T1) * chosen * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    values = [quad(f, a, b, epsabs=2e-11, epsrel=2e-12, limit=200) for a, b in pairwise(points)]
    return sum(x for x, _ in values), sum(e for _, e in values)


def _row(m):
    price, error = integrate_chooser(**m)
    return {**m, "price": price, "quadrature_error": error}


def _mc():
    z = np.random.default_rng(268).standard_normal(MC_PATHS)
    rows = []
    for t1 in (0.1, 0.5, 0.9, 0.999999):
        m = {**MARKET, "T1": t1}
        tau = m["T2"] - t1
        s1 = m["S"] * np.exp(
            (m["r"] - m["q"] - m["sigma"] ** 2 / 2) * t1 + m["sigma"] * math.sqrt(t1) * z
        )
        v = m["sigma"] * math.sqrt(tau)
        d = (np.log(s1 / m["K"]) + (m["r"] - m["q"] + m["sigma"] ** 2 / 2) * tau) / v
        c = s1 * np.exp(-m["q"] * tau) * ndtr(d) - m["K"] * np.exp(-m["r"] * tau) * ndtr(d - v)
        p = m["K"] * np.exp(-m["r"] * tau) * ndtr(-d + v) - s1 * np.exp(-m["q"] * tau) * ndtr(-d)
        pay = np.exp(-m["r"] * t1) * np.maximum(c, p)
        price = float(pay.mean())
        se = float(pay.std(ddof=1) / math.sqrt(MC_PATHS))
        rows.append(
            {
                **m,
                "price": price,
                "standard_error": se,
                "ci95": [price - 1.959963984540054 * se, price + 1.959963984540054 * se],
                "reference_price": integrate_chooser(**m)[0],
                "paths": MC_PATHS,
                "seed": 268,
                "estimator": "T1 spot sampling with conditional chosen vanilla value",
            }
        )
    return rows


@functools.lru_cache(maxsize=1)
def build():
    markets = [
        MARKET,
        {**MARKET, "S": 80, "K": 90, "r": -0.01, "sigma": 0.3, "T2": 1.5, "q": 0.04},
        {**MARKET, "S": 120, "r": 0.02, "sigma": 0.45, "T2": 2, "q": 0},
        {**MARKET, "sigma": 0},
        {**MARKET, "r": -0.02, "sigma": 0.12, "T2": 2, "q": -0.01},
        {**MARKET, "sigma": 0.005, "r": 0.02, "q": 0.02},
        {**MARKET, "S": 50, "sigma": 0.15},
        {**MARKET, "T2": 0},
    ]
    cases = [
        _row({**m, "T1": fraction * m["T2"]})
        for m in markets
        for fraction in (0, 0.01, 0.1, 0.25, 0.5, 0.9, 0.999999, 1)
    ]
    tau = MARKET["T2"] - MARKET["T1"]
    h = MARKET["K"] * math.exp(-(MARKET["r"] - MARKET["q"]) * tau)
    w = math.exp(-MARKET["q"] * tau)
    choice = dict(spot=np.linspace(60, 140, 81).tolist(), boundary=h, weight=w, market=MARKET)
    for kind in ("call", "put"):
        choice[kind] = [
            vanilla(s, MARKET["K"], MARKET["r"], MARKET["sigma"], tau, MARKET["q"], kind)
            for s in choice["spot"]
        ]
    choice["chosen"] = [max(c, p) for c, p in zip(choice["call"], choice["put"], strict=True)]
    package = dict(spot=np.linspace(60, 140, 41).tolist(), boundary=h, weight=w, market=MARKET)
    package["call"] = [vanilla(s, 100, 0.05, 0.2, 1, 0.02, "call") for s in package["spot"]]
    package["chooser"] = [integrate_chooser(**{**MARKET, "S": s})[0] for s in package["spot"]]
    # This residual is obtained from an independently integrated chooser,
    # rather than evaluating the production replication expression.
    package["extra_put"] = [v - c for v, c in zip(package["chooser"], package["call"], strict=True)]
    timing = dict(T1=[0, 0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 0.999999, 1], market=MARKET)
    timing["chooser"] = [integrate_chooser(**{**MARKET, "T1": t})[0] for t in timing["T1"]]
    c, p = (vanilla(100, 100, 0.05, 0.2, 1, 0.02, k) for k in ("call", "put"))
    timing["immediate"] = [max(c, p)] * len(timing["T1"])
    timing["straddle"] = [c + p] * len(timing["T1"])
    return dict(
        section="26.8",
        source="Hull 11e GE pp.619–620; all numerical examples synthetic",
        method="independent erfc vanilla and split T1 density integral of max(call1,put1)",
        cases=cases,
        example=_row(MARKET),
        mc=_mc(),
        figure=dict(choice=choice, package=package, timing=timing),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("chooser independent reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.8 independent conditional integral, 64 cases and 4 seeded MC")


if __name__ == "__main__":
    main()
