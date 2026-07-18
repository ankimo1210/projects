"""Validate Phase 4 GPU CSVs and render the three contracted figures.

Run from repo root: uv run --no-sync python cpp_algo_lab/scripts/plot_gpu.py
(or ``make plot-gpu`` inside cpp_algo_lab/). Full-size canonical CSVs are
required; quick or incomplete results are rejected before any plot is written.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from labviz import INK, MUTED, SLOTS, apply_style, save

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

HOST_COLOR = MUTED
KERNEL_COLOR = SLOTS[0]
END_TO_END_COLOR = SLOTS[2]

SORT_ROWS = [
    ("std_sort_cpu", "host", "std::sort · host", HOST_COLOR, "s"),
    ("bitonic", "kernel", "bitonic · kernel", KERNEL_COLOR, "o"),
    ("bitonic", "end_to_end", "bitonic · end-to-end", END_TO_END_COLOR, "D"),
    ("thrust", "kernel", "Thrust · kernel", KERNEL_COLOR, "o"),
    ("thrust", "end_to_end", "Thrust · end-to-end", END_TO_END_COLOR, "D"),
]
SEARCH_ROWS = [
    ("naive_cpu", "host", "naive CPU · host", HOST_COLOR, "s"),
    ("bmh_cpu", "host", "BMH CPU · host", HOST_COLOR, "s"),
    ("cuda_naive", "kernel", "CUDA naive · kernel", KERNEL_COLOR, "o"),
    ("cuda_naive", "end_to_end", "CUDA naive · end-to-end", END_TO_END_COLOR, "D"),
]

apply_style()


def size_label(n: int) -> str:
    if n > 0 and n & (n - 1) == 0:
        return f"2^{n.bit_length() - 1}={n:,}"
    return f"{n:,}"


def validate_inputs(sort: pd.DataFrame, search: pd.DataFrame) -> None:
    sort_columns = {"algo", "mode", "n", "repeats", "median_ms", "mad_ms"}
    search_columns = sort_columns | {"text", "m", "occurrences"}
    if set(sort.columns) != sort_columns:
        raise ValueError(
            f"gpu_sort.csv columns differ: expected {sorted(sort_columns)}, "
            f"got {sorted(sort.columns)}"
        )
    if set(search.columns) != search_columns:
        raise ValueError(
            f"gpu_search.csv columns differ: expected {sorted(search_columns)}, "
            f"got {sorted(search.columns)}"
        )

    expected_sort = {(algo, mode) for algo, mode, *_ in SORT_ROWS}
    actual_sort = set(zip(sort["algo"], sort["mode"], strict=True))
    expected_search = {
        (algo, text, mode) for text in ("english", "dna") for algo, mode, *_ in SEARCH_ROWS
    }
    actual_search = set(zip(search["algo"], search["text"], search["mode"], strict=True))
    if len(sort) != len(expected_sort) or actual_sort != expected_sort:
        raise ValueError("gpu_sort.csv does not contain exactly the five full benchmark rows")
    if len(search) != len(expected_search) or actual_search != expected_search:
        raise ValueError("gpu_search.csv does not contain exactly the eight full benchmark rows")

    if set(sort["n"]) != {1 << 24} or set(search["n"]) != {1 << 26}:
        raise ValueError("GPU CSVs contain quick or mixed workload sizes")
    if set(search["m"]) != {16} or set(sort["repeats"]) != {5} or set(search["repeats"]) != {5}:
        raise ValueError("GPU CSVs contain unexpected pattern size or repeat count")

    for name, frame in (("gpu_sort.csv", sort), ("gpu_search.csv", search)):
        timings = frame[["median_ms", "mad_ms"]].to_numpy(dtype=float)
        if not np.isfinite(timings).all():
            raise ValueError(f"{name} contains non-finite timings")
        if (frame["median_ms"] <= 0).any() or (frame["mad_ms"] < 0).any():
            raise ValueError(f"{name} contains non-positive medians or negative MAD values")
        if (frame["median_ms"] - frame["mad_ms"] <= 0).any():
            raise ValueError(f"{name} has an interval incompatible with the log timing axis")

    counts = search.groupby("text")["occurrences"]
    if (search["occurrences"] < 0).any() or any(values.nunique() != 1 for _, values in counts):
        raise ValueError("gpu_search.csv occurrence counts disagree within a corpus")
    if search.groupby("text")["occurrences"].first().nunique() == 1:
        raise ValueError("GPU search corpora unexpectedly have identical occurrence counts")


def selected_row(df: pd.DataFrame, algo: str, mode: str, text: str | None = None) -> pd.Series:
    rows = df[(df["algo"] == algo) & (df["mode"] == mode)]
    if text is not None:
        rows = rows[rows["text"] == text]
    if len(rows) != 1:
        raise ValueError(f"expected one row for {algo}/{mode}/{text}, got {len(rows)}")
    return rows.iloc[0]


def timing_dot(ax: plt.Axes, row: pd.Series, y: int, color: str, marker: str) -> None:
    ax.errorbar(
        float(row["median_ms"]),
        y,
        xerr=float(row["mad_ms"]),
        color=color,
        marker=marker,
        markersize=6,
        capsize=3,
        linestyle="none",
    )


def fig_sort_times(sort: pd.DataFrame) -> None:
    n = int(sort["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(8.1, 4.7))
    labels = []
    for y, (algo, mode, label, color, marker) in enumerate(SORT_ROWS):
        timing_dot(ax, selected_row(sort, algo, mode), y, color, marker)
        labels.append(label)
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("median time [ms], log scale (interval: ±MAD)")
    ax.set_title(f"GPU sort timings by measurement boundary (n={size_label(n)})", color=INK)
    save(fig, PLOTS, "gpu_sort_times.png")


def fig_search_times(search: pd.DataFrame) -> None:
    n = int(search["n"].iloc[0])
    m = int(search["m"].iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8), sharex=True, sharey=True)
    labels = [row[2] for row in SEARCH_ROWS]
    for ax, text in zip(axes, ("english", "dna"), strict=True):
        for y, (algo, mode, _, color, marker) in enumerate(SEARCH_ROWS):
            timing_dot(ax, selected_row(search, algo, mode, text), y, color, marker)
        occurrences = int(search[search["text"] == text]["occurrences"].iloc[0])
        ax.set_xscale("log")
        ax.set_xlabel("median time [ms], log scale")
        ax.set_title(f"{text} · {occurrences:,} matches", color=INK)
    axes[0].set_yticks(range(len(labels)), labels)
    axes[0].invert_yaxis()
    fig.suptitle(
        f"Exact search timings by text (n={size_label(n)}, m={m}; interval: ±MAD)",
        color=INK,
    )
    save(fig, PLOTS, "gpu_search_times.png")


def fig_transfer_tax(sort: pd.DataFrame, search: pd.DataFrame) -> None:
    ratios = [
        (
            "sort · bitonic",
            selected_row(sort, "bitonic", "end_to_end")["median_ms"]
            / selected_row(sort, "bitonic", "kernel")["median_ms"],
            KERNEL_COLOR,
        ),
        (
            "sort · Thrust",
            selected_row(sort, "thrust", "end_to_end")["median_ms"]
            / selected_row(sort, "thrust", "kernel")["median_ms"],
            KERNEL_COLOR,
        ),
        (
            "search · english",
            selected_row(search, "cuda_naive", "end_to_end", "english")["median_ms"]
            / selected_row(search, "cuda_naive", "kernel", "english")["median_ms"],
            KERNEL_COLOR,
        ),
        (
            "search · dna",
            selected_row(search, "cuda_naive", "end_to_end", "dna")["median_ms"]
            / selected_row(search, "cuda_naive", "kernel", "dna")["median_ms"],
            KERNEL_COLOR,
        ),
    ]
    fig, ax = plt.subplots(figsize=(8.1, 4.5))
    labels = [item[0] for item in ratios]
    values = np.asarray([float(item[1]) for item in ratios])
    bars = ax.barh(range(len(ratios)), values, color=[item[2] for item in ratios])
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(left=0, right=float(values.max()) * 1.16)
    ax.set_xlabel("end-to-end median / kernel median [×]")
    ax.set_title("Host-side work and transfers relative to kernel time", color=INK)
    ax.bar_label(bars, labels=[f"{value:.1f}×" for value in values], padding=4, color=MUTED)
    save(fig, PLOTS, "gpu_transfer_tax.png")


def main() -> None:
    sort = pd.read_csv(RESULTS / "gpu_sort.csv")
    search = pd.read_csv(RESULTS / "gpu_search.csv")
    validate_inputs(sort, search)
    fig_sort_times(sort)
    fig_search_times(search)
    fig_transfer_tax(sort, search)
    print("all GPU figures written to", PLOTS)


if __name__ == "__main__":
    main()
