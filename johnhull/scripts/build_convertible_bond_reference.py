"""Independent recursive reference for Hull GE §27.4, Example 27.1.

No hullkit imports. The production implementation rolls back arrays; this
reference recursively prices each state and checks the printed Figure 27.2.
"""

import argparse
import json
import math
from functools import cache
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-27-4/reference.json"
PARAMETERS = {
    "spot": 50.0,
    "face": 100.0,
    "conversion_ratio": 2.0,
    "call_price": 113.0,
    "rate": 0.05,
    "dividend_yield": 0.0,
    "volatility": 0.3,
    "hazard_rate": 0.01,
    "recovery_value": 40.0,
    "maturity": 0.75,
    "steps": 3,
}
NODES = {
    "A": (0, 0, 50.00, 107.44),
    "B": (1, 1, 58.09, 116.18),
    "C": (1, 0, 43.04, 101.37),
    "D": (2, 2, 67.49, 134.99),
    "E": (2, 1, 50.00, 106.78),
    "F": (2, 0, 37.04, 98.61),
    "G": (3, 3, 78.42, 156.83),
    "H": (3, 2, 58.09, 116.18),
    "I": (3, 1, 43.04, 100.00),
    "J": (3, 0, 31.88, 100.00),
}


def recursive_tree(**terms):
    """Enumerate each node through memoized state recursion, separately from hullkit."""
    spot = terms["spot"]
    face = terms["face"]
    ratio = terms["conversion_ratio"]
    call = terms["call_price"]
    rate = terms["rate"]
    dividend = terms["dividend_yield"]
    volatility = terms["volatility"]
    hazard = terms["hazard_rate"]
    recovery = terms["recovery_value"]
    maturity = terms["maturity"]
    steps = terms["steps"]
    coupon = terms.get("coupon_amount", 0.0)
    dt = maturity / steps
    up_factor = math.exp(volatility * math.sqrt(dt))
    down_factor = math.exp(-volatility * math.sqrt(dt))
    survive = math.exp(-hazard * dt)
    default = 1 - survive
    expected_stock = math.exp((rate - dividend) * dt)
    up_probability = (expected_stock - down_factor * survive) / (up_factor - down_factor)
    down_probability = survive - up_probability
    if min(up_probability, down_probability) < 0:
        raise ValueError("invalid risk-neutral probability")
    discount = math.exp(-rate * dt)

    @cache
    def node(time, up_count):
        stock = spot * up_factor**up_count * down_factor ** (time - up_count)
        conversion = ratio * stock
        if time == steps:
            return {
                "stock": stock,
                "value": max(face, conversion),
                "continuation": None,
                "decision": "convert" if conversion > face else "redeem",
            }
        child_up = node(time + 1, up_count + 1)["value"]
        child_down = node(time + 1, up_count)["value"]
        continuation = discount * (
            up_probability * (child_up + coupon)
            + down_probability * (child_down + coupon)
            + default * recovery
        )
        holder = max(continuation, conversion)
        if call is not None and holder > max(call, conversion):
            decision = "call-convert" if conversion > call else "call-redeem"
            value = max(call, conversion)
        else:
            decision = "convert" if conversion > continuation else "hold"
            value = holder
        return {"stock": stock, "value": value, "continuation": continuation, "decision": decision}

    return {
        "price": node(0, 0)["value"],
        "nodes": {name: node(time, up) for name, (time, up, _, _) in NODES.items()}
        if steps == 3
        else {},
        "probabilities": {"up": up_probability, "down": down_probability, "default": default},
    }


def build():
    """Build checked textbook nodes, contract scenarios and grid convergence."""
    textbook = recursive_tree(**PARAMETERS)
    for name, (_, _, printed_stock, printed_value) in NODES.items():
        node = textbook["nodes"][name]
        if abs(node["stock"] - printed_stock) > 0.005 or abs(node["value"] - printed_value) > 0.005:
            raise ValueError(f"printed Figure 27.2 mismatch at {name}: {node}")
    for name, printed in {"B": 119.54, "D": 135.08, "E": 106.78}.items():
        if abs(textbook["nodes"][name]["continuation"] - printed) > 0.015:
            raise ValueError(f"printed continuation mismatch at {name}")
    credit = [
        {
            "hazard_rate": hazard,
            "price": recursive_tree(**dict(PARAMETERS, hazard_rate=hazard))["price"],
        }
        for hazard in (0, 0.005, 0.01, 0.02, 0.04)
    ]
    recovery = [
        {
            "recovery_value": value,
            "price": recursive_tree(**dict(PARAMETERS, recovery_value=value))["price"],
        }
        for value in (0, 20, 40, 60, 80)
    ]
    calls = [
        {
            "call_price": value,
            "price": recursive_tree(**dict(PARAMETERS, call_price=value))["price"],
        }
        for value in (105.0, 113.0, 125.0, None)
    ]
    convergence = [
        {"steps": steps, "price": recursive_tree(**dict(PARAMETERS, steps=steps))["price"]}
        for steps in (3, 6, 12, 24, 48, 96)
    ]
    return {
        "section": "27.4",
        "source": "Hull 11e Global Edition pp.650–653, Example 27.1 and Figure 27.2",
        "units": "stock, bond, face, call, coupon and recovery in dollars; maturity in years; rates and volatility annual decimals",
        "parameters": PARAMETERS,
        "textbook": textbook,
        "scenarios": {
            "credit": credit,
            "recovery": recovery,
            "call": calls,
            "convergence": convergence,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §27.4 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §27.4 independent recursion matches Figure 27.2")


if __name__ == "__main__":
    main()
