"""Chart generation.

Matplotlib is driven through the non-interactive Agg backend so the workflow
runs headless and deterministically.  Every chart is written as a PNG and
returned as raw bytes as well, so the HTML report can embed it and remain a
single self-contained file.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .workflow import WorkflowResult  # noqa: E402

__all__ = ["PALETTE", "write_charts"]

#: A small, colour-blind-safe palette used consistently across every chart.
PALETTE = {
    "ink": "#1c1f26",
    "muted": "#6b7280",
    "grid": "#e2e5ea",
    "series_1": "#1f4e79",   # advanced / primary
    "series_2": "#c2622d",   # baseline / secondary
    "deposit": "#2f6f4f",
    "ois_swap": "#1f4e79",
    "bond": "#c2622d",
    "excluded": "#a02c2c",
    "band": "#cbd5e1",
}

TYPE_LABEL = {"deposit": "Deposit", "ois_swap": "OIS swap", "bond": "Bond"}

_FIGSIZE = (9.0, 5.0)
_DPI = 130


def _style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=12, color=PALETTE["ink"], pad=10, loc="left")
    ax.set_xlabel(xlabel, fontsize=10, color=PALETTE["muted"])
    ax.set_ylabel(ylabel, fontsize=10, color=PALETTE["muted"])
    ax.grid(True, color=PALETTE["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(PALETTE["grid"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=9)


def _save(fig, path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    # ``Software: None`` strips the only non-deterministic PNG metadata field
    # matplotlib writes, so two runs of the same workflow produce byte-identical
    # charts regardless of the installed matplotlib version.
    fig.savefig(
        path, dpi=_DPI, format="png", facecolor="white",
        metadata={"Software": None},
    )
    plt.close(fig)
    return path.read_bytes()


def _zero_curve_chart(result: WorkflowResult, path: Path) -> bytes:
    grid = result.grid
    advanced = result.comparison.advanced_full.curve
    baseline = result.comparison.baseline_full.curve
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.plot(grid, np.asarray(advanced.zero(grid)) * 100, color=PALETTE["series_1"],
            linewidth=2.0, label="Advanced: penalised robust spline")
    ax.plot(grid, np.asarray(baseline.zero(grid)) * 100, color=PALETTE["series_2"],
            linewidth=1.4, linestyle="--", label="Baseline: bootstrap")
    for kind in ("deposit", "ois_swap", "bond"):
        subset = [i for i in result.instruments if i.instrument_type == kind]
        if not subset:
            continue
        x = np.array([i.maturity_years for i in subset])
        y = np.array(
            [float(result.curve.zero(np.array([i.maturity_years]))[0]) for i in subset]
        ) * 100
        ax.scatter(x, y, s=18, color=PALETTE[kind], alpha=0.75, zorder=3,
                   label=f"{TYPE_LABEL[kind]} maturity", edgecolors="none")
    selected = result.comparison.selected
    _style(
        ax,
        f"Continuously compounded zero curve  (published model: {selected})",
        "Maturity (years)",
        "Zero rate (%)",
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right", ncols=2)
    return _save(fig, path)


def _forward_chart(result: WorkflowResult, path: Path) -> bytes:
    grid = result.grid
    advanced = result.comparison.advanced_full.curve
    baseline = result.comparison.baseline_full.curve
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9.0, 6.4), sharex=True, height_ratios=[2, 1]
    )
    top.plot(grid, np.asarray(advanced.forward(grid)) * 100, color=PALETTE["series_1"],
             linewidth=2.0, label="Advanced: penalised robust spline")
    top.plot(grid, np.asarray(baseline.forward(grid)) * 100, color=PALETTE["series_2"],
             linewidth=1.1, linestyle="-", alpha=0.85, label="Baseline: bootstrap")
    admissible = result.model_comparison["baseline"]["forward_admissibility"]
    top.axhspan(
        admissible["lower_bound_percent"],
        admissible["upper_bound_percent"],
        color=PALETTE["band"],
        alpha=0.35,
        zorder=0,
        label="Admissible forward band",
    )
    _style(top, "Instantaneous forward rate", "", "Forward rate (%)")
    top.legend(frameon=False, fontsize=9, loc="upper right")

    bottom.plot(grid, np.asarray(result.curve.discount(grid)), color=PALETTE["series_1"],
                linewidth=1.8)
    _style(bottom, "Discount factor (published curve)", "Maturity (years)", "D(T)")
    return _save(fig, path)


def _repricing_chart(result: WorkflowResult, path: Path) -> bytes:
    frame = result.repricing
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9.0, 6.4), sharex=True, height_ratios=[2, 1]
    )
    for kind in ("deposit", "ois_swap", "bond"):
        subset = frame[frame["instrument_type"] == kind]
        if subset.empty:
            continue
        sizes = 12.0 + 60.0 * np.clip(subset["weight"].to_numpy(), 0.0, 3.0) / 3.0
        top.scatter(subset["maturity_years"], subset["residual_bp"], s=sizes,
                    color=PALETTE[kind], alpha=0.8, edgecolors="none",
                    label=f"{TYPE_LABEL[kind]} (n={len(subset)})")
    top.axhline(0.0, color=PALETTE["muted"], linewidth=1.0)
    for level, style in ((1.0, ":"), (5.0, "--")):
        for sign in (1, -1):
            top.axhline(sign * level, color=PALETTE["muted"], linewidth=0.7,
                        linestyle=style, alpha=0.6)
    _style(
        top,
        "Repricing residuals, yield-equivalent (marker size = calibration weight)",
        "",
        "Market minus model (bp)",
    )
    # Reserve headroom so the legend never sits on top of a data point.
    limit = float(np.nanmax(np.abs(frame["residual_bp"].to_numpy()))) if len(frame) else 1.0
    limit = max(limit, 1.0)
    top.set_ylim(-1.25 * limit, 1.6 * limit)
    top.legend(frameon=False, fontsize=9, loc="upper left", ncols=3)

    bottom.bar(frame["maturity_years"], frame["weight"], width=0.28,
               color=[PALETTE[k] for k in frame["instrument_type"]], alpha=0.85)
    _style(bottom, "Calibration weight", "Maturity (years)", "Weight")
    return _save(fig, path)


def _model_comparison_chart(result: WorkflowResult, path: Path) -> bytes:
    payload = result.model_comparison
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.6))

    labels = ["train", "holdout", "full sample"]
    keys = ["train_metrics", "holdout_metrics", "full_sample_metrics"]
    base = [payload["baseline"][k].get("weighted_rmse_bp", np.nan) for k in keys]
    adv = [payload["advanced"][k].get("weighted_rmse_bp", np.nan) for k in keys]
    x = np.arange(len(labels))
    left.bar(x - 0.19, base, width=0.36, color=PALETTE["series_2"], label="Baseline")
    left.bar(x + 0.19, adv, width=0.36, color=PALETTE["series_1"], label="Advanced")
    for xi, (b, a) in enumerate(zip(base, adv)):
        for offset, value in ((-0.19, b), (0.19, a)):
            if np.isfinite(value):
                left.text(xi + offset, value, f"{value:.2f}", ha="center",
                          va="bottom", fontsize=8, color=PALETTE["ink"])
    left.set_xticks(x, labels)
    _style(left, "Weighted RMSE by sample", "", "bp")
    left.legend(frameon=False, fontsize=9)

    grid = result.grid
    advanced = result.comparison.advanced_full.curve
    baseline = result.comparison.baseline_full.curve
    delta = (np.asarray(advanced.zero(grid)) - np.asarray(baseline.zero(grid))) * 1.0e4
    right.plot(grid, delta, color=PALETTE["ink"], linewidth=1.6)
    right.axhline(0.0, color=PALETTE["muted"], linewidth=1.0)
    right.fill_between(grid, delta, 0.0, color=PALETTE["series_1"], alpha=0.15)
    _style(right, "Advanced minus baseline zero rate", "Maturity (years)", "bp")
    return _save(fig, path)


def _cleaning_chart(result: WorkflowResult, path: Path) -> bytes:
    audit = result.cleaning.audit
    order = ["keep", "correct", "downweight", "exclude"]
    counts = [int((audit["action"] == a).sum()) for a in order]
    colours = [PALETTE["series_1"], PALETTE["deposit"], PALETTE["series_2"],
               PALETTE["excluded"]]
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.4))
    bars = left.bar(order, counts, color=colours, alpha=0.9)
    for bar, value in zip(bars, counts):
        left.text(bar.get_x() + bar.get_width() / 2, value, str(value), ha="center",
                  va="bottom", fontsize=9, color=PALETTE["ink"])
    _style(left, "Cleaning decisions", "", "Observations")

    flags = result.validation_summary
    items = [(k, v) for k, v in sorted(flags.items(), key=lambda kv: -kv[1]) if v > 0]
    if items:
        names = [k.replace("_", " ") for k, _ in items][:10][::-1]
        values = [v for _, v in items][:10][::-1]
        right.barh(names, values, color=PALETTE["muted"], alpha=0.85)
        for index, value in enumerate(values):
            right.text(value, index, f" {value}", va="center", fontsize=9,
                       color=PALETTE["ink"])
    _style(right, "Validation findings", "Observations flagged", "")
    return _save(fig, path)


def _sensitivity_chart(result: WorkflowResult, path: Path) -> bytes:
    checks = result.sensitivity.get("checks", [])
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    if checks:
        names = [c["name"].replace("_", " ") for c in checks][::-1]
        values = [c["value"] for c in checks][::-1]
        ax.barh(names, values, color=PALETTE["series_1"], alpha=0.85)
        for index, value in enumerate(values):
            ax.text(value, index, f" {value:.2f}", va="center", fontsize=9,
                    color=PALETTE["ink"])
    _style(ax, "Sensitivity checks: induced zero-rate shift",
           "Maximum absolute shift on the published grid (bp)", "")
    return _save(fig, path)


def _key_rate_chart(result: WorkflowResult, path: Path) -> bytes:
    risk = result.risk
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    for column, colour, label in (
        ("key_2y", PALETTE["deposit"], "2Y key rate"),
        ("key_5y", PALETTE["series_1"], "5Y key rate"),
        ("key_10y", PALETTE["muted"], "10Y key rate"),
        ("key_30y", PALETTE["series_2"], "30Y key rate"),
    ):
        rates = risk[risk["instrument_type"] != "bond"]
        ax.plot(rates["maturity_years"], rates[column], marker="o", markersize=3,
                linewidth=1.4, color=colour, label=label)
    ax.plot(
        risk[risk["instrument_type"] != "bond"]["maturity_years"],
        risk[risk["instrument_type"] != "bond"]["dv01"],
        color=PALETTE["ink"], linewidth=1.0, linestyle="--", label="Parallel DV01",
    )
    _style(
        ax,
        "Key-rate profile of the deposit and OIS book (notional 1,000,000)",
        "Instrument maturity (years)",
        "Sensitivity per basis point",
    )
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return _save(fig, path)


def write_charts(result: WorkflowResult, charts_dir: str | Path) -> dict[str, bytes]:
    """Write every chart and return ``{filename: png bytes}``."""
    root = Path(charts_dir)
    root.mkdir(parents=True, exist_ok=True)
    builders = {
        "zero_curve.png": _zero_curve_chart,
        "forward_curve.png": _forward_chart,
        "repricing.png": _repricing_chart,
        "model_comparison.png": _model_comparison_chart,
        "data_quality.png": _cleaning_chart,
        "sensitivity.png": _sensitivity_chart,
        "key_rate_profile.png": _key_rate_chart,
    }
    out: dict[str, bytes] = {}
    for name, builder in builders.items():
        out[name] = builder(result, root / name)
    return out
