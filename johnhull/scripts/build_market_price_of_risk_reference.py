"""Independent real-world quadrature of growth and loading, without hullkit (§28.1)."""

import argparse
import functools
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.hermite_e import hermegauss

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-1/reference.json"
MARKET = dict(S=100.0, r=0.05, sigma=0.2, mu=0.12)
NEGATIVE = dict(S=100.0, r=0.05, sigma=0.3, mu=0.02)
KINDS = ("call", "put", "cash_call", "cash_put", "asset_call", "asset_put")
CONTRACTS = ((90.0, 0.25), (100.0, 1.0), (120.0, 2.0))
STEPS = (2e-3, 1e-3, 5e-4)
MC_PATHS = 524288
MC_SEED = 281
_NODES, _WEIGHTS = hermegauss(120)
_WEIGHTS = _WEIGHTS / _WEIGHTS.sum()


def _n(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def price(kind, s, k, r, sigma, t):
    """Own erfc risk-neutral value of a non-income claim on a non-dividend asset."""
    if kind == "stock":
        return s
    v = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r + sigma * sigma / 2) * t) / v
    d2 = d1 - v
    df = math.exp(-r * t)
    return {
        "call": s * _n(d1) - k * df * _n(d2),
        "put": k * df * _n(-d2) - s * _n(-d1),
        "cash_call": df * _n(d2),
        "cash_put": df * _n(-d2),
        "asset_call": s * _n(d1),
        "asset_put": s * _n(-d1),
    }[kind]


def _moments(value, s, sigma, drift, h, t):
    """E[f_h]/f_0 - 1 and E[(f_h - f_0) Z]/f_0 under ln S_h ~ N(ln s + (drift-σ²/2)h, σ²h)."""
    f0 = value(s, t)
    sh = s * np.exp((drift - sigma * sigma / 2) * h + sigma * math.sqrt(h) * _NODES)
    fh = np.array([value(x, t - h) for x in sh])
    return float(_WEIGHTS @ fh) / f0 - 1, float(_WEIGHTS @ ((fh - f0) * _NODES)) / f0


def growth_and_loading(value, s, sigma, drift, t):
    """Second-order Richardson limit of the one-step real-world mean and Z-covariance."""
    g, z = [], []
    for h in STEPS:
        mean, cov = _moments(value, s, sigma, drift, h, t)
        g.append(mean / h)
        z.append(cov / math.sqrt(h))
    return (8 * g[2] - 6 * g[1] + g[0]) / 3, (8 * z[2] - 6 * z[1] + z[0]) / 3


def _contract(kind, k, t, m):
    def value(x, tau):
        return price(kind, x, k, m["r"], m["sigma"], tau)

    growth, loading = growth_and_loading(value, m["S"], m["sigma"], m["mu"], t)
    return dict(
        kind=kind,
        K=k,
        T=t,
        **m,
        price=value(m["S"], t),
        growth=growth,
        loading=loading,
        implied_lambda=(growth - m["r"]) / loading,
    )


def _contracts(m):
    rows = [_contract("stock", m["S"], 1.0, m)]
    rows += [_contract(kind, k, t, m) for kind in KINDS for k, t in CONTRACTS]
    return rows


