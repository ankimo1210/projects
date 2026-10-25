"""Validated private inputs and failure records for the DSINC reproduction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from numbers import Integral, Real
from typing import Literal

import numpy as np


def _real(name, value):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite and real")
    return float(value)


@dataclass(frozen=True)
class PutContract:
    """Continuous-exercise put; years, continuous rates, and currency strike."""

    strike: float
    expiry: float
    domestic_rate: float
    foreign_rate: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        if self.strike <= 0 or self.expiry < 0:
            raise ValueError("strike must be positive and expiry nonnegative")
        if not self.domestic_rate > self.foreign_rate >= 0:
            raise ValueError("v1 requires domestic_rate > foreign_rate >= 0")


@dataclass(frozen=True)
class VarianceModel:
    """Risk-neutral variance dynamics; theta and v0 are variance rates."""

    kind: Literal["heston", "three_halves"]
    kappa: float
    theta: float
    xi: float
    rho: float
    v0: float

    def __post_init__(self):
        if self.kind not in ("heston", "three_halves"):
            raise ValueError("unsupported variance model")
        for name in ("kappa", "theta", "xi", "rho", "v0"):
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        if min(self.kappa, self.theta, self.xi, self.v0) <= 0 or abs(self.rho) >= 1:
            raise ValueError("positive coefficients and |rho| < 1 are required")
        if self.kind == "three_halves" and self.rho * self.xi > self.kappa + self.xi**2 / 2:
            raise ValueError("v1 excludes the strict-local-martingale region")


@dataclass(frozen=True)
class SpectralConfig:
    """Log-variance nodes, frequency panels, and local-root tolerances."""

    n_time: int
    n_var: int
    log_var_bounds: tuple[float, float]
    chi: float
    panels: tuple[float, ...]
    points_per_panel: int
    root_width: float = 0.1
    root_max_width: float = 0.3
    root_x_tol: float = 1e-10
    root_residual_tol: float = 1e-8
    root_maxiter: int = 60

    def __post_init__(self):
        for name, minimum in (
            ("n_time", 1),
            ("n_var", 4),
            ("points_per_panel", 2),
            ("root_maxiter", 1),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
            object.__setattr__(self, name, int(value))
        for name in ("chi", "root_width", "root_max_width", "root_x_tol", "root_residual_tol"):
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        bounds = tuple(_real("log_var_bounds", v) for v in self.log_var_bounds)
        panels = tuple(_real("panels", v) for v in self.panels)
        if len(bounds) != 2 or bounds[0] >= bounds[1]:
            raise ValueError("log_var_bounds must increase")
        if len(panels) < 2 or panels[0] != 0 or any(a >= z for a, z in pairwise(panels)):
            raise ValueError("frequency panels must increase from zero")
        if not 0 < self.chi < 1:
            raise ValueError("chi must lie in (0, 1)")
        if (
            not 0 < self.root_width <= self.root_max_width
            or min(self.root_x_tol, self.root_residual_tol) <= 0
        ):
            raise ValueError("root widths and tolerances must be positive and ordered")
        object.__setattr__(self, "log_var_bounds", bounds)
        object.__setattr__(self, "panels", panels)


class PricingFailure(RuntimeError):  # noqa: N818 -- fixed name in the approved plan
    """A numerical failure carrying its original node and solver evidence."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.details = {} if details is None else details
        super().__init__(message)


@dataclass(frozen=True)
class PricingResult:
    """Prices in input spot order and a time-by-log-variance boundary."""

    european: np.ndarray
    american: np.ndarray
    early_exercise_premium: np.ndarray
    times: np.ndarray
    log_variances: np.ndarray
    log_boundary: np.ndarray
    diagnostics: dict
