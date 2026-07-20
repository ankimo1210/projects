"""Shared dataviz style for cpp_algo_lab plot scripts.

The dataviz reference palette (light mode) validated in Phase 1, plus small
helpers used by plot_results.py (sorting) and plot_search.py (search).
Import this module only after calling matplotlib.use("Agg") -- it imports
matplotlib.pyplot at module level.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# Categorical series slots in validated fixed order; SLOTS7 extends them for
# figures that pool many series on one axes.
SLOTS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]
SLOTS7 = [*SLOTS, "#4a3aa7", "#e34948", "#e87ba4"]
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


def apply_style() -> None:
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


def save(fig: plt.Figure, plots_dir: Path, name: str) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    out = plots_dir / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def slope_label(x: np.ndarray, y: np.ndarray, var: str = "n") -> str:
    """Empirical exponent from the last 3 points of a log-log series."""
    if len(x) < 3 or np.any(y[-3:] <= 0):
        return ""
    k = np.polyfit(np.log(x[-3:]), np.log(y[-3:]), 1)[0]
    return f" {var}^{k:.2f}"