def _riskless(m):
    """Two claims on S: hold s2*f2 of f1 and -s1*f1 of f2, then measure ΔΠ."""
    rows = []
    for (a, ka, ta), (b, kb, tb) in (
        (("call", 100.0, 1.0), ("put", 100.0, 1.0)),
        (("cash_call", 90.0, 0.25), ("asset_put", 120.0, 2.0)),
    ):
        one, two = _contract(a, ka, ta, m), _contract(b, kb, tb, m)
        n1 = two["loading"] * two["price"]
        # Solve n1*s1*f1 + n2*s2*f2 = 0 for n2 rather than quoting eq. 28.4.
        n2 = -n1 * one["loading"] * one["price"] / (two["loading"] * two["price"])
        pi0 = n1 * one["price"] + n2 * two["price"]

        def portfolio(x, tau, one=one, two=two, n1=n1, n2=n2):
            return n1 * price(one["kind"], x, one["K"], m["r"], m["sigma"], one["T"] - tau) + (
                n2 * price(two["kind"], x, two["K"], m["r"], m["sigma"], two["T"] - tau)
            )

        steps, growth, ratio = [0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001], [], []
        for h in steps:
            sh = m["S"] * np.exp(
                (m["mu"] - m["sigma"] ** 2 / 2) * h + m["sigma"] * math.sqrt(h) * _NODES
            )
            # Elapsed time is passed as tau, so each claim's remaining life is T - h.
            d_pi = np.array([portfolio(x, h) for x in sh]) - pi0
            d_one = n1 * (
                np.array(
                    [price(one["kind"], x, one["K"], m["r"], m["sigma"], one["T"] - h) for x in sh]
                )
                - one["price"]
            )
            mean = float(_WEIGHTS @ d_pi)
            growth.append(mean / (pi0 * h))
            ratio.append(
                math.sqrt(float(_WEIGHTS @ (d_pi - mean) ** 2))
                / math.sqrt(float(_WEIGHTS @ (d_one - _WEIGHTS @ d_one) ** 2))
            )

        g = []
        for h in STEPS:
            sh = m["S"] * np.exp(
                (m["mu"] - m["sigma"] ** 2 / 2) * h + m["sigma"] * math.sqrt(h) * _NODES
            )
            g.append(float(_WEIGHTS @ (np.array([portfolio(x, h) for x in sh]) - pi0)) / (pi0 * h))
        rows.append(
            dict(
                first=one,
                second=two,
                units=[n1, n2],
                value=pi0,
                instantaneous_growth=(8 * g[2] - 6 * g[1] + g[0]) / 3,
                diffusion=n1 * one["loading"] * one["price"] + n2 * two["loading"] * two["price"],
                steps=steps,
                step_growth=growth,
                residual_std_ratio=ratio,
            )
        )
    return rows


def _worlds():
    """Same claims under several lambdas: growth r + λs, loading unchanged (eq. 28.10)."""
    rows = []
    for lam in (-0.3, 0.0, 0.2, 0.35, 0.6):
        m = {**MARKET, "mu": MARKET["r"] + lam * MARKET["sigma"]}
        for kind, k, t in (("stock", 100.0, 1.0), ("call", 100.0, 1.0), ("put", 100.0, 1.0)):
            rows.append(dict(world_lambda=lam, **_contract(kind, k, t, m)))
    return rows


def _consumption():
    """Ex. 28.1 caveat: a call on oil with net convenience yield y, synthetic inputs."""
    r, y, s_u, lam = 0.08, 0.05, 0.3, 0.2
    m_u = r - y + lam * s_u

    def value(x, tau):
        # Risk-neutral oil drift r - y: e^{-rτ}E[(S_T-K)^+] with forward x e^{(r-y)τ}.
        v = s_u * math.sqrt(tau)
        d1 = (math.log(x / 100.0) + (r - y + s_u * s_u / 2) * tau) / v
        return x * math.exp(-y * tau) * _n(d1) - 100.0 * math.exp(-r * tau) * _n(d1 - v)

    growth, loading = growth_and_loading(value, 100.0, s_u, m_u, 1.0)
    return dict(
        r=r,
        convenience_yield=y,
        spot_volatility=s_u,
        market_price_of_risk=lam,
        spot_growth=m_u,
        naive_spot_lambda=(m_u - r) / s_u,
        derivative=dict(kind="call", K=100.0, T=1.0, growth=growth, loading=loading),
        derivative_lambda=(growth - r) / loading,
    )


