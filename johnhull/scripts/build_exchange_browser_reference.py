"""Independent browser pins for §26.14; never imports the lesson or hullkit pricer.

Every displayed number is pinned either to the frozen M6a reference table in
prices.json / numerical-check.json or to algebra recomputed here (the payoff
identity, equation 26.5 written out, the ratio restatement, and the discounted
forward spread). Prices are in currency, maturities in years, yields and
volatilities annualised per year.
"""

import hashlib
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-14"
SOURCE_PATHS = (
    "scripts/build_exchange_browser_reference.py",
    "scripts/build_exchange_reference.py",
    "docs/validation/section-26-14/prices.json",
    "docs/validation/section-26-14/numerical-check.json",
)
PAYOFF_TERMINALS = (60.0, 80.0, 100.0, 120.0, 140.0, 160.0)
PAYOFF_U = 100.0
CORRELATION_MARKETS = ("equal-vol-uncorrelated", "asymmetric-vol", "long-high-vol")
RATE_MARKETS = ("equal-vol-tight", "yield-on-received", "long-high-vol")
AMERICAN_MARKETS = ("equal-vol-uncorrelated", "yield-on-received", "equal-vol-tight")
NOTEBOOK_RHOS = (-0.5, 0.0, 0.5, 0.9)
NOTEBOOK_AMERICAN = (("配当なし q_V=0", 0.0), ("受取側に配当 q_V=6%", 0.06))
NOTEBOOK_RATIOS = (1.0, 1.25)


def _normal_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _spread_volatility(sigma_u, sigma_v, rho):
    return math.sqrt(sigma_u**2 + sigma_v**2 - 2.0 * rho * sigma_u * sigma_v)


def _margrabe(spot_u, spot_v, sigma_u, sigma_v, rho, expiry, yield_u, yield_v):
    """Equation 26.5 written out here; the pricer under test is never imported."""
    forward_u = spot_u * math.exp(-yield_u * expiry)
    forward_v = spot_v * math.exp(-yield_v * expiry)
    spread = _spread_volatility(sigma_u, sigma_v, rho)
    if spread <= 0.0:
        return max(forward_v - forward_u, 0.0)
    scale = spread * math.sqrt(expiry)
    d1 = (math.log(forward_v / forward_u) + 0.5 * scale**2) / scale
    return forward_v * _normal_cdf(d1) - forward_u * _normal_cdf(d1 - scale)


def _market(rows, name):
    row = next(row for row in rows if row["market"] == name)
    return {
        key: row[key]
        for key in ("volatility_u", "volatility_v", "correlation", "yield_u", "yield_v", "expiry")
    }


def _payoff_pins():
    """The terminal payoffs, recomputed from max/min rather than read back."""
    return {
        "terminal_u": PAYOFF_U,
        "rows": [
            {
                "terminal_v": terminal,
                "exchange": max(terminal - PAYOFF_U, 0.0),
                "better_of": max(PAYOFF_U, terminal),
                "worse_of": min(PAYOFF_U, terminal),
            }
            for terminal in PAYOFF_TERMINALS
        ],
    }


def _correlation_pins(rows):
    """The endpoints and shape quoted in the correlation figure's title."""
    pins = []
    for name in CORRELATION_MARKETS:
        market = _market(rows, name)
        endpoints = {}
        for correlation in (-0.95, 0.95):
            endpoints[f"{correlation:+.2f}"] = {
                "price": _margrabe(100.0, 100.0, market["volatility_u"], market["volatility_v"],
                                   correlation, market["expiry"], market["yield_u"],
                                   market["yield_v"]),
                "spread_volatility": _spread_volatility(
                    market["volatility_u"], market["volatility_v"], correlation),
            }
        pins.append(
            {
                "market": name,
                "endpoints": endpoints,
                "forward_spread": max(
                    100.0 * math.exp(-market["yield_v"] * market["expiry"])
                    - 100.0 * math.exp(-market["yield_u"] * market["expiry"]),
                    0.0,
                ),
                **market,
            }
        )
    return pins


def _rate_pins(rows):
    """The flat price, the ratio restatement and the line that does move."""
    pins = []
    probes = (-0.05, -0.02, 0.0, 0.02, 0.05, 0.08, 0.12)
    for name in RATE_MARKETS:
        market = _market(rows, name)
        spread = _spread_volatility(
            market["volatility_u"], market["volatility_v"], market["correlation"])
        price = _margrabe(100.0, 110.0, market["volatility_u"], market["volatility_v"],
                          market["correlation"], market["expiry"], market["yield_u"],
                          market["yield_v"])
        # The restatement: U0 calls on V/U struck at 1, risk-free rate qU, yield qV.
        scale = spread * math.sqrt(market["expiry"])
        forward_ratio = 1.1 * math.exp((market["yield_u"] - market["yield_v"]) * market["expiry"])
        d1 = (math.log(forward_ratio) + 0.5 * scale**2) / scale
        restated = 100.0 * math.exp(-market["yield_u"] * market["expiry"]) * (
            forward_ratio * _normal_cdf(d1) - _normal_cdf(d1 - scale))
        misreadings = []
        for rate in probes:
            forward = 110.0 * math.exp(rate * market["expiry"])
            d1_fixed = (math.log(forward / 100.0) + 0.5 * scale**2) / scale
            misreadings.append(
                math.exp(-rate * market["expiry"])
                * (forward * _normal_cdf(d1_fixed) - 100.0 * _normal_cdf(d1_fixed - scale))
            )
        pins.append(
            {
                "market": name,
                "value_ratio": 1.1,
                "spread_volatility": spread,
                "price": price,
                "restated_price": restated,
                "rates": list(probes),
                "fixed_strike_misreading": misreadings,
                "misreading_spread": max(misreadings) - min(misreadings),
                **market,
            }
        )
    return pins


