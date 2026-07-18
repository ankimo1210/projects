"""Render CPU parallel benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_parallel.py
(or `make plot-parallel` inside cpp_algo_lab/). Reads results/parallel_*.csv,
writes results/plots/parallel_*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from labviz import INK, MUTED, SLOTS, apply_style, save

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

SORT_COLOR = {"thread_merge": SLOTS[0], "omp_merge": SLOTS[1]}
SEARCH_COLOR = {"english": SLOTS[2], "dna": SLOTS[3]}
REF_STYLE = {"merge_seq": "--", "std_sort_seq": "-.", "par_stl": ":"}

apply_style()


def curve(df: pd.DataFrame, algo: str, text: str | None = None) -> pd.DataFrame:
    sub = df[df["algo"] == algo]
    if text is not None:
        sub = sub[sub["text"] == text]
    return sub.sort_values("threads")


def ref_line(ax, label: str, y: float, ls: str) -> None:
    ax.axhline(y, color=MUTED, linestyle=ls, linewidth=1.4, label=f"{label} ({y:.0f} ms)")


def fig_sort_scaling(sort: pd.DataFrame) -> None:
    n = int(sort["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for algo, color in SORT_COLOR.items():
        s = curve(sort, algo)
        ax.plot(s["threads"], s["median_ms"], color=color, marker="o", markersize=5, label=algo)
    ref_line(ax, "merge_seq", curve(sort, "merge_seq")["median_ms"].iloc[0], "--")
    ref_line(ax, "std_sort_seq", curve(sort, "std_sort_seq")["median_ms"].iloc[0], "-.")
    ref_line(ax, "par_stl (all cores)", curve(sort, "par_stl")["median_ms"].iloc[0], ":")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("threads")
    ax.set_ylabel("median wall time [ms]")
    ax.set_xticks([1, 2, 4, 8, 16, 20], [1, 2, 4, 8, 16, 20])
    ax.legend(fontsize=8, framealpha=0.9)
    ax.set_title(f"Parallel sort: time vs threads (n=2^24={n})", color=INK)
    save(fig, PLOTS, "parallel_sort_scaling.png")


def fig_search_scaling(search: pd.DataFrame) -> None:
    n = int(search["n"].iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, text in zip(axes, ["english", "dna"], strict=True):
        s = curve(search, "omp_bmh", text)
        ax.plot(
            s["threads"],
            s["median_ms"],
            color=SEARCH_COLOR[text],
            marker="o",
            markersize=5,
            label=f"omp_bmh ({text})",
        )
        seq = curve(search, "bmh_seq", text)["median_ms"].iloc[0]
        ax.axhline(seq, color=MUTED, linestyle="--", linewidth=1.4, label=f"bmh_seq ({seq:.0f} ms)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks([1, 2, 4, 8, 16, 20], [1, 2, 4, 8, 16, 20])
        ax.set_xlabel("threads")
        ax.set_title(f"text: {text}", color=INK)
        ax.legend(fontsize=8, framealpha=0.9)
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(f"Parallel search: time vs threads (n=2^26={n}, m=16)", color=INK)
    save(fig, PLOTS, "parallel_search_scaling.png")


def fig_speedup(sort: pd.DataFrame, search: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.6))
    max_t = 20
    ax.plot(
        [1, max_t], [1, max_t], color=MUTED, linestyle=":", linewidth=1.4, label="ideal (y = x)"
    )

    def speedup(sub: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        base = sub[sub["threads"] == 1]["median_ms"].iloc[0]
        return sub["threads"], base / sub["median_ms"]

    for algo, color in SORT_COLOR.items():
        t, sp = speedup(curve(sort, algo))
        ax.plot(t, sp, color=color, marker="o", markersize=5, label=f"sort: {algo}")
    for text, color in SEARCH_COLOR.items():
        t, sp = speedup(curve(search, "omp_bmh", text))
        ax.plot(t, sp, color=color, marker="s", markersize=5, label=f"search: omp_bmh ({text})")

    ax.set_xlabel("threads")
    ax.set_ylabel("speedup vs 1 thread (same implementation)")
    ax.set_xticks([1, 2, 4, 6, 8, 12, 16, 20])
    ax.legend(fontsize=8, framealpha=0.9, loc="upper left")
    ax.set_title(
        "The ladder's conclusion: search scales, sort plateaus\n"
        "(merge's final join is sequential; chunked search has no join)",
        color=INK,
    )
    save(fig, PLOTS, "parallel_speedup.png")


def main() -> None:
    sort = pd.read_csv(RESULTS / "parallel_sort.csv")
    search = pd.read_csv(RESULTS / "parallel_search.csv")
    fig_sort_scaling(sort)
    fig_search_scaling(search)
    fig_speedup(sort, search)
    print("all parallel figures written to", PLOTS)


if __name__ == "__main__":
    main()
