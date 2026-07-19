"""P0a audit convergence analysis and report rendering.

The package reads ``solver-bench`` RunRecord JSON emitted by ``gto-hu``.
"""

from gto.bench.report import (
    aggregate_seeds,
    artifact_time_to,
    fit_slope,
    fit_window,
    load_dir,
    render_markdown,
    time_to,
)

__all__ = [
    "aggregate_seeds",
    "artifact_time_to",
    "fit_slope",
    "fit_window",
    "load_dir",
    "render_markdown",
    "time_to",
]
