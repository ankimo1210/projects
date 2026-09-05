"""Step D/E: does switching the bond schedule to backward-from-maturity
(monkeypatched, NOT yet edited in submission/) fix the mismatch case
without regressing the case where forward-generated bonds happen to be
the true convention? Symmetric check before touching submission/ code.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/ankimo1210/Documents/projects/quant-agent-benchmark/feedback_runs/feedback_round_01/sonnet/submission/src")

import numpy as np

import quantcurve.calibration as calib
import quantcurve.cashflows as cf
from exp_C_D_synthetic_truth import (
    KNOTS, backward_bond_price, build_synthetic_frame, evaluate,
)
from quantcurve.calibration import fit_baseline

ORIG_BOND_PRICER = calib.bond_model_price

print("=" * 90)
print("Symmetric check: backward-convention PRICER against both bond-generation conventions")
print("=" * 90)

for shape in ("flat", "upward", "humped"):
    for gen_label, gen_fn in (("forward-generated (pkg default)", cf.bond_model_price),
                               ("backward-generated (standard)", backward_bond_price)):
        df, z_true = build_synthetic_frame(shape, gen_fn)
        calib.bond_model_price = backward_bond_price
        try:
            fb = fit_baseline(df, knots=KNOTS)
        finally:
            calib.bond_model_price = ORIG_BOND_PRICER
        _, rmse = evaluate(fb.curve, z_true, f"backward-pricer vs {gen_label}")
        print(f"  shape={shape:8s} bonds={gen_label:32s} -> overall RMSE with BACKWARD pricer = {rmse:.3f}bp")
    print()
