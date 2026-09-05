"""Step B: independent pricing diagnostics.

Deliberately does NOT import quantcurve.cashflows for the "reference"
values -- every formula here is hand-written from CONVENTIONS.md directly,
so a bug shared between the package and its own tests cannot hide here.
Only the package's own functions are imported for the "actual" side of
each comparison.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/Users/ankimo1210/Documents/projects/quant-agent-benchmark/feedback_runs/feedback_round_01/sonnet/submission/src")

from quantcurve.cashflows import (
    bond_model_price as pkg_bond_price,
    deposit_model_rate as pkg_deposit_rate,
    swap_model_par_rate as pkg_swap_rate,
)

results = []


def log(name, ref, actual, tol=1e-8, note=""):
    if ref == 0:
        rel = abs(actual - ref)
    else:
        rel = abs(actual - ref) / abs(ref)
    ok = rel < tol
    results.append((name, ref, actual, rel, ok, note))
    print(f"{'OK ' if ok else 'FAIL'} {name}: ref={ref:.12g} actual={actual:.12g} rel_err={rel:.3e} {note}")


# ---- synthetic discount curves (hand-written, independent of quantcurve.curve) ----

def flat_curve(z):
    return lambda t: math.exp(-z * t)


def linear_z_curve(z0, slope):
    return lambda t: math.exp(-(z0 + slope * t) * t)


def humped_curve():
    # z(t) rises then falls; deliberately not piecewise-linear or spline-based.
    def z(t):
        return 0.02 + 0.01 * math.sin(t / 5.0) - 0.0003 * t
    return lambda t: math.exp(-z(t) * t)


CURVES = {
    "flat_2pct": flat_curve(0.02),
    "flat_negative_1pct": flat_curve(-0.01),
    "upward_slope": linear_z_curve(0.01, 0.0015),
    "downward_slope": linear_z_curve(0.03, -0.0015),
    "humped": humped_curve(),
    "deep_negative_flat": flat_curve(-0.05),
}


# ---- independent reference formulas, from CONVENTIONS.md text directly ----

def ref_deposit_simple_rate(discount_fn, T):
    """CONVENTIONS.md: D(T) = 1/(1+r*T)  =>  r = (1/D(T) - 1) / T."""
    D = discount_fn(T)
    return (1.0 / D - 1.0) / T


def ref_swap_schedule_forward_from_zero(T, freq):
    """Independent schedule generator: regular grid from t=0 at 1/freq
    spacing, stub at the END if T is not an exact multiple (forward
    generation, back-stub) -- written from scratch, not calling payment_times.
    """
    step = 1.0 / freq
    times = []
    t = step
    while t < T - 1e-9:
        times.append(t)
        t += step
    if not times or abs(times[-1] - T) > 1e-9:
        times.append(T)
    return times


def ref_swap_par_rate(discount_fn, T, freq):
    times = ref_swap_schedule_forward_from_zero(T, freq)
    alphas = []
    prev = 0.0
    for t in times:
        alphas.append(t - prev)
        prev = t
    annuity = sum(a * discount_fn(t) for a, t in zip(alphas, times))
    return (1.0 - discount_fn(T)) / annuity


def ref_bond_schedule_backward_from_maturity(T, freq):
    """Independent schedule generator: regular grid ending exactly at T,
    spaced 1/freq apart, stub (if any) at the FRONT -- written from
    scratch, not calling bond_cashflows.
    """
    step = 1.0 / freq
    n = max(1, math.ceil(T * freq - 1e-9))
    return [T - (n - i) * step for i in range(1, n + 1)]


def ref_bond_price(discount_fn, T, coupon, freq, face=100.0):
    times = ref_bond_schedule_backward_from_maturity(T, freq)
    coupon_amt = coupon / freq * face
    price = 0.0
    for i, t in enumerate(times):
        amt = coupon_amt + (face if i == len(times) - 1 else 0.0)
        price += amt * discount_fn(t)
    return price


# ---- run the comparisons across curve shapes and maturities ----

print("=== Deposits: independent simple-rate formula vs package ===")
for cname, D in CURVES.items():
    for T in (1 / 12, 0.25, 0.5, 0.75, 1.0):
        ref = ref_deposit_simple_rate(D, T)
        actual = pkg_deposit_rate(D, T)
        log(f"deposit[{cname}, T={T:.4f}]", ref, actual)

print()
print("=== OIS swaps: independent schedule/par-rate vs package (integer & fractional T) ===")
for cname, D in CURVES.items():
    for T, freq in ((1.0, 1), (1.25, 1), (1.5, 1), (2.0, 1), (2.5, 2), (5.0, 2), (7.3, 2), (30.0, 2)):
        ref = ref_swap_par_rate(D, T, freq)
        actual = pkg_swap_rate(D, T, freq)
        log(f"swap[{cname}, T={T}, freq={freq}]", ref, actual)

print()
print("=== Bonds: independent backward schedule/price vs package (integer & fractional T) ===")
for cname, D in CURVES.items():
    for T, coupon in ((2.0, 0.02), (1.508434, 0.025451), (5.5, 0.03), (13.730254, 0.016726), (29.783214, 0.023512)):
        ref = ref_bond_price(D, T, coupon, 2)
        actual = pkg_bond_price(D, T, coupon, 2)
        log(f"bond[{cname}, T={T}, coupon={coupon}]", ref, actual)

print()
print("=== Negative-rate / positive-discount-factor safety (deep negative flat curve) ===")
D = CURVES["deep_negative_flat"]
for T in (1 / 12, 1.0, 10.0, 30.0):
    d = D(T)
    print(f"T={T}: D(T)={d:.6f} positive={d > 0}")
    assert d > 0

n_fail = sum(1 for r in results if not r[4])
print()
print(f"TOTAL comparisons: {len(results)}, FAILURES: {n_fail}")
if n_fail:
    print("FAILED CASES:")
    for r in results:
        if not r[4]:
            print(" ", r)
