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

apply_style()


def curve(df: pd.DataFrame, algo: str, text: str | None = None) -> pd.DataFrame:
    sub = df[df["algo"] == algo]
    if text is not None:
        sub = sub[sub["text"] == text]
    return sub.sort_values("threads")


def ref_line(ax, label: str, y: float, ls: str) -> None:
    ax.axhline(y, color=MUTED, linestyle=ls, linewidth=1.4, label=f"{label} ({y:.0f} ms)")


def size_label(n: int) -> str:
    if n > 0 and n & (n - 1) == 0:
        return f"2^{n.bit_length() - 1}={n:,}"
    return f"{n:,}"


def validate_inputs(sort: pd.DataFrame, search: pd.DataFrame) -> None:
    sort_columns = {"algo", "threads", "n", "repeats", "median_ms", "mad_ms"}
    search_columns = sort_columns | {"text", "m", "occurrences"}
    if not sort_columns <= set(sort.columns):
        raise ValueError(f"parallel_sort.csv missing columns: {sort_columns - set(sort.columns)}")
    if not search_columns <= set(search.columns):
        raise ValueError(
            f"parallel_search.csv missing columns: {search_columns - set(search.columns)}"
        )

    expected_sort = {
        ("merge_seq", 1),
        ("std_sort_seq", 1),
        *(("thread_merge", t) for t in (1, 2, 4, 8, 16)),
        *(("omp_merge", t) for t in (1, 2, 4, 6, 8, 12, 16, 20)),
        ("par_stl", 0),
    }
    actual_sort = {
        (str(algo), int(threads))
        for algo, threads in zip(sort["algo"], sort["threads"], strict=True)
    }
    expected_search = {
        (algo, text, threads)
        for text in ("english", "dna")
        for algo, threads in (
            ("bmh_seq", 1),
            *(("omp_bmh", t) for t in (1, 2, 4, 6, 8, 12, 16, 20)),
        )
    }
    actual_search = {
        (str(algo), str(text), int(threads))
        for algo, text, threads in zip(
            search["algo"], search["text"], search["threads"], strict=True
        )
    }
    if len(sort) != len(expected_sort) or len(search) != len(expected_search):
        raise ValueError("parallel CSVs contain missing or duplicate rows")
    if actual_sort != expected_sort:
        raise ValueError("parallel_sort.csv is not the expected full sweep")
    if actual_search != expected_search:
        raise ValueError("parallel_search.csv is not the expected full sweep")
    if set(sort["n"]) != {1 << 24} or set(search["n"]) != {1 << 26}:
        raise ValueError("parallel CSVs contain quick or mixed workload sizes")
    if set(search["m"]) != {16} or set(sort["repeats"]) != {5} or set(search["repeats"]) != {5}:
        raise ValueError("parallel CSVs contain unexpected pattern size or repeat count")
    if (sort["median_ms"] <= 0).any() or (search["median_ms"] <= 0).any():
        raise ValueError("parallel CSVs contain non-positive timings")
    if (sort["mad_ms"] < 0).any() or (search["mad_ms"] < 0).any():
        raise ValueError("parallel CSVs contain negative MAD values")
    if any(search[search["text"] == text]["occurrences"].nunique() != 1 for text in SEARCH_COLOR):
        raise ValueError("parallel_search.csv occurrence counts differ across thread counts")


def fig_sort_scaling(sort: pd.DataFrame) -> None:
    n = int(sort["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for algo, color in SORT_COLOR.items():
        s = curve(sort, algo)
        ax.errorbar(
            s["threads"],
            s["median_ms"],
            yerr=s["mad_ms"],
            color=color,
            marker="o",
            markersize=5,
            capsize=2,
            label=algo,
        )
    ref_line(ax, "merge_seq", curve(sort, "merge_seq")["median_ms"].iloc[0], "--")
    ref_line(ax, "std_sort_seq", curve(sort, "std_sort_seq")["median_ms"].iloc[0], "-.")
    ref_line(ax, "par_stl (all cores)", curve(sort, "par_stl")["median_ms"].iloc[0], ":")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("threads")
    ax.set_ylabel("median wall time [ms]")
    ax.set_xticks([1, 2, 4, 6, 8, 12, 16, 20], [1, 2, 4, 6, 8, 12, 16, 20])
    ax.legend(fontsize=8, framealpha=0.9)
    ax.set_title(f"Parallel sort: time vs threads (n={size_label(n)})", color=INK)
    save(fig, PLOTS, "parallel_sort_scaling.png")


def fig_search_scaling(search: pd.DataFrame) -> None:
    n = int(search["n"].iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, text in zip(axes, ["english", "dna"], strict=True):
        s = curve(search, "omp_bmh", text)
        ax.errorbar(
            s["threads"],
            s["median_ms"],
            yerr=s["mad_ms"],
            color=SEARCH_COLOR[text],
            marker="o",
            markersize=5,
            capsize=2,
            label=f"omp_bmh ({text})",
        )
        seq = curve(search, "bmh_seq", text)["median_ms"].iloc[0]
        ax.axhline(seq, color=MUTED, linestyle="--", linewidth=1.4, label=f"bmh_seq ({seq:.0f} ms)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks([1, 2, 4, 6, 8, 12, 16, 20], [1, 2, 4, 6, 8, 12, 16, 20])
        ax.set_xlabel("threads")
        ax.set_title(f"text: {text}", color=INK)
        ax.legend(fontsize=8, framealpha=0.9)
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(f"Parallel search: time vs threads (n={size_label(n)}, m=16)", color=INK)
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
        "Search scales nearly linearly through 12 threads; both eventually saturate\n"
        "(speedup includes runtime, memory, and WSL2 scheduling overheads)",
        color=INK,
    )
    save(fig, PLOTS, "parallel_speedup.png")


def main() -> None:
    sort = pd.read_csv(RESULTS / "parallel_sort.csv")
    search = pd.read_csv(RESULTS / "parallel_search.csv")
    validate_inputs(sort, search)
    fig_sort_scaling(sort)
    fig_search_scaling(search)
    fig_speedup(sort, search)
    print("all parallel figures written to", PLOTS)


if __name__ == "__main__":
    main()
