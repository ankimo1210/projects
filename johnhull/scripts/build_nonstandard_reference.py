"""Independent §26.3 stopping-time reference, without importing hullkit.

Two independent constructions are used: full binary path enumeration for
small contracts and scalar recombining backward induction for longer ones.
All exercise dates are integer steps on the stated CRR grid.
"""

import argparse
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-3/reference.json"


def _parameters(r, sigma, maturity, steps, q):
    dt = maturity / steps
    up = math.exp(sigma * math.sqrt(dt))
    down = 1.0 / up
    probability = (math.exp((r - q) * dt) - down) / (up - down)
    if not 0.0 < probability < 1.0:
        raise ValueError("CRR probability must be inside (0, 1)")
    return up, down, probability, math.exp(-r * dt)


def _payoff(kind, stock, strike):
    if kind == "call":
        return max(stock - strike, 0.0)
    if kind == "put":
        return max(strike - stock, 0.0)
    raise ValueError("kind must be call or put")


def exhaustive_price(kind, spot, r, sigma, maturity, steps, exercise_strikes, q=0.0):
    """Enumerate every up/down path; the same stock node is not merged."""
    if steps > 12:
        raise ValueError("full path enumeration is limited to 12 steps")
    up, down, probability, discount = _parameters(r, sigma, maturity, steps, q)

    def stop(step, stock):
        if step == steps:
            return _payoff(kind, stock, exercise_strikes[steps])
        continuation = discount * (
            probability * stop(step + 1, stock * up)
            + (1.0 - probability) * stop(step + 1, stock * down)
        )
        if step in exercise_strikes:
            return max(continuation, _payoff(kind, stock, exercise_strikes[step]))
        return continuation

    return stop(0, spot)


def scalar_tree_price(kind, spot, r, sigma, maturity, steps, exercise_strikes, q=0.0):
    """Scalar list rollback, independent of hullkit's vectorized tree."""
    up, down, probability, discount = _parameters(r, sigma, maturity, steps, q)
    value = [
        _payoff(kind, spot * up ** (steps - j) * down**j, exercise_strikes[steps])
        for j in range(steps + 1)
    ]
    for step in range(steps - 1, -1, -1):
        updated = []
        for j in range(step + 1):
            continuation = discount * (probability * value[j] + (1.0 - probability) * value[j + 1])
            if step in exercise_strikes:
                stock = spot * up ** (step - j) * down**j
                continuation = max(continuation, _payoff(kind, stock, exercise_strikes[step]))
            updated.append(continuation)
        value = updated
    return value[0]


def exercise_lattice(kind, spot, r, sigma, maturity, steps, exercise_strikes, q=0.0):
    """List allowed nodes and strict early-exercise choices for a small tree."""
    up, down, probability, discount = _parameters(r, sigma, maturity, steps, q)
    value = [
        _payoff(kind, spot * up ** (steps - j) * down**j, exercise_strikes[steps])
        for j in range(steps + 1)
    ]
    candidates = [
        {"step": steps, "stock": spot * up ** (steps - j) * down**j} for j in range(steps + 1)
    ]
    points = [row for row in candidates if _payoff(kind, row["stock"], exercise_strikes[steps]) > 0]
    for step in range(steps - 1, -1, -1):
        updated = []
        for j in range(step + 1):
            stock = spot * up ** (step - j) * down**j
            continuation = discount * (probability * value[j] + (1.0 - probability) * value[j + 1])
            if step in exercise_strikes:
                candidates.append({"step": step, "stock": stock})
                intrinsic = _payoff(kind, stock, exercise_strikes[step])
                if intrinsic > continuation and intrinsic > 0.0:
                    points.append({"step": step, "stock": stock})
                continuation = max(continuation, intrinsic)
            updated.append(continuation)
        value = updated
    return {
        "allowed_steps": sorted(exercise_strikes),
        "candidates": sorted(candidates, key=lambda row: (row["step"], row["stock"])),
        "points": sorted(points, key=lambda row: (row["step"], row["stock"])),
    }


