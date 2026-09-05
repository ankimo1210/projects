"""Step D: H2/H6 -- analytic forward f(t)=z(t)+t*z'(t) vs central finite
difference, at knots, boundaries, and refined grids; on both the
reproduced baseline curve and a controlled synthetic curve. Also checks
H6: does a larger local slope inflate FORWARD error more than ZERO error
at the same point, for a fixed z(t) representation error?
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/ankimo1210/Documents/projects/quant-agent-benchmark/feedback_runs/feedback_round_01/sonnet/submission/src")

import numpy as np
import pandas as pd

from quantcurve.curve import PiecewiseLinearZeroCurve

ROUND_DIR = "/Users/ankimo1210/Documents/projects/quant-agent-benchmark/feedback_runs/feedback_round_01/sonnet"


def central_fd_forward(curve, t, h):
    zp = curve.zero_rate(t + h)
    zm = curve.zero_rate(max(t - h, 1e-8))
    zprime = (zp - zm) / (2 * h)
    z = curve.zero_rate(t)
    return z + t * zprime


def check_curve(curve, label, probe_points):
    print(f"--- {label} ---")
    rows = []
    for t in probe_points:
        f_analytic = float(curve.forward_rate(t))
        for h in (1e-2, 1e-3, 1e-4):
            f_fd = central_fd_forward(curve, t, h)
            diff_bp = abs(f_analytic - f_fd) * 1e4
            rows.append((t, h, f_analytic, f_fd, diff_bp))
    df = pd.DataFrame(rows, columns=["t", "h", "f_analytic", "f_fd", "diff_bp"])
    for t in probe_points:
        sub = df[df.t == t]
        shrinking = sub["diff_bp"].is_monotonic_decreasing or sub["diff_bp"].max() < 0.01
        print(f"  t={t:8.4f}  diffs(bp) at h=1e-2/1e-3/1e-4: "
              f"{sub['diff_bp'].values[0]:.4f} / {sub['diff_bp'].values[1]:.4f} / {sub['diff_bp'].values[2]:.4f}  "
              f"{'(shrinks w/ h -> discretisation artifact)' if shrinking else '(DOES NOT SHRINK -> investigate)'}")
    return df


# 1) Reproduced baseline curve (real dataset, piecewise-linear baseline model)
curve_csv = pd.read_csv(f"{ROUND_DIR}/audit/baseline_repro_outputs/curves/curve.csv")
print("curve.csv columns:", list(curve_csv.columns))
knot_col = "maturity_years" if "maturity_years" in curve_csv.columns else curve_csv.columns[0]
zero_col = "zero_rate" if "zero_rate" in curve_csv.columns else curve_csv.columns[1]
knots = curve_csv[knot_col].to_numpy(dtype=float)
zeros = curve_csv[zero_col].to_numpy(dtype=float)
real_curve = PiecewiseLinearZeroCurve(knots=knots, zero_rates=zeros)

interior_knots = [k for k in knots if k not in (knots[0], knots[-1])][:4]
mid_segment_points = [(knots[i] + knots[i + 1]) / 2 for i in range(0, min(4, len(knots) - 1))]
boundary_points = [knots[0], knots[-1]]
probe_real = sorted(set([float(x) for x in interior_knots + mid_segment_points + boundary_points]))
df_real = check_curve(real_curve, "REPRODUCED BASELINE CURVE (real data)", probe_real)

print()
# 2) Controlled synthetic piecewise-linear curve, deliberately with one sharp kink
synth_knots = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0])
synth_zeros = np.array([0.01, 0.012, 0.015, 0.014, 0.02, 0.021, 0.019, 0.018])  # kink at t=3 (slope sign flip)
synth_curve = PiecewiseLinearZeroCurve(knots=synth_knots, zero_rates=synth_zeros)
probe_synth = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 30.0]
df_synth = check_curve(synth_curve, "CONTROLLED SYNTHETIC CURVE (deliberate kink at t=3)", probe_synth)

print()
print("=" * 90)
print("H6: does larger LOCAL SLOPE inflate FORWARD diff more than ZERO-RATE diff,")
print("    for the SAME representation (real baseline curve, all knots)?")
print("=" * 90)
slopes = np.diff(zeros) / np.diff(knots)
seg_mid = (knots[:-1] + knots[1:]) / 2
rows = []
for i, tm in enumerate(seg_mid):
    z_fd_h = 1e-4
    z_here = float(real_curve.zero_rate(tm))
    f_here = float(real_curve.forward_rate(tm))
    rows.append((tm, slopes[i], z_here, f_here, abs(f_here - z_here) * 1e4))
h6 = pd.DataFrame(rows, columns=["t_mid", "local_slope", "z", "f", "abs_f_minus_z_bp"])
corr = h6["local_slope"].abs().corr(h6["abs_f_minus_z_bp"])
print(h6.to_string(index=False))
print(f"\ncorrelation(|local slope|, |f - z| in bp) = {corr:.4f}")
