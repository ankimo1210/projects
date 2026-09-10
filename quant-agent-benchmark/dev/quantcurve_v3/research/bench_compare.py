"""Compare two synthetic_bench runs (A = before, B = after) under the adoption rule.

usage: python research/bench_compare.py <A/results.csv> <B/results.csv> [--worsen-tol 0.5] [--improve-tol 0.05]
Adoption rule: advanced zero RMSE ('all' band) improves by > improve_tol in >= 2 scenarios, no scenario/band worsens by
more than worsen_tol (zero, forward or hidden), and no new failures.
"""
import sys
import pandas as pd

a = pd.read_csv(sys.argv[1]); b = pd.read_csv(sys.argv[2])
wt = float(sys.argv[sys.argv.index("--worsen-tol") + 1]) if "--worsen-tol" in sys.argv else 0.5
it = float(sys.argv[sys.argv.index("--improve-tol") + 1]) if "--improve-tol" in sys.argv else 0.05
k = ["scenario", "model", "band"]
m = a.merge(b, on=k, suffixes=("_A", "_B"))
adv = m[(m.model == "advanced") & (m.band.isin(["short", "mid", "long", "all"]))].copy()
for c in ("zero_rmse_bp", "fwd_rmse_bp", "hidden_rmse_bp"):
    adv[f"d_{c}"] = adv[f"{c}_B"] - adv[f"{c}_A"]
pd.set_option("display.width", 250)
allb = adv[adv.band == "all"]
print("per-scenario (advanced, all band): zero / fwd / hidden RMSE A -> B")
print(allb[["scenario", "zero_rmse_bp_A", "zero_rmse_bp_B", "fwd_rmse_bp_A", "fwd_rmse_bp_B", "hidden_rmse_bp_A", "hidden_rmse_bp_B"]].round(3).to_string(index=False))
print("\nmean over scenarios by band (A -> B):")
print(adv.groupby("band")[["zero_rmse_bp_A", "zero_rmse_bp_B", "fwd_rmse_bp_A", "fwd_rmse_bp_B", "hidden_rmse_bp_A", "hidden_rmse_bp_B"]].mean().round(3).to_string())
imp = int((allb.d_zero_rmse_bp < -it).sum()); wor = int((allb.d_zero_rmse_bp > it).sum())
worst = adv[["d_zero_rmse_bp", "d_fwd_rmse_bp", "d_hidden_rmse_bp"]].max().max()
fa = set(a[a.status != "ok"].scenario); fb = set(b[b.status != "ok"].scenario)
print(f"\nscenarios improved (zero, all band, >{it}bp): {imp}; worsened: {wor}; max worsening in any band/metric: {worst:.3f}bp; failures A={sorted(fa)} B={sorted(fb)}")
print("ADOPT" if (imp >= 2 and worst <= wt and not (fb - fa)) else "DO NOT ADOPT (rule not met)")
