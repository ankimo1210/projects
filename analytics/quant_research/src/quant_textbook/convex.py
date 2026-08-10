r"""Convex quadratic-program models, reference solves, and KKT audits.

The canonical problem is

.. math::

   \min_x \tfrac12 x^\top P x + q^\top x
   \quad\text{s.t.}\quad Gx\le h,\; Ax=b,\; \ell\le x\le u.

Inequality, lower-bound, and upper-bound multipliers are non-negative.  The
Lagrangian uses ``lambda * (Gx - h)``, ``mu_l * (l - x)``, and
``mu_u * (x - u)``.  Consequently, the local value derivative with respect
to an inequality right-hand side is ``-lambda``.

SciPy provides the reference primal solve.  Multipliers are reconstructed
independently from the active set so that the KKT audit has one convention
across SciPy versions, including SciPy 1.13 where SLSQP does not expose
multipliers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import qr
from scipy.optimize import Bounds, LinearConstraint, lsq_linear, minimize

FloatArray = NDArray[np.float64]
QPSolverMethod = Literal["SLSQP", "trust-constr"]


def _matrix(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _vector(values: ArrayLike, *, name: str, size: int | None = None) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional array")
    if size is not None and array.size != size:
        raise ValueError(f"{name} must contain exactly {size} entries")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _bounds_vector(
    values: ArrayLike | None,
    *,
    name: str,
    size: int,
    default: float,
) -> FloatArray:
    if values is None:
        return np.full(size, default, dtype=float)
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size != size:
        raise ValueError(f"{name} must contain exactly {size} entries")
    if np.any(np.isnan(array)):
        raise ValueError(f"{name} must not contain NaN")
    return array.copy()


def _units(values: tuple[str, ...] | None, *, name: str, size: int) -> tuple[str, ...]:
    if values is None:
        return ("dimensionless",) * size
    result = tuple(values)
    if len(result) != size:
        raise ValueError(f"{name} must contain exactly {size} entries")
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{name} entries must be non-empty strings")
    return result


def _positive_scalar(value: float, *, name: str, allow_zero: bool = False) -> float:
    result = float(value)
    valid = result >= 0.0 if allow_zero else result > 0.0
    if not np.isfinite(result) or not valid:
        qualifier = "non-negative" if allow_zero else "strictly positive"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return result


def _positive_integer(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be strictly positive")
    return int(value)


def _read_only(array: FloatArray) -> FloatArray:
    result = np.asarray(array, dtype=float).copy()
    result.setflags(write=False)
    return result


def _independent_row_indices(matrix: FloatArray) -> NDArray[np.int_]:
    """Select a deterministic independent row subset from a scaled matrix."""

    if matrix.shape[0] == 0:
        return np.empty(0, dtype=int)
    rank = int(np.linalg.matrix_rank(matrix))
    if rank == 0:
        return np.empty(0, dtype=int)
    _, _, pivots = qr(matrix.T, mode="economic", pivoting=True, check_finite=False)
    return np.sort(np.asarray(pivots[:rank], dtype=int))


@dataclass(frozen=True)
class QuadraticProgram:
    """A finite-dimensional quadratic program with explicit units.

    Empty inequality and equality systems are represented by ``None`` at
    construction and normalized to zero-row arrays.  Infinite variable bounds
    are allowed; all objective and linear-constraint coefficients must be
    finite.  A candidate model may have a non-PSD Hessian so that
    :func:`validate_quadratic_program` can explain why it is not a convex QP;
    the reference solver rejects such a model.
    """

    P: FloatArray
    q: FloatArray
    G: FloatArray | None = None
    h: FloatArray | None = None
    A: FloatArray | None = None
    b: FloatArray | None = None
    lower_bounds: FloatArray | None = None
    upper_bounds: FloatArray | None = None
    variable_units: tuple[str, ...] | None = None
    inequality_units: tuple[str, ...] | None = None
    equality_units: tuple[str, ...] | None = None
    objective_unit: str = "objective units"
    name: str = "quadratic_program"

    def __post_init__(self) -> None:
        hessian = _matrix(self.P, name="P")
        if hessian.shape[0] == 0 or hessian.shape[0] != hessian.shape[1]:
            raise ValueError("P must be a non-empty square matrix")
        size = hessian.shape[0]
        linear = _vector(self.q, name="q", size=size)
        symmetry_scale = float(np.linalg.norm(hessian, ord=np.inf))
        # A unit floor would incorrectly accept a tiny but materially
        # non-symmetric matrix after a change of units.  The all-zero matrix is
        # exactly symmetric and needs no positive floor.
        symmetry_tolerance = 100.0 * size * np.finfo(float).eps * symmetry_scale
        if float(np.linalg.norm(hessian - hessian.T, ord=np.inf)) > symmetry_tolerance:
            raise ValueError("P must be symmetric within floating-point tolerance")
        hessian = 0.5 * (hessian + hessian.T)

        if self.G is None:
            if self.h is not None:
                raise ValueError("h requires G")
            inequalities = np.empty((0, size), dtype=float)
            inequality_rhs = np.empty(0, dtype=float)
        else:
            inequalities = _matrix(self.G, name="G")
            if inequalities.shape[1] != size:
                raise ValueError("G must have one column per variable")
            if self.h is None:
                raise ValueError("G requires h")
            inequality_rhs = _vector(self.h, name="h", size=inequalities.shape[0])

        if self.A is None:
            if self.b is not None:
                raise ValueError("b requires A")
            equalities = np.empty((0, size), dtype=float)
            equality_rhs = np.empty(0, dtype=float)
        else:
            equalities = _matrix(self.A, name="A")
            if equalities.shape[1] != size:
                raise ValueError("A must have one column per variable")
            if self.b is None:
                raise ValueError("A requires b")
            equality_rhs = _vector(self.b, name="b", size=equalities.shape[0])

        lower = _bounds_vector(
            self.lower_bounds,
            name="lower_bounds",
            size=size,
            default=-np.inf,
        )
        upper = _bounds_vector(
            self.upper_bounds,
            name="upper_bounds",
            size=size,
            default=np.inf,
        )
        if np.any(np.isposinf(lower)):
            raise ValueError("lower_bounds must not contain positive infinity")
        if np.any(np.isneginf(upper)):
            raise ValueError("upper_bounds must not contain negative infinity")
        if np.any(lower > upper):
            raise ValueError("lower_bounds must not exceed upper_bounds")

        variable_units = _units(self.variable_units, name="variable_units", size=size)
        inequality_units = _units(
            self.inequality_units,
            name="inequality_units",
            size=inequalities.shape[0],
        )
        equality_units = _units(
            self.equality_units,
            name="equality_units",
            size=equalities.shape[0],
        )
        if not isinstance(self.objective_unit, str) or not self.objective_unit.strip():
            raise ValueError("objective_unit must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")

        object.__setattr__(self, "P", _read_only(hessian))
        object.__setattr__(self, "q", _read_only(linear))
        object.__setattr__(self, "G", _read_only(inequalities))
        object.__setattr__(self, "h", _read_only(inequality_rhs))
        object.__setattr__(self, "A", _read_only(equalities))
        object.__setattr__(self, "b", _read_only(equality_rhs))
        object.__setattr__(self, "lower_bounds", _read_only(lower))
        object.__setattr__(self, "upper_bounds", _read_only(upper))
        object.__setattr__(self, "variable_units", variable_units)
        object.__setattr__(self, "inequality_units", inequality_units)
        object.__setattr__(self, "equality_units", equality_units)

    @property
    def n_variables(self) -> int:
        """Number of primal variables."""

        return self.q.size


@dataclass(frozen=True)
class QPValidation:
    """Convexity, rank, scale, and immediate-feasibility diagnostics."""

    n_variables: int
    n_inequalities: int
    n_equalities: int
    hessian_rank: int
    equality_rank: int
    equality_augmented_rank: int
    symmetric_error: float
    minimum_eigenvalue: float
    hessian_condition_number: float
    positive_semidefinite: bool
    equality_system_consistent: bool
    equality_rows_independent: bool
    variable_scale: float
    objective_coefficient_scale: float
    constraint_coefficient_scale: float
    convex_qp: bool
    warnings: tuple[str, ...]


def validate_quadratic_program(problem: QuadraticProgram) -> QPValidation:
    """Validate convexity without treating solver success as a certificate."""

    if not isinstance(problem, QuadraticProgram):
        raise TypeError("problem must be a QuadraticProgram")
    eigenvalues = np.linalg.eigvalsh(problem.P)
    hessian_scale = float(np.linalg.norm(problem.P, ord=2))
    # Scale relative to P itself.  In particular, P=[[-1e-20]] remains
    # non-convex instead of being hidden by an absolute unit floor.
    psd_tolerance = 100.0 * problem.n_variables * np.finfo(float).eps * hessian_scale
    minimum_eigenvalue = float(eigenvalues[0])
    positive_semidefinite = bool(minimum_eigenvalue >= -psd_tolerance)
    hessian_rank = int(np.linalg.matrix_rank(problem.P))
    condition_number = (
        float(np.linalg.cond(problem.P)) if hessian_rank == problem.n_variables else np.inf
    )

    if problem.A.shape[0]:
        equality_row_scales = np.maximum(
            np.maximum(
                np.linalg.norm(problem.A, ord=np.inf, axis=1),
                np.abs(problem.b),
            ),
            np.finfo(float).tiny,
        )
        scaled_equalities = problem.A / equality_row_scales[:, None]
        scaled_rhs = problem.b / equality_row_scales
        equality_rank = int(np.linalg.matrix_rank(scaled_equalities))
        augmented = np.column_stack((scaled_equalities, scaled_rhs))
        augmented_rank = int(np.linalg.matrix_rank(augmented))
    else:
        equality_rank = 0
        augmented_rank = 0
    equality_consistent = equality_rank == augmented_rank
    equality_independent = equality_rank == problem.A.shape[0]

    finite_bounds = np.concatenate(
        (
            problem.lower_bounds[np.isfinite(problem.lower_bounds)],
            problem.upper_bounds[np.isfinite(problem.upper_bounds)],
        )
    )
    variable_scale = float(np.max(np.abs(finite_bounds))) if finite_bounds.size else 0.0
    objective_scale = max(
        float(np.linalg.norm(problem.P, ord=np.inf)),
        float(np.linalg.norm(problem.q, ord=np.inf)),
    )
    constraint_parts: list[FloatArray] = []
    if problem.G.size:
        constraint_parts.extend((np.abs(problem.G).ravel(), np.abs(problem.h)))
    if problem.A.size:
        constraint_parts.extend((np.abs(problem.A).ravel(), np.abs(problem.b)))
    constraint_scale = (
        float(max(np.max(part) for part in constraint_parts if part.size))
        if constraint_parts
        else 0.0
    )

    warnings: list[str] = []
    if not positive_semidefinite:
        warnings.append("P is not positive semidefinite; this is not a convex QP")
    if not equality_consistent:
        warnings.append("the equality system is algebraically inconsistent")
    if not equality_independent:
        warnings.append("A has linearly dependent rows; equality multipliers are not unique")
    if np.isinf(condition_number):
        warnings.append("P is singular; the primal minimizer may be non-unique")

    return QPValidation(
        n_variables=problem.n_variables,
        n_inequalities=problem.G.shape[0],
        n_equalities=problem.A.shape[0],
        hessian_rank=hessian_rank,
        equality_rank=equality_rank,
        equality_augmented_rank=augmented_rank,
        symmetric_error=float(np.linalg.norm(problem.P - problem.P.T, ord=np.inf)),
        minimum_eigenvalue=minimum_eigenvalue,
        hessian_condition_number=condition_number,
        positive_semidefinite=positive_semidefinite,
        equality_system_consistent=equality_consistent,
        equality_rows_independent=equality_independent,
        variable_scale=variable_scale,
        objective_coefficient_scale=objective_scale,
        constraint_coefficient_scale=constraint_scale,
        convex_qp=bool(positive_semidefinite and equality_consistent),
        warnings=tuple(warnings),
    )


def quadratic_objective(problem: QuadraticProgram, point: ArrayLike) -> float:
    """Evaluate ``1/2 x' P x + q' x`` at a finite point."""

    if not isinstance(problem, QuadraticProgram):
        raise TypeError("problem must be a QuadraticProgram")
    location = _vector(point, name="point", size=problem.n_variables)
    value = 0.5 * location @ problem.P @ location + problem.q @ location
    if not np.isfinite(value):
        raise FloatingPointError("quadratic objective produced a non-finite value")
    return float(value)


@dataclass(frozen=True)
class KKTResiduals:
    """Raw and dimensionless residuals for the four KKT families.

    Raw residuals preserve the units needed to enforce hard contracts such as
    a minimum discount factor.  The shorter field names are normalized and
    are used with the dimensionless educational gate ``tolerance``.
    """

    raw_stationarity: float
    raw_primal_inequality: float
    raw_primal_equality: float
    raw_primal_bounds: float
    raw_dual_feasibility: float
    raw_complementarity: float
    raw_duality_gap: float
    stationarity: float
    primal_inequality: float
    primal_equality: float
    primal_bounds: float
    dual_feasibility: float
    complementarity: float
    duality_gap: float
    tolerance: float
    passed: bool


def _relative_inf_residual(numerator: ArrayLike, *scales: ArrayLike) -> float:
    values = np.asarray(numerator, dtype=float)
    raw = float(np.linalg.norm(values, ord=np.inf)) if values.size else 0.0
    denominator = np.finfo(float).tiny
    for scale in scales:
        array = np.asarray(scale, dtype=float)
        if array.size:
            denominator = max(denominator, float(np.linalg.norm(array, ord=np.inf)))
    return raw / denominator


def evaluate_kkt(
    problem: QuadraticProgram,
    point: ArrayLike,
    inequality_duals: ArrayLike,
    equality_duals: ArrayLike,
    lower_bound_duals: ArrayLike,
    upper_bound_duals: ArrayLike,
    *,
    dual_objective: float | None = None,
    tolerance: float | None = None,
) -> KKTResiduals:
    """Independently evaluate primal, dual, stationarity, and complementarity.

    Residuals are normalized by the terms entering their equations, which
    makes the common tolerance dimensionless.  This is preferable to applying
    one absolute tolerance to quantities with unrelated units.
    """

    if not isinstance(problem, QuadraticProgram):
        raise TypeError("problem must be a QuadraticProgram")
    x = _vector(point, name="point", size=problem.n_variables)
    lambda_ineq = _vector(
        inequality_duals,
        name="inequality_duals",
        size=problem.G.shape[0],
    )
    nu = _vector(equality_duals, name="equality_duals", size=problem.A.shape[0])
    mu_lower = _vector(
        lower_bound_duals,
        name="lower_bound_duals",
        size=problem.n_variables,
    )
    mu_upper = _vector(
        upper_bound_duals,
        name="upper_bound_duals",
        size=problem.n_variables,
    )
    threshold = (
        float(100.0 * np.sqrt(np.finfo(float).eps))
        if tolerance is None
        else _positive_scalar(tolerance, name="tolerance")
    )

    gradient = problem.P @ x + problem.q
    inequality_term = problem.G.T @ lambda_ineq
    equality_term = problem.A.T @ nu
    stationarity_vector = gradient + inequality_term + equality_term - mu_lower + mu_upper
    raw_stationarity = float(np.linalg.norm(stationarity_vector, ord=np.inf))
    stationarity = raw_stationarity / max(
        float(np.linalg.norm(problem.P @ x, ord=np.inf)),
        float(np.linalg.norm(problem.q, ord=np.inf)),
        float(np.linalg.norm(inequality_term, ord=np.inf)),
        float(np.linalg.norm(equality_term, ord=np.inf)),
        float(np.linalg.norm(mu_lower, ord=np.inf)),
        float(np.linalg.norm(mu_upper, ord=np.inf)),
        np.finfo(float).tiny,
    )

    inequality_values = problem.G @ x - problem.h
    inequality_violation = np.maximum(inequality_values, 0.0)
    raw_primal_inequality = (
        float(np.linalg.norm(inequality_violation, ord=np.inf))
        if inequality_violation.size
        else 0.0
    )
    if inequality_violation.size:
        row_scale = np.maximum(
            np.maximum(
                np.abs(problem.h),
                np.abs(problem.G) @ np.abs(x),
            ),
            np.finfo(float).tiny,
        )
        primal_inequality = float(np.max(inequality_violation / row_scale))
    else:
        primal_inequality = 0.0
    equality_values = problem.A @ x - problem.b
    raw_primal_equality = (
        float(np.linalg.norm(equality_values, ord=np.inf)) if equality_values.size else 0.0
    )
    if equality_values.size:
        row_scale = np.maximum(
            np.maximum(
                np.abs(problem.b),
                np.abs(problem.A) @ np.abs(x),
            ),
            np.finfo(float).tiny,
        )
        primal_equality = float(np.max(np.abs(equality_values) / row_scale))
    else:
        primal_equality = 0.0

    finite_lower = np.isfinite(problem.lower_bounds)
    finite_upper = np.isfinite(problem.upper_bounds)
    lower_violation = np.maximum(problem.lower_bounds[finite_lower] - x[finite_lower], 0.0)
    upper_violation = np.maximum(x[finite_upper] - problem.upper_bounds[finite_upper], 0.0)
    bound_violation = np.concatenate((lower_violation, upper_violation))
    raw_primal_bounds = (
        float(np.linalg.norm(bound_violation, ord=np.inf)) if bound_violation.size else 0.0
    )
    if bound_violation.size:
        # lower and upper entries align with their corresponding finite bounds.
        lower_denominators = np.maximum(
            np.maximum(np.abs(x[finite_lower]), np.abs(problem.lower_bounds[finite_lower])),
            np.finfo(float).tiny,
        )
        upper_denominators = np.maximum(
            np.maximum(np.abs(x[finite_upper]), np.abs(problem.upper_bounds[finite_upper])),
            np.finfo(float).tiny,
        )
        bound_denominators = np.concatenate((lower_denominators, upper_denominators))
        primal_bounds = float(np.max(bound_violation / bound_denominators))
    else:
        primal_bounds = 0.0

    signed_duals = np.concatenate((lambda_ineq, mu_lower, mu_upper))
    negative_duals = np.maximum(-signed_duals, 0.0)
    raw_dual_feasibility = (
        float(np.linalg.norm(negative_duals, ord=np.inf)) if negative_duals.size else 0.0
    )
    dual_feasibility = float(
        raw_dual_feasibility
        / max(
            float(np.linalg.norm(signed_duals, ord=np.inf)) if signed_duals.size else 0.0,
            np.finfo(float).tiny,
        )
    )

    inequality_slack = problem.h - problem.G @ x
    lower_slack = np.zeros(problem.n_variables, dtype=float)
    upper_slack = np.zeros(problem.n_variables, dtype=float)
    lower_slack[finite_lower] = x[finite_lower] - problem.lower_bounds[finite_lower]
    upper_slack[finite_upper] = problem.upper_bounds[finite_upper] - x[finite_upper]
    products = np.concatenate(
        (
            lambda_ineq * inequality_slack,
            mu_lower[finite_lower] * lower_slack[finite_lower],
            mu_upper[finite_upper] * upper_slack[finite_upper],
        )
    )
    raw_complementarity = float(np.linalg.norm(products, ord=np.inf)) if products.size else 0.0

    primal_objective = quadratic_objective(problem, x)
    objective_scale = max(
        0.5 * abs(float(x @ problem.P @ x)),
        abs(float(problem.q @ x)),
        abs(float(problem.h @ lambda_ineq)),
        abs(float(problem.b @ nu)),
        abs(float(problem.lower_bounds[finite_lower] @ mu_lower[finite_lower])),
        abs(float(problem.upper_bounds[finite_upper] @ mu_upper[finite_upper])),
        np.finfo(float).tiny,
    )
    if dual_objective is None or not np.isfinite(dual_objective):
        raw_duality_gap = np.inf
        duality_gap = np.inf
        complementarity = raw_complementarity / objective_scale
    else:
        raw_duality_gap = abs(primal_objective - float(dual_objective))
        objective_denominator = max(
            objective_scale,
            abs(primal_objective),
            abs(float(dual_objective)),
            np.finfo(float).tiny,
        )
        duality_gap = raw_duality_gap / objective_denominator
        complementarity = raw_complementarity / objective_denominator
    values = (
        stationarity,
        primal_inequality,
        primal_equality,
        primal_bounds,
        dual_feasibility,
        complementarity,
        duality_gap,
    )
    return KKTResiduals(
        raw_stationarity=raw_stationarity,
        raw_primal_inequality=raw_primal_inequality,
        raw_primal_equality=raw_primal_equality,
        raw_primal_bounds=raw_primal_bounds,
        raw_dual_feasibility=raw_dual_feasibility,
        raw_complementarity=raw_complementarity,
        raw_duality_gap=raw_duality_gap,
        stationarity=stationarity,
        primal_inequality=primal_inequality,
        primal_equality=primal_equality,
        primal_bounds=primal_bounds,
        dual_feasibility=dual_feasibility,
        complementarity=complementarity,
        duality_gap=duality_gap,
        tolerance=threshold,
        passed=bool(all(value <= threshold for value in values)),
    )


@dataclass(frozen=True)
class QPSolverDiagnostics:
    """Solver status kept separate from independent convexity and KKT checks."""

    optimizer_success: bool
    optimizer_status: int
    optimizer_message: str
    iterations: int
    function_evaluations: int
    active_set_polished: bool
    validation: QPValidation
    kkt: KKTResiduals
    accepted: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class QPSolution:
    """Primal and reconstructed-dual solution of a quadratic program."""

    x: FloatArray
    primal_objective: float
    dual_objective: float
    inequality_duals: FloatArray
    equality_duals: FloatArray
    lower_bound_duals: FloatArray
    upper_bound_duals: FloatArray
    diagnostics: QPSolverDiagnostics
    method: QPSolverMethod

    @property
    def success(self) -> bool:
        """Whether both the optimizer status and independent KKT audit pass."""

        return self.diagnostics.accepted

    @property
    def status(self) -> int:
        """SciPy optimizer status code."""

        return self.diagnostics.optimizer_status

    @property
    def message(self) -> str:
        """SciPy optimizer message."""

        return self.diagnostics.optimizer_message

    @property
    def iterations(self) -> int:
        """Reported optimizer iterations."""

        return self.diagnostics.iterations


def _initial_point(problem: QuadraticProgram, initial: ArrayLike | None) -> FloatArray:
    if initial is not None:
        return _vector(initial, name="initial", size=problem.n_variables)
    point = np.zeros(problem.n_variables, dtype=float)
    if problem.A.shape[0] and validate_quadratic_program(problem).equality_system_consistent:
        row_scales = np.maximum(
            np.maximum(np.linalg.norm(problem.A, ord=np.inf, axis=1), np.abs(problem.b)),
            np.finfo(float).tiny,
        )
        point, *_ = np.linalg.lstsq(
            problem.A / row_scales[:, None],
            problem.b / row_scales,
            rcond=None,
        )
    point = np.maximum(point, problem.lower_bounds)
    point = np.minimum(point, problem.upper_bounds)
    return np.asarray(point, dtype=float)


def _reconstruct_duals(
    problem: QuadraticProgram,
    point: FloatArray,
    *,
    active_tolerance: float,
    inequality_activity_hint: FloatArray | None = None,
    bound_activity_hint: FloatArray | None = None,
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    gradient = problem.P @ point + problem.q
    inequality_slack = problem.h - problem.G @ point
    inequality_scale = np.maximum(
        np.maximum(
            np.abs(problem.h),
            np.abs(problem.G) @ np.abs(point),
        ),
        np.finfo(float).tiny,
    )
    active_inequality = (inequality_slack <= active_tolerance * inequality_scale) & (
        np.linalg.norm(problem.G, ord=np.inf, axis=1) > 0.0
    )
    if inequality_activity_hint is not None:
        active_inequality |= inequality_activity_hint > active_tolerance

    finite_lower = np.isfinite(problem.lower_bounds)
    finite_upper = np.isfinite(problem.upper_bounds)
    stationary_reference, *_ = np.linalg.lstsq(problem.P, -problem.q, rcond=None)
    bound_scale = np.maximum(
        np.maximum(np.abs(point), np.abs(stationary_reference)),
        np.finfo(float).tiny,
    )
    bound_scale[finite_lower] = np.maximum(
        bound_scale[finite_lower], np.abs(problem.lower_bounds[finite_lower])
    )
    bound_scale[finite_upper] = np.maximum(
        bound_scale[finite_upper], np.abs(problem.upper_bounds[finite_upper])
    )
    active_lower = finite_lower & (point - problem.lower_bounds <= active_tolerance * bound_scale)
    active_upper = finite_upper & (problem.upper_bounds - point <= active_tolerance * bound_scale)
    if bound_activity_hint is not None:
        active_lower |= finite_lower & (bound_activity_hint < -active_tolerance)
        active_upper |= finite_upper & (bound_activity_hint > active_tolerance)

    columns: list[FloatArray] = []
    lower_dual_bounds: list[float] = []
    upper_dual_bounds: list[float] = []
    inequality_indices = np.flatnonzero(active_inequality)
    for index in inequality_indices:
        columns.append(problem.G[index])
        lower_dual_bounds.append(0.0)
        upper_dual_bounds.append(np.inf)
    equality_indices = np.flatnonzero(np.linalg.norm(problem.A, ord=np.inf, axis=1) > 0.0)
    for index in equality_indices:
        columns.append(problem.A[index])
        lower_dual_bounds.append(-np.inf)
        upper_dual_bounds.append(np.inf)
    lower_indices = np.flatnonzero(active_lower)
    for index in lower_indices:
        column = np.zeros(problem.n_variables, dtype=float)
        column[index] = -1.0
        columns.append(column)
        lower_dual_bounds.append(0.0)
        upper_dual_bounds.append(np.inf)
    upper_indices = np.flatnonzero(active_upper)
    for index in upper_indices:
        column = np.zeros(problem.n_variables, dtype=float)
        column[index] = 1.0
        columns.append(column)
        lower_dual_bounds.append(0.0)
        upper_dual_bounds.append(np.inf)

    if columns:
        multiplier_matrix = np.column_stack(columns)
        column_scales = np.linalg.norm(multiplier_matrix, ord=np.inf, axis=0)
        if np.any(column_scales == 0.0):
            raise ValueError("an active constraint has an all-zero coefficient row")
        gradient_scale = max(
            float(np.linalg.norm(gradient, ord=np.inf)),
            np.finfo(float).tiny,
        )
        result = lsq_linear(
            multiplier_matrix / column_scales,
            -gradient / gradient_scale,
            bounds=(np.asarray(lower_dual_bounds), np.asarray(upper_dual_bounds)),
            tol=1e-12,
            lsmr_tol="auto",
            max_iter=2_000,
        )
        multipliers = np.asarray(result.x, dtype=float) * gradient_scale / column_scales
    else:
        multipliers = np.empty(0, dtype=float)

    cursor = 0
    inequality_duals = np.zeros(problem.G.shape[0], dtype=float)
    inequality_duals[inequality_indices] = multipliers[cursor : cursor + inequality_indices.size]
    cursor += inequality_indices.size
    equality_duals = np.zeros(problem.A.shape[0], dtype=float)
    equality_duals[equality_indices] = multipliers[cursor : cursor + equality_indices.size]
    cursor += equality_indices.size
    lower_duals = np.zeros(problem.n_variables, dtype=float)
    lower_duals[lower_indices] = multipliers[cursor : cursor + lower_indices.size]
    cursor += lower_indices.size
    upper_duals = np.zeros(problem.n_variables, dtype=float)
    upper_duals[upper_indices] = multipliers[cursor : cursor + upper_indices.size]
    return inequality_duals, equality_duals, lower_duals, upper_duals


def _dual_objective(
    problem: QuadraticProgram,
    inequality_duals: FloatArray,
    equality_duals: FloatArray,
    lower_duals: FloatArray,
    upper_duals: FloatArray,
    *,
    tolerance: float,
) -> float:
    linear_term = (
        problem.q
        + problem.G.T @ inequality_duals
        + problem.A.T @ equality_duals
        - lower_duals
        + upper_duals
    )
    minimizer, *_ = np.linalg.lstsq(problem.P, -linear_term, rcond=None)
    range_residual = problem.P @ minimizer + linear_term
    relative_residual = _relative_inf_residual(range_residual, problem.P @ minimizer, linear_term)
    if relative_residual > max(10.0 * tolerance, 1e-7):
        return float("nan")
    finite_lower = np.isfinite(problem.lower_bounds)
    finite_upper = np.isfinite(problem.upper_bounds)
    constant = (
        -problem.h @ inequality_duals
        - problem.b @ equality_duals
        + problem.lower_bounds[finite_lower] @ lower_duals[finite_lower]
        - problem.upper_bounds[finite_upper] @ upper_duals[finite_upper]
    )
    return float(-0.5 * minimizer @ problem.P @ minimizer + constant)


def _polish_trust_constr_active_point(
    problem: QuadraticProgram,
    point: FloatArray,
    *,
    inequality_activity_hint: FloatArray | None,
    bound_activity_hint: FloatArray | None,
    tolerance: float,
) -> FloatArray:
    """Snap trust-constr's barrier point to its strongly active linear faces."""

    rows: list[FloatArray] = []
    right_hand_sides: list[float] = []
    if inequality_activity_hint is not None:
        for index in np.flatnonzero(inequality_activity_hint > tolerance):
            rows.append(problem.G[index])
            right_hand_sides.append(float(problem.h[index]))
    for index, row in enumerate(problem.A):
        if np.any(row != 0.0):
            rows.append(row)
            right_hand_sides.append(float(problem.b[index]))
    if bound_activity_hint is not None:
        active_lower_indices = np.flatnonzero(
            np.isfinite(problem.lower_bounds) & (bound_activity_hint < -tolerance)
        )
        active_upper_indices = np.flatnonzero(
            np.isfinite(problem.upper_bounds) & (bound_activity_hint > tolerance)
        )
        for index in active_lower_indices:
            row = np.zeros(problem.n_variables, dtype=float)
            row[index] = 1.0
            rows.append(row)
            right_hand_sides.append(float(problem.lower_bounds[index]))
        for index in active_upper_indices:
            row = np.zeros(problem.n_variables, dtype=float)
            row[index] = 1.0
            rows.append(row)
            right_hand_sides.append(float(problem.upper_bounds[index]))
    else:
        active_lower_indices = np.empty(0, dtype=int)
        active_upper_indices = np.empty(0, dtype=int)
    if not rows:
        return point

    active_matrix = np.vstack(rows)
    active_rhs = np.asarray(right_hand_sides, dtype=float)
    row_scales = np.maximum(
        np.maximum(np.linalg.norm(active_matrix, ord=np.inf, axis=1), np.abs(active_rhs)),
        np.finfo(float).tiny,
    )
    active_matrix = active_matrix / row_scales[:, None]
    active_rhs = active_rhs / row_scales
    objective_scale = max(
        float(np.linalg.norm(problem.P, ord=np.inf)),
        float(np.linalg.norm(problem.q, ord=np.inf)),
        np.finfo(float).tiny,
    )
    scaled_hessian = problem.P / objective_scale
    scaled_linear = problem.q / objective_scale
    saddle = np.block(
        [
            [scaled_hessian, active_matrix.T],
            [active_matrix, np.zeros((active_matrix.shape[0], active_matrix.shape[0]))],
        ]
    )
    rhs = np.concatenate((-scaled_linear, active_rhs))
    candidate = np.linalg.lstsq(saddle, rhs, rcond=None)[0][: problem.n_variables]
    if not np.all(np.isfinite(candidate)):
        return point
    candidate[active_lower_indices] = problem.lower_bounds[active_lower_indices]
    candidate[active_upper_indices] = problem.upper_bounds[active_upper_indices]

    inequality_scale = np.maximum(
        np.maximum(np.abs(problem.h), np.abs(problem.G) @ np.abs(candidate)),
        np.finfo(float).tiny,
    )
    equality_scale = np.maximum(
        np.maximum(np.abs(problem.b), np.abs(problem.A) @ np.abs(candidate)),
        np.finfo(float).tiny,
    )
    feasible = bool(
        np.all(problem.G @ candidate - problem.h <= tolerance * inequality_scale)
        and np.all(np.abs(problem.A @ candidate - problem.b) <= tolerance * equality_scale)
        and np.all(candidate >= problem.lower_bounds)
        and np.all(candidate <= problem.upper_bounds)
    )
    if not feasible:
        return point
    old_objective = quadratic_objective(problem, point)
    candidate_objective = quadratic_objective(problem, candidate)
    comparison_scale = max(
        abs(old_objective),
        abs(candidate_objective),
        0.5 * abs(float(point @ problem.P @ point)),
        abs(float(problem.q @ point)),
        np.finfo(float).tiny,
    )
    if candidate_objective > old_objective + tolerance * comparison_scale:
        return point
    return np.asarray(candidate, dtype=float)


