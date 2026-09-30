"""Hull GE §26.6: independent GBM density integrals and multitime cashflows."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-26-6/reference.json"
MC_PATHS = 524288
NORMALIZER = math.sqrt(2 * math.pi)
Z95 = 1.959963984540054


def integrate_period(S, r, sigma, T1, T2, q=0.0, kind="call"):
    """Two independent GBM increments; cashflow discounted from T2.

    No hullkit, BSM formula or normal CDF. Both density factors are integrated
    numerically. Return price and the propagated absolute quadrature error.
    """
    if not all(math.isfinite(x) for x in (S, r, sigma, T1, T2, q)):
        raise ValueError("finite inputs required")
    if S <= 0 or sigma < 0 or T1 < 0 or T2 < T1 or kind not in ("call", "put"):
        raise ValueError("invalid period or option kind")
    tau, sign = T2 - T1, 1 if kind == "call" else -1
    if tau == 0:
        return 0.0, 0.0
    if sigma == 0:
        return S * math.exp((r - q) * T1 - r * T2) * max(sign * math.expm1((r - q) * tau), 0), 0.0
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
    lower, upper = (trigger, math.inf) if kind == "call" else (-math.inf, trigger)
    second, error2 = quad(
        lambda z: (
            sign * (math.exp(drift2 + scale2 * z - z * z / 2) - math.exp(-z * z / 2)) / NORMALIZER
        ),
        lower,
        upper,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    discount = S * math.exp(-r * T2)
    error = discount * (abs(second) * error1 + abs(first) * error2 + error1 * error2)
    return discount * first * second, error


def integrate_cliquet(S, r, sigma, payment_times, q=0.0, kind="call"):
    dates = np.asarray(payment_times, dtype=float)
    if (
        dates.ndim != 1
        or not dates.size
        or np.any(~np.isfinite(dates))
        or np.any(dates <= 0)
        or np.any(np.diff(dates) <= 0)
    ):
        raise ValueError("positive increasing 1D payment schedule required")
    legs = [
        integrate_period(S, r, sigma, start, end, q, kind)
        for start, end in zip(np.r_[0, dates[:-1]], dates, strict=True)
    ]
    return sum(row[0] for row in legs), sum(row[1] for row in legs), [row[0] for row in legs]


def _case(label, market, dates, kind):
    price, error, components = integrate_cliquet(**market, payment_times=dates, kind=kind)
    return dict(
        label=label,
        **market,
        payment_times=dates,
        kind=kind,
        price=price,
        quadrature_error=error,
        components=components,
    )


def _stocks(market, dates, paths, seed):
    dt = np.diff([0, *dates])
    random = np.random.default_rng(seed).standard_normal((paths, len(dates)))
    growth = (market["r"] - market["q"] - market["sigma"] ** 2 / 2) * dt + market[
        "sigma"
    ] * np.sqrt(dt) * random
    return market["S"] * np.exp(np.c_[np.zeros(paths), np.cumsum(growth, axis=1)])


def _summary(values):
    price = float(values.mean())
    se = float(values.std(ddof=1) / math.sqrt(len(values)))
    return dict(price=price, standard_error=se, ci95=[price - Z95 * se, price + Z95 * se])


def _mc(market, dates, kind, seed):
    stock = _stocks(market, dates, MC_PATHS, seed)
    sign = 1 if kind == "call" else -1
    cashflows = np.maximum(sign * np.diff(stock, axis=1), 0) * np.exp(
        -market["r"] * np.array(dates)
    )
    reference, error, _ = integrate_cliquet(**market, payment_times=dates, kind=kind)
    return dict(
        **market,
        payment_times=dates,
        kind=kind,
        seed=seed,
        paths=MC_PATHS,
        **_summary(cashflows.sum(axis=1)),
        components=cashflows.mean(axis=0).tolist(),
        reference_price=reference,
        quadrature_error=error,
        payoff="stock-price differences; random previous fixing strike; paid at each t_i",
    )


def _complex():
    market = dict(S=100.0, r=0.0, sigma=0.2, q=0.0)
    dates = [0.5, 1.0, 1.5, 2.0]
    stock = _stocks(market, dates, MC_PATHS, 260699)
    flows = np.maximum(np.diff(stock, axis=1), 0)
    total = flows.sum(axis=1)
    stopped = (stock[:, 1:] >= 95) & (stock[:, 1:] <= 105)
    # Pay the current period before testing termination; stop only later legs.
    live = np.c_[np.ones(MC_PATHS, dtype=bool), np.cumsum(stopped, axis=1)[:, :-1] == 0]
    values = [
        total,
        np.clip(total, 5, 20),
        np.minimum(flows, 5).sum(axis=1),
        (flows * live).sum(axis=1),
    ]
    contracts = [
        dict(key=key, label=label, **_summary(value))
        for key, label, value in zip(
            ("simple", "global", "local", "termination"),
            ("単純和", "総額 floor 5 / cap 20", "各期 cap 5", "95–105で期末終了"),
            values,
            strict=True,
        )
    ]
    reference, error, _ = integrate_cliquet(**market, payment_times=dates)
    return dict(
        market=market,
        payment_times=dates,
        paths=MC_PATHS,
        seed=260699,
        global_floor=5,
        global_cap=20,
        local_cap=5,
        termination_range=[95, 105],
        settlement="r=q=0; current payment precedes termination; global bound applies to total",
        contracts=contracts,
        reference_price=reference,
        quadrature_error=error,
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
    schedules = [[2.0], [1.0, 2.0], [0.5, 1.0, 1.5, 2.0], [0.2, 0.7, 1.4, 2.0], [0.01, 0.5, 2.0]]
    market, dates = markets[1], schedules[2]
    cases = [
        _case(f"market-{i}-schedule-{j}-{kind}", row, schedule, kind)
        for i, row in enumerate(markets)
        for j, schedule in enumerate(schedules)
        for kind in ("call", "put")
    ]
    example = {kind: _case("synthetic-example", market, dates, kind) for kind in ("call", "put")}
    mc = [
        _mc(market, schedule, kind, 260600 + i * 2 + j)
        for i, schedule in enumerate(schedules[2:4])
        for j, kind in enumerate(("call", "put"))
    ]
    stock = _stocks(market, dates, 1, 260618)[0]
    reset = dict(
        market=market,
        time=[0, *dates],
        stock=stock.tolist(),
        strikes=stock[:-1].tolist(),
        call_payoffs=np.maximum(np.diff(stock), 0).tolist(),
        put_payoffs=np.maximum(-np.diff(stock), 0).tolist(),
        seed=260618,
        selection="one illustrative GBM path; not an expectation",
    )
    frequency = dict(market=market, expiry=2.0, periods=[1, 2, 4, 8, 12, 24])
    for kind in ("call", "put"):
        frequency[kind] = [
            integrate_cliquet(**market, payment_times=np.linspace(2 / n, 2, n), kind=kind)[0]
            for n in frequency["periods"]
        ]
    return dict(
        section="26.6",
        source="Hull GE p.618; no printed numeric example",
        cases=cases,
        example=example,
        mc=mc,
        complex=_complex(),
        figure=dict(reset=reset, frequency=frequency),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("cliquet reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.6 independent density integrals and multitime Monte Carlo")


if __name__ == "__main__":
    main()
