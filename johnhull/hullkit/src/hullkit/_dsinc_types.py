"""Private DSINC input contracts, validation, boundary status codes and digests.

Types shared by the constant-coefficient Heston / 3/2 American-put research
(``research/DSINC``).  Time is in years, rates are continuously compounded annual
rates, ``v`` and ``theta`` are variance rates (not volatilities), ``xi`` is the
vol-of-variance and ``rho`` is the spot/variance correlation.

The v1 scope is ``rd > rf >= 0``, ``kappa, theta, v0, xi > 0``, ``|rho| < 1`` and,
for the 3/2 model, the true-martingale region ``rho*xi <= kappa + xi**2/2``
(equality included).  Every invalid input raises ``ValueError``; nothing is
clipped or replaced.  Numerical failures are reported as ``PricingFailure`` and
each boundary node carries a code from ``BOUNDARY_STATUS``.  No RNG, no I/O, no
public API.
"""

import dataclasses
import hashlib
import itertools
import json
import math
import numbers
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import numpy as np

_MODEL_KINDS = ("heston", "three_halves")
_CROSSINGS = ("upper", "lower")


def _real(name: str, value: object) -> float:
    """Return ``value`` as a finite float; bool, non-real and non-finite are rejected."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _integer(name: str, value: object, minimum: int) -> int:
    """Return ``value`` as an int >= ``minimum``; bool and non-integers are rejected."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an int, got {value!r}")
    number = int(value)
    if number < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value!r}")
    return number


def _reals(name: str, values: Iterable[object]) -> tuple[float, ...]:
    """Return ``values`` (a list, tuple or array) as a tuple of finite floats."""
    try:
        items = tuple(values)
    except TypeError:
        raise ValueError(f"{name} must be a sequence of real numbers, got {values!r}") from None
    return tuple(_real(f"{name}[{i}]", item) for i, item in enumerate(items))


def _strictly_increasing(name: str, values: tuple[float, ...]) -> None:
    """Raise ValueError unless ``values`` strictly increases."""
    if any(left >= right for left, right in itertools.pairwise(values)):
        raise ValueError(f"{name} must be strictly increasing, got {values!r}")


@dataclass(frozen=True)
class PutContract:
    """Put payoff ``(K - S)^+`` with continuous exercise and continuously compounded rates.

    ``strike`` is positive, ``expiry`` is finite and non-negative (``0`` asks for the
    exact payoff) and ``domestic_rate > foreign_rate >= 0``, which puts the maturity
    boundary at ``x* = 0``.  All values are validated and stored as floats.
    """

    strike: float
    expiry: float
    domestic_rate: float
    foreign_rate: float

    def __post_init__(self) -> None:
        for name in ("strike", "expiry", "domestic_rate", "foreign_rate"):
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        if self.strike <= 0.0:
            raise ValueError(f"strike must be > 0, got {self.strike!r}")
        if self.expiry < 0.0:
            raise ValueError(f"expiry must be >= 0, got {self.expiry!r}")
        if self.foreign_rate < 0.0:
            raise ValueError(f"foreign_rate must be >= 0, got {self.foreign_rate!r}")
        if self.domestic_rate <= self.foreign_rate:
            raise ValueError(
                "domestic_rate must exceed foreign_rate (v1 scope rd > rf >= 0), "
                f"got rd={self.domestic_rate!r}, rf={self.foreign_rate!r}"
            )


@dataclass(frozen=True)
class VarianceModel:
    """Constant-coefficient stochastic-variance model, ``kind`` ``heston`` or ``three_halves``.

    ``kappa``, ``theta``, ``xi`` and ``v0`` are positive, ``|rho| < 1``.  For
    ``three_halves`` the stock must be a true martingale, ``rho*xi <= kappa +
    xi**2/2`` (equality is accepted); the strict local martingale region is outside
    v1.  All values are validated and stored as floats.
    """

    kind: Literal["heston", "three_halves"]
    kappa: float
    theta: float
    xi: float
    rho: float
    v0: float

    def __post_init__(self) -> None:
        if self.kind not in _MODEL_KINDS:
            raise ValueError(f"kind must be one of {_MODEL_KINDS}, got {self.kind!r}")
        for name in ("kappa", "theta", "xi", "rho", "v0"):
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        for name in ("kappa", "theta", "xi", "v0"):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        if abs(self.rho) >= 1.0:
            raise ValueError(f"|rho| must be < 1, got {self.rho!r}")
        if self.kind == "three_halves" and self.rho * self.xi > self.kappa + self.xi**2 / 2:
            raise ValueError(
                "three_halves needs the stock to be a true martingale, "
                "rho*xi <= kappa + xi**2/2; got "
                f"rho*xi={self.rho * self.xi!r} > kappa + xi**2/2={self.kappa + self.xi**2 / 2!r}"
            )


