"""Plotly figure helpers, grouped by the chapters they serve.

``probability`` covers Part I (01-05). ``inference`` and ``regression``
arrive with Plan 2. Consumers import from this package, not the submodules,
so the split stays an implementation detail.
"""

from .core import apply_defaults, curve_slider, frame_slider
from .probability import (
    clt_convergence,
    joint_marginal_heatmap,
    markov_convergence_slider,
    poisson_limit_slider,
    ppv_slider,
    random_walk_paths,
    relation_graph,
)

__all__ = [
    "apply_defaults",
    "clt_convergence",
    "curve_slider",
    "frame_slider",
    "joint_marginal_heatmap",
    "markov_convergence_slider",
    "poisson_limit_slider",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
]
