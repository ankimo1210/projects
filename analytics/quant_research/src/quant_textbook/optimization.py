"""Transparent first- and second-order optimization algorithms for B4.

These routines favor numerical contracts and inspectable convergence traces
over feature breadth.  Every method records the objective, a gradient-mapping
norm, feasibility, and accepted step size from the initial point onward.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
ScalarFunction = Callable[[FloatArray], float]
GradientFunction = Callable[[FloatArray], ArrayLike]
HessianFunction = Callable[[FloatArray], ArrayLike]
Projection = Callable[[FloatArray], ArrayLike]
ProximalOperator = Callable[[FloatArray, float], ArrayLike]
FeasibilityFunction = Callable[[FloatArray], float]


def _point(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _positive_scalar(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and strictly positive")
    return result


def _unit_interval(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or not 0.0 < result < 1.0:
        raise ValueError(f"{name} must be strictly between zero and one")
    return result


def _positive_integer(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be strictly positive")
    return int(value)


def _objective(function: ScalarFunction, point: FloatArray, *, name: str = "objective") -> float:
    if not callable(function):
        raise TypeError(f"{name} must be callable")
    value = np.asarray(function(point.copy()), dtype=float)
    if value.ndim != 0 or not np.isfinite(value):
        raise FloatingPointError(f"{name} must return one finite scalar")
    return float(value)


def _finite_sum(left: float, right: float, *, name: str) -> float:
    """Add two validated objective terms without admitting float overflow."""

    with np.errstate(over="ignore", invalid="ignore"):
        value = float(np.add(left, right))
    if not np.isfinite(value):
        raise FloatingPointError(f"{name} must be one finite scalar")
    return value


def _gradient(function: GradientFunction, point: FloatArray) -> FloatArray:
    if not callable(function):
        raise TypeError("gradient must be callable")
    value = np.asarray(function(point.copy()), dtype=float)
    if value.shape != point.shape:
        raise ValueError("gradient must return one finite value per parameter")
    if not np.all(np.isfinite(value)):
        raise FloatingPointError("gradient returned non-finite values")
    return value


def _hessian(function: HessianFunction, point: FloatArray) -> FloatArray:
    if not callable(function):
        raise TypeError("hessian must be callable")
    value = np.asarray(function(point.copy()), dtype=float)
    expected_shape = (point.size, point.size)
    if value.shape != expected_shape:
        raise ValueError(f"hessian must have shape {expected_shape}")
    if not np.all(np.isfinite(value)):
        raise FloatingPointError("hessian returned non-finite values")
    scale = float(np.linalg.norm(value, ord=np.inf))
    tolerance = 100.0 * point.size * np.finfo(float).eps * scale
    if float(np.linalg.norm(value - value.T, ord=np.inf)) > tolerance:
        raise ValueError("hessian must be symmetric within floating-point tolerance")
    return 0.5 * (value + value.T)


def _transform(
    function: Projection,
    point: FloatArray,
    *,
    name: str,
) -> FloatArray:
    if not callable(function):
        raise TypeError(f"{name} must be callable")
    value = np.asarray(function(point.copy()), dtype=float)
    if value.shape != point.shape:
        raise ValueError(f"{name} must preserve the parameter shape")
    if not np.all(np.isfinite(value)):
        raise FloatingPointError(f"{name} returned non-finite values")
    return value


def _proximal(
    function: ProximalOperator,
    point: FloatArray,
    step_size: float,
) -> FloatArray:
    if not callable(function):
        raise TypeError("proximal_operator must be callable")
    value = np.asarray(function(point.copy(), step_size), dtype=float)
    if value.shape != point.shape:
        raise ValueError("proximal_operator must preserve the parameter shape")
    if not np.all(np.isfinite(value)):
        raise FloatingPointError("proximal_operator returned non-finite values")
    return value


def _feasibility(
    function: FeasibilityFunction | None,
    point: FloatArray,
) -> float:
    if function is None:
        return 0.0
    if not callable(function):
        raise TypeError("feasibility must be callable")
    value = np.asarray(function(point.copy()), dtype=float)
    if value.ndim != 0 or not np.isfinite(value) or value < 0.0:
        raise ValueError("feasibility must return one finite non-negative scalar")
    return float(value)


def _read_only(values: ArrayLike) -> FloatArray:
    result = np.asarray(values, dtype=float).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class OptimizationTrace:
    """Per-iterate diagnostics including the initial point at index zero.

    ``gradient_mapping_norms`` are normalized by the initial raw mapping norm,
    which makes the stopping rule invariant to a positive rescaling of the
    objective.  ``feasibility_values`` use the same initial-value
    normalization, making the stopping rule invariant to positive changes in
    the residual's units.  The corresponding ``raw_*`` histories retain the
    caller's original units.
    """

    objective_values: FloatArray
    gradient_mapping_norms: FloatArray
    raw_gradient_mapping_norms: FloatArray
    gradient_mapping_scale: float
    feasibility_values: FloatArray
    raw_feasibility_values: FloatArray
    feasibility_scale: float
    step_sizes: FloatArray


@dataclass(frozen=True)
class OptimizationResult:
    """Final iterate and a complete convergence trace."""

    x: FloatArray
    converged: bool
    iterations: int
    message: str
    trace: OptimizationTrace
    method: str

    @property
    def objective(self) -> float:
        """Final recorded objective value."""

        return float(self.trace.objective_values[-1])

    @property
    def gradient_mapping_norm(self) -> float:
        """Final objective-scale-normalized first-order optimality measure."""

        return float(self.trace.gradient_mapping_norms[-1])

    @property
    def raw_gradient_mapping_norm(self) -> float:
        """Final first-order measure in the derivative's original units."""

        return float(self.trace.raw_gradient_mapping_norms[-1])

    @property
    def feasibility(self) -> float:
        """Final initial-scale-normalized feasibility residual."""

        return float(self.trace.feasibility_values[-1])

    @property
    def raw_feasibility(self) -> float:
        """Final feasibility residual in the callback's original units."""

        return float(self.trace.raw_feasibility_values[-1])


