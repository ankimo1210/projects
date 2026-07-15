"""Render search benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_search.py
(or `make plot-search` inside cpp_algo_lab/). Reads results/search_*.csv,
writes results/plots/search_*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from labviz import INK, MUTED, SEQ_CMAP, SLOTS, apply_style, save, slope_label
from matplotlib.colors import LogNorm

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

TEXTS = ["dna", "ascii", "english", "periodic"]
OWN = ["naive", "kmp", "bmh", "rabin_karp"]
COLOR = dict(zip(OWN, SLOTS, strict=True))
BASELINE_STYLE = {"sv_find": "--", "std_bmh": "-.", "std_bm": ":"}

apply_style()


def panel_series(
    ax, sub: pd.DataFrame, xcol: str, var: str, loc: str | None = None, fontsize: float = 7
) -> None:
    """Own algorithms in color with slope labels; std baselines gray-styled."""
    for algo in OWN:
        s = sub[sub["algo"] == algo].sort_values(xcol)
        x, y = s[xcol].to_numpy(float), s["median_ms"].to_numpy(float)
        ax.loglog(
            x,
            y,
            color=COLOR[algo],
            marker="o",
            markersize=4,
            label=f"{algo}{slope_label(x, y, var=var)}",
        )
    for algo, ls in BASELINE_STYLE.items():
        s = sub[sub["algo"] == algo].sort_values(xcol)
        ax.loglog(s[xcol], s["median_ms"], color=MUTED, linestyle=ls, label=algo)
    # "best" places the legend well everywhere except the periodic/time_vs_m
    # panel, where naive's rising line clips the box's corner; that one call
    # site pins loc/fontsize explicitly (see fig_time_vs_m).
    ax.legend(fontsize=fontsize, framealpha=0.9, loc=loc)


def fig_time_vs_n(times_n: pd.DataFrame) -> None:
    m_fixed = int(times_n["m"].iloc[0])
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        panel_series(ax, times_n[times_n["text"] == text], "n", "n")
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("n (text length)")
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(
        f"Search: time vs text length n (m={m_fixed}, log-log) — "
        "everyone is linear in n; the constants tell the story",
        color=INK,
    )
    save(fig, PLOTS, "search_time_vs_n.png")


def fig_time_vs_m(times_m: pd.DataFrame) -> None:
    n_fixed = int(times_m["n"].max())
    sub_n = times_m[times_m["n"] == n_fixed]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        loc = "upper left" if text == "periodic" else None
        fontsize = 6 if text == "periodic" else 7
        panel_series(ax, sub_n[sub_n["text"] == text], "m", "m", loc=loc, fontsize=fontsize)
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("m (pattern length)")
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(
        f"Search: time vs pattern length m (n={n_fixed}, log-log) — "
        "BMH gets FASTER as m grows; KMP stays flat; naive×periodic pays m",
        color=INK,
    )
    save(fig, PLOTS, "search_time_vs_m.png")


def fig_reads_per_char(ops: pd.DataFrame) -> None:
    sub = ops[ops["sweep"] == "m"]
    n_fixed = int(sub["n"].max())
    sub = sub[sub["n"] == n_fixed]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        s0 = sub[sub["text"] == text]
        for algo in OWN:
            s = s0[s0["algo"] == algo].sort_values("m")
            ax.loglog(
                s["m"],
                s["text_reads"] / n_fixed,
                color=COLOR[algo],
                marker="o",
                markersize=4,
                label=algo,
            )
        ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1.2)
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("m (pattern length)")
        ax.legend(fontsize=8, framealpha=0.9)
    axes[0].text(4.2, 1.12, "1 read per text char", color=MUTED, fontsize=7)
    axes[0].set_ylabel("text reads / n")
    fig.suptitle(
        f"Search: text reads per character vs m (n={n_fixed}) — "
        "BMH drops below 1 (sublinear); naive×periodic explodes to m",
        color=INK,
    )
    save(fig, PLOTS, "search_reads_per_char.png")


def fig_pre_vs_match(ops: pd.DataFrame) -> None:
    sub = ops[(ops["sweep"] == "m") & (ops["text"] == "dna")]
    n_fixed = int(sub["n"].max())
    sub = sub[sub["n"] == n_fixed]
    ms = [m for m in (4, 64, 1024) if m in set(sub["m"])]
    fig, axes = plt.subplots(1, len(ms), figsize=(4.4 * len(ms), 4.2), sharey=True)
    axes = np.atleast_1d(axes)
    x = np.arange(len(OWN))
    for ax, m in zip(axes, ms, strict=True):
        rows = sub[sub["m"] == m].set_index("algo").reindex(OWN)
        pre = np.maximum(rows["pre_ops"].to_numpy(float), 1.0)
        scan = rows["text_reads"].to_numpy(float)
        ax.bar(x - 0.2, pre, width=0.38, color=MUTED, label="preprocess (pattern ops)")
        ax.bar(x + 0.2, scan, width=0.38, color=SLOTS[0], label="scan (text reads)")
        ax.set_yscale("log")
        ax.set_xticks(x, ["naive", "kmp", "bmh", "rk"])
        ax.set_title(f"m = {m}", color=INK)
        ax.grid(False, axis="x")
    axes[0].set_ylabel("elementary ops (log)")
    # The scan bars are solid rectangles reaching most of the panel height on
    # this log axis, so "best" has no clean corner and overlaps the kmp/rk
    # bars. Widen headroom above the tallest bar and lay the legend out in
    # one row above all bars instead of stacking it into their span.
    ylo, yhi = axes[0].get_ylim()
    axes[0].set_ylim(ylo, yhi * 3.0)
    axes[0].legend(fontsize=8, framealpha=0.9, ncols=2, loc="upper center")
    fig.text(
        0.01,
        -0.02,
        "naive has no preprocessing; its bar is clipped to 1 on the log axis.",
        fontsize=7,
        color=MUTED,
    )
    fig.suptitle(
        f"Search: preprocessing grows with m, the scan is pinned to n={n_fixed} (dna text)",
        color=INK,
    )
    save(fig, PLOTS, "search_pre_vs_match.png")


def fig_search_heatmap(times_m: pd.DataFrame) -> None:
    n_fixed = int(times_m["n"].max())
    sub = times_m[times_m["n"] == n_fixed]
    ms = sorted(int(m) for m in sub["m"].unique())
    target_m = 16 if 16 in ms else ms[len(ms) // 2]
    sub = sub[sub["m"] == target_m]
    order = OWN + list(BASELINE_STYLE)
    pivot = sub.pivot_table(index="algo", columns="text", values="median_ms").reindex(
        index=order, columns=TEXTS
    )
    fig, ax = plt.subplots(figsize=(7, 5.6))
    im = ax.imshow(
        pivot.to_numpy(),
        cmap=SEQ_CMAP,
        norm=LogNorm(vmin=max(pivot.min().min(), 1e-3), vmax=pivot.max().max()),
        aspect="auto",
    )
    ax.set_xticks(range(len(TEXTS)), TEXTS)
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
    ax.set_title(f"Search: median time [ms] at n={n_fixed}, m={target_m}", color=INK)
    save(fig, PLOTS, "search_heatmap.png")


def main() -> None:
    times_n = pd.read_csv(RESULTS / "search_times_n.csv")
    times_m = pd.read_csv(RESULTS / "search_times_m.csv")
    ops = pd.read_csv(RESULTS / "search_ops.csv")
    fig_time_vs_n(times_n)
    fig_time_vs_m(times_m)
    fig_reads_per_char(ops)
    fig_pre_vs_match(ops)
    fig_search_heatmap(times_m)
    print("all search figures written to", PLOTS)


if __name__ == "__main__":
    main()
