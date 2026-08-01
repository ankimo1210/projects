"""Plotly figure helpers, grouped by the chapters they serve.

``probability`` covers Part I (01-05), ``inference`` covers 06-08, and
``regression`` covers 09-10. Consumers import from this package, not the
submodules, so the split stays an implementation detail.
"""

from .core import apply_defaults, curve_slider, frame_slider
from .inference import (
    bootstrap_distribution,
    coverage_intervals,
    likelihood_curve,
    mle_sampling_distribution,
    phacking_demo,
    power_curves,
)
from .probability import (
    clt_convergence,
    joint_marginal_heatmap,
    markov_convergence_slider,
    poisson_limit_slider,
    ppv_slider,
    random_walk_paths,
    relation_graph,
)
from .regression import (
    coefficient_sampling,
    irls_convergence,
    link_function_fits,
    residual_catalogue,
    robust_se_comparison,
)

__all__ = [
    "apply_defaults",
    "bootstrap_distribution",
    "clt_convergence",
    "coefficient_sampling",
    "coverage_intervals",
    "curve_slider",
    "frame_slider",
    "irls_convergence",
    "joint_marginal_heatmap",
    "likelihood_curve",
    "link_function_fits",
    "markov_convergence_slider",
    "mle_sampling_distribution",
    "phacking_demo",
    "poisson_limit_slider",
    "power_curves",
    "ppv_slider",
    "random_walk_paths",
    "relation_graph",
    "residual_catalogue",
    "robust_se_comparison",
]
