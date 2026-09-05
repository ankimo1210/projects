"""Step C/D: baseline vs advanced vs KNOWN truth on synthetic curves,
plus a controlled A/B test of the bond schedule convention (H5) using
bonds generated with the *standard* backward-from-maturity convention
(simulating "the real world uses this convention") while the package's
pricing initially still uses forward-from-valuation-date.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/Users/ankimo1210/Documents/projects/quant-agent-benchmark/feedback_runs/feedback_round_01/sonnet/submission/src")

import numpy as np
import pandas as pd

from quantcurve.calibration import fit_baseline, fit_advanced, model_quote
from quantcurve.curve import PiecewiseLinearZeroCurve
import quantcurve.cashflows as cf

DEPOSIT_MATS = [1 / 12, 0.25, 0.5, 0.75, 1.0]
SWAP_MATS = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0]
BOND_SPECS = [  # (T, coupon) -- fractional, matching the real dataset's flavor
    (1.508434, 0.025451), (2.964904, 0.020116), (4.922553, 0.032812), (6.965686, 0.029094),
    (9.025154, 0.036447), (11.772147, 0.025911), (14.312569, 0.019082), (18.347137, 0.017413),
    (22.417865, 0.021310), (26.512248, 0.017559), (29.783214, 0.023512),
]


def make_true_curve(shape: str):
    if shape == "flat":
        z = lambda t: 0.022
    elif shape == "upward":
        z = lambda t: 0.010 + 0.0006 * t
    elif shape == "humped":
        z = lambda t: 0.015 + 0.012 * math.exp(-((t - 6.0) ** 2) / (2 * 4.0 ** 2))
    else:
        raise ValueError(shape)
    return z


def discount_from_z(z_fn):
    return lambda t: math.exp(-z_fn(t) * t)


def backward_bond_schedule(T, freq):
    step = 1.0 / freq
    n = max(1, math.ceil(T * freq - 1e-9))
    return [T - (n - i) * step for i in range(1, n + 1)]


def backward_bond_price(discount_fn, T, coupon, freq, face=100.0):
    times = backward_bond_schedule(T, freq)
    coupon_amt = coupon / freq * face
    price = 0.0
    for i, t in enumerate(times):
        amt = coupon_amt + (face if i == len(times) - 1 else 0.0)
        price += amt * discount_fn(t)
    return price


def build_synthetic_frame(shape: str, bond_price_fn):
    z_true = make_true_curve(shape)
    D = discount_from_z(z_true)
    rows = []
    for t in DEPOSIT_MATS:
        rate = (1.0 / D(t) - 1.0) / t
        rows.append(dict(instrument_id=f"DEP{t}", instrument_type="deposit", maturity_years=t,
                          coupon_rate=None, payment_frequency=1, normalized_quote=rate * 100.0,
                          weight=1.0, action="keep"))
    for t in SWAP_MATS:
        freq = 1 if t <= 2 else 2
        times = cf.payment_times(t, freq)
        alphas = cf.year_fractions(times)
        disc = np.array([D(x) for x in times])
        annuity = float(np.sum(alphas * disc))
        par = (1.0 - disc[-1]) / annuity
        rows.append(dict(instrument_id=f"SWP{t}", instrument_type="ois_swap", maturity_years=t,
                          coupon_rate=None, payment_frequency=freq, normalized_quote=par * 100.0,
                          weight=1.0, action="keep"))
    for t, c in BOND_SPECS:
        price = bond_price_fn(D, t, c, 2)
        rows.append(dict(instrument_id=f"BND{t}", instrument_type="bond", maturity_years=t,
                          coupon_rate=c, payment_frequency=2, normalized_quote=price,
                          weight=1.0, action="keep"))
    return pd.DataFrame(rows), z_true


def band(t):
    return "short(T<=2)" if t <= 2 else ("mid(2<T<15)" if t < 15 else "long(T>=15)")


def evaluate(curve, z_true, label):
    probe = np.array(sorted(set(DEPOSIT_MATS + SWAP_MATS + [t for t, _ in BOND_SPECS])))
    z_fit = curve.zero_rate(probe)
    z_ref = np.array([z_true(t) for t in probe])
    err_bp = (z_fit - z_ref) * 1e4
    df = pd.DataFrame({"T": probe, "err_bp": err_bp, "band": [band(t) for t in probe]})
    out = df.groupby("band")["err_bp"].agg(lambda s: float(np.sqrt(np.mean(s**2))))
    print(f"  [{label}] zero-rate RMSE by band (bp): {out.to_dict()}  overall={np.sqrt(np.mean(err_bp**2)):.3f}bp")
    return out, float(np.sqrt(np.mean(err_bp**2)))


KNOTS = np.array([1/12, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0])

print("=" * 90)
print("EXPERIMENT: baseline vs advanced recovery of KNOWN synthetic curves")
print("Bonds generated with the package's CURRENT convention (forward-from-t=0, back stub)")
print("=" * 90)
summary_current = {}
for shape in ("flat", "upward", "humped"):
    print(f"\n--- shape={shape} (package's own bond convention) ---")
    df, z_true = build_synthetic_frame(shape, cf.bond_model_price)
    fb = fit_baseline(df, knots=KNOTS)
    _, rmse_b = evaluate(fb.curve, z_true, "baseline")
    fa = fit_advanced(df, fb.per_type_scale, lambda_reg=1e4, knots=KNOTS, z0=fb.curve.zero_rates, n_irls=3)
    _, rmse_a = evaluate(fa.curve, z_true, "advanced")
    summary_current[shape] = (rmse_b, rmse_a)

print()
print("=" * 90)
print("EXPERIMENT: SAME shapes, bonds generated with the STANDARD backward-from-maturity")
print("convention, priced by the package's CURRENT (forward) pricing function --")
print("this simulates 'real bonds follow the standard convention but our pricer assumes the other one'")
print("=" * 90)
summary_mismatched = {}
for shape in ("flat", "upward", "humped"):
    print(f"\n--- shape={shape} (bonds=backward-generated, priced with package's forward pricer) ---")
    df, z_true = build_synthetic_frame(shape, backward_bond_price)
    fb = fit_baseline(df, knots=KNOTS)
    _, rmse_b = evaluate(fb.curve, z_true, "baseline")
    summary_mismatched[shape] = rmse_b

print()
print("SUMMARY (overall zero-rate RMSE, bp):")
print(f"{'shape':<10} {'baseline(current-conv)':<24} {'advanced(current-conv)':<24} {'baseline(bond-conv-mismatch)':<28}")
for shape in ("flat", "upward", "humped"):
    b, a = summary_current[shape]
    m = summary_mismatched[shape]
    print(f"{shape:<10} {b:<24.3f} {a:<24.3f} {m:<28.3f}")