def solve_quadratic_program(
    problem: QuadraticProgram,
    *,
    initial: ArrayLike | None = None,
    method: QPSolverMethod = "SLSQP",
    tolerance: float | None = None,
    max_iterations: int = 2_000,
) -> QPSolution:
    """Solve a convex QP with SciPy and independently reconstruct its dual.

    ``optimizer_success`` records SciPy's termination status.  ``success`` is
    stricter: convexity validation, optimizer status, and every normalized KKT
    residual must pass.  Neither status is presented as a DCP certificate.
    """

    if not isinstance(problem, QuadraticProgram):
        raise TypeError("problem must be a QuadraticProgram")
    if method not in {"SLSQP", "trust-constr"}:
        raise ValueError(f"unknown QP solver method: {method!r}")
    threshold = (
        float(100.0 * np.sqrt(np.finfo(float).eps))
        if tolerance is None
        else _positive_scalar(tolerance, name="tolerance")
    )
    maximum_iterations = _positive_integer(max_iterations, name="max_iterations")
    validation = validate_quadratic_program(problem)
    if not validation.positive_semidefinite:
        raise ValueError("solve_quadratic_program requires a positive-semidefinite P")
    point = _initial_point(problem, initial)

    # SciPy stopping rules use absolute objective and constraint scales.  Solve
    # an equivalent normalized formulation, then reconstruct duals and audit
    # KKT conditions in the caller's original units.
    objective_scale = max(
        float(np.linalg.norm(problem.P, ord=np.inf)),
        float(np.linalg.norm(problem.q, ord=np.inf)),
    )
    if objective_scale == 0.0:
        objective_scale = 1.0
    scaled_P = problem.P / objective_scale
    scaled_q = problem.q / objective_scale
    if problem.G.shape[0]:
        inequality_row_scales = np.maximum(
            np.maximum(np.linalg.norm(problem.G, ord=np.inf, axis=1), np.abs(problem.h)),
            np.finfo(float).tiny,
        )
        scaled_G = problem.G / inequality_row_scales[:, None]
        scaled_h = problem.h / inequality_row_scales
    else:
        scaled_G = problem.G
        scaled_h = problem.h
    if problem.A.shape[0]:
        equality_row_scales = np.maximum(
            np.maximum(np.linalg.norm(problem.A, ord=np.inf, axis=1), np.abs(problem.b)),
            np.finfo(float).tiny,
        )
        scaled_A = problem.A / equality_row_scales[:, None]
        scaled_b = problem.b / equality_row_scales
    else:
        scaled_A = problem.A
        scaled_b = problem.b
    independent_equality_rows = _independent_row_indices(scaled_A)
    solver_A = scaled_A[independent_equality_rows]
    solver_b = scaled_b[independent_equality_rows]

    def objective(x: FloatArray) -> float:
        return float(0.5 * x @ scaled_P @ x + scaled_q @ x)

    def gradient(x: FloatArray) -> FloatArray:
        return scaled_P @ x + scaled_q

    bounds = Bounds(problem.lower_bounds, problem.upper_bounds)
    if method == "SLSQP":
        constraints: list[dict[str, object]] = []
        if problem.G.shape[0]:
            constraints.append(
                {
                    "type": "ineq",
                    "fun": lambda x: scaled_h - scaled_G @ x,
                    "jac": lambda x: -scaled_G,
                }
            )
        if solver_A.shape[0]:
            constraints.append(
                {
                    "type": "eq",
                    "fun": lambda x: solver_A @ x - solver_b,
                    "jac": lambda x: solver_A,
                }
            )
        optimize_result = minimize(
            objective,
            point,
            jac=gradient,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": min(1e-10, threshold / 10.0), "maxiter": maximum_iterations},
        )
    else:
        linear_constraints: list[LinearConstraint] = []
        if problem.G.shape[0]:
            linear_constraints.append(LinearConstraint(scaled_G, -np.inf, scaled_h))
        if solver_A.shape[0]:
            linear_constraints.append(LinearConstraint(solver_A, solver_b, solver_b))
        optimize_result = minimize(
            objective,
            point,
            jac=gradient,
            hess=lambda x: scaled_P,
            method="trust-constr",
            bounds=bounds,
            constraints=linear_constraints,
            options={
                "gtol": min(1e-12, threshold / 1_000.0),
                "xtol": min(1e-12, threshold / 1_000.0),
                "barrier_tol": min(1e-12, threshold / 1_000.0),
                # A small initial barrier is important when the optimum is on
                # a bound: trust-constr may otherwise stop at a visibly
                # interior point whose complementarity fails our independent
                # gate even though its own optimality test passed.
                "initial_barrier_parameter": min(1e-12, threshold / 1_000_000.0),
                "initial_barrier_tolerance": min(1e-12, threshold / 1_000_000.0),
                "maxiter": maximum_iterations,
                "verbose": 0,
            },
        )

    solution = np.asarray(optimize_result.x, dtype=float)
    raw_optimizer_solution = solution.copy()
    active_tolerance = max(10.0 * threshold, 1e-7)
    inequality_activity_hint = None
    bound_activity_hint = None
    if method == "trust-constr":
        scipy_multipliers = getattr(optimize_result, "v", None)
        if isinstance(scipy_multipliers, (list, tuple)) and scipy_multipliers:
            cursor = 0
            if problem.G.shape[0]:
                candidate = np.asarray(scipy_multipliers[cursor], dtype=float)
                if candidate.shape == (problem.G.shape[0],):
                    inequality_activity_hint = candidate
                cursor += 1
            if solver_A.shape[0]:
                cursor += 1
            if cursor < len(scipy_multipliers):
                candidate = np.asarray(scipy_multipliers[cursor], dtype=float)
                if candidate.shape == (problem.n_variables,):
                    bound_activity_hint = candidate
        solution = _polish_trust_constr_active_point(
            problem,
            solution,
            inequality_activity_hint=inequality_activity_hint,
            bound_activity_hint=bound_activity_hint,
            tolerance=active_tolerance,
        )
    active_set_polished = bool(not np.array_equal(solution, raw_optimizer_solution))
    inequality_duals, equality_duals, lower_duals, upper_duals = _reconstruct_duals(
        problem,
        solution,
        active_tolerance=active_tolerance,
        inequality_activity_hint=inequality_activity_hint,
        bound_activity_hint=bound_activity_hint,
    )
    dual_objective = _dual_objective(
        problem,
        inequality_duals,
        equality_duals,
        lower_duals,
        upper_duals,
        tolerance=threshold,
    )
    kkt = evaluate_kkt(
        problem,
        solution,
        inequality_duals,
        equality_duals,
        lower_duals,
        upper_duals,
        dual_objective=dual_objective,
        tolerance=threshold,
    )
    warnings = list(validation.warnings)
    if bool(optimize_result.success) and not kkt.passed:
        warnings.append("the optimizer reported success but the independent KKT audit failed")
    if not bool(optimize_result.success) and kkt.passed:
        warnings.append("KKT residuals pass despite a non-success optimizer status")
    diagnostics = QPSolverDiagnostics(
        optimizer_success=bool(optimize_result.success),
        optimizer_status=int(optimize_result.status),
        optimizer_message=str(optimize_result.message),
        iterations=int(getattr(optimize_result, "nit", 0)),
        function_evaluations=int(getattr(optimize_result, "nfev", 0)),
        active_set_polished=active_set_polished,
        validation=validation,
        kkt=kkt,
        accepted=bool(validation.convex_qp and optimize_result.success and kkt.passed),
        warnings=tuple(warnings),
    )
    return QPSolution(
        x=_read_only(solution),
        primal_objective=quadratic_objective(problem, solution),
        dual_objective=dual_objective,
        inequality_duals=_read_only(inequality_duals),
        equality_duals=_read_only(equality_duals),
        lower_bound_duals=_read_only(lower_duals),
        upper_bound_duals=_read_only(upper_duals),
        diagnostics=diagnostics,
        method=method,
    )


