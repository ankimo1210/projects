"""Independent one-factor risk-price arithmetic, Ito claims and Gaussian measures."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-1/reference.json"
N = 262144


def density(x, mean, variance):
    return np.exp(-0.5 * (np.asarray(x) - mean) ** 2 / variance) / math.sqrt(2 * math.pi * variance)


def standard_normal(u):
    return math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)


def build():
    pins = dict(
        example_28_1_lambda=(0.12 - 0.08) / 0.2,
        example_28_2_lambda=(0.03 - 0.06) / 0.2,
        example_28_2_return=0.06 + ((0.03 - 0.06) / 0.2) * 0.3,
    )
    cases = [
        dict(r=r, risk_price=lam, loading=s, mu=r + lam * s)
        for r in (-0.02, 0.06)
        for lam in (-0.15, 0, 0.2)
        for s in (-0.3, 0.2)
    ]
    powers = []
    for a in (-2, -1.5, -1, 0, 1, 2):
        # Price from a Q Gaussian expectation. Ito derivatives are of this
        # power claim, independently of any risk-price inversion API.
        price, error = quad(
            lambda z, a=a: (
                math.exp(-0.04)
                * (100 * math.exp((0.04 - 0.5 * 0.2**2) + 0.2 * z)) ** a
                * math.exp(-0.5 * z * z)
                / math.sqrt(2 * math.pi)
            ),
            -12,
            12,
            epsabs=1e-11,
            epsrel=1e-12,
        )
        f_t = -((a - 1) * 0.04 + 0.5 * a * (a - 1) * 0.2**2) * price
        s_f_s, s2_f_ss = a * price, a * (a - 1) * price
        drift = (f_t + 0.09 * s_f_s + 0.5 * 0.2**2 * s2_f_ss) / price
        powers.append(
            dict(
                power=a,
                price=price,
                quadrature_error=error,
                drift=drift,
                loading=0.2 * s_f_s / price,
                r=0.04,
                underlying_mu=0.09,
                underlying_vol=0.2,
                risk_price=0.25,
            )
        )
    # Current money fractions; the holdings in shares would be w_i/f_i.
    weights = [0.6, 0.4]
    selected = [next(row for row in powers if row["power"] == a) for a in (1, -1.5)]
    hedge = dict(
        weights=weights,
        loading=[row["loading"] for row in selected],
        mu=[row["drift"] for row in selected],
        r=0.04,
        risk=[w * row["loading"] for w, row in zip(weights, selected, strict=True)],
        returns=[w * row["drift"] for w, row in zip(weights, selected, strict=True)],
    )
    loading = np.linspace(-0.6, 0.6, 61)
    slopes = dict(
        loading=loading.tolist(),
        r=0.06,
        risk_prices=[-0.15, 0, 0.2],
        returns=[(0.06 + lam * loading).tolist() for lam in (-0.15, 0, 0.2)],
    )
    x = np.linspace(-1.3, 1.3, 131)
    r, lam, s, t = 0.06, -0.15, 0.3, 2.0
    mean_p, mean_q = (r + lam * s - 0.5 * s * s) * t, (r - 0.5 * s * s) * t
    p = density(x, mean_p, s * s * t)
    q = density(x, mean_q, s * s * t)
    rn = np.exp(-lam * ((x - mean_p) / s) - 0.5 * lam * lam * t)
    distribution = dict(
        log_return=x.tolist(),
        p=p.tolist(),
        q=q.tolist(),
        weighted_p=(p * rn).tolist(),
        r=r,
        risk_price=lam,
        loading=s,
        T=t,
        mean_p=mean_p,
        mean_q=mean_q,
        variance_p=s * s * t,
        variance_q=s * s * t,
    )
    z = np.random.default_rng(281).standard_normal(N)
    mc = []
    for lam, s in ((-0.15, 0.3), (-0.15, -0.3), (0.2, 0.2), (0.2, -0.2)):
        r, t, f0 = 0.06, 2.0, 100.0
        w_t = math.sqrt(t) * z
        rn = np.exp(-lam * w_t - 0.5 * lam * lam * t)  # raw dQ/dP, never self-normalized
        p_terminal = f0 * np.exp((r + lam * s - 0.5 * s * s) * t + s * w_t)
        direct = math.exp(-r * t) * f0 * np.exp((r - 0.5 * s * s) * t + s * w_t)
        weighted = math.exp(-r * t) * rn * p_terminal
        difference = weighted - direct  # same draws: retain the covariance

        def se(values):
            return float(np.std(values, ddof=1) / math.sqrt(N))

        # Independent Gaussian integration of both density and weighted payoff.
        weight_integral, weight_error = quad(
            lambda u, lam=lam, t=t: (
                math.exp(-lam * math.sqrt(t) * u - 0.5 * lam * lam * t) * standard_normal(u)
            ),
            -12,
            12,
            epsabs=1e-11,
            epsrel=1e-12,
        )
        expectation, expectation_error = quad(
            lambda u, r=r, lam=lam, t=t, f0=f0, s=s: (
                math.exp(-r * t - lam * math.sqrt(t) * u - 0.5 * lam * lam * t)
                * f0
                * math.exp((r + lam * s - 0.5 * s * s) * t + s * math.sqrt(t) * u)
                * standard_normal(u)
            ),
            -12,
            12,
            epsabs=1e-10,
            epsrel=1e-12,
        )
        mc.append(
            dict(
                r=r,
                risk_price=lam,
                loading=s,
                T=t,
                f0=f0,
                weighted_price=float(np.mean(weighted)),
                weighted_se=se(weighted),
                direct_price=float(np.mean(direct)),
                direct_se=se(direct),
                weight_mean=float(np.mean(rn)),
                weight_se=se(rn),
                paired_difference=float(np.mean(difference)),
                paired_se=se(difference),
                reference_price=expectation,
                reference_weight=weight_integral,
                quadrature_error=max(weight_error, expectation_error),
            )
        )
    return dict(
        section="28.1",
        source="Hull 11e GE pp.671–674",
        assumptions="One common Wiener risk; no-income investment claims; constant GBM demos",
        printed_pins=pins,
        cases=cases,
        powers=powers,
        seed=281,
        mc_paths=N,
        mc=mc,
        figure=dict(loading=slopes, hedge=hedge, density=distribution),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(build(), indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("risk premium reference missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §28.1 independent printed pins, Ito powers, Gaussian measures and paired MC")


if __name__ == "__main__":
    main()
