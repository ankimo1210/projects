"""Publication-style static figures built only from saved experiment data."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import Config
from .provenance import artifact_dirs, generated_at, git_commit

# Okabe–Ito chromatic slots only: the achromatic gray fails the series-color
# chroma floor (validated with the dataviz palette checker; worst adjacent
# CVD dE 17.9). Sub-3:1 slots (orange, sky blue) are relieved by the data
# tables and direct labels that accompany every comparison.
PALETTE = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
)

STRATEGY_LABELS = {
    "immediate": "Immediate",
    "twap": "TWAP",
    "vwap": "VWAP",
    "pov": "POV",
    "ac": "Almgren–Chriss",
    "ow": "Resilience-aware",
    "twap_mkt": "TWAP market",
    "ac_mkt": "AC market",
    "pov_mkt": "POV market",
    "limit_only": "Limit only",
    "heuristic": "Mixed heuristic",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (9.0, 5.4),
            "figure.dpi": 120,
            "savefig.dpi": 160,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
            "legend.frameon": False,
            "lines.linewidth": 2.0,
        }
    )


def _save(fig: plt.Figure, cfg: Config, stem: str, title: str) -> list[Path]:
    out_dir = artifact_dirs(cfg)["figures"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at()
    commit = git_commit() or "uncommitted"
    description = (
        f"optimal_execution; profile={cfg.profile}; seed={cfg.seed}; "
        f"generated_at={stamp}; git_commit={commit}"
    )
    paths: list[Path] = []
    for suffix in ("png", "svg"):
        path = out_dir / f"{stem}.{suffix}"
        metadata = {
            "Title": title,
            "Creator": "optimal_execution",
            "Description": description,
        }
        fig.savefig(path, bbox_inches="tight", facecolor="white", metadata=metadata)
        paths.append(path)
    plt.close(fig)
    return paths


def _read_csv(cfg: Config, area: str, name: str) -> pd.DataFrame:
    return pd.read_csv(artifact_dirs(cfg)[area] / name)


def generate_classical_figures(cfg: Config) -> list[Path]:
    """Figures for Experiments A--E plus market-state diagnostics."""
    _style()
    made: list[Path] = []

    sensitivity = _read_csv(cfg, "data", "ac_sensitivity.csv")
    lam = sensitivity[sensitivity["parameter"] == "risk_aversion_lambda"]
    fig, ax = plt.subplots()
    for color, (value, group) in zip(PALETTE, lam.groupby("value", sort=True), strict=False):
        ax.plot(
            group["time_fraction"],
            group["inventory_fraction"],
            color=color,
            label=f"lambda={value:.1e}",
        )
    ax.set(
        title="Almgren–Chriss inventory trajectories",
        xlabel="Time / horizon",
        ylabel="Inventory / initial inventory",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.legend(ncol=2)
    made += _save(fig, cfg, "ac_trajectories", "Almgren–Chriss trajectories")

    frontier = _read_csv(cfg, "data", "efficient_frontier.csv")
    fig, ax = plt.subplots()
    sc = ax.scatter(
        frontier["cost_sd_bps"],
        frontier["expected_cost_bps"],
        c=np.log10(frontier["lambda"]),
        cmap="viridis",
        s=40,
    )
    ax.plot(frontier["cost_sd_bps"], frontier["expected_cost_bps"], color="#4D4D4D", alpha=0.55)
    ax.set(
        title="Impact–timing-risk efficient frontier",
        xlabel="Timing risk, standard deviation (bps)",
        ylabel="Expected cost (bps)",
    )
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("log10 risk aversion")
    made += _save(fig, cfg, "efficient_frontier", "Efficient frontier")

    impact = _read_csv(cfg, "data", "impact_model_comparison.csv")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for color, (name, group) in zip(
        PALETTE, impact.groupby("impact_model", sort=False), strict=False
    ):
        ax1.plot(
            group["time_s"],
            group["execution_price"],
            label=name.replace("_", " ").title(),
            color=color,
        )
        ax2.plot(
            group["time_s"],
            group["impacted_mid"],
            label=name.replace("_", " ").title(),
            color=color,
        )
    ax1.set(title="Execution price by impact channel", ylabel="Price")
    ax2.set(xlabel="Time (s)", ylabel="Impacted mid")
    ax1.legend(ncol=2)
    made += _save(fig, cfg, "impact_channels", "Impact channel comparison")

    recovery = _read_csv(cfg, "data", "impact_recovery.csv")
    fig, ax = plt.subplots()
    for color, (rho, group) in zip(PALETTE, recovery.groupby("rho", sort=True), strict=False):
        ax.plot(group["time_after_s"], group["displacement"], color=color, label=f"rho={rho:g} 1/s")
    ax.set(
        title="Transient-impact recovery",
        xlabel="Time after final trade (s)",
        ylabel="Adverse displacement (price/share)",
    )
    ax.legend()
    made += _save(fig, cfg, "impact_recovery", "Transient-impact recovery")

    schedules = _read_csv(cfg, "data", "classical_schedules.csv")
    fig, ax = plt.subplots()
    for color, (name, group) in zip(
        PALETTE, schedules.groupby("strategy_id", sort=False), strict=False
    ):
        ax.step(
            group["time_s"],
            group["inventory_fraction"],
            where="post",
            label=STRATEGY_LABELS.get(name, name),
            color=color,
        )
    ax.set(
        title="Static execution schedules",
        xlabel="Time (s)",
        ylabel="Inventory / initial inventory",
    )
    ax.legend(ncol=2)
    made += _save(fig, cfg, "strategy_schedules", "Static strategy schedules")

    path = artifact_dirs(cfg)["data"] / "classical_path_tca.parquet"
    tca = pd.read_parquet(path)
    fig, ax = plt.subplots()
    for color, (name, group) in zip(PALETTE, tca.groupby("strategy_id", sort=False), strict=False):
        x = np.sort(group["is_bps"].to_numpy())
        y = np.arange(1, len(x) + 1) / len(x)
        ax.plot(x, y, label=STRATEGY_LABELS.get(name, name), color=color)
    ax.set(
        title="Implementation-shortfall distributions",
        xlabel="Implementation shortfall (bps; higher is worse)",
        ylabel="Empirical CDF",
    )
    ax.legend(ncol=2)
    made += _save(fig, cfg, "is_distributions", "Implementation-shortfall ECDF")

    summary = _read_csv(cfg, "metrics", "classical_strategy_summary.csv")
    component_cols = [c for c in summary if c.startswith("mean_comp_")]
    if component_cols:
        names = summary["strategy_id"].tolist()
        fig, ax = plt.subplots(figsize=(10, 5.8))
        positive_bottom = np.zeros(len(summary))
        negative_bottom = np.zeros(len(summary))
        for color, col in zip(PALETTE, component_cols, strict=False):
            values = summary[col].fillna(0.0).to_numpy()
            bottom = np.where(values >= 0, positive_bottom, negative_bottom)
            ax.bar(
                names,
                values,
                bottom=bottom,
                label=col.removeprefix("mean_comp_").replace("_bps", ""),
                color=color,
            )
            positive_bottom += np.maximum(values, 0.0)
            negative_bottom += np.minimum(values, 0.0)
        ax.set(title="Mean synthetic cost decomposition", xlabel="Strategy ID", ylabel="Cost (bps)")
        ax.tick_params(axis="x", rotation=30)
        ax.legend(ncol=3)
        made += _save(fig, cfg, "tca_decomposition", "TCA cost decomposition")

    sqrt_frame = _read_csv(cfg, "data", "sqrt_impact.csv")
    fig, ax = plt.subplots()
    ax.plot(sqrt_frame["participation_adv"], sqrt_frame["impact_bps"], color=PALETTE[0])
    ax.scatter(
        [cfg.initial_inventory / cfg.average_daily_volume],
        [
            float(
                np.interp(
                    cfg.initial_inventory / cfg.average_daily_volume,
                    sqrt_frame["participation_adv"],
                    sqrt_frame["impact_bps"],
                )
            )
        ],
        color=PALETTE[1],
        label="Default order",
        zorder=3,
    )
    ax.set(
        title="Square-root impact diagnostic",
        xlabel="Order size / ADV",
        ylabel="Impact (bps of price)",
    )
    ax.legend()
    made += _save(fig, cfg, "sqrt_impact", "Square-root impact diagnostic")

    scenario_path = artifact_dirs(cfg)["data"] / "scenario_sample.npz"
    sample = np.load(scenario_path)
    mids = sample["unaffected_mid"]
    fig, ax = plt.subplots()
    time = np.linspace(0, cfg.horizon_seconds, mids.shape[1])
    for i in range(min(len(PALETTE), len(mids))):
        ax.plot(time, mids[i], color=PALETTE[i], alpha=0.78, label=f"Path {i + 1}")
    ax.set(title="Synthetic unaffected mid-price paths", xlabel="Time (s)", ylabel="Price")
    ax.legend(ncol=2)
    made += _save(fig, cfg, "unaffected_price_paths", "Unaffected price paths")
    return made


def generate_lob_figures(cfg: Config) -> list[Path]:
    """Figures for Experiments F--G."""
    _style()
    made: list[Path] = []
    trace = _read_csv(cfg, "data", "lob_trace_sample.csv")
    if trace.empty:
        return made
    preferred = (
        "heuristic" if "heuristic" in set(trace["strategy_id"]) else trace["strategy_id"].iloc[0]
    )
    one = trace[(trace["strategy_id"] == preferred) & (trace["episode"] == 0)]

    fig, ax = plt.subplots()
    ax.plot(one["time_s"], one["bid_depth"], label="Bid depth", color=PALETTE[0])
    ax.plot(one["time_s"], one["ask_depth"], label="Ask depth", color=PALETTE[1])
    ax.fill_between(one["time_s"], one["bid_depth"], one["ask_depth"], color="#BBBBBB", alpha=0.12)
    ax.set(
        title=f"Reactive LOB depth — {preferred}",
        xlabel="Time (s)",
        ylabel="Displayed L1 depth (shares)",
    )
    ax.legend()
    made += _save(fig, cfg, "lob_depth", "Reactive limit-order-book depth")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax1.plot(one["time_s"], one["imbalance"], color=PALETTE[2])
    ax1.axhline(0, color="#777777", linewidth=1)
    ax1.set(title="Queue imbalance and transient impact", ylabel="Queue imbalance")
    ax2.plot(one["time_s"], one["transient_impact"], color=PALETTE[1])
    ax2.set(xlabel="Time (s)", ylabel="Transient displacement")
    made += _save(fig, cfg, "queue_imbalance", "Queue imbalance and transient impact")

    lob_path = artifact_dirs(cfg)["data"] / "lob_path_tca.parquet"
    lob = pd.read_parquet(lob_path)
    fig, ax = plt.subplots()
    groups = ["twap_mkt", "limit_only", "heuristic"]
    values = [lob.loc[lob["strategy_id"] == name, "is_bps"].to_numpy() for name in groups]
    ax.boxplot(values, tick_labels=groups, showfliers=False)
    ax.set(
        title="Market versus limit-order execution",
        xlabel="Strategy ID",
        ylabel="Implementation shortfall (bps)",
    )
    made += _save(fig, cfg, "market_vs_limit", "Market versus limit orders")

    reactive = _read_csv(cfg, "metrics", "reactive_comparison.csv")
    fig, ax = plt.subplots()
    x = np.arange(len(reactive))
    ax.bar(x, reactive["is_mean_bps"], color=[PALETTE[0], PALETTE[1]][: len(reactive)])
    ax.set_xticks(x, reactive["mode"])
    ax.set(
        title="Reactive simulator versus non-reactive replay",
        xlabel="Simulator mode",
        ylabel="Mean implementation shortfall (bps)",
    )
    made += _save(fig, cfg, "reactive_vs_replay", "Reactive versus replay simulator")
    return made


def generate_evaluation_figures(cfg: Config) -> list[Path]:
    """Figures for Experiments H--J."""
    _style()
    made: list[Path] = []
    history = _read_csv(cfg, "metrics", "rl_training_history.csv")
    fig, ax = plt.subplots()
    for color, (run, group) in zip(PALETTE, history.groupby("run_id", sort=False), strict=False):
        ax.plot(
            group["episodes"],
            group["train_is_ma_bps"],
            color=color,
            alpha=0.7,
            label=f"{run} train",
        )
        valid = group[np.isfinite(group["val_is_bps"])]
        if not valid.empty:
            ax.scatter(valid["episodes"], valid["val_is_bps"], color=color, marker="o", s=34)
    ax.set(
        title="RL training and validation",
        xlabel="Training episodes",
        ylabel="Implementation shortfall (bps)",
    )
    ax.legend(fontsize=8, ncol=2)
    made += _save(fig, cfg, "rl_training_history", "RL training history")

    stress = _read_csv(cfg, "metrics", "stress_summary.csv")
    pivot = stress.pivot(index="strategy_id", columns="regime", values="is_mean_bps")
    fig, ax = plt.subplots(figsize=(10, max(4.8, 0.5 * len(pivot))))
    im = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="magma")
    ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
    ax.set(title="Out-of-sample mean execution cost", xlabel="Regime", ylabel="Strategy ID")
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            values = pivot.to_numpy()
            cut = np.nanmin(values) + 0.68 * (np.nanmax(values) - np.nanmin(values))
            ax.text(
                j,
                i,
                f"{val:.2f}",
                ha="center",
                va="center",
                color="black" if val >= cut else "white",
                fontsize=8,
            )
    fig.colorbar(im, ax=ax, label="Mean IS (bps)")
    made += _save(fig, cfg, "stress_test_heatmap", "Stress-test heatmap")

    ablation = _read_csv(cfg, "metrics", "ablation_summary.csv")
    fig, ax = plt.subplots()
    ordered = ablation.sort_values("delta_vs_full_bps")
    ax.barh(ordered["feature_removed"], ordered["delta_vs_full_bps"], color=PALETTE[0])
    ax.axvline(0, color="#555555", linewidth=1)
    ax.set(
        title="Residual-RL feature ablation",
        xlabel="Change in mean IS versus matched-budget full model (bps)",
        ylabel="Feature removed",
    )
    made += _save(fig, cfg, "feature_ablation", "Feature ablation")

    miss = _read_csv(cfg, "metrics", "misspecification_summary.csv")
    fig, ax = plt.subplots()
    order = miss.sort_values("is_mean_bps")
    ax.bar(order["strategy_id"], order["is_mean_bps"], color=PALETTE[1])
    ax.set(title="Model-misspecification test", xlabel="Strategy ID", ylabel="Mean IS (bps)")
    ax.tick_params(axis="x", rotation=30)
    made += _save(fig, cfg, "model_misspecification", "Model misspecification")
    return made