@dataclass(frozen=True)
class QPSensitivityResult:
    """Dual shadow price compared with a finite-difference RHS derivative."""

    inequality_index: int
    perturbation: float
    relative_perturbation: float
    rhs_scale: float
    predicted_derivative: float
    finite_difference_derivative: float
    absolute_error: float
    relative_error: float
    base_objective: float
    lower_objective: float
    upper_objective: float
    sign_convention: str


def check_inequality_sensitivity(
    problem: QuadraticProgram,
    solution: QPSolution,
    inequality_index: int,
    *,
    perturbation: float = 1e-5,
    method: QPSolverMethod | None = None,
    tolerance: float | None = None,
) -> QPSensitivityResult:
    """Compare ``dv/dh_i = -lambda_i`` with a centered finite difference.

    ``perturbation`` is a dimensionless fraction of the selected constraint
    row's natural RHS scale.  The realized perturbation is enlarged when
    needed to exceed the floating-point spacing of ``h_i``.
    """

    if not isinstance(problem, QuadraticProgram):
        raise TypeError("problem must be a QuadraticProgram")
    if not isinstance(solution, QPSolution):
        raise TypeError("solution must be a QPSolution")
    if isinstance(inequality_index, bool) or not isinstance(inequality_index, (int, np.integer)):
        raise TypeError("inequality_index must be an integer")
    index = int(inequality_index)
    if index < 0 or index >= problem.G.shape[0]:
        raise IndexError("inequality_index is out of range")
    relative_delta = _positive_scalar(perturbation, name="perturbation")
    selected_method = solution.method if method is None else method
    stationary_reference, *_ = np.linalg.lstsq(problem.P, -problem.q, rcond=None)
    variable_reference = np.maximum(np.abs(solution.x), np.abs(stationary_reference))
    rhs_scale = max(
        abs(float(problem.h[index])),
        float(np.abs(problem.G[index]) @ variable_reference),
        np.finfo(float).tiny,
    )
    ulp = abs(float(np.spacing(problem.h[index])))
    delta = max(relative_delta * rhs_scale, 32.0 * ulp)
    if not np.isfinite(delta) or delta <= 0.0:
        raise FloatingPointError("could not construct a finite RHS perturbation")
    lower_rhs = np.asarray(problem.h, dtype=float).copy()
    upper_rhs = np.asarray(problem.h, dtype=float).copy()
    lower_rhs[index] -= delta
    upper_rhs[index] += delta
    if lower_rhs[index] == problem.h[index] or upper_rhs[index] == problem.h[index]:
        raise FloatingPointError("RHS perturbation is smaller than floating-point spacing")
    lower_problem = replace(problem, h=lower_rhs)
    upper_problem = replace(problem, h=upper_rhs)
    lower_solution = solve_quadratic_program(
        lower_problem,
        initial=solution.x,
        method=selected_method,
        tolerance=tolerance,
    )
    upper_solution = solve_quadratic_program(
        upper_problem,
        initial=solution.x,
        method=selected_method,
        tolerance=tolerance,
    )
    if not lower_solution.success or not upper_solution.success:
        raise RuntimeError("perturbed QP did not pass its optimizer and KKT checks")
    finite_difference = (upper_solution.primal_objective - lower_solution.primal_objective) / (
        2.0 * delta
    )
    predicted = -float(solution.inequality_duals[index])
    absolute_error = abs(finite_difference - predicted)
    relative_error = absolute_error / max(
        abs(finite_difference), abs(predicted), np.finfo(float).tiny
    )
    return QPSensitivityResult(
        inequality_index=index,
        perturbation=delta,
        relative_perturbation=relative_delta,
        rhs_scale=rhs_scale,
        predicted_derivative=predicted,
        finite_difference_derivative=float(finite_difference),
        absolute_error=float(absolute_error),
        relative_error=float(relative_error),
        base_objective=solution.primal_objective,
        lower_objective=lower_solution.primal_objective,
        upper_objective=upper_solution.primal_objective,
        sign_convention="dv/dh_i = -lambda_i for Gx <= h and lambda_i >= 0",
    )
