"""Independent Hull GE §26.4 references from signed lognormal payoff quadrature.

No hullkit import and no BSM normal-CDF formula is used. The trigger splits
the standard-normal integration interval; the payoff is never floored at zero.
"""

import argparse
import json
import math
from pathlib import Path

from scipy.integrate import quad

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-4/reference.json"
NORMALIZER = math.sqrt(2 * math.pi)


def gap_payoff(kind, stock, K1, K2):
    if kind == "call":
        return stock - K1 if stock > K2 else 0.0
    if kind == "put":
        return K1 - stock if stock < K2 else 0.0
    raise ValueError("kind must be call or put")


def _parameters(kind, S, K1, K2, r, sigma, T, q):
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    if not all(math.isfinite(x) for x in (S, K1, K2, r, sigma, T, q)):
        raise ValueError("finite inputs required")
    if min(S, K1, K2, sigma, T) <= 0:
        raise ValueError("positive spot, strikes, sigma and maturity required")
    scale = sigma * math.sqrt(T)
    mean = math.log(S) + (r - q - sigma * sigma / 2) * T
    trigger = (math.log(K2) - mean) / scale
    bounds = (trigger, math.inf) if kind == "call" else (-math.inf, trigger)
    return mean, scale, bounds


def integrate_gap(kind, S, K1, K2, r, sigma, T, q=0.0):
    """Discount the signed terminal payoff; return value and quadrature error."""
    mean, scale, bounds = _parameters(kind, S, K1, K2, r, sigma, T, q)
    sign = 1 if kind == "call" else -1

    def weighted_payoff(z):
        density = math.exp(-z * z / 2) / NORMALIZER
        stock_density = math.exp(mean + scale * z - z * z / 2) / NORMALIZER
        return sign * (stock_density - K1 * density)

    value, error = quad(weighted_payoff, *bounds, epsabs=1e-9, epsrel=1e-12)
    discount = math.exp(-r * T)
    return value * discount, error * discount


def discounted_indicator(kind, S, K2, r, sigma, T, q=0.0):
    """Independent discounted exercise probability, also by density quadrature."""
    _, _, bounds = _parameters(kind, S, K2, K2, r, sigma, T, q)
    probability, error = quad(
        lambda z: math.exp(-z * z / 2) / NORMALIZER,
        *bounds,
        epsabs=1e-13,
        epsrel=1e-12,
    )
    return math.exp(-r * T) * probability, math.exp(-r * T) * error


def _case(label, kind, market, K1, K2):
    price, error = integrate_gap(kind, **market, K1=K1, K2=K2)
    vanilla, _ = integrate_gap(kind, **market, K1=K2, K2=K2)
    binary, _ = discounted_indicator(kind, **market, K2=K2)
    adjustment = (K2 - K1 if kind == "call" else K1 - K2) * binary
    return dict(
        label=label,
        kind=kind,
        **market,
        K1=K1,
        K2=K2,
        price=price,
        quadrature_error=error,
        vanilla=vanilla,
        cash_binary=binary,
        cash_adjustment=adjustment,
    )


def build():
    markets = [
        dict(S=100.0, r=0.05, sigma=0.2, T=1.0, q=0.0),
        dict(S=85.0, r=0.01, sigma=0.35, T=2.0, q=0.03),
        dict(S=120.0, r=-0.01, sigma=0.15, T=0.5, q=0.02),
    ]
    pairs = [(100.0, 100.0), (90.0, 110.0), (120.0, 100.0), (80.0, 100.0), (160.0, 90.0)]
    cases = [
        _case(f"market-{i}-{kind}-{j}", kind, market, K1, K2)
        for i, market in enumerate(markets)
        for j, (K1, K2) in enumerate(pairs)
        for kind in ("call", "put")
    ]
    market = dict(S=500000.0, r=0.05, sigma=0.2, T=1.0, q=0.0)
    ordinary, ordinary_error = integrate_gap("put", **market, K1=400000.0, K2=400000.0)
    insurer, insurer_error = integrate_gap("put", **market, K1=400000.0, K2=350000.0)
    holder, holder_error = integrate_gap("put", **market, K1=350000.0, K2=350000.0)
    binary, _ = discounted_indicator("put", **market, K2=350000.0)
    example = dict(
        **market,
        K1=400000.0,
        K2=350000.0,
        transfer_cost=50000.0,
        ordinary_put=ordinary,
        insurer_gap_put=insurer,
        policyholder_net_put=holder,
        discounted_transfer_cost=50000.0 * binary,
        reduction_percent=100 * (1 - insurer / ordinary),
        printed={"ordinary_put": 3436, "insurer_gap_put": 1896, "reduction_percent_approx": 45},
        quadrature_error=max(ordinary_error, insurer_error, holder_error),
        terminal_hand_check=[
            {
                "asset": x,
                "insurer": gap_payoff("put", x, 400000, 350000),
                "transfer_cost": 50000 if x < 350000 else 0,
                "holder_net": gap_payoff("put", x, 350000, 350000),
            }
            for x in (340000, 350000, 360000)
        ],
    )
    payoff_x = list(range(60, 141, 2))
    payoff = dict(
        stock=payoff_x,
        trigger=100,
        call_strike=120,
        put_strike=80,
        call=[gap_payoff("call", x, 120, 100) for x in payoff_x],
        put=[gap_payoff("put", x, 80, 100) for x in payoff_x],
    )
    decomposition = [
        _case(f"call-K1-{K1}", "call", markets[0], float(K1), 100.0) for K1 in range(60, 161, 5)
    ]
    insurance_x = list(range(250000, 450001, 5000))
    insurance = dict(
        stock=insurance_x,
        trigger=350000,
        ordinary=[max(400000 - x, 0) for x in insurance_x],
        insurer=[gap_payoff("put", x, 400000, 350000) for x in insurance_x],
        holder=[gap_payoff("put", x, 350000, 350000) for x in insurance_x],
    )
    premium = []
    for cost in range(0, 100001, 5000):
        K2 = 400000 - cost
        ins, error = integrate_gap("put", **market, K1=400000.0, K2=K2)
        net, _ = integrate_gap("put", **market, K1=K2, K2=K2)
        cash, _ = discounted_indicator("put", **market, K2=K2)
        premium.append(
            dict(
                cost=cost,
                trigger=K2,
                insurer=ins,
                holder=net,
                transfer=cost * cash,
                quadrature_error=error,
            )
        )
    return dict(
        section="26.4",
        source="Hull 11e Global Edition p.617",
        method="discounted signed payoff integrated against lognormal density, split at trigger",
        note="Example26.1 uses printed market inputs; other markets and figure curves are synthetic.",
        cases=cases,
        example=example,
        figure=dict(
            payoff=payoff, decomposition=decomposition, insurance=insurance, premium=premium
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("missing or stale §26.4 independent reference")
        print("PASS: §26.4 independent payoff quadrature and Example26.1")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