def _mc():
    """Sample S_T under P, reweight to other worlds, and sample each world directly."""
    rng = np.random.default_rng(MC_SEED)
    m, t = MARKET, 1.0
    lam_p = (m["mu"] - m["r"]) / m["sigma"]
    w_p = rng.standard_normal(MC_PATHS) * math.sqrt(t)
    s_p = m["S"] * np.exp((m["mu"] - m["sigma"] ** 2 / 2) * t + m["sigma"] * w_p)
    rows = []
    for lam in (-0.3, 0.0, 0.35, 0.6):
        drift = m["r"] + lam * m["sigma"]
        theta = lam_p - lam
        weight = np.exp(-theta * w_p - theta * theta * t / 2)
        reweighted = weight * s_p
        z = rng.standard_normal(MC_PATHS)
        log_direct = (drift - m["sigma"] ** 2 / 2) * t + m["sigma"] * math.sqrt(t) * z
        direct = m["S"] * np.exp(log_direct)
        log_std = float(log_direct.std(ddof=1))
        rows.append(
            dict(
                world_lambda=lam,
                drift=drift,
                analytic_mean=m["S"] * math.exp(drift * t),
                direct_mean=float(direct.mean()),
                direct_se=float(direct.std(ddof=1) / math.sqrt(MC_PATHS)),
                reweighted_mean=float(reweighted.mean()),
                reweighted_se=float(reweighted.std(ddof=1) / math.sqrt(MC_PATHS)),
                weight_mean=float(weight.mean()),
                weight_se=float(weight.std(ddof=1) / math.sqrt(MC_PATHS)),
                log_std=log_std,
                log_std_se=log_std / math.sqrt(2 * (MC_PATHS - 1)),
                analytic_log_std=m["sigma"] * math.sqrt(t),
                paths=MC_PATHS,
                seed=MC_SEED,
                T=t,
            )
        )
    disc = (
        np.exp(-m["r"] * t)
        * np.maximum(s_p - 100.0, 0.0)
        * np.exp(-lam_p * w_p - lam_p * lam_p * t / 2)
    )
    call = dict(
        K=100.0,
        T=t,
        reweighted_price=float(disc.mean()),
        standard_error=float(disc.std(ddof=1) / math.sqrt(MC_PATHS)),
        reference_price=price("call", m["S"], 100.0, m["r"], m["sigma"], t),
    )
    return dict(worlds=rows, risk_neutral_call=call)


def _density(lam, grid):
    m, t = MARKET, 1.0
    mean = math.log(m["S"]) + (m["r"] + lam * m["sigma"] - m["sigma"] ** 2 / 2) * t
    sd = m["sigma"] * math.sqrt(t)
    return [
        math.exp(-((x - mean) ** 2) / (2 * sd * sd)) / (sd * math.sqrt(2 * math.pi)) for x in grid
    ]


@functools.lru_cache(maxsize=1)
def build():
    contracts = _contracts(MARKET)
    negative = _contracts(NEGATIVE)
    grid = np.linspace(math.log(40), math.log(250), 121).tolist()
    worlds = _worlds()
    return dict(
        section="28.1",
        source="Hull 11e GE pp.671–674; Examples 28.1–28.2 printed, other inputs synthetic",
        method=(
            "own erfc claim values; Gauss–Hermite one-step real-world mean and Z-covariance "
            "with second-order Richardson limit; seeded likelihood-ratio and direct MC"
        ),
        examples=dict(
            example_28_1=dict(m=0.12, s=0.2, r=0.08, market_price_of_risk=(0.12 - 0.08) / 0.2),
            example_28_2=dict(
                m1=0.03,
                s1=0.2,
                s2=0.3,
                r=0.06,
                market_price_of_risk=(0.03 - 0.06) / 0.2,
                m2=0.06 + (0.03 - 0.06) / 0.2 * 0.3,
            ),
        ),
        market=MARKET,
        negative_market=NEGATIVE,
        contracts=contracts,
        negative_contracts=negative,
        riskless=_riskless(MARKET),
        worlds=worlds,
        consumption=_consumption(),
        mc=_mc(),
        figure=dict(
            line=dict(
                market_lambda=(MARKET["mu"] - MARKET["r"]) / MARKET["sigma"],
                negative_lambda=(NEGATIVE["mu"] - NEGATIVE["r"]) / NEGATIVE["sigma"],
            ),
            densities=dict(
                log_spot=grid,
                lambdas=[-0.3, 0.0, 0.35, 0.6],
                density=[_density(lam, grid) for lam in (-0.3, 0.0, 0.35, 0.6)],
            ),
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("market price of risk independent reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §28.1 independent quadrature, 38 claims, 2 riskless pairs and seeded MC")


if __name__ == "__main__":
    main()
