"""laplace_book — shared helpers for the Laplace transform notebook textbook.

The notebooks treat the Laplace transform as a tool that moves time-domain
phenomena (growth, decay, oscillation) into the complex-frequency (s) domain,
where differentiation becomes multiplication, convolution becomes a product,
and ODEs become algebra. These helpers keep that machinery out of the prose.
"""

from . import circuits, datasets, plotting, systems, transforms, widgets
from .circuits import (
    rc_highpass,
    rc_lowpass,
    rlc_params,
    rlc_series_vc,
    rlc_series_vr,
)
from .systems import (
    classify_stability,
    convolve,
    dc_gain,
    evaluate,
    feedback,
    first_order,
    gain_phase_margin,
    impulse_response,
    is_stable,
    partial_fraction_numeric,
    pid,
    poles,
    root_locus,
    routh_hurwitz,
    second_order,
    second_order_params,
    series,
    step_response,
    tf,
    time_constant,
    zeros,
)
from .transforms import (
    L,
    Linv,
    inverse_laplace_stehfest,
    inverse_laplace_talbot,
    laplace_pairs,
    numeric_laplace,
    partial_fractions,
    s,
    t,
    verify_derivative_rule,
)

__all__ = [
    # transforms
    "L",
    "Linv",
    "circuits",
    "classify_stability",
    "convolve",
    "datasets",
    "dc_gain",
    "evaluate",
    "feedback",
    "first_order",
    "gain_phase_margin",
    "impulse_response",
    "inverse_laplace_stehfest",
    "inverse_laplace_talbot",
    "is_stable",
    "laplace_pairs",
    "numeric_laplace",
    "partial_fraction_numeric",
    "partial_fractions",
    "pid",
    "plotting",
    "poles",
    "rc_highpass",
    # circuits
    "rc_lowpass",
    "rlc_params",
    "rlc_series_vc",
    "rlc_series_vr",
    "root_locus",
    "routh_hurwitz",
    "s",
    "second_order",
    "second_order_params",
    "series",
    "step_response",
    "systems",
    "t",
    # systems
    "tf",
    "time_constant",
    "transforms",
    "verify_derivative_rule",
    "widgets",
    "zeros",
]

__version__ = "0.1.0"
