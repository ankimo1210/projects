"""Publication-style Matplotlib figures generated from saved experiment data."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .config import ProjectConfig
from .simulation import simulate_gbm
from .training import checkpoint_directory

COLORS = {
    "neural_mse": "#2563EB",
    "black_scholes_delta": "#111827",
    "black_scholes_band": "#D97706",
    "no_hedge": "#9CA3AF",
    "entropic": "#BE185D",
}
LABELS = {
    "neural_mse": "Neural hedge (MSE)",
    "black_scholes_delta": "Black–Scholes delta",
    "black_scholes_band": "Black–Scholes band",
    "no_hedge": "No hedge",
}


def apply_style() -> None:
    """Apply one restrained visual system to all exported figures."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#374151",
            "axes.grid": True,
            "grid.color": "#E5E7EB",
            "grid.linewidth": 0.7,
            "axes.titleweight": "semibold",
            "font.size": 10,
            "legend.frameon": False,
            "savefig.bbox": "tight",
        }
    )


def save_figure(figure: Figure, base_path: str | Path) -> tuple[Path, Path]:
    """Save a figure as both PNG and SVG."""
    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)
    png, svg = base.with_suffix(".png"), base.with_suffix(".svg")
    figure.savefig(png, dpi=150)
    figure.savefig(svg)
    return png, svg


def training_diagram() -> Figure:
    """Visualize the differentiable training path."""
    figure, axis = plt.subplots(figsize=(11, 2.6))
    axis.axis("off")
    labels = [
        "Fresh GBM\npaths",
        "Shared neural\npolicy",
        "Pathwise trades\n& costs",
        "Terminal hedge\nloss",
        "Risk objective\n& backprop",
    ]
    x_positions = np.linspace(0.08, 0.92, len(labels))
    for index, (x_pos, label) in enumerate(zip(x_positions, labels, strict=True)):
        axis.text(
            x_pos,
            0.52,
            label,
            ha="center",
            va="center",
            transform=axis.transAxes,
            bbox={"boxstyle": "round,pad=0.55", "facecolor": "#EFF6FF", "edgecolor": "#2563EB"},
        )
        if index < len(labels) - 1:
            axis.annotate(
                "",
                xy=(x_positions[index + 1] - 0.09, 0.52),
                xytext=(x_pos + 0.09, 0.52),
                xycoords=axis.transAxes,
                arrowprops={"arrowstyle": "->", "color": "#374151", "lw": 1.5},
            )
    axis.annotate(
        "gradient through every hedge date",
        xy=(0.28, 0.22),
        xytext=(0.75, 0.22),
        xycoords=axis.transAxes,
        arrowprops={"arrowstyle": "->", "color": "#BE185D", "lw": 1.5},
        ha="center",
        color="#BE185D",
    )
    figure.suptitle("Deep Hedging training loop")
    return figure


def sample_paths_figure(config: ProjectConfig, n_paths: int = 24) -> Figure:
    paths = simulate_gbm(config.market, n_paths, seed=config.market.seed + 40_000).numpy()
    days = np.arange(config.market.n_steps + 1)
    figure, axis = plt.subplots(figsize=(8.5, 4.5))
    axis.plot(days, paths.T, alpha=0.45, lw=1)
    axis.axhline(config.market.strike, color="#111827", ls="--", lw=1, label="Strike")
    axis.set(title="Sample physical-measure GBM paths", xlabel="Trading day", ylabel="Spot price")
    axis.legend()
    return figure


def payoff_figure(config: ProjectConfig) -> Figure:
    spots = np.linspace(60, 140, 300)
    payoff = np.maximum(spots - config.market.strike, 0)
    figure, axis = plt.subplots(figsize=(7.5, 4.2))
    axis.plot(spots, payoff, color="#2563EB", lw=2)
    axis.axvline(config.market.strike, color="#111827", ls="--", lw=1)
    axis.set(
        title="European call payoff at maturity",
        xlabel="Terminal spot",
        ylabel="Call payoff per option",
    )
    return figure


def training_history_figure(history: pd.DataFrame, objective: str = "MSE") -> Figure:
    figure, axis = plt.subplots(figsize=(8.5, 4.5))
    train = history.dropna(subset=["train_objective"])
    axis.plot(train["epoch"], train["train_objective"], label="Training", color="#2563EB")
    axis.plot(
        history["epoch"],
        history["validation_objective"],
        label="Fixed validation set",
        color="#D97706",
    )
    axis.set(title=f"Training and validation objective — {objective}", xlabel="Epoch", ylabel="Objective")
    axis.legend()
    return figure


