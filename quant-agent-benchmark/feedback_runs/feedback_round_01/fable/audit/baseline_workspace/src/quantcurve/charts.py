"""Matplotlib charts (PNG, Agg backend, deterministic)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

COLORS = {"baseline": "#8a8a8a", "advanced": "#1f5fbf", "deposit": "#d1495b", "ois_swap": "#1f5fbf", "bond": "#2a9d8f", "excluded": "#f0a202"}
TYPE_LABEL = {"deposit": "Deposit", "ois_swap": "OIS", "bond": "Bond"}


def _style() -> None:
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    return path


def chart_curves(grid_base: pd.DataFrame, grid_adv: pd.DataFrame, knots: np.ndarray, repricing: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1]})
    for ax, xmax, title in ((axes[0], 3.0, "Front end (0-3Y)"), (axes[1], None, "Full curve")):
        ax.plot(grid_base["maturity_years"], grid_base["zero_rate"] * 100, color=COLORS["baseline"], lw=1.4, label="Baseline (bootstrap, linear zero)")
        ax.plot(grid_adv["maturity_years"], grid_adv["zero_rate"] * 100, color=COLORS["advanced"], lw=1.8, label="Advanced (penalised B-spline forward)")
        dep = repricing[(repricing["instrument_type"] == "deposit") & (repricing["weight"] > 0)]
        if len(dep):
            implied = np.log(1 + dep["market_quote"] / 100 * dep["maturity_years"]) / dep["maturity_years"] * 100
            ax.scatter(dep["maturity_years"], implied, s=16, color=COLORS["deposit"], zorder=5, label="Deposit-implied zero")
        for k in knots:
            ax.axvline(k, color="#cccccc", lw=0.5, zorder=0)
        if xmax is not None:
            ax.set_xlim(0, xmax)
            sub = grid_adv[grid_adv["maturity_years"] <= xmax]["zero_rate"] * 100
            subb = grid_base[grid_base["maturity_years"] <= xmax]["zero_rate"] * 100
            lo, hi = min(sub.min(), subb.min()), max(sub.max(), subb.max())
            ax.set_ylim(lo - 0.1, hi + 0.1)
        ax.set_title(title)
        ax.set_xlabel("Maturity (years)")
        ax.set_ylabel("Zero rate (%, continuous)")
    axes[1].legend(loc="lower right", fontsize=8)
    fig.suptitle("Zero curves (vertical lines: spline knots)")
    return _save(fig, path)


def chart_forwards(grid_base: pd.DataFrame, grid_adv: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(grid_base["maturity_years"], grid_base["forward_rate"] * 100, color=COLORS["baseline"], lw=1.2, label="Baseline instantaneous forward (piecewise)")
    ax.plot(grid_adv["maturity_years"], grid_adv["forward_rate"] * 100, color=COLORS["advanced"], lw=1.8, label="Advanced instantaneous forward")
    ax.plot(grid_adv["maturity_years"], grid_adv["zero_rate"] * 100, color=COLORS["advanced"], lw=1.0, ls="--", label="Advanced zero rate")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Rate (%, continuous)")
    ax.set_title("Instantaneous forward rates")
    ax.legend(loc="best", fontsize=8)
    return _save(fig, path)


def chart_repricing(repricing: pd.DataFrame, cleaning: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax = axes[0]
    for t in ("deposit", "ois_swap", "bond"):
        sub = repricing[(repricing["instrument_type"] == t) & (repricing["robust_factor"] > 0)]
        if len(sub):
            ax.scatter(sub["maturity_years"], sub["residual_bp"], s=12 + 60 * sub["weight"], color=COLORS[t], alpha=0.8, label=f"{TYPE_LABEL[t]} (size = weight)")
        ex = repricing[(repricing["instrument_type"] == t) & (repricing["robust_factor"] <= 0)]
        if len(ex):
            ax.scatter(ex["maturity_years"], np.clip(ex["residual_bp"], -25, 25), s=40, facecolors="none", edgecolors=COLORS["excluded"], label=f"{TYPE_LABEL[t]} rejected by robust fit (clipped)")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Market - model (bp, yield-equivalent)")
    ax.set_title("Repricing residuals of the advanced model")
    ax.legend(fontsize=7, ncol=2)
    ax.set_ylim(-26, 26)
    ax = axes[1]
    sub = repricing[repricing["robust_factor"] > 0]
    ax.scatter(sub["maturity_years"], sub["std_residual"], s=14, c=[COLORS[t] for t in sub["instrument_type"]], alpha=0.8)
    for level in (-4.685, 4.685):
        ax.axhline(level, color=COLORS["excluded"], lw=0.8, ls="--")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Standardised residual u")
    ax.set_xlabel("Maturity (years)")
    ax.set_title("Standardised residuals (dashed: Tukey rejection bound)")
    return _save(fig, path)


def chart_model_comparison(cv_table: pd.DataFrame | None, power_table: pd.DataFrame | None, lam: float, holdout_metrics: dict, per_fold: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    ax = axes[0]
    if cv_table is not None and len(cv_table):
        ax.plot(cv_table["lambda"], cv_table["cv_score"], marker="o", ms=3, color=COLORS["advanced"])
        ax.axvline(lam, color=COLORS["excluded"], lw=1.2, label=f"selected lambda = {lam:.3g}")
        ax.set_xscale("log")
        ax.legend(fontsize=8)
    ax.set_xlabel("Smoothing parameter lambda")
    ax.set_ylabel("Grouped-CV score (RMSE of standardised held-out residuals)")
    ax.set_title("Cross-validation of the smoothing parameter")
    ax = axes[1]
    types = ["overall"] + sorted(holdout_metrics["advanced"]["by_type"].keys())
    x = np.arange(len(types))
    for k, model in enumerate(("baseline", "advanced")):
        vals = []
        for t in types:
            m = holdout_metrics[model]["overall"] if t == "overall" else holdout_metrics[model]["by_type"][t]
            vals.append(m["rmse_bp"] if m["rmse_bp"] is not None else 0.0)
        ax.bar(x + (k - 0.5) * 0.36, vals, width=0.36, color=COLORS[model], label=model)
        for xi, v in zip(x + (k - 0.5) * 0.36, vals):
            ax.text(xi, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([TYPE_LABEL.get(t, t) for t in types])
    ax.set_ylabel("Holdout RMSE (bp)")
    ax.set_title("Maturity-grouped holdout error")
    ax.legend(fontsize=8)
    ax = axes[2]
    if len(per_fold):
        ax.plot(per_fold["fold"], per_fold["baseline_rmse_bp"], marker="s", color=COLORS["baseline"], label="baseline")
        ax.plot(per_fold["fold"], per_fold["advanced_rmse_bp"], marker="o", color=COLORS["advanced"], label="advanced")
        ax.set_xticks(per_fold["fold"])
    ax.set_xlabel("Fold")
    ax.set_ylabel("RMSE (bp)")
    ax.set_title("Per-fold holdout RMSE")
    ax.legend(fontsize=8)
    return _save(fig, path)


def chart_data_quality(cleaning: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    actions = ["keep", "correct", "downweight", "exclude"]
    types = ["deposit", "ois_swap", "bond"]
    counts = cleaning.groupby(["instrument_type", "action"]).size().unstack(fill_value=0).reindex(index=types, columns=actions, fill_value=0)
    bottom = np.zeros(len(types))
    palette = {"keep": "#2a9d8f", "correct": "#1f5fbf", "downweight": "#f0a202", "exclude": "#d1495b"}
    for a in actions:
        ax.bar([TYPE_LABEL[t] for t in types], counts[a].values, bottom=bottom, color=palette[a], label=a)
        bottom += counts[a].values
    ax.set_ylabel("Observations")
    ax.set_title("Cleaning actions by instrument type")
    ax.legend(fontsize=8)
    ax = axes[1]
    for a in actions:
        sub = cleaning[cleaning["action"] == a]
        y = {"keep": 0, "correct": 1, "downweight": 2, "exclude": 3}[a]
        ax.scatter(sub["maturity_years"], np.full(len(sub), y) + np.linspace(-0.2, 0.2, len(sub)), s=14, color=palette[a], alpha=0.8)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(actions)
    ax.set_xlabel("Maturity (years)")
    ax.set_title("Where the actions fall on the curve")
    return _save(fig, path)


def chart_sensitivity(deltas: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    cols = [c for c in deltas.columns if c not in ("maturity_years", "noise_std")]
    cmap = plt.get_cmap("tab10")
    for k, c in enumerate(cols):
        ax.plot(deltas["maturity_years"], deltas[c], lw=1.2, color=cmap(k % 10), label=c)
    if "noise_std" in deltas:
        ax.fill_between(deltas["maturity_years"], -deltas["noise_std"], deltas["noise_std"], color="#999999", alpha=0.25, label="+/- 1 sd quote-noise bootstrap")
    ax.axhline(0, color="black", lw=0.8)
    vals = deltas[cols].to_numpy(dtype=float)
    limit = float(np.nanmax(np.abs(vals))) if vals.size else 1.0
    if limit > 10.0:
        ax.set_ylim(-10.5, 10.5)
        ax.text(0.01, 0.98, f"y-axis clipped at +/-10bp (largest change {limit:.1f}bp)", transform=ax.transAxes, va="top", fontsize=8, color="#b23a48")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Zero-rate change vs. selected fit (bp)")
    ax.set_title("Sensitivity of the zero curve to modelling choices")
    ax.legend(fontsize=7, ncol=3)
    return _save(fig, path)


def chart_risk(risk: pd.DataFrame, path: Path) -> Path:
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    for t in ("deposit", "ois_swap", "bond"):
        sub = risk[risk["instrument_type"] == t]
        if len(sub):
            ax.scatter(sub["maturity_years"], sub["dv01"], s=14, color=COLORS[t], label=TYPE_LABEL[t])
    ax.set_yscale("symlog", linthresh=1.0)
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Receiver DV01 per 1bp (currency units, symlog)")
    ax.set_title("Parallel DV01 (notional 1e6 rates, face 100 bonds)")
    ax.legend(fontsize=8)
    ax = axes[1]
    sub = risk[risk["instrument_type"] == "ois_swap"].copy()
    if len(sub):
        sub["maturity_years"] = sub["maturity_years"].round(4)
        sub = sub.groupby("maturity_years", as_index=False)[["dv01", "key_2y", "key_5y", "key_10y", "key_30y"]].median().sort_values("maturity_years")
        share = sub[["key_2y", "key_5y", "key_10y", "key_30y"]].div(sub["dv01"], axis=0)
        bottom = np.zeros(len(sub))
        cmap = plt.get_cmap("Blues")
        for k, col in enumerate(["key_2y", "key_5y", "key_10y", "key_30y"]):
            ax.bar(np.arange(len(sub)), share[col].values, bottom=bottom, color=cmap(0.3 + 0.18 * k), label=col)
            bottom += share[col].values
        ax.set_xticks(np.arange(len(sub)))
        ax.set_xticklabels([f"{m:g}" for m in sub["maturity_years"]], rotation=90, fontsize=6)
    ax.set_xlabel("OIS maturity (years)")
    ax.set_ylabel("Share of DV01")
    ax.set_title("Key-rate decomposition of OIS DV01 (tent bumps)")
    ax.legend(fontsize=7, loc="lower right")
    return _save(fig, path)
