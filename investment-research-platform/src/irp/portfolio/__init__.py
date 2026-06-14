"""irp.portfolio — portfolio construction with constraints.

Constructors (:mod:`~irp.portfolio.construct`: equal_weight, inverse_volatility,
risk_parity, min_variance, mean_variance) turn a vol/cov estimate (+ a signal as
the expected-return proxy) into weights; :func:`~irp.portfolio.constraints.apply_constraints`
projects them onto the config's feasible set; :func:`~irp.portfolio.build.build_weights`
runs that over time into a held, causal weight panel for the backtest engine —
replacing the crude ``long_short_quantile`` with proper, comparable schemes.
"""

from __future__ import annotations

from .build import build_weights
from .constraints import Constraints, apply_constraints
from .construct import (
    equal_weight,
    inverse_volatility,
    mean_variance,
    min_variance,
    risk_contributions,
    risk_parity,
)

__all__ = [
    "Constraints",
    "apply_constraints",
    "build_weights",
    "equal_weight",
    "inverse_volatility",
    "mean_variance",
    "min_variance",
    "risk_contributions",
    "risk_parity",
]