def _american_pins(rows, record):
    """The European leg of the American figure, plus what the record measured."""
    pins = []
    recorded = {(item["market"], item["value_ratio"]): item for item in record["american"]["rows"]}
    for name in AMERICAN_MARKETS:
        market = _market(rows, name)
        ratios = [round(0.60 + 0.05 * step, 2) for step in range(17)]
        pins.append(
            {
                "market": name,
                "ratios": ratios,
                "european": [
                    _margrabe(100.0, 100.0 * ratio, market["volatility_u"], market["volatility_v"],
                              market["correlation"], market["expiry"], market["yield_u"],
                              market["yield_v"])
                    for ratio in ratios
                ],
                "intrinsic": [max(100.0 * ratio - 100.0, 0.0) for ratio in ratios],
                "recorded_premiums": {
                    str(ratio): recorded[(name, ratio)]["early_exercise_premium"]
                    for ratio in (0.8, 1.0, 1.25)
                    if (name, ratio) in recorded
                },
                **market,
            }
        )
    return pins


def _notebook_pins(rows):
    """The two DataFrames the notebook displays, recomputed independently."""
    equal = dict(volatility_u=0.2, volatility_v=0.2, expiry=1.0, yield_u=0.0, yield_v=0.0)
    ratio_rows = []
    for correlation in NOTEBOOK_RHOS:
        spread = _spread_volatility(equal["volatility_u"], equal["volatility_v"], correlation)
        price = _margrabe(100.0, 100.0, equal["volatility_u"], equal["volatility_v"],
                          correlation, equal["expiry"], equal["yield_u"], equal["yield_v"])
        scale = spread * math.sqrt(equal["expiry"])
        restated = 100.0 * (_normal_cdf(0.5 * scale) - _normal_cdf(-0.5 * scale))
        ratio_rows.append(
            {
                "correlation": correlation,
                "spread_volatility": spread,
                "price": price,
                "restated": restated,
            }
        )
    american_rows = []
    for label, yield_v in NOTEBOOK_AMERICAN:
        for ratio in NOTEBOOK_RATIOS:
            american_rows.append(
                {
                    "label": label,
                    "value_ratio": ratio,
                    "yield_v": yield_v,
                    "european": _margrabe(100.0, 100.0 * ratio, 0.25, 0.25, 0.5, 1.5, 0.0,
                                          yield_v),
                }
            )
    better = _margrabe(100.0, 110.0, 0.25, 0.25, 0.5, 1.5, 0.0, 0.06)
    return {
        "ratio_table": ratio_rows,
        "american_table": american_rows,
        "decomposition": {
            "exchange": better,
            "better_of": 100.0 + better,
            "worse_of": 110.0 * math.exp(-0.06 * 1.5) - better,
            "forward_sum": 100.0 + 110.0 * math.exp(-0.06 * 1.5),
        },
    }


def build():
    rows = json.loads((VALIDATION / "prices.json").read_text())["rows"]
    record = json.loads((VALIDATION / "numerical-check.json").read_text())
    return {
        "method": (
            "Displayed values are pinned to the frozen independent table in prices.json and to "
            "algebra recomputed here; no hullkit pricer and no lesson module is imported."
        ),
        "source_sha256": {
            path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS
        },
        "payoff": _payoff_pins(),
        "correlation": _correlation_pins(rows),
        "rate": _rate_pins(rows),
        "american": _american_pins(rows, record),
        "notebook": _notebook_pins(rows),
        "record": {
            "rate_independence_max_spread": record["rate_independence"]["max_spread"],
            "decomposition_max_residual": max(
                abs(item["sum_residual"]) for item in record["decomposition"]["rows"]),
            "max_premium_without_yield": record["american"]["max_premium_without_yield"],
            "max_premium_with_yield": record["american"]["max_premium_with_yield"],
        },
        "limits": [
            "満期給付であって現在価値ではない",
            "格子",
            "例題がなく",
            "近似",
        ],
    }


def main():
    reference = build()
    path = VALIDATION / "browser-reference.json"
    path.write_text(json.dumps(reference, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"wrote {path.relative_to(PROJECT)}")
    for pin in reference["correlation"]:
        ends = pin["endpoints"]
        print(f"  {pin['market']}: {ends['-0.95']['price']:.4f} -> {ends['+0.95']['price']:.4f}")
    for pin in reference["rate"]:
        print(
            f"  {pin['market']}: price {pin['price']:.6f}, restated {pin['restated_price']:.6f}, "
            f"misreading spans {pin['misreading_spread']:.3f}"
        )


if __name__ == "__main__":
    main()