@dataclass(frozen=True)
class SpectralConfig:
    """Fixed-frequency spectral grid, frequency rule and boundary-root settings.

    ``n_time`` time steps and ``n_var`` log-variance nodes (both ends included) on
    ``log_var_bounds``; ``chi`` in ``(0, 1)`` is the damping; ``panels`` are the
    Gauss-Legendre panel edges (start at 0, strictly increasing) with
    ``points_per_panel`` nodes each.  ``root_widths`` are the strictly increasing
    half-widths of the boundary brackets, tried in order until a node shows a sign
    change; the default ends in a reserve of 0.5 that only the nodes without one up to
    0.3 reach (deviation D-6).  ``root_x_tol``, ``root_residual_tol`` and
    ``root_maxiter`` stop the bisection, and ``crossing`` picks the ``upper`` or
    ``lower`` positive-to-negative crossing.  Lists are stored as float tuples.
    """

    n_time: int
    n_var: int
    log_var_bounds: tuple[float, float]
    chi: float
    panels: tuple[float, ...]
    points_per_panel: int
    root_widths: tuple[float, ...] = (0.1, 0.2, 0.3, 0.5)
    root_x_tol: float = 1e-10
    root_residual_tol: float = 1e-8
    root_maxiter: int = 60
    crossing: Literal["upper", "lower"] = "upper"

    def __post_init__(self) -> None:
        for name, minimum in (
            ("n_time", 1),
            ("n_var", 4),
            ("points_per_panel", 1),
            ("root_maxiter", 1),
        ):
            object.__setattr__(self, name, _integer(name, getattr(self, name), minimum))
        for name in ("chi", "root_x_tol", "root_residual_tol"):
            object.__setattr__(self, name, _real(name, getattr(self, name)))
        for name in ("log_var_bounds", "panels", "root_widths"):
            object.__setattr__(self, name, _reals(name, getattr(self, name)))
        if len(self.log_var_bounds) != 2 or not self.log_var_bounds[0] < self.log_var_bounds[1]:
            raise ValueError(
                f"log_var_bounds must be an ascending (low, high) pair, got {self.log_var_bounds!r}"
            )
        if not 0.0 < self.chi < 1.0:
            raise ValueError(f"chi must be in (0, 1), got {self.chi!r}")
        if len(self.panels) < 2 or self.panels[0] != 0.0:
            raise ValueError(f"panels must start at 0 and hold >= 2 edges, got {self.panels!r}")
        _strictly_increasing("panels", self.panels)
        if not self.root_widths or self.root_widths[0] <= 0.0:
            raise ValueError(
                f"root_widths must be non-empty and positive, got {self.root_widths!r}"
            )
        _strictly_increasing("root_widths", self.root_widths)
        for name in ("root_x_tol", "root_residual_tol"):
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be > 0, got {getattr(self, name)!r}")
        if self.crossing not in _CROSSINGS:
            raise ValueError(f"crossing must be one of {_CROSSINGS}, got {self.crossing!r}")


# Status of the early-exercise boundary root at one (time, variance) node.  Codes 2-6
# are failures (FAILURE_CODES); -1, 0, 1 and 7 are not.  The values are fixed by test.
BOUNDARY_STATUS: dict[str, int] = {
    "not_run": -1,  # not computed: earlier than a failed slice
    "single": 0,  # one positive-to-negative crossing in the bracket
    "multiple_crossings": 1,  # several crossings; the chosen one is kept and recorded
    "missing_sign_change": 2,  # no bracket with R(lo) > 0 > R(hi)
    "wrong_orientation": 3,  # the bracket changes sign the wrong way, R(lo) < 0 < R(hi)
    "ambiguous_contact": 4,  # two or more consecutive residuals within the tolerance
    "nonfinite": 5,  # a non-finite residual
    "maxiter": 6,  # the bisection missed the tolerances within root_maxiter
    "terminal": 7,  # maturity slice, x* = 0 by definition
}
FAILURE_CODES: frozenset[int] = frozenset({2, 3, 4, 5, 6})


