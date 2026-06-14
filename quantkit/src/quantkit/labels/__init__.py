"""quantkit.labels — forward-looking supervised targets with explicit availability dates.

Labels describe the future (next-``horizon`` return, barrier touch), so they are
known only at ``t+horizon``. :func:`label_available_date` exposes that lag so the
backtest layer can embargo train/test windows. The trailing rows with no future
are NaN, never filled. See :mod:`quantkit.labels.forward`.
"""

from __future__ import annotations

from .forward import (
    binary_label,
    forward_return,
    label_available_date,
    ternary_label,
    triple_barrier,
)

__all__ = [
    "binary_label",
    "forward_return",
    "label_available_date",
    "ternary_label",
    "triple_barrier",
]
