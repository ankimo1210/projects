"""Hull GE §26.5 references from two independent GBM increments, without hullkit/CDF."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-5/reference.json"
NORMALIZER = math.sqrt(2 * math.pi)
MC_PATHS = 524288


def integrate_forward_start(S, r, sigma, T1, T2, q=0.0):
    """Discount the two-time payoff at T2; return value and quadrature error.

    Independence factorizes the two-dimensional density integral. Both
    factors are integrated numerically; no BSM formula or normal CDF is used.
    """
    if not all(math.isfinite(x) for x in (S, r, sigma, T1, T2, q)):
        raise ValueError("finite inputs required")
    if S <= 0 or sigma < 0 or T1 < 0 or T2 < T1:
        raise ValueError("require S>0, sigma>=0, 0<=T1<=T2")
    tau = T2 - T1
    if tau == 0:
        return 0.0, 0.0
    if sigma == 0:
        return S * math.exp((r - q) * T1 - r * T2) * max(math.expm1((r - q) * tau), 0), 0.0
    drift1, drift2 = ((r - q - sigma * sigma / 2) * t for t in (T1, tau))
    scale1, scale2 = (sigma * math.sqrt(t) for t in (T1, tau))
    first, error1 = quad(
        lambda z: math.exp(drift1 + scale1 * z - z * z / 2) / NORMALIZER,
        -math.inf,
        math.inf,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    trigger = -drift2 / scale2
    second, error2 = quad(
        lambda z: (math.exp(drift2 + scale2 * z - z * z / 2) - math.exp(-z * z / 2)) / NORMALIZER,
        trigger,
        math.inf,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    discount = S * math.exp(-r * T2)
    error = discount * (abs(second) * error1 + abs(first) * error2 + error1 * error2)
    return discount * first * second, error


def _case(label, market):
    price, error = integrate_forward_start(**market)
    return dict(label=label, **market, price=price, quadrature_error=error)


def _mc(market, seed):
    random = np.random.default_rng(seed).standard_normal((MC_PATHS, 2))
    S, r, q, sigma, T1, T2 = (market[k] for k in ("S", "r", "q", "sigma", "T1", "T2"))
    drift = r - q - sigma * sigma / 2
    fixing = S * np.exp(drift * T1 + sigma * math.sqrt(T1) * random[:, 0])
    terminal = fixing * np.exp(drift * (T2 - T1) + sigma * math.sqrt(T2 - T1) * random[:, 1])
    discounted = np.maximum(terminal - fixing, 0) * math.exp(-r * T2)
    price = float(discounted.mean())
    se = float(discounted.std(ddof=1) / math.sqrt(MC_PATHS))
    reference, error = integrate_forward_start(**market)
    return dict(
        **market,
        seed=seed,
        paths=MC_PATHS,
        price=price,
        standard_error=se,
        ci95=[price - 1.959963984540054 * se, price + 1.959963984540054 * se],
        reference_price=reference,
        quadrature_error=error,
        payoff="max(S(T2)-S(T1),0), paid at T2",
    )


def _contract(market):
    T1, T2 = market["T1"], market["T2"]
    time = np.r_[np.linspace(0, T1, 16), np.linspace(T1, T2, 21)[1:]]
    rng = np.random.default_rng(260518)
    increments = rng.standard_normal((12, len(time) - 1))
    dt = np.diff(time)
    growth = (market["r"] - market["q"] - market["sigma"] ** 2 / 2) * dt + market[
        "sigma"
    ] * np.sqrt(dt) * increments
    stock = market["S"] * np.exp(np.c_[np.zeros(12), np.cumsum(growth, axis=1)])
    strike = stock[:, 15]
    winners = np.flatnonzero(stock[:, -1] > strike)
    losers = np.flatnonzero(stock[:, -1] <= strike)
    selected = [int(winners[0]), int(losers[0]), int(winners[1])]
    return dict(
        market=market,
        time=time.tolist(),
        selection="three illustrative paths, including positive and zero payoff",
        paths=[
            dict(
                label=label,
                stock=stock[i].tolist(),
                strike=float(strike[i]),
                payoff=max(float(stock[i, -1] - strike[i]), 0),
            )
            for label, i in zip(("A", "B", "C"), selected, strict=True)
        ],
    )


def build():
    markets = [
        dict(S=100.0, r=0.05, sigma=0.2, q=0.0),
        dict(S=100.0, r=0.05, sigma=0.2, q=0.03),
        dict(S=85.0, r=-0.01, sigma=0.35, q=0.06),
        dict(S=100.0, r=0.05, sigma=0.0, q=0.02),
        dict(S=100.0, r=0.01, sigma=0.0, q=0.05),
        dict(S=120.0, r=0.01, sigma=0.15, q=-0.02),
    ]
    times = [(0.0, 1.0), (0.25, 1.25), (1.0, 2.0), (2.0, 3.0), (1.0, 1.0), (0.25, 2.0)]
    cases = [
        _case(f"market-{i}-times-{j}", dict(**market, T1=start, T2=end))
        for i, market in enumerate(markets)
        for j, (start, end) in enumerate(times)
    ]
    market = dict(S=100.0, r=0.05, sigma=0.2, q=0.03, T1=1.0, T2=2.0)
    example = _case("synthetic-example", market)
    example["same_life_atm"], _ = integrate_forward_start(**{**market, "T1": 0.0, "T2": 1.0})
    mc = [_mc({**market, "T1": start}, 260500 + i) for i, start in enumerate((0.0, 1.0, 1.75))]
    spots = list(range(50, 151, 10))
    homogeneity = dict(
        spot=spots,
        price=[integrate_forward_start(s, 0.05, 0.2, 0, 1, 0.03)[0] for s in spots],
        market=dict(S=100.0, r=0.05, sigma=0.2, q=0.03, T1=0.0, T2=1.0),
    )
    delay, fixed = [], []
    for q in (0.0, 0.03, 0.06):
        start = np.linspace(0, 3, 13).tolist()
        delay.append(
            dict(
                q=q,
                start=start,
                tenor=1.0,
                price=[integrate_forward_start(100, 0.05, 0.2, t, t + 1, q)[0] for t in start],
            )
        )
        start = np.linspace(0, 2, 17).tolist()
        fixed.append(
            dict(
                q=q,
                start=start,
                expiry=2.0,
                price=[integrate_forward_start(100, 0.05, 0.2, t, 2, q)[0] for t in start],
            )
        )
    return dict(
        section="26.5",
        source="Hull GE p.618; no printed numeric example",
        cases=cases,
        example=example,
        mc=mc,
        figure=dict(
            contract=_contract({**market, "T1": 0.75, "T2": 1.75}),
            homogeneity=homogeneity,
            delay=delay,
            fixed_expiry=fixed,
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("forward-start reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.5 independent two-increment integral and Monte Carlo")


if __name__ == "__main__":
    main()