def pnl_distribution_figure(frame: pd.DataFrame) -> Figure:
    figure, axis = plt.subplots(figsize=(9, 4.8))
    lower, upper = frame["discounted_pnl"].quantile([0.005, 0.995])
    bins = np.linspace(lower, upper, 90)
    for strategy, group in frame.groupby("strategy", sort=False):
        axis.hist(
            group["discounted_pnl"],
            bins=bins,
            density=True,
            histtype="step",
            lw=1.8,
            color=COLORS.get(strategy),
            label=LABELS.get(strategy, strategy),
        )
    axis.axvline(0, color="#111827", lw=1, ls="--")
    axis.set(
        title="Discounted economic P&L distributions",
        xlabel="P&L after costs, including initial premium",
        ylabel="Density",
    )
    axis.legend(ncol=2)
    return figure


def ecdf_figure(frame: pd.DataFrame) -> Figure:
    figure, axis = plt.subplots(figsize=(9, 4.8))
    lower = frame["discounted_pnl"].quantile(0.001)
    upper = frame["discounted_pnl"].quantile(0.25)
    for strategy, group in frame.groupby("strategy", sort=False):
        values = np.sort(group["discounted_pnl"].to_numpy())
        probabilities = np.arange(1, len(values) + 1) / len(values)
        axis.plot(values, probabilities, color=COLORS.get(strategy), label=LABELS.get(strategy, strategy))
    axis.set_xlim(lower, upper)
    axis.set_ylim(0, 0.25)
    axis.set(
        title="Lower-tail empirical CDF",
        xlabel="Discounted P&L after costs, including premium",
        ylabel="Cumulative probability",
    )
    axis.legend(ncol=2)
    return figure


def var_cvar_figure(summary: pd.DataFrame) -> Figure:
    ordered = [name for name in LABELS if name in summary.index]
    x = np.arange(len(ordered))
    width = 0.36
    figure, axis = plt.subplots(figsize=(8.5, 4.6))
    axis.bar(x - width / 2, summary.loc[ordered, "var_loss_99"], width, label="99% VaR", color="#93C5FD")
    axis.bar(x + width / 2, summary.loc[ordered, "cvar_loss_99"], width, label="99% CVaR", color="#2563EB")
    axis.set_xticks(x, [LABELS[name] for name in ordered], rotation=12, ha="right")
    axis.set(title="99% tail loss by strategy", ylabel="Discounted economic loss")
    axis.legend()
    return figure


def turnover_cost_figure(summary: pd.DataFrame) -> Figure:
    ordered = [name for name in LABELS if name in summary.index]
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    labels = [LABELS[name] for name in ordered]
    axes[0].barh(labels, summary.loc[ordered, "average_turnover_shares"], color="#2563EB")
    axes[0].set(title="Average turnover", xlabel="Shares per path")
    axes[1].barh(labels, summary.loc[ordered, "average_discounted_transaction_cost"], color="#D97706")
    axes[1].set(title="Average transaction cost", xlabel="Discounted currency units")
    figure.suptitle("Trading intensity and cost at 5 bp")
    figure.tight_layout()
    return figure