def _result(
    *,
    point: FloatArray,
    converged: bool,
    message: str,
    method: str,
    objectives: list[float],
    mappings: list[float],
    feasibilities: list[float],
    steps: list[float],
) -> OptimizationResult:
    if not (len(objectives) == len(mappings) == len(feasibilities) == len(steps)):
        raise RuntimeError("optimization histories have inconsistent lengths")
    raw_mappings = np.asarray(mappings, dtype=float)
    mapping_scale = float(raw_mappings[0])
    if mapping_scale > 0.0:
        normalized_mappings = raw_mappings / mapping_scale
    else:
        normalized_mappings = np.where(raw_mappings == 0.0, 0.0, np.inf)
    raw_feasibilities = np.asarray(feasibilities, dtype=float)
    feasibility_scale = float(raw_feasibilities[0])
    if feasibility_scale > 0.0:
        normalized_feasibilities = raw_feasibilities / feasibility_scale
    else:
        normalized_feasibilities = np.where(raw_feasibilities == 0.0, 0.0, np.inf)
    return OptimizationResult(
        x=_read_only(point),
        converged=converged,
        iterations=len(objectives) - 1,
        message=message,
        trace=OptimizationTrace(
            objective_values=_read_only(objectives),
            gradient_mapping_norms=_read_only(normalized_mappings),
            raw_gradient_mapping_norms=_read_only(raw_mappings),
            gradient_mapping_scale=mapping_scale,
            feasibility_values=_read_only(normalized_feasibilities),
            raw_feasibility_values=_read_only(raw_feasibilities),
            feasibility_scale=feasibility_scale,
            step_sizes=_read_only(steps),
        ),
        method=method,
    )


def _normalized_residual(value: float, scale: float) -> float:
    if scale > 0.0:
        return value / scale
    return 0.0 if value == 0.0 else np.inf


def _configuration(
    *,
    step_size: float,
    tolerance: float,
    max_iterations: int,
    contraction: float,
    armijo: float,
) -> tuple[float, float, int, float, float]:
    return (
        _positive_scalar(step_size, name="step_size"),
        _positive_scalar(tolerance, name="tolerance"),
        _positive_integer(max_iterations, name="max_iterations"),
        _unit_interval(contraction, name="contraction"),
        _unit_interval(armijo, name="armijo"),
    )


def gradient_descent(
    objective: ScalarFunction,
    gradient: GradientFunction,
    initial: ArrayLike,
    *,
    step_size: float = 1.0,
    backtracking: bool = False,
    contraction: float = 0.5,
    armijo: float = 1e-4,
    tolerance: float = 1e-8,
    max_iterations: int = 1_000,
    feasibility: FeasibilityFunction | None = None,
    minimum_step: float = 1e-16,
) -> OptimizationResult:
    """Minimize a smooth objective by fixed-step or Armijo gradient descent."""

    if not isinstance(backtracking, bool):
        raise TypeError("backtracking must be a boolean")
    step, threshold, maximum, shrinkage, armijo_constant = _configuration(
        step_size=step_size,
        tolerance=tolerance,
        max_iterations=max_iterations,
        contraction=contraction,
        armijo=armijo,
    )
    smallest_step = _positive_scalar(minimum_step, name="minimum_step")
    point = _point(initial, name="initial")
    value = _objective(objective, point)
    derivative = _gradient(gradient, point)
    mapping = float(np.linalg.norm(derivative))
    mapping_scale = mapping
    feasibility_value = _feasibility(feasibility, point)
    feasibility_scale = feasibility_value
    objectives = [value]
    mappings = [mapping]
    feasibilities = [feasibility_value]
    steps = [0.0]
    method = "backtracking_gradient_descent" if backtracking else "gradient_descent"
    if (
        _normalized_residual(mapping, mapping_scale) <= threshold
        and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
    ):
        return _result(
            point=point,
            converged=True,
            message="initial point satisfies the stopping rule",
            method=method,
            objectives=objectives,
            mappings=mappings,
            feasibilities=feasibilities,
            steps=steps,
        )

    for _ in range(maximum):
        accepted_step = step
        direction = -derivative
        while True:
            candidate = point + accepted_step * direction
            try:
                candidate_value = _objective(objective, candidate)
            except FloatingPointError:
                candidate_value = np.inf
            sufficient = candidate_value <= value + armijo_constant * accepted_step * float(
                derivative @ direction
            )
            if not backtracking or sufficient:
                break
            accepted_step *= shrinkage
            if accepted_step < smallest_step:
                return _result(
                    point=point,
                    converged=False,
                    message="backtracking line search reached minimum_step",
                    method=method,
                    objectives=objectives,
                    mappings=mappings,
                    feasibilities=feasibilities,
                    steps=steps,
                )
        if not np.isfinite(candidate_value):
            return _result(
                point=point,
                converged=False,
                message="fixed step produced a non-finite objective",
                method=method,
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
        point = candidate
        value = float(candidate_value)
        derivative = _gradient(gradient, point)
        mapping = float(np.linalg.norm(derivative))
        feasibility_value = _feasibility(feasibility, point)
        objectives.append(value)
        mappings.append(mapping)
        feasibilities.append(feasibility_value)
        steps.append(accepted_step)
        if (
            _normalized_residual(mapping, mapping_scale) <= threshold
            and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
        ):
            return _result(
                point=point,
                converged=True,
                message="gradient norm and feasibility satisfy tolerance",
                method=method,
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
    return _result(
        point=point,
        converged=False,
        message="maximum iterations reached",
        method=method,
        objectives=objectives,
        mappings=mappings,
        feasibilities=feasibilities,
        steps=steps,
    )


def backtracking_gradient_descent(
    objective: ScalarFunction,
    gradient: GradientFunction,
    initial: ArrayLike,
    **kwargs: object,
) -> OptimizationResult:
    """Convenience wrapper for Armijo backtracking gradient descent."""

    if "backtracking" in kwargs:
        raise TypeError("backtracking_gradient_descent fixes backtracking=True")
    return gradient_descent(
        objective,
        gradient,
        initial,
        backtracking=True,
        **kwargs,  # type: ignore[arg-type]
    )


def newton_method(
    objective: ScalarFunction,
    gradient: GradientFunction,
    hessian: HessianFunction,
    initial: ArrayLike,
    *,
    step_size: float = 1.0,
    backtracking: bool = True,
    contraction: float = 0.5,
    armijo: float = 1e-4,
    tolerance: float = 1e-8,
    max_iterations: int = 100,
    feasibility: FeasibilityFunction | None = None,
    minimum_step: float = 1e-16,
) -> OptimizationResult:
    """Newton's method with a positive-definite and descent-direction audit."""

    if not isinstance(backtracking, bool):
        raise TypeError("backtracking must be a boolean")
    step, threshold, maximum, shrinkage, armijo_constant = _configuration(
        step_size=step_size,
        tolerance=tolerance,
        max_iterations=max_iterations,
        contraction=contraction,
        armijo=armijo,
    )
    smallest_step = _positive_scalar(minimum_step, name="minimum_step")
    point = _point(initial, name="initial")
    value = _objective(objective, point)
    derivative = _gradient(gradient, point)
    mapping = float(np.linalg.norm(derivative))
    mapping_scale = mapping
    feasibility_value = _feasibility(feasibility, point)
    feasibility_scale = feasibility_value
    objectives = [value]
    mappings = [mapping]
    feasibilities = [feasibility_value]
    steps = [0.0]
    if (
        _normalized_residual(mapping, mapping_scale) <= threshold
        and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
    ):
        return _result(
            point=point,
            converged=True,
            message="initial point satisfies the stopping rule",
            method="newton",
            objectives=objectives,
            mappings=mappings,
            feasibilities=feasibilities,
            steps=steps,
        )

    for _ in range(maximum):
        curvature = _hessian(hessian, point)
        try:
            np.linalg.cholesky(curvature)
            direction = np.linalg.solve(curvature, -derivative)
        except np.linalg.LinAlgError:
            return _result(
                point=point,
                converged=False,
                message="Hessian is not positive definite at the current iterate",
                method="newton",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
        directional_derivative = float(derivative @ direction)
        if directional_derivative >= 0.0:
            return _result(
                point=point,
                converged=False,
                message="Newton direction is not a descent direction",
                method="newton",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
        accepted_step = step
        while True:
            candidate = point + accepted_step * direction
            try:
                candidate_value = _objective(objective, candidate)
            except FloatingPointError:
                candidate_value = np.inf
            sufficient = candidate_value <= value + armijo_constant * accepted_step * (
                directional_derivative
            )
            if not backtracking or sufficient:
                break
            accepted_step *= shrinkage
            if accepted_step < smallest_step:
                return _result(
                    point=point,
                    converged=False,
                    message="backtracking line search reached minimum_step",
                    method="newton",
                    objectives=objectives,
                    mappings=mappings,
                    feasibilities=feasibilities,
                    steps=steps,
                )
        if not np.isfinite(candidate_value):
            return _result(
                point=point,
                converged=False,
                message="Newton step produced a non-finite objective",
                method="newton",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
        point = candidate
        value = float(candidate_value)
        derivative = _gradient(gradient, point)
        mapping = float(np.linalg.norm(derivative))
        feasibility_value = _feasibility(feasibility, point)
        objectives.append(value)
        mappings.append(mapping)
        feasibilities.append(feasibility_value)
        steps.append(accepted_step)
        if (
            _normalized_residual(mapping, mapping_scale) <= threshold
            and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
        ):
            return _result(
                point=point,
                converged=True,
                message="gradient norm and feasibility satisfy tolerance",
                method="newton",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
    return _result(
        point=point,
        converged=False,
        message="maximum iterations reached",
        method="newton",
        objectives=objectives,
        mappings=mappings,
        feasibilities=feasibilities,
        steps=steps,
    )


def projected_gradient(
    objective: ScalarFunction,
    gradient: GradientFunction,
    projection: Projection,
    initial: ArrayLike,
    *,
    step_size: float = 1.0,
    backtracking: bool = True,
    contraction: float = 0.5,
    armijo: float = 1e-4,
    tolerance: float = 1e-8,
    max_iterations: int = 1_000,
    feasibility: FeasibilityFunction | None = None,
    minimum_step: float = 1e-16,
) -> OptimizationResult:
    """Projected gradient descent for a caller-supplied convex projection.

    If no feasibility function is supplied, the residual is the distance to a
    second projection.  The gradient mapping is ``(x - Pi(x - t*g))/t``.
    """

    if not isinstance(backtracking, bool):
        raise TypeError("backtracking must be a boolean")
    step, threshold, maximum, shrinkage, armijo_constant = _configuration(
        step_size=step_size,
        tolerance=tolerance,
        max_iterations=max_iterations,
        contraction=contraction,
        armijo=armijo,
    )
    smallest_step = _positive_scalar(minimum_step, name="minimum_step")
    point = _transform(projection, _point(initial, name="initial"), name="projection")

    def constraint_residual(location: FloatArray) -> float:
        if feasibility is not None:
            return _feasibility(feasibility, location)
        reprojected = _transform(projection, location, name="projection")
        return float(np.linalg.norm(location - reprojected, ord=np.inf))

    value = _objective(objective, point)
    derivative = _gradient(gradient, point)
    derivative_scale = float(np.linalg.norm(derivative))
    mapping_step = step / derivative_scale if derivative_scale > 0.0 else step
    projected = _transform(
        projection,
        point - mapping_step * derivative,
        name="projection",
    )
    mapping = float(np.linalg.norm((point - projected) / mapping_step))
    mapping_scale = mapping
    feasibility_value = constraint_residual(point)
    feasibility_scale = feasibility_value
    objectives = [value]
    mappings = [mapping]
    feasibilities = [feasibility_value]
    steps = [0.0]
    if (
        _normalized_residual(mapping, mapping_scale) <= threshold
        and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
    ):
        return _result(
            point=point,
            converged=True,
            message="initial point satisfies the projected stopping rule",
            method="projected_gradient",
            objectives=objectives,
            mappings=mappings,
            feasibilities=feasibilities,
            steps=steps,
        )

    for _ in range(maximum):
        accepted_step = step
        while True:
            candidate = _transform(
                projection,
                point - accepted_step * derivative,
                name="projection",
            )
            candidate_value = _objective(objective, candidate)
            displacement = candidate - point
            sufficient = candidate_value <= value + float(derivative @ displacement) + (
                0.5 / accepted_step
            ) * float(displacement @ displacement)
            # ``armijo`` supplies a small margin against an equality caused by
            # roundoff, without changing the projected majorization rule.
            sufficient = sufficient or candidate_value <= value - armijo_constant * (
                float(displacement @ displacement) / accepted_step
            )
            if not backtracking or sufficient:
                break
            accepted_step *= shrinkage
            if accepted_step < smallest_step:
                return _result(
                    point=point,
                    converged=False,
                    message="projected backtracking reached minimum_step",
                    method="projected_gradient",
                    objectives=objectives,
                    mappings=mappings,
                    feasibilities=feasibilities,
                    steps=steps,
                )
        point = candidate
        value = candidate_value
        derivative = _gradient(gradient, point)
        projected = _transform(
            projection,
            point - mapping_step * derivative,
            name="projection",
        )
        mapping = float(np.linalg.norm((point - projected) / mapping_step))
        feasibility_value = constraint_residual(point)
        objectives.append(value)
        mappings.append(mapping)
        feasibilities.append(feasibility_value)
        steps.append(accepted_step)
        if (
            _normalized_residual(mapping, mapping_scale) <= threshold
            and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
        ):
            return _result(
                point=point,
                converged=True,
                message="gradient mapping and feasibility satisfy tolerance",
                method="projected_gradient",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
    return _result(
        point=point,
        converged=False,
        message="maximum iterations reached",
        method="projected_gradient",
        objectives=objectives,
        mappings=mappings,
        feasibilities=feasibilities,
        steps=steps,
    )


def proximal_gradient(
    smooth_objective: ScalarFunction,
    gradient: GradientFunction,
    nonsmooth_objective: ScalarFunction,
    proximal_operator: ProximalOperator,
    initial: ArrayLike,
    *,
    step_size: float = 1.0,
    backtracking: bool = True,
    contraction: float = 0.5,
    tolerance: float = 1e-8,
    max_iterations: int = 1_000,
    feasibility: FeasibilityFunction | None = None,
    minimum_step: float = 1e-16,
) -> OptimizationResult:
    """Proximal gradient for ``smooth_objective + nonsmooth_objective``.

    ``proximal_operator(z, t)`` must return the proximal map of ``t*g`` at
    ``z``.  The stopping measure is the proximal-gradient mapping.
    """

    if not isinstance(backtracking, bool):
        raise TypeError("backtracking must be a boolean")
    step = _positive_scalar(step_size, name="step_size")
    threshold = _positive_scalar(tolerance, name="tolerance")
    maximum = _positive_integer(max_iterations, name="max_iterations")
    shrinkage = _unit_interval(contraction, name="contraction")
    smallest_step = _positive_scalar(minimum_step, name="minimum_step")
    point = _point(initial, name="initial")
    smooth_value = _objective(smooth_objective, point, name="smooth_objective")
    nonsmooth_value = _objective(
        nonsmooth_objective,
        point,
        name="nonsmooth_objective",
    )
    value = _finite_sum(
        smooth_value,
        nonsmooth_value,
        name="smooth_objective + nonsmooth_objective",
    )
    derivative = _gradient(gradient, point)
    derivative_scale = float(np.linalg.norm(derivative))
    mapping_step = step / derivative_scale if derivative_scale > 0.0 else step
    prox = _proximal(
        proximal_operator,
        point - mapping_step * derivative,
        mapping_step,
    )
    mapping = float(np.linalg.norm((point - prox) / mapping_step))
    mapping_scale = mapping
    feasibility_value = _feasibility(feasibility, point)
    feasibility_scale = feasibility_value
    objectives = [value]
    mappings = [mapping]
    feasibilities = [feasibility_value]
    steps = [0.0]
    if (
        _normalized_residual(mapping, mapping_scale) <= threshold
        and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
    ):
        return _result(
            point=point,
            converged=True,
            message="initial point satisfies the proximal stopping rule",
            method="proximal_gradient",
            objectives=objectives,
            mappings=mappings,
            feasibilities=feasibilities,
            steps=steps,
        )

    for _ in range(maximum):
        accepted_step = step
        while True:
            candidate = _proximal(
                proximal_operator,
                point - accepted_step * derivative,
                accepted_step,
            )
            candidate_smooth = _objective(
                smooth_objective,
                candidate,
                name="smooth_objective",
            )
            displacement = candidate - point
            quadratic_upper_bound = (
                smooth_value
                + float(derivative @ displacement)
                + (0.5 / accepted_step) * float(displacement @ displacement)
            )
            if not backtracking or candidate_smooth <= quadratic_upper_bound:
                break
            accepted_step *= shrinkage
            if accepted_step < smallest_step:
                return _result(
                    point=point,
                    converged=False,
                    message="proximal backtracking reached minimum_step",
                    method="proximal_gradient",
                    objectives=objectives,
                    mappings=mappings,
                    feasibilities=feasibilities,
                    steps=steps,
                )
        point = candidate
        smooth_value = candidate_smooth
        nonsmooth_value = _objective(
            nonsmooth_objective,
            point,
            name="nonsmooth_objective",
        )
        value = _finite_sum(
            smooth_value,
            nonsmooth_value,
            name="smooth_objective + nonsmooth_objective",
        )
        derivative = _gradient(gradient, point)
        prox = _proximal(
            proximal_operator,
            point - mapping_step * derivative,
            mapping_step,
        )
        mapping = float(np.linalg.norm((point - prox) / mapping_step))
        feasibility_value = _feasibility(feasibility, point)
        objectives.append(value)
        mappings.append(mapping)
        feasibilities.append(feasibility_value)
        steps.append(accepted_step)
        if (
            _normalized_residual(mapping, mapping_scale) <= threshold
            and _normalized_residual(feasibility_value, feasibility_scale) <= threshold
        ):
            return _result(
                point=point,
                converged=True,
                message="proximal mapping and feasibility satisfy tolerance",
                method="proximal_gradient",
                objectives=objectives,
                mappings=mappings,
                feasibilities=feasibilities,
                steps=steps,
            )
    return _result(
        point=point,
        converged=False,
        message="maximum iterations reached",
        method="proximal_gradient",
        objectives=objectives,
        mappings=mappings,
        feasibilities=feasibilities,
        steps=steps,
    )


def _finite_difference_gradient(
    objective: ScalarFunction,
    point: FloatArray,
    *,
    relative_step: float,
) -> FloatArray:
    gradient = np.empty(point.size, dtype=float)
    for index in range(point.size):
        step = relative_step * max(1.0, abs(float(point[index])))
        upper = point.copy()
        lower = point.copy()
        upper[index] += step
        lower[index] -= step
        gradient[index] = (_objective(objective, upper) - _objective(objective, lower)) / (
            2.0 * step
        )
    return gradient


@dataclass(frozen=True)
class GradientAudit:
    """Analytic and step-swept central differences with a conservative verdict."""

    point: FloatArray
    analytic_gradient: FloatArray
    finite_difference_gradient: FloatArray
    finite_difference_gradients: FloatArray
    relative_steps: FloatArray
    absolute_errors: FloatArray
    maximum_absolute_error: float
    relative_error: float
    step_instability: float
    cancellation_detected: bool
    tolerance: float
    passed: bool
    diagnostic: str


def finite_difference_gradient_audit(
    objective: ScalarFunction,
    analytic_gradient: GradientFunction,
    point: ArrayLike,
    *,
    relative_step: float = 1e-6,
    absolute_tolerance: float = 1e-7,
    relative_tolerance: float = 1e-5,
) -> GradientAudit:
    """Audit an analytic gradient with a central-difference step sweep.

    The verdict is based on a derivative-relative error, so multiplying the
    objective by a positive scalar does not turn a wrong gradient into a pass.
    When every probe equals a large nonzero center value, the audit reports
    floating-point cancellation instead of claiming that a zero gradient was
    verified.
    """

    location = _point(point, name="point")
    step = _positive_scalar(relative_step, name="relative_step")
    absolute = _positive_scalar(absolute_tolerance, name="absolute_tolerance")
    relative = _positive_scalar(relative_tolerance, name="relative_tolerance")
    analytic = _gradient(analytic_gradient, location)
    step_multipliers = np.array([0.25, 0.5, 1.0, 2.0, 4.0])
    relative_steps = step * step_multipliers
    numeric_sweep = np.vstack(
        [
            _finite_difference_gradient(
                objective,
                location,
                relative_step=float(candidate_step),
            )
            for candidate_step in relative_steps
        ]
    )
    numeric = np.median(numeric_sweep, axis=0)
    errors = np.abs(analytic - numeric)
    maximum_error = float(np.max(errors))
    scale = max(
        float(np.linalg.norm(analytic, ord=np.inf)),
        float(np.linalg.norm(numeric, ord=np.inf)),
        float(np.max(np.abs(numeric_sweep))),
        np.finfo(float).tiny,
    )
    normalized_tolerance = absolute + relative
    relative_error = maximum_error / scale
    step_instability = float(np.max(np.ptp(numeric_sweep, axis=0))) / scale

    center = _objective(objective, location)
    cancellation_by_coordinate = np.ones(location.size, dtype=bool)
    for candidate_step in relative_steps:
        for index in range(location.size):
            coordinate_step = float(candidate_step) * max(1.0, abs(float(location[index])))
            upper = location.copy()
            lower = location.copy()
            upper[index] += coordinate_step
            lower[index] -= coordinate_step
            cancellation_by_coordinate[index] &= (
                _objective(objective, upper) == center and _objective(objective, lower) == center
            )
    cancellation_detected = bool(center != 0.0 and np.any(cancellation_by_coordinate))
    stable_steps = step_instability <= max(10.0 * normalized_tolerance, 1e-3)
    passed = bool(
        relative_error <= normalized_tolerance and stable_steps and not cancellation_detected
    )
    if cancellation_detected:
        diagnostic = "finite-difference probes were absorbed by a nonzero objective level"
    elif not stable_steps:
        diagnostic = "finite-difference estimates are unstable across the step sweep"
    elif passed:
        diagnostic = "analytic and finite-difference gradients agree on a stable step range"
    else:
        diagnostic = "analytic and finite-difference gradients disagree on a relative scale"
    return GradientAudit(
        point=_read_only(location),
        analytic_gradient=_read_only(analytic),
        finite_difference_gradient=_read_only(numeric),
        finite_difference_gradients=_read_only(numeric_sweep),
        relative_steps=_read_only(relative_steps),
        absolute_errors=_read_only(errors),
        maximum_absolute_error=maximum_error,
        relative_error=float(relative_error),
        step_instability=step_instability,
        cancellation_detected=cancellation_detected,
        tolerance=float(normalized_tolerance),
        passed=passed,
        diagnostic=diagnostic,
    )
