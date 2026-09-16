"""Controller independent browser pins; never imports the new tree/figure code."""

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.stats import lognorm

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "scripts"))
import build_shout_reference as oracle


def load_module(path):
    spec = importlib.util.spec_from_file_location("lookback_independent_oracle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lookback = load_module(P / "hullkit/tests/test_lookback_reference.py")


def euro_integral(spot, strike, r, q, sigma, tau):
    law = lognorm(
        s=sigma * math.sqrt(tau), scale=spot * math.exp((r - q - 0.5 * sigma * sigma) * tau)
    )
    value, error = quad(
        lambda terminal: (terminal - strike) * law.pdf(terminal),
        strike,
        np.inf,
        epsabs=1e-10,
        epsrel=1e-11,
        limit=250,
    )
    assert error * math.exp(-r * tau) < 1e-8
    return math.exp(-r * tau) * value


rows = json.loads((P / "docs/validation/section-26-12/prices.json").read_text())["rows"]
comparison = []
for row in rows:
    if row["contract"] != "call":
        continue
    spot, strike, r, q, sigma, expiry = (
        row[k] for k in ["spot", "strike", "rate", "dividend", "volatility", "expiry"]
    )
    european = euro_integral(spot, strike, r, q, sigma, expiry)
    assert abs(european - row["european"]) < 1e-8
    market = lookback.Market(spot, r, sigma, expiry, q)
    independent_ceiling = lookback._reference_price(
        market, "fixed_call", (1.0, 1.0), strike_ratio=strike / spot
    )
    comparison.append(
        {
            "market": row["market"],
            "spot": spot,
            "strike": strike,
            "european": european,
            "shout_reference": row["price"],
            "lookback": None if abs(r - q) < 1e-8 else independent_ceiling,
            "lookback_zero_carry_integral": independent_ceiling if abs(r - q) < 1e-8 else None,
        }
    )

# Every small-tree node independently built with payoff integration for the reset call.
spot = strike = 100.0
r, q, sigma, expiry, n = 0.05, 0.02, 0.2, 1.0, 3
dt = expiry / n
up = math.exp(sigma * math.sqrt(dt))
prob = (math.exp((r - q) * dt) - 1 / up) / (up - 1 / up)
discount = math.exp(-r * dt)
levels = []
for i in range(n + 1):
    nodes = []
    for j in range(i + 1):
        s = spot * up ** (2 * j - i)
        tau = expiry - i * dt
        cash = math.exp(-r * tau) * (s - strike)
        reset = euro_integral(s, s, r, q, sigma, tau) if tau > 0 else 0.0
        nodes.append(
            {
                "id": f"{i}:{j}",
                "step": i,
                "up_count": j,
                "spot": s,
                "remaining": tau,
                "cash": cash,
                "reset_european": reset,
                "shout": cash + reset,
                "continuation": None,
                "value": max(s - strike, 0.0),
                "action": "expiry",
            }
        )
    levels.append(nodes)
for i in range(n - 1, -1, -1):
    for j, node in enumerate(levels[i]):
        cont = discount * (
            (1 - prob) * levels[i + 1][j]["value"] + prob * levels[i + 1][j + 1]["value"]
        )
        node.update(
            continuation=cont,
            value=max(cont, node["shout"]),
            action="shout" if node["shout"] > cont else "continue",
        )

boundaries = []
for market in oracle.MARKETS:
    if market.name not in ["positive-carry", "zero-carry", "long-high-vol"]:
        continue
    _, taus, boundary = oracle.integral_equation_price(
        100.0,
        100.0,
        market.rate,
        market.dividend,
        market.volatility,
        market.expiry,
        "call",
        steps=400,
    )
    boundaries.append(
        {
            "market": market.name,
            "expiry": market.expiry,
            "remaining_times": taus.tolist(),
            "levels": boundary.tolist(),
            "engine": "B,400sqrt-time intervals,not an exact boundary",
        }
    )

sources = [
    "scripts/build_shout_browser_reference.py",
    "scripts/build_shout_reference.py",
    "hullkit/tests/test_lookback_reference.py",
    "docs/validation/section-26-12/prices.json",
]
payload = {
    "method": "Payoff literals; independent lognormal quadrature; frozen M4a shout prices; independent extrema-tail lookback integral; independent N3 recursion; M4a engineB boundary.",
    "source_sha256": {
        path: hashlib.sha256((P / path).read_bytes()).hexdigest() for path in sources
    },
    "payoff": [
        {
            "shouted": h,
            "terminal": s,
            "locked": max(s - 50.0, h - 50.0),
            "european": max(s - 50.0, 0.0),
            "cash": h - 50.0,
            "reset_call": max(s - h, 0.0),
        }
        for h in [50.0, 60.0]
        for s in [30.0, 50.0, 60.0, 75.0, 100.0]
    ],
    "comparison": comparison,
    "small_tree": {
        "steps": n,
        "market": {
            "spot": spot,
            "strike": strike,
            "rate": r,
            "dividend": q,
            "sigma": sigma,
            "expiry": expiry,
        },
        "probability": prob,
        "nodes": [node for level in levels for node in level],
    },
    "boundaries": boundaries,
    "limits": [
        "Continuous-time reference prices have empirical error, not a proved bound.",
        "Zero-carry lookback integral is finite but production lookback API remains unsupported; omit that comparison bar.",
        "CRR tree numeric tolerance and boundary grid resolution must come from measured tree-check record, not machine equality to continuous prices.",
    ],
}
out = P / "docs/validation/section-26-12/browser-reference.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(
    f"Independent browser pins: {len(comparison)} call-price rows,10N3nodes,10payoff pins,3boundary curves -> {out}"
)