def _surface_grid(surface: pd.DataFrame, value: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pivot = surface.pivot(index="tau_normalized", columns="spot", values=value).sort_index()
    return pivot.columns.to_numpy(), pivot.index.to_numpy(), pivot.to_numpy()


def policy_heatmap_figure(surface: pd.DataFrame, *, difference: bool = False) -> Figure:
    field = "difference" if difference else "neural_delta"
    spots, taus, values = _surface_grid(surface, field)
    figure, axis = plt.subplots(figsize=(8.6, 5.2))
    maximum = np.max(np.abs(values)) if difference else None
    image = axis.imshow(
        values,
        origin="lower",
        aspect="auto",
        extent=[spots.min(), spots.max(), taus.min(), taus.max()],
        cmap="RdBu_r" if difference else "viridis",
        vmin=-maximum if difference else None,
        vmax=maximum if difference else None,
    )
    title = "Neural hedge minus Black–Scholes delta" if difference else "Neural hedge policy"
    axis.set(title=title, xlabel="Spot", ylabel="Normalized time to maturity")
    figure.colorbar(image, ax=axis, label="Delta difference" if difference else "Stock position")
    axis.text(
        0.01,
        -0.15,
        "Conditioned on previous hedge = 0.5 shares, volatility = 20%, cost = 5 bp",
        transform=axis.transAxes,
        fontsize=9,
        color="#4B5563",
    )
    return figure


def policy_slices_figure(surface: pd.DataFrame) -> Figure:
    figure, axis = plt.subplots(figsize=(8.6, 4.8))
    available = np.sort(surface["tau_normalized"].unique())
    for requested, color in zip((0.1, 0.3, 0.6, 1.0), ("#BE185D", "#D97706", "#2563EB", "#111827"), strict=True):
        tau = available[np.argmin(np.abs(available - requested))]
        subset = surface[np.isclose(surface["tau_normalized"], tau)]
        axis.plot(subset["spot"], subset["neural_delta"], color=color, label=f"Neural τ/T={tau:.2f}")
    maturity = available[np.argmin(np.abs(available - 0.6))]
    subset = surface[np.isclose(surface["tau_normalized"], maturity)]
    axis.plot(subset["spot"], subset["black_scholes_delta"], color="#6B7280", ls="--", label="BS delta (τ/T≈0.6)")
    axis.set(title="Neural policy slices across maturity", xlabel="Spot", ylabel="Stock position")
    axis.legend(ncol=2)
    return figure


def trade_scatter_figure(scatter: pd.DataFrame) -> Figure:
    figure, axis = plt.subplots(figsize=(7.4, 5.3))
    points = axis.scatter(
        scatter["previous_delta"],
        scatter["black_scholes_target"],
        c=scatter["neural_trade_size"],
        cmap="RdBu_r",
        s=12,
        alpha=0.55,
    )
    axis.set(
        title="Neural trade conditional on prior position and BS target",
        xlabel="Previous stock position",
        ylabel="Black–Scholes target",
    )
    figure.colorbar(points, ax=axis, label="Neural trade size")
    return figure


def sensitivity_figure(sensitivity: pd.DataFrame) -> Figure:
    figure, axes = plt.subplots(2, 2, figsize=(10, 7.2), sharex=True)
    specs = [
        ("std_discounted_pnl_after_costs_including_premium", "P&L standard deviation"),
        ("cvar_loss_99", "99% CVaR loss"),
        ("average_turnover_shares", "Average turnover (shares)"),
        ("average_discounted_transaction_cost", "Average transaction cost"),
    ]
    for axis, (column, title) in zip(axes.flat, specs, strict=True):
        axis.plot(sensitivity["transaction_cost_bps"], sensitivity[column], marker="o", color="#2563EB")
        axis.set(title=title, xlabel="Transaction cost (bp)")
    figure.suptitle("Neural hedge sensitivity to proportional transaction cost")
    figure.tight_layout()
    return figure


def risk_objective_figure(risk: pd.DataFrame) -> Figure:
    columns = [
        "std_discounted_pnl_after_costs_including_premium",
        "cvar_loss_99",
        "average_turnover_shares",
    ]
    labels = ["P&L std", "99% CVaR loss", "Turnover"]
    values = risk.set_index("objective")[columns]
    normalized = values / values.loc["mse"]
    figure, axis = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(labels))
    width = 0.35
    for offset, objective in enumerate(normalized.index):
        axis.bar(
            x + (offset - (len(normalized) - 1) / 2) * width,
            normalized.loc[objective],
            width,
            label=objective,
            color="#2563EB" if objective == "mse" else "#BE185D",
        )
    axis.axhline(1, color="#111827", ls="--", lw=1)
    axis.set_xticks(x, labels)
    axis.set(title="Risk-objective comparison relative to MSE", ylabel="Ratio to MSE")
    axis.legend()
    return figure


def generate_static_figures(
    config: ProjectConfig,
    project_root: str | Path,
    manifest: dict[str, Path],
) -> dict[str, Path]:
    """Generate and save all required static figures from durable artifacts."""
    apply_style()
    root = Path(project_root)
    output = root / config.output.artifacts_dir / "figures"
    frame = pd.read_csv(manifest["main_path_results"])
    summary = pd.read_csv(manifest["strategy_summary"], index_col=0)
    sensitivity = pd.read_csv(manifest["sensitivity_summary"])
    risk = pd.read_csv(manifest["risk_objective_summary"])
    surface = pd.read_csv(manifest["policy_surface"])
    scatter = pd.read_csv(manifest["trade_scatter"])
    history = pd.read_csv(
        checkpoint_directory(config.with_risk(objective="mse"), root) / "history.csv"
    )
    builders: dict[str, Figure] = {
        "training_diagram": training_diagram(),
        "sample_paths": sample_paths_figure(config),
        "call_payoff": payoff_figure(config),
        "training_history": training_history_figure(history),
        "pnl_distribution": pnl_distribution_figure(frame),
        "tail_ecdf": ecdf_figure(frame),
        "var_cvar": var_cvar_figure(summary),
        "turnover_cost": turnover_cost_figure(summary),
        "policy_heatmap": policy_heatmap_figure(surface),
        "policy_difference_heatmap": policy_heatmap_figure(surface, difference=True),
        "policy_slices": policy_slices_figure(surface),
        "trade_scatter": trade_scatter_figure(scatter),
        "cost_sensitivity": sensitivity_figure(sensitivity),
        "risk_objective": risk_objective_figure(risk),
    }
    paths: dict[str, Path] = {}
    for name, figure in builders.items():
        png, svg = save_figure(figure, output / name)
        paths[f"{name}_png"] = png
        paths[f"{name}_svg"] = svg
        plt.close(figure)
    (output / "chart_map.json").write_text(
        json.dumps(
            {
                name: {
                    "png": str(paths[f"{name}_png"]),
                    "svg": str(paths[f"{name}_svg"]),
                }
                for name in builders
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths
