"""Hull GE §27.8 Monte Carlo simulation and American options.

Two ways to choose early exercise on simulated paths: the least-squares
approach (Longstaff-Schwartz) and the exercise boundary parameterization
(Andersen). Both fit a policy on one set of paths; ``apply_least_squares`` and
``apply_boundary`` value that policy on new paths. Hull describes this two-pass
practice for the boundary (p.665); his least-squares example values on the
fitting paths.
"""

from __future__ import annotations

import itertools
import math
import operator
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

_KINDS = ("put", "call")


@dataclass(frozen=True)
class RegressionStep:
    """One early-exercise time of the least-squares approach.

    ``paths`` are the in-the-money path indices used in the regression,
    ``coefficients`` multiply the monomials of the states (``1, S, S^2`` for
    one variable and degree 2), ``continuation`` are the fitted values of
    continuing on those paths and ``exercised`` the paths exercised here.
    Without enough in-the-money paths for the regression the coefficients are
    empty and nothing is exercised.
    """

    time: float
    paths: np.ndarray
    coefficients: np.ndarray
    continuation: np.ndarray
    exercise_values: np.ndarray
    exercised: np.ndarray


@dataclass(frozen=True)
class BoundaryStep:
    """One early-exercise time of the boundary parameterization.

    ``candidates`` are the critical values tried (the first, +-inf, means
    never exercise) and ``averages`` the mean option value across all paths
    at ``time`` for each. ``threshold`` maximizes the mean; every critical
    value in ``interval`` gives the same mean. ``values`` are the path values
    at ``time`` under the chosen threshold.
    """

    time: float
    candidates: np.ndarray
    averages: np.ndarray
    threshold: float
    interval: tuple[float, float]
    values: np.ndarray


@dataclass(frozen=True)
class PolicyValue:
    """Value of an exercise policy on a set of paths.

    ``cash_flows`` has one row per path and one column per exercise time,
    undiscounted as in Hull's Table 27.7. ``continuation_value`` is their
    discounted mean, ``standard_error`` its Monte Carlo standard error,
    ``exercise_now`` the payoff at time zero and ``price`` the larger of the two.
    ``price`` assumes the option may also be exercised at time zero; without that
    right (a Bermudan whose first date is later) the value is ``continuation_value``.
    """

    price: float
    continuation_value: float
    standard_error: float
    exercise_now: float
    cash_flows: np.ndarray


@dataclass(frozen=True)
class LeastSquaresResult(PolicyValue):
    """Least-squares value on the fitting paths and the fitted regressions."""

    steps: tuple[RegressionStep, ...]
    degree: int


@dataclass(frozen=True)
class BoundaryResult(PolicyValue):
    """Boundary-parameterization value on the fitting paths and the boundary."""

    steps: tuple[BoundaryStep, ...]
    boundary: tuple[float, ...]
    kind: str


def _inputs(paths, payoff, rate, times):
    states = np.asarray(paths, dtype=float)
    if states.ndim not in (2, 3):
        raise ValueError(
            "paths must have shape (paths, times + 1) or (paths, times + 1, variables)"
        )
    if states.ndim == 2:
        states = states[:, :, None]
    grid = np.asarray(times, dtype=float)
    if grid.ndim != 1 or grid.size == 0:
        raise ValueError("times must list the exercise times")
    if not (math.isfinite(rate) and np.all(np.isfinite(grid)) and np.all(np.isfinite(states))):
        raise ValueError("rate, times and paths must be finite")
    if grid[0] <= 0 or np.any(np.diff(grid) <= 0):
        raise ValueError("times must be positive and strictly increasing")
    if states.shape[1] != grid.size + 1:
        raise ValueError("paths must have one column per exercise time plus the initial state")
    if not np.all(states[:, 0] == states[0, 0]):
        raise ValueError("all paths must start from the same initial state")
    if not callable(payoff):
        raise ValueError("payoff must be callable")
    values = []
    for column in range(states.shape[1]):
        state = states[:, column, 0] if states.shape[2] == 1 else states[:, column]
        value = np.asarray(payoff(state), dtype=float)
        if value.shape != (states.shape[0],):
            raise ValueError("payoff must return one value per path")
        if not np.all(np.isfinite(value)):
            raise ValueError("payoff values must be finite")
        values.append(value)
    discounts = np.exp(-rate * np.diff(np.concatenate([[0.0], grid])))
    return states, np.column_stack(values), grid, discounts


def _powers(variables, degree):
    return [
        tuple(combo.count(i) for i in range(variables))
        for total in range(degree + 1)
        for combo in itertools.combinations_with_replacement(range(variables), total)
    ]


def _basis(states, powers, scale):
    return np.column_stack(
        [np.prod((states / scale) ** np.array(power), axis=1) for power in powers]
    )


def _value(cash_flows, times, rate, exercise_now):
    discounted = cash_flows @ np.exp(-rate * times)
    mean = float(discounted.mean())
    error = (
        float(discounted.std(ddof=1) / math.sqrt(discounted.size)) if discounted.size > 1 else 0.0
    )
    return {
        "price": max(exercise_now, mean),
        "continuation_value": mean,
        "standard_error": error,
        "exercise_now": exercise_now,
        "cash_flows": cash_flows,
    }


def _check_times(fitted_times, grid):
    """Applied exercise times must equal the fitted ones up to floating-point rounding."""
    if len(fitted_times) != grid.size - 1 or not all(
        math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
        for a, b in zip(fitted_times, grid[:-1], strict=True)
    ):
        raise ValueError("times must match the fitted exercise times")


def _first_exercise(exercise, payoffs):
    """Cash flows paying each path's payoff at the first time ``exercise`` is true."""
    cash_flows = np.zeros_like(payoffs)
    alive = np.ones(payoffs.shape[0], dtype=bool)
    for column in range(payoffs.shape[1]):
        now = alive & exercise[:, column]
        cash_flows[now, column] = payoffs[now, column]
        alive &= ~now
    return cash_flows


def least_squares(
    paths,
    payoff: Callable[[np.ndarray], np.ndarray],
    rate: float,
    times,
    *,
    degree: int = 2,
) -> LeastSquaresResult:
    """Longstaff-Schwartz least-squares value on ``paths`` (Hull §27.8, Tables 27.4-27.7).

    ``paths`` holds the initial state and the state at each exercise time in
    ``times`` (years, the last is maturity), one row per path; a third axis
    holds several state variables. ``payoff`` maps the states at one time to
    the exercise value of each path. Working backward, the discounted cash
    flows of the in-the-money paths are regressed on all monomials of the
    states up to ``degree`` (Hull's ``V = a + bS + cS^2`` for one variable),
    and a path is exercised when its exercise value beats the fitted value of
    continuing (strictly greater). ``rate`` is the continuously compounded
    risk-free rate. A time with fewer in-the-money paths than monomials is
    skipped: nothing is exercised there.
    """
    try:
        order = operator.index(degree)
    except TypeError:
        order = 0
    if isinstance(degree, bool) or order < 1:
        raise ValueError("degree must be a positive integer")
    degree = int(order)
    states, payoffs, grid, discounts = _inputs(paths, payoff, rate, times)
    powers = _powers(states.shape[2], degree)
    future = payoffs[:, -1].copy()
    exercise = np.zeros_like(payoffs, dtype=bool)
    exercise[:, -1] = payoffs[:, -1] > 0
    steps = []
    for column in range(grid.size - 1, 0, -1):
        future *= discounts[column]
        values = payoffs[:, column]
        itm = np.nonzero(values > 0)[0]
        coefficients = np.empty(0)
        continuation = np.empty(0)
        exercised = np.empty(0, dtype=int)
        if itm.size >= len(powers):
            state = states[itm, column]
            scale = np.mean(np.abs(state), axis=0)
            scale[scale == 0] = 1.0
            matrix = _basis(state, powers, scale)
            fitted, *_ = np.linalg.lstsq(matrix, future[itm], rcond=None)
            continuation = matrix @ fitted
            coefficients = fitted / np.array([np.prod(scale ** np.array(p)) for p in powers])
            exercised = itm[values[itm] > continuation]
            future[exercised] = values[exercised]
            exercise[exercised, column] = True
        steps.append(
            RegressionStep(
                time=float(grid[column - 1]),
                paths=itm,
                coefficients=coefficients,
                continuation=continuation,
                exercise_values=values[itm],
                exercised=exercised,
            )
        )
    cash_flows = _first_exercise(exercise[:, 1:], payoffs[:, 1:])
    return LeastSquaresResult(
        **_value(cash_flows, grid, rate, float(payoffs[0, 0])),
        steps=tuple(reversed(steps)),
        degree=degree,
    )


def apply_least_squares(fitted: LeastSquaresResult, paths, payoff, rate, times) -> PolicyValue:
    """Value the fitted least-squares exercise rule on new ``paths``.

    A path is exercised at the first time where it is in the money and its
    exercise value beats the fitted value of continuing. Applied to the paths
    it was fitted on, this reproduces ``fitted``; on new paths it removes the
    foresight of fitting and valuing on the same sample, the two-pass practice
    Hull describes for the exercise boundary (p.665). ``times`` must be the
    fitted exercise times (up to floating-point rounding).
    """
    states, payoffs, grid, _ = _inputs(paths, payoff, rate, times)
    _check_times([step.time for step in fitted.steps], grid)
    powers = _powers(states.shape[2], fitted.degree)
    exercise = payoffs[:, 1:] > 0
    for column, step in enumerate(fitted.steps, start=1):
        if step.coefficients.size == 0:
            exercise[:, column - 1] = False
            continue
        if step.coefficients.size != len(powers):
            raise ValueError("paths must have the fitted number of state variables")
        continuation = _basis(states[:, column], powers, 1.0) @ step.coefficients
        exercise[:, column - 1] &= payoffs[:, column] > continuation
    cash_flows = _first_exercise(exercise, payoffs[:, 1:])
    return PolicyValue(**_value(cash_flows, grid, rate, float(payoffs[0, 0])))


def _exercised(spots, itm, threshold, kind):
    return itm & (spots <= threshold if kind == "put" else spots >= threshold)


def _candidate_averages(prices, gains, continuation, kind):
    """Mean value for each critical price, from cumulative exercise gains.

    Exercising a put at ``S*`` takes every in-the-money path with ``S <= S*``,
    so moving ``S*`` up one price adds that price's gains (exercise value minus
    continuation) to the total; a call walks the prices downward.
    """
    order = np.argsort(prices if kind == "put" else -prices, kind="stable")
    ordered = prices[order]
    unique = np.unique(ordered) if kind == "put" else np.unique(ordered)[::-1]
    last = (
        np.searchsorted(ordered, unique, side="right")
        if kind == "put"
        else np.searchsorted(-ordered, -unique, side="right")
    ) - 1
    totals = continuation.sum() + np.concatenate([[0.0], np.cumsum(gains[order])[last]])
    never = -math.inf if kind == "put" else math.inf
    return np.concatenate([[never], unique]), totals / continuation.size


def exercise_boundary(
    paths,
    payoff: Callable[[np.ndarray], np.ndarray],
    rate: float,
    times,
    *,
    kind: str = "put",
) -> BoundaryResult:
    """Andersen's exercise boundary parameterization on ``paths`` (Hull §27.8, pp.664-665).

    The boundary at each early-exercise time is a critical asset price
    ``S*(t)``: a put is exercised when in the money and ``S <= S*(t)``, a call
    when ``S >= S*(t)``. Working backward from maturity, ``S*(t)`` is chosen
    among the in-the-money prices at ``t`` (or never exercising) to maximize
    the average option value at ``t`` over all paths, as in Hull's example;
    on a tie the first maximum is kept (the lowest put price, the highest call
    price). ``paths`` holds one state variable and the exercise region at each
    time is one interval ending at ``S*(t)``; more complicated situations need
    their own assumption about the shape of the boundary (Hull p.665). The
    other inputs are as in :func:`least_squares`.
    """
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")
    states, payoffs, grid, discounts = _inputs(paths, payoff, rate, times)
    if states.shape[2] != 1:
        raise ValueError("the boundary parameterization needs one state variable")
    spots = states[:, :, 0]
    never = -math.inf if kind == "put" else math.inf
    value = payoffs[:, -1].copy()
    exercise = np.zeros_like(payoffs, dtype=bool)
    exercise[:, -1] = payoffs[:, -1] > 0
    steps = []
    for column in range(grid.size - 1, 0, -1):
        continuation = value * discounts[column]
        itm = payoffs[:, column] > 0
        candidates, averages = _candidate_averages(
            spots[itm, column], payoffs[itm, column] - continuation[itm], continuation, kind
        )
        best = int(np.argmax(averages))
        threshold = float(candidates[best])
        following = float(candidates[best + 1]) if best + 1 < candidates.size else -never
        interval = (threshold, following) if kind == "put" else (following, threshold)
        chosen = _exercised(spots[:, column], itm, threshold, kind)
        exercise[:, column] = chosen
        value = np.where(chosen, payoffs[:, column], continuation)
        steps.append(
            BoundaryStep(
                time=float(grid[column - 1]),
                candidates=candidates,
                averages=averages,
                threshold=threshold,
                interval=interval,
                values=value.copy(),
            )
        )
    steps.reverse()
    cash_flows = _first_exercise(exercise[:, 1:], payoffs[:, 1:])
    return BoundaryResult(
        **_value(cash_flows, grid, rate, float(payoffs[0, 0])),
        steps=tuple(steps),
        boundary=tuple(step.threshold for step in steps),
        kind=kind,
    )


def apply_boundary(fitted: BoundaryResult, paths, payoff, rate, times) -> PolicyValue:
    """Value a fitted exercise boundary on new ``paths`` (Hull p.665).

    Hull notes that the paths used to find the boundary are discarded and a
    new simulation values the option. (Valuing on the fitting paths biases the
    value upward; §14.4 of vol06 measures this.) ``times`` must be the fitted
    exercise times (up to floating-point rounding).
    """
    states, payoffs, grid, _ = _inputs(paths, payoff, rate, times)
    _check_times([step.time for step in fitted.steps], grid)
    if states.shape[2] != 1:
        raise ValueError("the boundary parameterization needs one state variable")
    exercise = payoffs[:, 1:] > 0
    for column, threshold in enumerate(fitted.boundary, start=1):
        exercise[:, column - 1] = _exercised(
            states[:, column, 0], exercise[:, column - 1], threshold, fitted.kind
        )
    cash_flows = _first_exercise(exercise, payoffs[:, 1:])
    return PolicyValue(**_value(cash_flows, grid, rate, float(payoffs[0, 0])))
