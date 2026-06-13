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
    impulse_response,
    is_stable,
    poles,
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
    laplace_pairs,
    numeric_laplace,
    partial_fractions,
    s,
    t,
    verify_derivative_rule,
)

__all__ = [
    "circuits",
    "datasets",
    "plotting",
    "systems",
    "transforms",
    "widgets",
    # transforms
    "L",
    "Linv",
    "s",
    "t",
    "numeric_laplace",
    "partial_fractions",
    "laplace_pairs",
    "verify_derivative_rule",
    # systems
    "tf",
    "first_order",
    "second_order",
    "second_order_params",
    "poles",
    "zeros",
    "evaluate",
    "dc_gain",
    "time_constant",
    "is_stable",
    "classify_stability",
    "step_response",
    "impulse_response",
    "series",
    "feedback",
    "convolve",
    # circuits
    "rc_lowpass",
    "rc_highpass",
    "rlc_series_vc",
    "rlc_series_vr",
    "rlc_params",
]

__version__ = "0.1.0"
