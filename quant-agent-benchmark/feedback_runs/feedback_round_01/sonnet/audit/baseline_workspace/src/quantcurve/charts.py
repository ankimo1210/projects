"""Matplotlib chart generation for the CLI workflow and HTML report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLOR_BASELINE = "#5b7ea6"
COLOR_ADVANCED = "#c65d3b"
COLOR_HOLDOUT = "#d1495b"
TYPE_COLORS = {"deposit": "#4f8a6f", "ois_swap": "#5b7ea6", "bond": "#c65d3b"}


def _style_ax(ax) -> None:
    ax.grid(True, alpha=0.3, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_curve(grid: np.ndarray, baseline_curve, advanced_curve, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    z_base = baseline_curve.zero_rate(grid) * 100.0
    z_adv = advanced_curve.zero_rate(grid) * 100.0
    d_base = baseline_curve.discount(grid)
    d_adv = advanced_curve.discount(grid)

    ax = axes[0]
    ax.plot(grid, z_base, label="Baseline (piecewise-linear)", color=COLOR_BASELINE, linewidth=1.6)
    ax.plot(grid, z_adv, label="Advanced (regularised spline)", color=COLOR_ADVANCED, linewidth=1.6)
    ax.axhline(0.0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Zero rate (%, cont. comp.)")
    ax.set_title("Zero curve")
    ax.legend(frameon=False, fontsize=8)
    _style_ax(ax)

    ax = axes[1]
    ax.plot(grid, d_base, label="Baseline", color=COLOR_BASELINE, linewidth=1.6)
    ax.plot(grid, d_adv, label="Advanced", color=COLOR_ADVANCED, linewidth=1.6)
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Discount factor")
    ax.set_title("Discount factor")
    ax.legend(frameon=False, fontsize=8)
    _style_ax(ax)

    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_forward(grid: np.ndarray, baseline_curve, advanced_curve, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    f_base = baseline_curve.forward_rate(grid) * 100.0
    f_adv = advanced_curve.forward_rate(grid) * 100.0
    ax.plot(grid, f_base, label="Baseline (kinked)", color=COLOR_BASELINE, linewidth=1.4)
    ax.plot(grid, f_adv, label="Advanced (smooth)", color=COLOR_ADVANCED, linewidth=1.6)
    ax.axhline(0.0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Instantaneous forward rate (%)")
    ax.set_title("Instantaneous forward rate")
    ax.legend(frameon=False, fontsize=8)
    _style_ax(ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_repricing(repricing_df: pd.DataFrame, maturities: pd.Series, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    df = repricing_df.copy()
    df["maturity_years"] = maturities.values
    for itype, sub in df.groupby("instrument_type"):
        train_sub = sub[sub["split"] == "train"]
        holdout_sub = sub[sub["split"] == "holdout"]
        ax.scatter(
            train_sub["maturity_years"], train_sub["residual"], s=22, alpha=0.75,
            color=TYPE_COLORS.get(itype, "#666666"), label=f"{itype} (train)", marker="o",
        )
        if len(holdout_sub):
            ax.scatter(
                holdout_sub["maturity_years"], holdout_sub["residual"], s=42, alpha=0.9,
                color=TYPE_COLORS.get(itype, "#666666"), label=f"{itype} (holdout)", marker="^",
                edgecolors="black", linewidths=0.5,
            )
    ax.axhline(0.0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Residual (market - model; % pts for rates, price pts for bonds)")
    ax.set_title("Repricing residuals (selected model)")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    _style_ax(ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_model_comparison(comparison: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    labels = ["Baseline", "Advanced"]
    train_vals = [comparison["baseline"]["train_weighted_rmse"], comparison["advanced"]["train_weighted_rmse"]]
    holdout_vals = [comparison["baseline"]["holdout_weighted_rmse"], comparison["advanced"]["holdout_weighted_rmse"]]
    x = np.arange(len(labels))
    width = 0.32
    ax.bar(x - width / 2, train_vals, width, label="Train", color="#8fb3d9")
    ax.bar(x + width / 2, holdout_vals, width, label="Holdout", color=COLOR_HOLDOUT)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Weighted RMSE (combined rate-space units)")
    ax.set_title(f"Model comparison (selected: {comparison['model_selected']})")
    ax.legend(frameon=False, fontsize=8)
    _style_ax(ax)

    ax = axes[1]
    grid = comparison["advanced"].get("_lambda_grid")
    if grid:
        lambdas = [g["lambda"] for g in grid]
        holdouts = [g["holdout_wrmse"] for g in grid]
        xs = np.where(np.array(lambdas) > 0, lambdas, 1e-1)
        ax.plot(xs, holdouts, marker="o", color=COLOR_ADVANCED, linewidth=1.4, markersize=4)
        ax.set_xscale("log")
        ax.set_xlabel("Regularisation strength (lambda, log scale; leftmost = 0)")
        ax.set_ylabel("Holdout weighted RMSE")
        ax.set_title("Advanced model: regularisation sweep")
        _style_ax(ax)
    else:
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
