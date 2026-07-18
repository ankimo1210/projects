"""Torch-free hard financial checks for pricing surrogates.

The functions never sort or interpolate caller data: grid order and units are
part of the validation contract.  A model is only ``arbitrage_free`` when all
applicable hard checks pass at their documented tolerances.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

import numpy as np


@dataclass(frozen=True)
class CheckResult:
    name: str
    n_checked: int
    n_violations: int
    violation_rate: float
    max_violation: float
    tolerance: float

    @property
    def passed(self):
        return self.n_violations == 0

    def to_dict(self):
        return asdict(self) | {"passed": self.passed}


@dataclass(frozen=True)
class HardValidationReport:
    checks: tuple[CheckResult, ...]
    applicable_checks: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def check_set_complete(self):
        names = tuple(check.name for check in self.checks)
        expected = self.applicable_checks or names
        return len(names) == len(set(names)) and set(names) == set(expected)

    @property
    def arbitrage_free(self):
        return (
            bool(self.checks)
            and self.check_set_complete
            and all(check.passed for check in self.checks)
        )

    def to_dict(self):
        return {
            "arbitrage_free": self.arbitrage_free,
            "check_set_complete": self.check_set_complete,
            "applicable_checks": list(self.applicable_checks or (c.name for c in self.checks)),
            "checks": [check.to_dict() for check in self.checks],
            "metadata": dict(self.metadata),
        }


def _result(name, violation, tolerance):
    values = np.asarray(violation, dtype=float).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError(f"{name} requires non-empty finite values")
    positive = np.maximum(values, 0.0)
    mask = positive > tolerance
    return CheckResult(
        name=name,
        n_checked=int(values.size),
        n_violations=int(mask.sum()),
        violation_rate=float(mask.mean()),
        max_violation=float(positive.max(initial=0.0)),
        tolerance=float(tolerance),
    )


def _finite(*values):
    arrays = np.broadcast_arrays(*[np.asarray(value, dtype=float) for value in values])
    if any(not np.all(np.isfinite(value)) for value in arrays):
        raise ValueError("hard checks require finite numeric arrays")
    return arrays


def check_price_bounds(
    prices,
    spots,
    strikes,
    rates,
    maturities,
    dividends=0.0,
    *,
    kind="call",
    tolerance=1e-10,
):
    prices, spots, strikes, rates, maturities, dividends = _finite(
        prices, spots, strikes, rates, maturities, dividends
    )
    if np.any(spots <= 0) or np.any(strikes <= 0) or np.any(maturities < 0):
        raise ValueError("spots/strikes must be positive and maturities non-negative")
    discounted_spot = spots * np.exp(-dividends * maturities)
    discounted_strike = strikes * np.exp(-rates * maturities)
    if kind == "call":
        lower = np.maximum(discounted_spot - discounted_strike, 0.0)
        upper = discounted_spot
    elif kind == "put":
        lower = np.maximum(discounted_strike - discounted_spot, 0.0)
        upper = discounted_strike
    else:
        raise ValueError("kind must be call or put")
    return _result("price_bounds", np.maximum(lower - prices, prices - upper), tolerance)


def check_put_call_parity(
    calls,
    puts,
    spots,
    strikes,
    rates,
    maturities,
    dividends=0.0,
    *,
    tolerance=1e-10,
):
    calls, puts, spots, strikes, rates, maturities, dividends = _finite(
        calls, puts, spots, strikes, rates, maturities, dividends
    )
    target = spots * np.exp(-dividends * maturities) - strikes * np.exp(-rates * maturities)
    return _result("put_call_parity", np.abs(calls - puts - target), tolerance)


def _grid(values, prices, name):
    values = np.asarray(values, dtype=float)
    prices = np.asarray(prices, dtype=float)
    if values.ndim != 1 or values.size < 2 or prices.shape[-1] != values.size:
        raise ValueError(f"{name} must be a 1D grid matching the last price axis")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(prices)):
        raise ValueError(f"{name} check requires finite values")
    if not np.all(np.diff(values) > 0):
        raise ValueError(f"{name} grid must be strictly increasing; data are not sorted")
    return values, prices


def check_strike_monotonicity(prices, strikes, *, kind="call", tolerance=1e-10):
    strikes, prices = _grid(strikes, prices, "strike")
    differences = np.diff(prices, axis=-1)
    if kind == "call":
        violation = differences
    elif kind == "put":
        violation = -differences
    else:
        raise ValueError("kind must be call or put")
    return _result("strike_monotonicity", violation, tolerance)


def check_spot_monotonicity(prices, spots, *, kind="call", tolerance=1e-10):
    spots, prices = _grid(spots, prices, "spot")
    differences = np.diff(prices, axis=-1)
    if kind == "call":
        violation = -differences
    elif kind == "put":
        violation = differences
    else:
        raise ValueError("kind must be call or put")
    return _result("spot_monotonicity", violation, tolerance)


def check_strike_convexity(prices, strikes, *, tolerance=1e-10):
    strikes, prices = _grid(strikes, prices, "strike")
    if strikes.size < 3:
        raise ValueError("strike convexity needs at least three strikes")
    slopes = np.diff(prices, axis=-1) / np.diff(strikes)
    return _result("strike_convexity", -np.diff(slopes, axis=-1), tolerance)


def check_calendar_monotonicity(prices, maturities, *, tolerance=1e-10):
    maturities, prices = _grid(maturities, prices, "maturity")
    return _result("calendar_monotonicity", -np.diff(prices, axis=-1), tolerance)


def check_nonnegative_gamma(gammas, *, tolerance=1e-10):
    gammas = np.asarray(gammas, dtype=float)
    if gammas.size == 0 or not np.all(np.isfinite(gammas)):
        raise ValueError("gamma check requires non-empty finite values")
    return _result("nonnegative_gamma", -gammas, tolerance)


def check_greek_consistency(
    spots,
    prices,
    deltas,
    gammas,
    *,
    tolerance=1e-4,
):
    spots, prices = _grid(spots, prices, "spot")
    deltas = np.asarray(deltas, dtype=float)
    gammas = np.asarray(gammas, dtype=float)
    if prices.shape != deltas.shape or prices.shape != gammas.shape or spots.size < 3:
        raise ValueError("prices, deltas and gammas must share a spot grid with >=3 points")
    numeric_delta = np.gradient(prices, spots, axis=-1, edge_order=2)
    numeric_gamma = np.gradient(numeric_delta, spots, axis=-1, edge_order=2)
    errors = np.concatenate(
        (
            np.abs(numeric_delta[..., 1:-1] - deltas[..., 1:-1]).reshape(-1),
            np.abs(numeric_gamma[..., 1:-1] - gammas[..., 1:-1]).reshape(-1),
        )
    )
    return _result("greek_consistency", errors, tolerance)


def validation_report(*checks, applicable_checks=None, metadata=None):
    """Build the sole aggregate ``arbitrage_free`` decision.

    When ``applicable_checks`` is supplied, omitted or duplicate results make
    the aggregate fail even if every provided result passes.
    """
    if not checks or not all(isinstance(check, CheckResult) for check in checks):
        raise ValueError("validation_report requires one or more CheckResult objects")
    expected = tuple(applicable_checks or ())
    if expected and (
        len(expected) != len(set(expected))
        or not all(isinstance(name, str) and name for name in expected)
    ):
        raise ValueError("applicable_checks must contain distinct non-empty names")
    return HardValidationReport(tuple(checks), expected, dict(metadata or {}))