def _row(label, kind, market, schedule):
    price = scalar_tree_price(kind, **market, exercise_strikes=schedule)
    return {
        "label": label,
        "kind": kind,
        **market,
        "exercise_strikes": {str(i): float(k) for i, k in sorted(schedule.items())},
        "price": price,
    }


def build():
    """Save hand-checkable examples, ordering cases, and Hull's contract dates."""
    small = dict(spot=100.0, r=math.log(1.1), sigma=math.log(2.0), maturity=2.0, steps=2, q=0.0)
    small_schedules = (
        ("european_put", {2: 100.0}),
        ("bermudan_put", {1: 100.0, 2: 100.0}),
        ("american_put", {0: 100.0, 1: 100.0, 2: 100.0}),
        ("low_early_strike", {1: 90.0, 2: 100.0}),
        ("high_early_strike", {1: 120.0, 2: 100.0}),
    )
    small_rows = [_row(label, "put", small, schedule) for label, schedule in small_schedules]
    for row in small_rows:
        schedule = {int(i): k for i, k in row["exercise_strikes"].items()}
        full = exhaustive_price("put", **small, exercise_strikes=schedule)
        if abs(row["price"] - full) > 1e-12:
            raise AssertionError(f"full path enumeration differs: {row['label']}")
        row["exhaustive_price"] = full

    market = dict(spot=100.0, r=0.05, sigma=0.25, maturity=1.0, steps=50, q=0.02)
    base = {50: 100.0}
    cases = [
        _row("european", "put", market, base),
        _row("bermudan_quarterly", "put", market, {10: 100, 20: 100, 30: 100, 40: 100, 50: 100}),
        _row("lockout_half_year", "put", market, {i: 100 for i in range(25, 51)}),
        _row("american", "put", market, {i: 100 for i in range(51)}),
        _row("rising_strike", "put", market, {10: 96, 20: 98, 30: 100, 40: 102, 50: 104}),
    ]
    prices = {row["label"]: row["price"] for row in cases}
    if not prices["european"] <= prices["bermudan_quarterly"] <= prices["american"]:
        raise AssertionError("European <= Bermudan <= American failed")
    if not prices["european"] <= prices["lockout_half_year"] <= prices["american"]:
        raise AssertionError("European <= lockout <= American failed")

    # Hull p.616 gives contractual years and strikes, not market inputs or a price.
    # The annual exercise dates and market below are explicitly synthetic.
    warrant_market = dict(spot=30.0, r=0.04, sigma=0.25, maturity=7.0, steps=70, q=0.01)
    warrant = _row(
        "synthetic_seven_year_warrant",
        "call",
        warrant_market,
        {30: 30, 40: 30, 50: 32, 60: 32, 70: 33},
    )
    frequency_market = {**market, "steps": 64}
    date_counts = [1, 2, 4, 8, 16, 64]
    frequency_prices = [
        scalar_tree_price(
            "put",
            **frequency_market,
            exercise_strikes={step: 100.0 for step in range(64 // count, 65, 64 // count)},
        )
        for count in date_counts
    ]
    lattice_market = {**market, "steps": 20}
    lattice = exercise_lattice(
        "put", **lattice_market, exercise_strikes={step: 100.0 for step in (4, 8, 12, 16, 20)}
    )
    return {
        "section": "26.3",
        "source": "Hull 11e Global Edition p.616",
        "note": "The seven-year contract years and strikes are from Hull; all market inputs, exercise dates within those years, and prices are synthetic.",
        "small_hand_check": small_rows,
        "cases": cases,
        "warrant": warrant,
        "figure": {
            "exercise_frequency": {
                "date_counts": date_counts,
                "prices": frequency_prices,
                "market": frequency_market,
            },
            "exercise_lattice": lattice,
            "warrant_years": [3, 4, 5, 6, 7],
            "warrant_strikes": [30, 30, 32, 32, 33],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("missing or stale §26.3 independent reference")
        print("PASS: §26.3 full-path and scalar reference")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(expected, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
