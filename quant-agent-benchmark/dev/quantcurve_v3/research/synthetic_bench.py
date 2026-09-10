"""Synthetic validation bench: known curves, curated stress scenarios, hidden off-grid instruments.

usage: PYTHONPATH=src python research/synthetic_bench.py <variant_name> <out_dir> [key=value ...]
keys: penalty_shape, max_knots, use_loo_screen (0/1), stub_rule, scenarios=<comma list or 'all'>

Every scenario is generated with the round-02 pricing contract (contract_v2) from a known
continuously compounded zero curve z(t). Metrics (all bp, never mixed):
  S1  zero / forward RMSE and max vs truth on a fixed evaluation grid (1/48 .. 30, step 1/48), per band
  S1h yield-equivalent pricing error of *hidden* off-grid instruments priced from the truth (no noise)
  R   robust-layer bookkeeping: contaminated rows caught, clean rows wrongly excluded
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from quantcurve.conventions import ois_accruals, schedule_times
from quantcurve.instruments import build_instrument
from quantcurve.pricing import rate_residual
from quantcurve.workflow import WorkflowOptions, run_workflow

VAL = pd.Timestamp("2026-01-15")
EVAL_GRID = np.arange(1, 1441) / 48.0
SEED0 = 20260906


# ----------------------------------------------------------------------------- truth shapes
def ns(b0, b1, b2, tau):
    def z(t):
        t = np.asarray(t, float)
        x = np.where(t > 0, (1 - np.exp(-t / tau)) / np.maximum(t / tau, 1e-12), 1.0)
        return b0 + b1 * x + b2 * (x - np.exp(-t / tau))
    return z


def long_hump(t):
    t = np.asarray(t, float)
    return 0.02 + 0.007 * np.exp(-t / 0.5) + 0.006 * np.exp(-((t - 14.0) / 2.5) ** 2) - 0.004 * np.exp(-((t - 7.0) / 2.0) ** 2)


SHAPES = {
    "flat2": lambda t: np.full_like(np.asarray(t, float), 0.02),
    "steep_up": ns(0.045, -0.040, 0.0, 3.0),
    "inverted": ns(0.015, 0.030, 0.0, 4.0),
    "humped": ns(0.020, 0.0, 0.040, 2.0),
    "neg_front": ns(0.015, -0.020, 0.0, 2.5),
    "neg_all": lambda t: -0.006 + 0.004 * (1 - np.exp(-np.asarray(t, float) / 8.0)),
    "long_hump": long_hump,
}

# ----------------------------------------------------------------------------- tenor patterns
DEP_NEW = [0.0898, 0.1502, 0.2549, 0.324, 0.7014, 1.0622, 1.1439, 1.2769, 1.421, 1.5379, 1.7098, 1.9002]
OIS_NEW = [0.0833, 0.2576, 0.4318, 0.6061, 0.7803, 0.9545, 1.1288, 1.303, 1.4773, 1.6515, 1.8258, 2.0, 2.25, 2.8667, 3.4833, 4.1, 4.7167, 5.3333, 5.95, 6.5667, 7.1833, 7.8, 8.4167, 9.0333, 9.65, 10.2667, 10.8833, 11.5, 12.1167, 12.7333, 13.35, 13.9667, 14.5833, 15.2, 15.8167, 16.4333, 17.05, 17.6667, 18.2833, 18.9, 19.5167, 20.1333, 20.75, 21.3667, 21.9833, 22.6, 23.2167, 23.8333, 24.45, 25.0667, 25.6833, 26.3, 26.9167, 27.5333, 28.15, 28.7667, 29.3833, 30.0]
BOND_NEW = [0.2075, 0.9143, 1.0161, 2.1046, 2.2374, 4.1562, 4.7221, 5.7686, 7.7035, 8.1039, 8.4629, 9.839, 10.4488, 10.7921, 10.9763, 12.0235, 13.9431, 14.6624, 15.5316, 16.2955, 16.8781, 17.4169, 18.9055, 19.8264, 19.9044, 20.2345, 20.6393, 22.5719, 23.2897, 24.2859, 24.857, 25.9, 26.7, 27.4, 28.065, 28.9, 29.5, 29.9]
DEP_ROUND = [1 / 12, 0.25, 0.5, 0.75, 1.0]
OIS_ROUND = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30]
BOND_ROUND = list(np.linspace(1.6, 29.5, 20))

TENOR_PATTERNS = {
    "new_public": dict(dep=DEP_NEW, ois=OIS_NEW, bond=BOND_NEW, reps=1),
    "round_grid": dict(dep=DEP_ROUND, ois=OIS_ROUND, bond=BOND_ROUND, reps=2),
    "sparse_long": dict(dep=DEP_NEW, ois=[t for t in OIS_NEW if t <= 12.0], bond=BOND_NEW, reps=1),
    "no_deposits": dict(dep=[], ois=OIS_NEW, bond=BOND_NEW, reps=1),
    "front_only_5y": dict(dep=DEP_NEW, ois=[t for t in OIS_NEW if t <= 5.0], bond=[t for t in BOND_NEW if t <= 5.0], reps=1),
}


# ----------------------------------------------------------------------------- scenario library
def S(shape, tenor="new_public", noise="gaussian", noise_bp=0.5, outliers=0.0, units=False, missing=0.0, missing_bidask=0.0, duplicates=0.0, stale=0.0):
    return dict(shape=shape, tenor=tenor, noise=noise, noise_bp=noise_bp, outliers=outliers, units=units, missing=missing, missing_bidask=missing_bidask, duplicates=duplicates, stale=stale)


SCENARIOS = {
    **{f"base_{s}": S(s) for s in SHAPES},
    "tenor_round_grid_humped": S("humped", tenor="round_grid"),
    "tenor_sparse_long_humped": S("humped", tenor="sparse_long"),
    "tenor_sparse_long_long_hump": S("long_hump", tenor="sparse_long"),
    "tenor_no_deposits_humped": S("humped", tenor="no_deposits"),
    "tenor_front_only_5y_humped": S("humped", tenor="front_only_5y"),
    "noise_hetero_steep_up": S("steep_up", noise="hetero"),
    "noise_hetero_long_hump": S("long_hump", noise="hetero"),
    "noise_t3_humped": S("humped", noise="t3"),
    "noise_t3_neg_front": S("neg_front", noise="t3"),
    "outliers05_humped": S("humped", outliers=0.05),
    "outliers10_humped": S("humped", outliers=0.10),
    "outliers20_humped": S("humped", outliers=0.20),
    "outliers05_long_hump": S("long_hump", outliers=0.05),
    "outliers10_long_hump": S("long_hump", outliers=0.10),
    "outliers20_long_hump": S("long_hump", outliers=0.20),
    "units_mix_steep_up": S("steep_up", units=True),
    "units_mix_inverted": S("inverted", units=True),
    "missing_bidask_humped": S("humped", missing_bidask=0.3),
    "duplicates_long_hump": S("long_hump", duplicates=0.15),
    "stale_inverted": S("inverted", stale=0.05),
    "missing20_humped": S("humped", missing=0.2),
    "missing20_neg_all": S("neg_all", missing=0.2),
    "combo_stress_long_hump": S("long_hump", noise="t3", outliers=0.10, units=True, missing=0.2, missing_bidask=0.2),
}


def _noise(rng, kind, scale_bp, T):
    if kind == "gaussian":
        return rng.standard_normal() * scale_bp
    if kind == "hetero":
        return rng.standard_normal() * (0.3 + 0.03 * T) * (scale_bp / 0.5)
    if kind == "t3":
        return rng.standard_t(3) * scale_bp / np.sqrt(3.0)  # unit-variance t(3) scaled
    raise ValueError(kind)


def make_market(sc: dict, rng: np.random.Generator):
    z = SHAPES[sc["shape"]]
    D = lambda t: np.exp(-z(t) * np.asarray(t, float))
    pat = TENOR_PATTERNS[sc["tenor"]]
    rows, flags = [], []

    def add(inst_type, T, quote, freq=1, coupon=np.nan, spread=0.002, liq=0.95, unit="PERCENT", flag="clean", ts="2026-01-15T15:00:00Z", src="VENUE_A"):
        k = len(rows) + 1
        rows.append({"obs_id": f"OBS{k:04d}", "instrument_id": f"INS{k:04d}", "source": src, "timestamp": ts, "currency": "USD",
                     "instrument_type": inst_type, "maturity_date": (VAL + pd.Timedelta(int(round(T * 365)), unit="D")).strftime("%Y-%m-%d"),
                     "maturity_years": float(T), "start_years": 0, "coupon_rate": coupon, "payment_frequency": freq, "day_count": "ACT/365F",
                     "quote_type": {"deposit": "simple_rate", "ois_swap": "par_rate", "bond": "clean_price"}[inst_type], "quote_value": quote,
                     "quote_unit": unit, "bid": quote - spread / 2, "ask": quote + spread / 2, "liquidity_score": liq, "settlement_days": 2})
        flags.append(flag)

    for _ in range(pat["reps"]):
        for T in pat["dep"]:
            add("deposit", T, (1 / D(T) - 1) / T * 100 + _noise(rng, sc["noise"], sc["noise_bp"], T) / 100)
        for T in pat["ois"]:
            f = 1 if T <= 2 else 2
            times = schedule_times(T, f); al = ois_accruals(times, f)
            par = (1 - D(T)) / np.sum(al * D(times)) * 100
            add("ois_swap", T, par + _noise(rng, sc["noise"], sc["noise_bp"], T) / 100, freq=f, spread=0.003 if T < 20 else 0.01, liq=0.9 if T < 20 else 0.3)
        for T in pat["bond"]:
            c = 0.015 + 0.02 * rng.random()
            times = schedule_times(T, 2); al = ois_accruals(times, 2)
            price = np.sum(100 * c * al * D(times)) + 100 * D(T)
            dd = np.sum(times * 100 * c * al * D(times)) + 100 * T * D(T)  # dollar duration per unit rate
            add("bond", float(T), price + _noise(rng, sc["noise"], sc["noise_bp"], T) / 1e4 * dd, freq=2, coupon=c, spread=0.05, liq=0.7, unit="PRICE_POINTS")
    df = pd.DataFrame(rows); df["_flag"] = flags
    n = len(df)
    # contamination (order matters: units and outliers modify quotes; duplicates/stale add rows)
    if sc["outliers"] > 0:
        idx = rng.choice(n, size=max(1, int(round(sc["outliers"] * n))), replace=False)
        for i in idx:
            r = df.loc[i]; s = rng.choice([-1.0, 1.0])
            if r.instrument_type == "bond":
                times = schedule_times(r.maturity_years, 2); al = ois_accruals(times, 2)
                dd = np.sum(times * 100 * r.coupon_rate * al * D(times)) + 100 * r.maturity_years * D(r.maturity_years)
                delta = s * 15e-4 * dd
            else:
                delta = s * 0.15
            df.loc[i, ["quote_value", "bid", "ask"]] = df.loc[i, ["quote_value", "bid", "ask"]] + delta
            df.loc[i, "_flag"] = "outlier"
    if sc["units"]:
        rate_idx = df.index[df.instrument_type != "bond"].to_numpy(); bond_idx = df.index[df.instrument_type == "bond"].to_numpy()
        a = rng.choice(rate_idx, size=max(1, int(0.05 * len(rate_idx))), replace=False)
        df.loc[a, ["quote_value", "bid", "ask"]] = df.loc[a, ["quote_value", "bid", "ask"]] / 100; df.loc[a, "quote_unit"] = "DECIMAL"; df.loc[a, "_flag"] = "unit_labelled"
        rest = np.setdiff1d(rate_idx, a)
        b = rng.choice(rest, size=max(1, int(0.03 * len(rate_idx))), replace=False)
        df.loc[b, ["quote_value", "bid", "ask"]] = df.loc[b, ["quote_value", "bid", "ask"]] / 100; df.loc[b, "_flag"] = "unit_defect"  # still labelled PERCENT
        cc = rng.choice(bond_idx, size=max(1, int(0.05 * len(bond_idx))), replace=False)
        df.loc[cc, ["quote_value", "bid", "ask"]] = df.loc[cc, ["quote_value", "bid", "ask"]] / 100; df.loc[cc, "_flag"] = "unit_defect"
    if sc["missing_bidask"] > 0:
        m = rng.random(len(df)) < sc["missing_bidask"]; df.loc[m, ["bid", "ask"]] = np.nan
    if sc["duplicates"] > 0:
        idx = rng.choice(len(df), size=max(1, int(round(sc["duplicates"] * len(df)))), replace=False)
        dup = df.loc[idx].copy()
        dup["obs_id"] = ["DUP" + o[3:] for o in dup.obs_id]; dup["source"] = "BACKUP"; dup["timestamp"] = "2026-01-15T11:00:00Z"
        shift = rng.standard_normal(len(dup)) * 0.0002 * np.where(dup.instrument_type == "bond", 10, 1)
        dup[["quote_value", "bid", "ask"]] = dup[["quote_value", "bid", "ask"]].to_numpy() + shift[:, None]; dup["_flag"] = "duplicate"
        df = pd.concat([df, dup], ignore_index=True)
    if sc["stale"] > 0:
        idx = rng.choice(len(df), size=max(1, int(round(sc["stale"] * len(df)))), replace=False)
        df.loc[idx, "timestamp"] = "2026-01-05T15:00:00Z"; df.loc[idx, ["quote_value", "bid", "ask"]] = df.loc[idx, ["quote_value", "bid", "ask"]] + 0.05  # stale and 5bp off
        df.loc[idx, "_flag"] = "stale"
    if sc["missing"] > 0:
        keep = rng.random(len(df)) > sc["missing"]; keep[df["maturity_years"].idxmax()] = True; df = df[keep].reset_index(drop=True)
    return df, z, D


def hidden_instruments(sc: dict, D, rng: np.random.Generator):
    """Off-grid instruments priced from the truth without noise (the evaluator's hidden holdout analogue)."""
    pat = TENOR_PATTERNS[sc["tenor"]]
    out = []
    for T in (0.05, 0.12, 0.4, 0.85, 1.6):
        out.append(("deposit", T, (1 / D(T) - 1) / T, 1, None))
    ois = sorted(pat["ois"]) if pat["ois"] else [1.0, 30.0]
    mids = [(a + b) / 2 for a, b in zip(ois[:-1], ois[1:])]
    mids = mids[:: max(1, len(mids) // 18)] + [0.06, 29.9]
    for T in mids:
        f = 1 if T <= 2 else 2; times = schedule_times(T, f); al = ois_accruals(times, f)
        out.append(("ois_swap", T, (1 - D(T)) / np.sum(al * D(times)), f, None))
    for T in np.round(rng.uniform(0.3, 29.9, 15), 4):
        m = int(rng.choice([1, 2, 2, 4])); c = float(np.round(0.0 if rng.random() < 0.1 else 0.01 + 0.04 * rng.random(), 4))
        times = schedule_times(T, m); al = ois_accruals(times, m)
        out.append(("bond", float(T), float(np.sum(100 * c * al * D(times)) + 100 * D(T)), m, c))
    return out


def band(t):
    t = np.asarray(t, float)
    return np.where(t <= 2, "short", np.where(t < 15, "mid", "long"))


def main():
    name, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    kv = dict(a.split("=", 1) for a in sys.argv[3:])
    opts = dict(valuation_date=date(2026, 1, 15), skip_sensitivity=True)
    if "penalty_shape" in kv: opts["penalty_shape"] = kv["penalty_shape"]
    if "max_knots" in kv: opts["max_knots"] = int(kv["max_knots"])
    if "use_loo_screen" in kv: opts["use_loo_screen"] = kv["use_loo_screen"] == "1"
    if "stub_rule" in kv: opts["stub_rule"] = kv["stub_rule"]
    if "knot_bond_gap" in kv: opts["knot_bond_gap"] = float(kv["knot_bond_gap"])
    if "cv_loss" in kv: opts["cv_loss"] = kv["cv_loss"]
    if "lambda_grid_points" in kv: opts["lambda_grid_points"] = int(kv["lambda_grid_points"])
    if "cv_max_tolerance" in kv: opts["cv_max_tolerance"] = float(kv["cv_max_tolerance"])
    if "loo_window" in kv: opts["loo_window"] = int(kv["loo_window"])
    wanted = SCENARIOS if kv.get("scenarios", "all") == "all" else {k: SCENARIOS[k] for k in kv["scenarios"].split(",")}
    rows = []
    for si, (sname, sc) in enumerate(wanted.items()):
        rng = np.random.default_rng(SEED0 + 100 * list(SCENARIOS).index(sname))
        df, z, D = make_market(sc, rng)
        hidden = hidden_instruments(sc, D, np.random.default_rng(SEED0 + 7))
        d = out / sname; d.mkdir(exist_ok=True)
        flags = df["_flag"].to_numpy(); ids = df["obs_id"].to_numpy()
        csv = d / "market.csv"; df.drop(columns=["_flag"]).to_csv(csv, index=False)
        t0 = time.time()
        try:
            res = run_workflow(WorkflowOptions(market_data=csv, output_dir=d / "out", **opts))
        except Exception as e:  # noqa: BLE001
            rows.append({"variant": name, "scenario": sname, "status": f"failed: {e!r}"}); print(f"{name:12s} {sname:30s} FAILED {e!r}", flush=True); continue
        el = time.time() - t0
        # robust bookkeeping
        audit = res.cleaning.audit.set_index("obs_id")
        act = audit.loc[ids, "action"].to_numpy(); w = audit.loc[ids, "weight"].to_numpy()
        contaminated = np.isin(flags, ["outlier", "stale", "unit_defect"])
        caught = int(np.sum(contaminated & ((act == "exclude") | (w < 0.5) | ((flags == "unit_defect") & (act == "correct")))))
        clean_excl = int(np.sum((flags == "clean") & (act == "exclude")))
        clean_down = int(np.sum((flags == "clean") & (act == "downweight")))
        common = {"variant": name, "scenario": sname, "shape": sc["shape"], "tenor": sc["tenor"], "n_obs": int(len(df)), "n_usable": int(len(res.instruments)),
                  "lambda": float(res.adv.lam), "n_knots": int(len(res.adv.knots)), "selected": res.selected_model, "n_contaminated": int(contaminated.sum()),
                  "contaminated_caught": caught, "clean_excluded": clean_excl, "clean_downweighted": clean_down, "seconds": round(el, 1), "status": "ok"}
        t = EVAL_GRID; zt = z(t); h = 1e-5; ft = zt + t * (z(t + h) - z(np.maximum(t - h, 0))) / (t + h - np.maximum(t - h, 0)); b = band(t)
        for model, curve in (("baseline", res.baseline_curve), ("advanced", res.adv.curve)):
            ez = (curve.zero(t) - zt) * 1e4; ef = (curve.forward(t) - ft) * 1e4
            herr = []
            for typ, T, q, m, c in hidden:
                inst = build_instrument("H", typ, T, q, m, c)
                herr.append((typ, T, rate_residual(inst, curve) * 1e4))
            hd = pd.DataFrame(herr, columns=["type", "T", "err_bp"]); hd["band"] = band(hd["T"])
            for bn in ("short", "mid", "long", "all"):
                msk = np.ones_like(t, bool) if bn == "all" else b == bn
                hm = hd if bn == "all" else hd[hd.band == bn]
                rows.append({**common, "model": model, "band": bn, "zero_rmse_bp": float(np.sqrt(np.mean(ez[msk] ** 2))), "zero_max_bp": float(np.abs(ez[msk]).max()),
                             "fwd_rmse_bp": float(np.sqrt(np.mean(ef[msk] ** 2))), "fwd_max_bp": float(np.abs(ef[msk]).max()),
                             "hidden_rmse_bp": float(np.sqrt(np.mean(hm.err_bp ** 2))) if len(hm) else np.nan, "hidden_max_bp": float(hm.err_bp.abs().max()) if len(hm) else np.nan, "hidden_n": int(len(hm))})
            for typ in ("deposit", "ois_swap", "bond"):
                hm = hd[hd.type == typ]
                rows.append({**common, "model": model, "band": f"type:{typ}", "hidden_rmse_bp": float(np.sqrt(np.mean(hm.err_bp ** 2))), "hidden_max_bp": float(hm.err_bp.abs().max()), "hidden_n": int(len(hm))})
        a = [r for r in rows if r["scenario"] == sname and r.get("model") == "advanced" and r.get("band") == "all"][0]
        print(f"{name:12s} {sname:30s} lam={res.adv.lam:.3g} knots={len(res.adv.knots)} caught={caught}/{int(contaminated.sum())} clean_excl={clean_excl} | adv zero={a['zero_rmse_bp']:.2f} fwd={a['fwd_rmse_bp']:.2f} hidden={a['hidden_rmse_bp']:.2f} {el:.0f}s", flush=True)
    res_df = pd.DataFrame(rows); res_df.to_csv(out / "results.csv", index=False)
    ok = res_df[(res_df.status == "ok") & (res_df.model == "advanced")]
    summ = {"variant": name, "n_scenarios": int(len(wanted)), "n_failed": int(len(wanted) - ok.scenario.nunique()),
            "advanced_mean_by_band": ok[ok.band.isin(["short", "mid", "long", "all"])].groupby("band")[["zero_rmse_bp", "fwd_rmse_bp", "hidden_rmse_bp"]].mean().round(3).to_dict(),
            "advanced_worst_by_band": ok[ok.band.isin(["short", "mid", "long", "all"])].groupby("band")[["zero_rmse_bp", "fwd_rmse_bp", "hidden_rmse_bp"]].max().round(3).to_dict(),
            "robust": {"contaminated_total": int(ok.drop_duplicates("scenario").n_contaminated.sum()), "caught": int(ok.drop_duplicates("scenario").contaminated_caught.sum()), "clean_excluded": int(ok.drop_duplicates("scenario").clean_excluded.sum())}}
    json.dump(summ, open(out / "summary.json", "w"), indent=2)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
