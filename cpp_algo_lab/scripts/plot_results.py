"""Render sorting benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_results.py
(or `make plot` inside cpp_algo_lab/). Reads results/*.csv relative to this
file's parent project directory, writes results/plots/*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

# --- dataviz reference palette (light mode) ---------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SLOTS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]  # validated fixed order
SEQ_STEPS = [
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
]
SEQ_CMAP = LinearSegmentedColormap.from_list("lab_blue", SEQ_STEPS)

FAMILIES = ["n2", "nlogn", "linear"]
FAMILY_TITLES = {
    "n2": "quadratic family",
    "nlogn": "O(n log n) family",
    "linear": "non-comparison family",
}
# Entity-stable colors: an algorithm keeps its slot in every figure.
FAMILY_SERIES = {
    "n2": ["bubble", "insertion", "selection", "shell"],
    "nlogn": ["merge", "quick", "heap"],
    "linear": ["counting", "radix", "bucket"],
}
BASELINES = ["std_sort", "std_stable_sort"]
COLOR = {}
for _fam, algos in FAMILY_SERIES.items():
    for i, a in enumerate(algos):
        COLOR[a] = SLOTS[i]
DISTS = ["random", "sorted", "reversed", "nearly_sorted", "few_unique"]
TRACE_ALGOS = [
    "bubble",
    "insertion",
    "selection",
    "shell",
    "merge",
    "quick",
    "heap",
    "counting",
    "radix",
    "bucket",
]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": BASELINE,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 2.0,
        "font.size": 10,
        "axes.titlesize": 11,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    out = PLOTS / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.relative_to(BASE.parent)}")


def slope_label(n: np.ndarray, y: np.ndarray) -> str:
    """Empirical exponent from the last 3 points of a log-log series."""
    if len(n) < 3 or np.any(y[-3:] <= 0):
        return ""
    k = np.polyfit(np.log(n[-3:]), np.log(y[-3:]), 1)[0]
    return f" n^{k:.2f}"


def plot_series(ax, sub: pd.DataFrame, algo: str, color: str, dashed: bool = False) -> None:
    s = sub[sub["algo"] == algo].sort_values("n")
    if s.empty:
        return
    n, y = s["n"].to_numpy(float), s["median_ms"].to_numpy(float)
    ax.loglog(n, y, color=color, linestyle="--" if dashed else "-", marker="o", markersize=4)
    ax.annotate(
        f"{algo}{slope_label(n, y)}",
        (n[-1], y[-1]),
        textcoords="offset points",
        xytext=(6, 0),
        fontsize=8,
        color=INK_2,
        va="center",
    )


def fig_time_vs_n(times: pd.DataFrame) -> None:
    sub = times[times["dist"] == "random"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    for ax, fam in zip(axes, FAMILIES, strict=True):
        for algo in FAMILY_SERIES[fam]:
            plot_series(ax, sub, algo, COLOR[algo])
        if fam in ("nlogn", "linear"):
            plot_series(ax, sub, "std_sort", MUTED, dashed=True)
        if fam == "nlogn":
            plot_series(ax, sub, "std_stable_sort", BASELINE, dashed=True)
        ax.set_title(FAMILY_TITLES[fam], color=INK)
        ax.set_xlabel("n (elements)")
        ax.margins(x=0.25)
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(
        "Sorting: time vs n (random input, log-log) — slope ≈ complexity exponent", color=INK
    )
    save(fig, "time_vs_n.png")


def fig_time_by_dist(times: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 5, figsize=(18, 10), sharex=False, sharey="row")
    for ri, fam in enumerate(FAMILIES):
        for ci, dist in enumerate(DISTS):
            ax = axes[ri][ci]
            sub = times[times["dist"] == dist]
            for algo in FAMILY_SERIES[fam]:
                s = sub[sub["algo"] == algo].sort_values("n")
                if not s.empty:
                    ax.loglog(
                        s["n"],
                        s["median_ms"],
                        color=COLOR[algo],
                        marker="o",
                        markersize=3,
                        label=algo,
                    )
            s = sub[sub["algo"] == "std_sort"].sort_values("n")
            ax.loglog(s["n"], s["median_ms"], color=MUTED, linestyle="--", label="std_sort")
            if ri == 0:
                ax.set_title(dist, color=INK)
            if ci == 0:
                ax.set_ylabel(f"{FAMILY_TITLES[fam]}\nmedian ms", color=INK_2)
            if ci == 4:
                ax.legend(fontsize=7, framealpha=0.9)
    fig.suptitle("Sorting: time vs n per input distribution", color=INK)
    fig.tight_layout()
    save(fig, "time_by_dist.png")


def fig_heatmap(times: pd.DataFrame) -> None:
    # Largest n present for every algorithm (16384 on a full run, smaller on --quick).
    target_n = int(times.groupby("algo")["n"].max().min())
    target_n = min(target_n, 16384)
    at_n = times[times["n"] == target_n]
    order = [a for fam in FAMILIES for a in FAMILY_SERIES[fam]] + BASELINES
    pivot = at_n.pivot_table(index="algo", columns="dist", values="median_ms")
    pivot = pivot.reindex(index=order, columns=DISTS)
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(
        pivot.to_numpy(),
        cmap=SEQ_CMAP,
        norm=LogNorm(vmin=max(pivot.min().min(), 1e-3), vmax=pivot.max().max()),
        aspect="auto",
    )
    ax.set_xticks(range(len(DISTS)), DISTS, rotation=20)
    ax.set_yticks(range(len(order)), order)
    ax.grid(False)
    mid = np.sqrt(pivot.min().min() * pivot.max().max())
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            v = pivot.iloc[r, c]
            ax.text(
                c,
                r,
                f"{v:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color="#ffffff" if v > mid else INK,
            )
    fig.colorbar(im, ax=ax, label="median ms (log scale)")
    ax.set_title(f"Sorting: median time [ms] at n={target_n}", color=INK)
    save(fig, "heatmap_dist.png")


def fig_ops(ops: pd.DataFrame) -> None:
    sub = ops[ops["dist"] == "random"]
    comp_algos = ["bubble", "insertion", "selection", "shell", "merge", "quick", "heap"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, col, title in zip(
        axes,
        ["comparisons", "movesswaps"],
        ["comparisons", "moves + swaps (element writes)"],
        strict=True,
    ):
        for algo in comp_algos:
            s = sub[sub["algo"] == algo].sort_values("n")
            if s.empty:
                continue
            y = (s["comparisons"] if col == "comparisons" else s["moves"] + s["swaps"]).to_numpy(
                float
            )
            n = s["n"].to_numpy(float)
            keep = y > 0
            ax.loglog(n[keep], y[keep], color=COLOR[algo], marker="o", markersize=3)
            if keep.any():
                ax.annotate(
                    algo,
                    (n[keep][-1], y[keep][-1]),
                    textcoords="offset points",
                    xytext=(6, 0),
                    fontsize=8,
                    color=INK_2,
                    va="center",
                )
        s = sub[sub["algo"] == "std_sort"].sort_values("n")
        y = (s["comparisons"] if col == "comparisons" else s["moves"] + s["swaps"]).to_numpy(float)
        ax.loglog(s["n"], y, color=MUTED, linestyle="--")
        ax.set_title(title, color=INK)
        ax.set_xlabel("n")
        ax.margins(x=0.25)
    axes[0].set_ylabel("operation count")
    fig.suptitle("Sorting: operation counts vs n (random input)", color=INK)
    save(fig, "ops_vs_n.png")


def fig_ops_theory(ops: pd.DataFrame) -> None:
    sub = ops[ops["dist"] == "random"]
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for algo in ["insertion", "merge"]:
        s = sub[sub["algo"] == algo].sort_values("n")
        ax.loglog(
            s["n"],
            s["comparisons"],
            color=COLOR[algo],
            marker="o",
            markersize=4,
            label=f"{algo} (measured)",
        )
    n = np.array(sorted(sub["n"].unique()), dtype=float)
    ax.loglog(n, n * n / 4, color=COLOR["insertion"], linestyle=":", label="insertion theory: n²/4")
    ax.loglog(n, n * np.log2(n), color=COLOR["merge"], linestyle=":", label="merge theory: n·log₂n")
    ax.set_xlabel("n")
    ax.set_ylabel("comparisons")
    ax.set_title("Measured comparisons vs theory (random input)", color=INK)
    ax.legend(fontsize=8)
    save(fig, "ops_theory.png")


def fig_traces() -> None:
    fig, axes = plt.subplots(2, 5, figsize=(16, 6.4))
    for ax, algo in zip(axes.ravel(), TRACE_ALGOS, strict=True):
        path = RESULTS / "traces" / f"trace_{algo}.csv"
        df = pd.read_csv(path)
        mat = df.drop(columns=["frame"]).to_numpy(float)  # frames x positions
        ax.imshow(mat.T, aspect="auto", origin="lower", cmap=SEQ_CMAP, interpolation="nearest")
        ax.set_title(algo, color=INK, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
    fig.suptitle(
        "Array state over time (x: progress, y: position, color: value) — n=256, random input",
        color=INK,
    )
    fig.tight_layout()
    save(fig, "traces.png")


def main() -> None:
    times = pd.read_csv(RESULTS / "sorting_times.csv")
    ops = pd.read_csv(RESULTS / "sorting_ops.csv")
    fig_time_vs_n(times)
    fig_time_by_dist(times)
    fig_heatmap(times)
    fig_ops(ops)
    fig_ops_theory(ops)
    fig_traces()
    print("all figures written to", PLOTS)


if __name__ == "__main__":
    main()