class PricingFailure(Exception):  # noqa: N818 -- fixed name from the task interface
    """Structured numerical failure; ``code`` names it and ``details`` carries diagnostics.

    Raised instead of hiding a failed root or a violated bound behind a clip or a
    substitute value.  ``str()`` gives ``"<code>: <message>"``; ``details`` is the
    dict passed in, kept as is.
    """

    def __init__(self, code: str, message: str, details: dict) -> None:
        super().__init__(code, message, details)  # args stay the constructor arguments (pickle)
        self.code = code
        self.message = message
        self.details = details

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True)
class PricingResult:
    """Prices, early-exercise premium and exercise boundary of one American-put solve.

    ``european``, ``american`` and ``early_exercise_premium`` have shape ``(n_spots,)``,
    are price divided by the strike and follow the order of the input spots.  ``times``
    is ``t_n = n*T/n_time`` with shape ``(n_time+1,)``, ``log_variances`` the node
    grid ``(n_var,)``, ``log_boundary`` the boundary ``x*`` ``(n_time+1, n_var)`` and
    ``boundary_status`` the ``int8`` ``BOUNDARY_STATUS`` codes of the same shape.  At
    ``T = 0`` the payoff is exact and ``times`` and ``log_variances`` have shape
    ``(0,)`` and both boundary arrays ``(0, 0)``.  ``diagnostics`` holds only
    JSON-serializable scalars and lists.
    """

    european: np.ndarray
    american: np.ndarray
    early_exercise_premium: np.ndarray
    times: np.ndarray
    log_variances: np.ndarray
    log_boundary: np.ndarray
    boundary_status: np.ndarray
    diagnostics: dict


def _array_record(array: np.ndarray) -> dict:
    """Return the dtype, shape and byte hash that stand for ``array`` in a digest."""
    if array.dtype.kind not in "biufc":
        raise ValueError(f"cannot digest an array of dtype {array.dtype}")
    return {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
    }


def _canonical(value: object) -> object:
    """Convert ``value`` to JSON-ready Python objects, rejecting what cannot be digested."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        record = {"__type__": type(value).__name__}
        for field in dataclasses.fields(value):
            record[field.name] = _canonical(getattr(value, field.name))
        return record
    if isinstance(value, dict):
        record = {str(key): _canonical(item) for key, item in value.items()}
        if len(record) != len(value):
            raise ValueError("dict keys collide once converted to str")
        return record
    if isinstance(value, tuple | list):
        return [_canonical(item) for item in value]
    if isinstance(value, np.ndarray):
        return _array_record(value)
    if isinstance(value, np.generic):
        item = value.item()
        if isinstance(item, np.generic):
            raise ValueError(f"cannot digest a NumPy scalar of dtype {value.dtype}")
        return _canonical(item)
    if value is None or isinstance(value, str | int | float):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"cannot digest the non-finite float {value!r}")
        return value
    raise ValueError(f"cannot digest a value of type {type(value).__name__}")


def canonical_digest(*parts: object) -> str:
    """Return the sha256 hex digest of the canonical JSON form of ``parts``.

    Dataclasses become ``{"__type__": class name, <fields>}``, dicts get ``str`` keys,
    tuples and lists become lists, NumPy arrays become ``{"dtype", "shape", "sha256"}``
    of their C-order bytes (NaN inside an array is hashed, not rejected) and NumPy
    scalars become Python values.  ``str``, ``int``, ``float``, ``bool`` and ``None``
    pass through.  A NaN or infinity, and any other type, raises ``ValueError``
    instead of being replaced.  The JSON uses sorted keys, so dict order is ignored.
    """
    payload = json.dumps([_canonical(part) for part in parts], sort_keys=True, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
