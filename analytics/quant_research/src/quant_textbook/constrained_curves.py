r"""Convex discount-factor fitting for the B4 constrained-curve project.

The primal variables are node discount factors ``D``.  Given a bond-by-node
cash-flow matrix ``C``, dirty prices ``p``, precision-style weights ``w``, and
the second-difference matrix ``L``, the model minimizes

.. math::

   \sum_i w_i (C_i D-p_i)^2 + \alpha\lVert LD\rVert_2^2

subject to ``D >= minimum_discount``.  Monotone non-increasing discount
factors are optional.  That option explicitly assumes non-negative forward
rates and an anchor ``D(0)=1``; it is not a universal no-arbitrage condition
when rates can be negative.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .bonds import CouponBondUniverse
from .convex import (
    QPSolution,
    QPSolverMethod,
    QuadraticProgram,
    solve_quadratic_program,
)

FloatArray = NDArray[np.float64]


def _matrix(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _vector(values: ArrayLike, *, name: str, size: int | None = None) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if size is not None and array.size != size:
        raise ValueError(f"{name} must contain exactly {size} entries")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array.copy()


def _positive_scalar(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and strictly positive")
    return result


def _nonnegative_scalar(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _unit(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _read_only(values: ArrayLike) -> FloatArray:
    result = np.asarray(values, dtype=float).copy()
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class BondCashflowMatrix:
    """Deterministic matrix view of a :class:`CouponBondUniverse`."""

    node_times: FloatArray
    cashflow_matrix: FloatArray
    dirty_prices: FloatArray
    bond_ids: tuple[str, ...]
    quote_widths: FloatArray | None
    node_time_unit: str = "years from valuation"
    cashflow_unit: str = "currency units"
    price_unit: str = "currency units"

    def __post_init__(self) -> None:
        matrix = _matrix(self.cashflow_matrix, name="cashflow_matrix")
        nodes = _vector(self.node_times, name="node_times", size=matrix.shape[1])
        prices = _vector(self.dirty_prices, name="dirty_prices", size=matrix.shape[0])
        if np.any(nodes <= 0.0) or np.any(np.diff(nodes) <= 0.0):
            raise ValueError("node_times must be strictly positive and strictly increasing")
        if np.any(matrix < 0.0) or np.any(np.sum(matrix, axis=1) <= 0.0):
            raise ValueError(
                "each bond must have finite non-negative cash flows with a positive sum"
            )
        if np.any(np.sum(matrix, axis=0) <= 0.0):
            raise ValueError("each node must contain at least one positive cash flow")
        if np.any(prices <= 0.0):
            raise ValueError("dirty_prices must be strictly positive")
        identifiers = tuple(self.bond_ids)
        if len(identifiers) != matrix.shape[0]:
            raise ValueError("bond_ids must contain one identifier per bond")
        if any(not isinstance(value, str) or not value for value in identifiers):
            raise ValueError("bond_ids must be non-empty strings")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("bond_ids must be unique")
        widths = None
        if self.quote_widths is not None:
            widths = _vector(
                self.quote_widths,
                name="quote_widths",
                size=matrix.shape[0],
            )
            if np.any(widths <= 0.0):
                raise ValueError("quote_widths must be strictly positive")
        object.__setattr__(self, "node_times", _read_only(nodes))
        object.__setattr__(self, "cashflow_matrix", _read_only(matrix))
        object.__setattr__(self, "dirty_prices", _read_only(prices))
        object.__setattr__(self, "bond_ids", identifiers)
        object.__setattr__(self, "quote_widths", None if widths is None else _read_only(widths))
        object.__setattr__(
            self, "node_time_unit", _unit(self.node_time_unit, name="node_time_unit")
        )
        object.__setattr__(self, "cashflow_unit", _unit(self.cashflow_unit, name="cashflow_unit"))
        object.__setattr__(self, "price_unit", _unit(self.price_unit, name="price_unit"))

    @property
    def cashflows(self) -> FloatArray:
        """Alias for the bond-by-node cash-flow matrix."""

        return self.cashflow_matrix


def bond_cashflow_matrix(
    universe: CouponBondUniverse,
    *,
    quote_width_column: str | None = None,
    node_time_unit: str = "years from valuation",
    cashflow_unit: str = "currency units",
    price_unit: str = "currency units",
) -> BondCashflowMatrix:
    """Build a sorted node grid and cash-flow matrix without future refitting.

    Bond rows preserve ``universe.bonds`` order.  Payment nodes are the sorted
    unique times from the complete universe.  This same full node grid is then
    retained by leave-one-bond-out validation; only the held-out price and its
    cash-flow row are removed from fitting.
    """

    if not isinstance(universe, CouponBondUniverse):
        raise TypeError("universe must be a CouponBondUniverse")
    bonds = universe.bonds
    cashflows = universe.cashflows
    required_bond_columns = {"bond_id", "dirty_price"}
    required_cashflow_columns = {"bond_id", "payment_time", "cashflow"}
    missing_bonds = required_bond_columns.difference(bonds.columns)
    missing_cashflows = required_cashflow_columns.difference(cashflows.columns)
    if missing_bonds:
        raise ValueError(f"bonds are missing required columns: {sorted(missing_bonds)}")
    if missing_cashflows:
        raise ValueError(f"cashflows are missing required columns: {sorted(missing_cashflows)}")
    if bonds.empty or cashflows.empty:
        raise ValueError("universe bonds and cashflows must not be empty")
    if bonds["bond_id"].isna().any() or cashflows["bond_id"].isna().any():
        raise ValueError("bond_id must not contain missing values")
    if bonds["bond_id"].duplicated().any():
        raise ValueError("bond_id must be unique in universe.bonds")

    raw_bond_ids = tuple(bonds["bond_id"].tolist())
    try:
        row_lookup = {identifier: index for index, identifier in enumerate(raw_bond_ids)}
    except TypeError as exc:
        raise ValueError("bond_id values must be hashable") from exc
    if len(row_lookup) != len(raw_bond_ids):
        raise ValueError("bond_id values collide or are duplicated")
    string_ids = tuple(str(identifier) for identifier in raw_bond_ids)
    if len(set(string_ids)) != len(string_ids):
        raise ValueError("bond_id values must remain unique when rendered as strings")

    payment_times = _vector(cashflows["payment_time"], name="payment_time")
    cashflow_amounts = _vector(cashflows["cashflow"], name="cashflow")
    if np.any(payment_times <= 0.0):
        raise ValueError("payment_time must be strictly positive")
    if np.any(cashflow_amounts < 0.0):
        raise ValueError("cashflow must be non-negative")
    node_times = np.unique(payment_times)
    node_lookup = {float(value): index for index, value in enumerate(node_times)}
    matrix = np.zeros((len(raw_bond_ids), node_times.size), dtype=float)
    for identifier, payment_time, amount in zip(
        cashflows["bond_id"].tolist(),
        payment_times,
        cashflow_amounts,
        strict=True,
    ):
        if identifier not in row_lookup:
            raise ValueError("cashflows contain a bond_id absent from universe.bonds")
        matrix[row_lookup[identifier], node_lookup[float(payment_time)]] += float(amount)
    if np.any(np.sum(matrix, axis=1) <= 0.0):
        raise ValueError("every bond must have at least one positive contractual cash flow")

    widths = None
    if quote_width_column is not None:
        if not isinstance(quote_width_column, str) or not quote_width_column:
            raise ValueError("quote_width_column must be a non-empty string or None")
        if quote_width_column not in bonds.columns:
            raise ValueError(f"bonds do not contain quote-width column {quote_width_column!r}")
        widths = _vector(
            bonds[quote_width_column],
            name=quote_width_column,
            size=len(raw_bond_ids),
        )
    return BondCashflowMatrix(
        node_times=node_times,
        cashflow_matrix=matrix,
        dirty_prices=np.asarray(bonds["dirty_price"], dtype=float),
        bond_ids=string_ids,
        quote_widths=widths,
        node_time_unit=node_time_unit,
        cashflow_unit=cashflow_unit,
        price_unit=price_unit,
    )


def second_difference_matrix(nodes: int | ArrayLike) -> FloatArray:
    """Return a slope-difference operator for node indices or explicit times.

    An integer retains the equal-spacing ``[1, -2, 1]`` teaching operator.
    Explicit strictly increasing times use adjacent divided differences, so a
    discount curve that is linear in time lies exactly in the null space even
    on an irregular grid.
    """

    if isinstance(nodes, bool):
        raise TypeError("nodes must be an integer count or a vector of times")
    if isinstance(nodes, (int, np.integer)):
        n_nodes = int(nodes)
        node_times = np.arange(n_nodes, dtype=float)
    else:
        node_times = _vector(nodes, name="node_times")
        n_nodes = node_times.size
        if np.any(node_times <= 0.0) or np.any(np.diff(node_times) <= 0.0):
            raise ValueError("node_times must be strictly positive and strictly increasing")
    if n_nodes < 3:
        raise ValueError("second differences require at least three nodes")
    intervals = np.diff(node_times)
    result = np.zeros((n_nodes - 2, n_nodes), dtype=float)
    rows = np.arange(result.shape[0])
    result[rows, rows] = 1.0 / intervals[:-1]
    result[rows, rows + 1] = -(1.0 / intervals[:-1] + 1.0 / intervals[1:])
    result[rows, rows + 2] = 1.0 / intervals[1:]
    return result


def predict_prices_from_discounts(
    cashflow_matrix: ArrayLike,
    discount_factors: ArrayLike,
) -> FloatArray:
    """Price each bond by the matrix product ``C @ D``."""

    matrix = _matrix(cashflow_matrix, name="cashflow_matrix")
    discounts = _vector(
        discount_factors,
        name="discount_factors",
        size=matrix.shape[1],
    )
    if np.any(matrix < 0.0):
        raise ValueError("cashflow_matrix must be non-negative")
    if np.any(discounts <= 0.0):
        raise ValueError("discount_factors must be strictly positive")
    return np.asarray(matrix @ discounts, dtype=float)


def _curve_inputs(
    cashflow_matrix: ArrayLike,
    prices: ArrayLike,
    node_times: ArrayLike,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    matrix = _matrix(cashflow_matrix, name="cashflow_matrix")
    observed = _vector(prices, name="prices", size=matrix.shape[0])
    nodes = _vector(node_times, name="node_times", size=matrix.shape[1])
    if matrix.shape[1] < 3:
        raise ValueError("constrained curve fitting requires at least three nodes")
    if np.any(matrix < 0.0) or np.any(np.sum(matrix, axis=1) <= 0.0):
        raise ValueError("each observation must have non-negative cash flows with a positive sum")
    if np.any(np.sum(matrix, axis=0) <= 0.0):
        raise ValueError("each node must appear in at least one cash-flow row")
    if np.any(observed <= 0.0):
        raise ValueError("prices must be strictly positive")
    if np.any(nodes <= 0.0) or np.any(np.diff(nodes) <= 0.0):
        raise ValueError("node_times must be strictly positive and strictly increasing")
    return matrix, observed, nodes


def _precision_weights(
    weights: ArrayLike | None,
    quote_widths: ArrayLike | None,
    *,
    n_observations: int,
) -> tuple[FloatArray, str]:
    if weights is not None and quote_widths is not None:
        raise ValueError("provide weights or quote_widths, not both")
    if quote_widths is not None:
        widths = _vector(quote_widths, name="quote_widths", size=n_observations)
        if np.any(widths <= 0.0):
            raise ValueError("quote_widths must be strictly positive")
        with np.errstate(over="ignore", divide="ignore"):
            result = 1.0 / widths**2
        if not np.all(np.isfinite(result)) or np.any(result <= 0.0):
            raise ValueError("quote_widths produce non-finite precision weights")
        return result, "inverse squared quote width (precision-style)"
    if weights is not None:
        result = _vector(weights, name="weights", size=n_observations)
        if np.any(result <= 0.0):
            raise ValueError("weights must be strictly positive")
        return result, "caller-supplied positive precision-style weights"
    return np.ones(n_observations, dtype=float), "equal weights"


@dataclass(frozen=True)
class ConstrainedCurveMetadata:
    """Assumptions, units, and convex/non-convex boundary of a curve fit."""

    variable: str
    objective: str
    minimum_discount_factor: float
    minimum_discount_rationale: str
    smoothness_penalty: float
    smoothness_operator: str
    weighting: str
    monotone_discount_factors: bool
    monotonicity_assumption: str | None
    monotonicity_warning: str
    first_node_upper_bound: float | None
    node_time_unit: str
    cashflow_unit: str
    price_unit: str
    leave_one_out_contract: str
    convexity_boundary: str


@dataclass(frozen=True)
class LeaveOneOutCurveResult:
    """Held-out prices using one fixed full-sample node grid."""

    predictions: FloatArray
    residuals: FloatArray
    rmse: float
    weighted_rmse: float
    accepted_fits: int
    identified_fits: int
    total_fits: int
    all_fits_accepted: bool
    node_grid_fixed: bool
    contract: str


@dataclass(frozen=True)
class ConstrainedCurveDiagnostics:
    """Pricing, rank, constraint, LOO, and solver-comparison diagnostics."""

    pricing_rmse: float
    weighted_pricing_rmse: float
    penalized_objective: float
    leave_one_out_pricing_rmse: float | None
    leave_one_out_weighted_pricing_rmse: float | None
    cashflow_rank: int
    penalized_design_rank: int
    penalized_design_full_column_rank: bool
    penalized_design_condition_number: float
    maximum_discount_floor_violation: float
    maximum_monotonicity_violation: float
    first_node_anchor_violation: float
    hard_constraint_tolerance: float
    hard_constraints_passed: bool
    solver_objective_disagreement: float | None
    solver_prediction_disagreement: float | None
    raw_solver_prediction_disagreement: float | None
    alternate_solver_kkt_passed: bool | None
    solver_comparison_tolerance: float | None
    solver_comparison_passed: bool | None
    accepted: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ConstrainedDiscountCurveFit:
    """Fitted node discounts and complete independent diagnostics."""

    node_times: FloatArray
    discount_factors: FloatArray
    observed_prices: FloatArray
    fitted_prices: FloatArray
    residuals: FloatArray
    weights: FloatArray
    second_differences: FloatArray
    observation_ids: tuple[str, ...]
    problem: QuadraticProgram
    qp_solution: QPSolution
    alternate_qp_solution: QPSolution | None
    leave_one_out: LeaveOneOutCurveResult | None
    diagnostics: ConstrainedCurveDiagnostics
    metadata: ConstrainedCurveMetadata

    @property
    def solution(self) -> QPSolution:
        """Alias for the primary quadratic-program solution."""

        return self.qp_solution

    def predict_prices(self, cashflow_matrix: ArrayLike) -> FloatArray:
        """Price new cash-flow rows on the fitted, fixed node grid."""

        return predict_prices_from_discounts(cashflow_matrix, self.discount_factors)


def _curve_problem(
    matrix: FloatArray,
    prices: FloatArray,
    weights: FloatArray,
    node_times: FloatArray,
    *,
    smoothness: float,
    minimum_discount: float,
    monotone: bool,
    price_unit: str,
) -> tuple[QuadraticProgram, FloatArray]:
    penalty = second_difference_matrix(node_times)
    weighted_matrix = weights[:, None] * matrix
    hessian = 2.0 * (matrix.T @ weighted_matrix + smoothness * (penalty.T @ penalty))
    linear = -2.0 * (matrix.T @ (weights * prices))
    inequalities = None
    inequality_rhs = None
    inequality_units = None
    if monotone:
        inequalities = np.zeros((matrix.shape[1] - 1, matrix.shape[1]), dtype=float)
        rows = np.arange(inequalities.shape[0])
        inequalities[rows, rows] = -1.0
        inequalities[rows, rows + 1] = 1.0
        inequality_rhs = np.zeros(inequalities.shape[0], dtype=float)
        inequality_units = ("discount factor",) * inequalities.shape[0]
    upper_bounds = np.full(matrix.shape[1], np.inf)
    if monotone:
        # D(0)=1 plus non-increasing D implies D(T_1)<=1.  One first-node
        # bound is sufficient; all later upper bounds follow from G D <= 0.
        upper_bounds[0] = 1.0
    problem = QuadraticProgram(
        P=hessian,
        q=linear,
        G=inequalities,
        h=inequality_rhs,
        lower_bounds=np.full(matrix.shape[1], minimum_discount),
        upper_bounds=upper_bounds,
        variable_units=("discount factor",) * matrix.shape[1],
        inequality_units=inequality_units,
        objective_unit=f"weighted squared {price_unit}",
        name="constrained_discount_factor_curve",
    )
    return problem, penalty


def _initial_discounts(
    matrix: FloatArray,
    prices: FloatArray,
    weights: FloatArray,
    penalty: FloatArray,
    *,
    smoothness: float,
    minimum_discount: float,
    monotone: bool,
) -> FloatArray:
    root_weights = np.sqrt(weights)
    design = root_weights[:, None] * matrix
    target = root_weights * prices
    if smoothness > 0.0:
        design = np.vstack((design, np.sqrt(smoothness) * penalty))
        target = np.concatenate((target, np.zeros(penalty.shape[0])))
    initial, *_ = np.linalg.lstsq(design, target, rcond=None)
    if not np.all(np.isfinite(initial)):
        initial = np.ones(matrix.shape[1], dtype=float)
    initial = np.maximum(initial, minimum_discount)
    if monotone:
        initial[0] = min(initial[0], 1.0)
        initial = np.minimum.accumulate(initial)
        initial = np.maximum(initial, minimum_discount)
    return np.asarray(initial, dtype=float)


def _penalized_objective(
    matrix: FloatArray,
    prices: FloatArray,
    weights: FloatArray,
    discounts: FloatArray,
    penalty: FloatArray,
    smoothness: float,
) -> float:
    residuals = matrix @ discounts - prices
    return float(weights @ residuals**2 + smoothness * np.sum((penalty @ discounts) ** 2))


def _hard_constraint_audit(
    discounts: FloatArray,
    *,
    minimum_discount: float,
    monotone: bool,
) -> tuple[float, float, float, float, bool]:
    epsilon_factor = 100.0 * discounts.size * np.finfo(float).eps
    absolute_floor = 1e-4 * minimum_discount
    floor_violations = np.maximum(minimum_discount - discounts, 0.0)
    floor_tolerances = np.maximum(
        epsilon_factor * np.maximum(np.abs(discounts), minimum_discount),
        absolute_floor,
    )
    floor_violation = float(np.max(floor_violations))
    local_passes = [bool(np.all(floor_violations <= floor_tolerances))]
    local_tolerances = [floor_tolerances]

    monotonicity_violations = np.maximum(np.diff(discounts), 0.0)
    monotonicity_violation = float(np.max(monotonicity_violations)) if monotone else 0.0
    anchor_violation = max(float(discounts[0] - 1.0), 0.0) if monotone else 0.0
    if monotone:
        monotonicity_tolerances = np.maximum(
            epsilon_factor
            * np.maximum.reduce(
                (
                    np.abs(discounts[:-1]),
                    np.abs(discounts[1:]),
                    np.full(discounts.size - 1, minimum_discount),
                )
            ),
            absolute_floor,
        )
        anchor_tolerance = max(
            epsilon_factor * max(abs(float(discounts[0])), 1.0),
            absolute_floor,
        )
        local_passes.extend(
            (
                bool(np.all(monotonicity_violations <= monotonicity_tolerances)),
                anchor_violation <= anchor_tolerance,
            )
        )
        local_tolerances.extend(
            (monotonicity_tolerances, np.asarray([anchor_tolerance], dtype=float))
        )
    # This scalar is a conservative summary only.  Acceptance above is
    # evaluated elementwise against each constraint's own local scale.
    tolerance = float(min(np.min(values) for values in local_tolerances))
    passed = all(local_passes)
    return (
        floor_violation,
        monotonicity_violation,
        anchor_violation,
        tolerance,
        bool(passed),
    )


def _solve_curve(
    matrix: FloatArray,
    prices: FloatArray,
    weights: FloatArray,
    node_times: FloatArray,
    *,
    smoothness: float,
    minimum_discount: float,
    monotone: bool,
    method: QPSolverMethod,
    tolerance: float | None,
    price_unit: str,
) -> tuple[QuadraticProgram, FloatArray, QPSolution]:
    problem, penalty = _curve_problem(
        matrix,
        prices,
        weights,
        node_times,
        smoothness=smoothness,
        minimum_discount=minimum_discount,
        monotone=monotone,
        price_unit=price_unit,
    )
    initial = _initial_discounts(
        matrix,
        prices,
        weights,
        penalty,
        smoothness=smoothness,
        minimum_discount=minimum_discount,
        monotone=monotone,
    )
    solution = solve_quadratic_program(
        problem,
        initial=initial,
        method=method,
        tolerance=tolerance,
    )
    return problem, penalty, solution


def _loo_curve(
    matrix: FloatArray,
    prices: FloatArray,
    weights: FloatArray,
    node_times: FloatArray,
    *,
    smoothness: float,
    minimum_discount: float,
    monotone: bool,
    method: QPSolverMethod,
    tolerance: float | None,
    price_unit: str,
) -> LeaveOneOutCurveResult:
    if matrix.shape[0] < 3:
        raise ValueError("leave-one-bond-out validation requires at least three bonds")
    predictions = np.full(matrix.shape[0], np.nan, dtype=float)
    accepted = 0
    identified = 0
    penalty = second_difference_matrix(node_times)
    for index in range(matrix.shape[0]):
        mask = np.arange(matrix.shape[0]) != index
        fold_design = np.vstack(
            (
                np.sqrt(weights[mask])[:, None] * matrix[mask],
                np.sqrt(smoothness) * penalty,
            )
        )
        fold_identified = np.linalg.matrix_rank(fold_design) == matrix.shape[1]
        identified += int(fold_identified)
        _, _, solution = _solve_curve(
            matrix[mask],
            prices[mask],
            weights[mask],
            node_times,
            smoothness=smoothness,
            minimum_discount=minimum_discount,
            monotone=monotone,
            method=method,
            tolerance=tolerance,
            price_unit=price_unit,
        )
        *_, hard_constraints_pass = _hard_constraint_audit(
            solution.x,
            minimum_discount=minimum_discount,
            monotone=monotone,
        )
        if solution.success and hard_constraints_pass and fold_identified:
            predictions[index] = float(matrix[index] @ solution.x)
            accepted += 1
    residuals = prices - predictions
    all_accepted = accepted == matrix.shape[0]
    rmse = float(np.sqrt(np.mean(residuals**2))) if all_accepted else float("nan")
    weighted_rmse = (
        float(np.sqrt(np.average(residuals**2, weights=weights))) if all_accepted else float("nan")
    )
    contract = (
        "full-sample node grid and cash-flow columns remain fixed; only the held-out "
        "bond price and its cash-flow row are excluded from fitting"
    )
    return LeaveOneOutCurveResult(
        predictions=_read_only(predictions),
        residuals=_read_only(residuals),
        rmse=rmse,
        weighted_rmse=weighted_rmse,
        accepted_fits=accepted,
        identified_fits=identified,
        total_fits=matrix.shape[0],
        all_fits_accepted=all_accepted,
        node_grid_fixed=True,
        contract=contract,
    )


def fit_constrained_discount_curve(
    cashflow_matrix: ArrayLike,
    prices: ArrayLike,
    node_times: ArrayLike,
    *,
    weights: ArrayLike | None = None,
    quote_widths: ArrayLike | None = None,
    smoothness: float = 1e-2,
    minimum_discount: float = 1e-8,
    monotone: bool = False,
    method: QPSolverMethod = "SLSQP",
    tolerance: float | None = None,
    compute_loo: bool = True,
    compare_solver: bool = True,
    observation_ids: tuple[str, ...] | None = None,
    node_time_unit: str = "years from valuation",
    cashflow_unit: str = "currency units",
    price_unit: str = "currency units",
) -> ConstrainedDiscountCurveFit:
    """Fit positive node discounts by a convex weighted least-squares QP."""

    matrix, observed, nodes = _curve_inputs(cashflow_matrix, prices, node_times)
    precision, weight_description = _precision_weights(
        weights,
        quote_widths,
        n_observations=matrix.shape[0],
    )
    alpha = _nonnegative_scalar(smoothness, name="smoothness")
    floor = _positive_scalar(minimum_discount, name="minimum_discount")
    if not isinstance(monotone, bool):
        raise TypeError("monotone must be a boolean")
    if not isinstance(compute_loo, bool) or not isinstance(compare_solver, bool):
        raise TypeError("compute_loo and compare_solver must be booleans")
    node_time_unit = _unit(node_time_unit, name="node_time_unit")
    cashflow_unit = _unit(cashflow_unit, name="cashflow_unit")
    price_unit = _unit(price_unit, name="price_unit")
    if observation_ids is None:
        identifiers = tuple(f"observation_{index}" for index in range(matrix.shape[0]))
    else:
        identifiers = tuple(observation_ids)
        if len(identifiers) != matrix.shape[0]:
            raise ValueError("observation_ids must contain one identifier per price")
        if any(not isinstance(value, str) or not value for value in identifiers):
            raise ValueError("observation_ids must be non-empty strings")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("observation_ids must be unique")

    problem, penalty, solution = _solve_curve(
        matrix,
        observed,
        precision,
        nodes,
        smoothness=alpha,
        minimum_discount=floor,
        monotone=monotone,
        method=method,
        tolerance=tolerance,
        price_unit=price_unit,
    )
    discounts = np.asarray(solution.x, dtype=float)
    fitted = matrix @ discounts
    residuals = observed - fitted
    second_differences = penalty @ discounts
    penalized_objective = _penalized_objective(
        matrix,
        observed,
        precision,
        discounts,
        penalty,
        alpha,
    )

    loo = (
        _loo_curve(
            matrix,
            observed,
            precision,
            nodes,
            smoothness=alpha,
            minimum_discount=floor,
            monotone=monotone,
            method=method,
            tolerance=tolerance,
            price_unit=price_unit,
        )
        if compute_loo
        else None
    )
    alternate_solution = None
    objective_disagreement = None
    prediction_disagreement = None
    raw_prediction_disagreement = None
    alternate_kkt_passed = None
    comparison_tolerance = None
    comparison_passed = None
    warnings: list[str] = []
    if compare_solver:
        alternate_method: QPSolverMethod = "trust-constr" if method == "SLSQP" else "SLSQP"
        _, _, alternate_solution = _solve_curve(
            matrix,
            observed,
            precision,
            nodes,
            smoothness=alpha,
            minimum_discount=floor,
            monotone=monotone,
            method=alternate_method,
            tolerance=tolerance,
            price_unit=price_unit,
        )
        alternate_kkt_passed = alternate_solution.diagnostics.kkt.passed
        *_, alternate_hard_constraints_pass = _hard_constraint_audit(
            alternate_solution.x,
            minimum_discount=floor,
            monotone=monotone,
        )
        if alternate_solution.success and alternate_hard_constraints_pass:
            alternate_predictions = matrix @ alternate_solution.x
            alternate_objective = _penalized_objective(
                matrix,
                observed,
                precision,
                alternate_solution.x,
                penalty,
                alpha,
            )
            objective_scale = max(
                float(precision @ observed**2),
                alpha * float(np.sum((penalty @ discounts) ** 2)),
                np.finfo(float).tiny,
            )
            objective_disagreement = (
                abs(penalized_objective - alternate_objective) / objective_scale
            )
            raw_prediction_disagreement = float(np.max(np.abs(fitted - alternate_predictions)))
            prediction_disagreement = raw_prediction_disagreement / max(
                float(np.max(np.abs(observed))), np.finfo(float).tiny
            )
            comparison_tolerance = float(100.0 * np.sqrt(np.finfo(float).eps))
            comparison_passed = bool(
                objective_disagreement <= comparison_tolerance
                and prediction_disagreement <= comparison_tolerance
            )
        else:
            comparison_tolerance = float(100.0 * np.sqrt(np.finfo(float).eps))
            comparison_passed = False
            warnings.append("alternate solver did not pass its optimizer and KKT checks")

    (
        floor_violation,
        monotonicity_violation,
        anchor_violation,
        hard_tolerance,
        hard_constraints_pass,
    ) = _hard_constraint_audit(
        discounts,
        minimum_discount=floor,
        monotone=monotone,
    )
    if not hard_constraints_pass:
        warnings.append("a hard discount-factor constraint exceeds its raw-scale tolerance")
    if loo is not None and not loo.all_fits_accepted:
        warnings.append(
            "at least one leave-one-bond-out fit failed its identification, hard-constraint, "
            "or KKT gate"
        )
    if comparison_passed is False:
        warnings.append("primary and alternate solvers did not pass the comparison gate")

    root_weights = np.sqrt(precision)
    penalized_design = np.vstack((root_weights[:, None] * matrix, np.sqrt(alpha) * penalty))
    penalized_rank = int(np.linalg.matrix_rank(penalized_design))
    penalized_full_rank = penalized_rank == penalized_design.shape[1]
    condition_number = float(np.linalg.cond(penalized_design)) if penalized_full_rank else np.inf
    if penalized_rank < penalized_design.shape[1]:
        warnings.append("penalized design is rank deficient; node discounts may be non-unique")

    loo_contract = (
        "full-sample node grid and cash-flow columns remain fixed; only the held-out "
        "bond price and its cash-flow row are excluded from fitting"
    )
    metadata = ConstrainedCurveMetadata(
        variable="node discount factors D, not yields and not a jointly fitted decay parameter",
        objective="sum_i w_i (C_i D - p_i)^2 + smoothness * ||second_difference(D)||_2^2",
        minimum_discount_factor=floor,
        minimum_discount_rationale=(
            "1e-8 by default is a numerical positivity floor, audited again in raw discount-factor "
            "units; it is not an economic lower bound"
        ),
        smoothness_penalty=alpha,
        smoothness_operator=(
            "adjacent time-slope differences; linear-in-time discounts have zero penalty"
        ),
        weighting=weight_description,
        monotone_discount_factors=monotone,
        monotonicity_assumption=(
            "non-negative forward rates and the anchor D(0)=1" if monotone else None
        ),
        monotonicity_warning=(
            "monotonicity is optional: negative rates can imply D(T)>1 or locally increasing D"
        ),
        first_node_upper_bound=1.0 if monotone else None,
        node_time_unit=node_time_unit,
        cashflow_unit=cashflow_unit,
        price_unit=price_unit,
        leave_one_out_contract=loo_contract,
        convexity_boundary=(
            "D enters prices linearly and the fixed second-difference penalty is convex; jointly "
            "estimating a Nelson-Siegel decay parameter would be non-convex and is outside Core"
        ),
    )
    diagnostics = ConstrainedCurveDiagnostics(
        pricing_rmse=float(np.sqrt(np.mean(residuals**2))),
        weighted_pricing_rmse=float(np.sqrt(np.average(residuals**2, weights=precision))),
        penalized_objective=penalized_objective,
        leave_one_out_pricing_rmse=None if loo is None else loo.rmse,
        leave_one_out_weighted_pricing_rmse=None if loo is None else loo.weighted_rmse,
        cashflow_rank=int(np.linalg.matrix_rank(root_weights[:, None] * matrix)),
        penalized_design_rank=penalized_rank,
        penalized_design_full_column_rank=penalized_full_rank,
        penalized_design_condition_number=condition_number,
        maximum_discount_floor_violation=floor_violation,
        maximum_monotonicity_violation=monotonicity_violation,
        first_node_anchor_violation=anchor_violation,
        hard_constraint_tolerance=hard_tolerance,
        hard_constraints_passed=hard_constraints_pass,
        solver_objective_disagreement=objective_disagreement,
        solver_prediction_disagreement=prediction_disagreement,
        raw_solver_prediction_disagreement=raw_prediction_disagreement,
        alternate_solver_kkt_passed=alternate_kkt_passed,
        solver_comparison_tolerance=comparison_tolerance,
        solver_comparison_passed=comparison_passed,
        accepted=bool(
            solution.success
            and hard_constraints_pass
            and penalized_full_rank
            and (comparison_passed is not False)
            and (loo is None or loo.all_fits_accepted)
        ),
        warnings=tuple(warnings),
    )
    return ConstrainedDiscountCurveFit(
        node_times=_read_only(nodes),
        discount_factors=_read_only(discounts),
        observed_prices=_read_only(observed),
        fitted_prices=_read_only(fitted),
        residuals=_read_only(residuals),
        weights=_read_only(precision),
        second_differences=_read_only(second_differences),
        observation_ids=identifiers,
        problem=problem,
        qp_solution=solution,
        alternate_qp_solution=alternate_solution,
        leave_one_out=loo,
        diagnostics=diagnostics,
        metadata=metadata,
    )


def leave_one_bond_out_constrained_curve(
    cashflow_matrix: ArrayLike,
    prices: ArrayLike,
    node_times: ArrayLike,
    *,
    weights: ArrayLike | None = None,
    quote_widths: ArrayLike | None = None,
    smoothness: float = 1e-2,
    minimum_discount: float = 1e-8,
    monotone: bool = False,
    method: QPSolverMethod = "SLSQP",
    tolerance: float | None = None,
    price_unit: str = "currency units",
) -> LeaveOneOutCurveResult:
    """Run fixed-node-grid leave-one-bond-out pricing validation."""

    matrix, observed, nodes = _curve_inputs(cashflow_matrix, prices, node_times)
    if not isinstance(monotone, bool):
        raise TypeError("monotone must be a boolean")
    precision, _ = _precision_weights(
        weights,
        quote_widths,
        n_observations=matrix.shape[0],
    )
    return _loo_curve(
        matrix,
        observed,
        precision,
        nodes,
        smoothness=_nonnegative_scalar(smoothness, name="smoothness"),
        minimum_discount=_positive_scalar(minimum_discount, name="minimum_discount"),
        monotone=monotone,
        method=method,
        tolerance=tolerance,
        price_unit=_unit(price_unit, name="price_unit"),
    )


def leave_one_bond_out_constrained_curve_rmse(
    cashflow_matrix: ArrayLike,
    prices: ArrayLike,
    node_times: ArrayLike,
    **kwargs: object,
) -> float:
    """Return the unweighted RMSE from fixed-grid leave-one-bond-out fits."""

    return leave_one_bond_out_constrained_curve(
        cashflow_matrix,
        prices,
        node_times,
        **kwargs,  # type: ignore[arg-type]
    ).rmse


def fit_constrained_bond_discount_curve(
    universe: CouponBondUniverse,
    *,
    quote_width_column: str | None = None,
    weights: ArrayLike | None = None,
    smoothness: float = 1e-2,
    minimum_discount: float = 1e-8,
    monotone: bool = False,
    method: QPSolverMethod = "SLSQP",
    tolerance: float | None = None,
    compute_loo: bool = True,
    compare_solver: bool = True,
) -> ConstrainedDiscountCurveFit:
    """Adapt a B1 ``CouponBondUniverse`` and fit its constrained curve."""

    data = bond_cashflow_matrix(universe, quote_width_column=quote_width_column)
    if weights is not None and data.quote_widths is not None:
        raise ValueError("provide weights or quote_width_column, not both")
    return fit_constrained_discount_curve(
        data.cashflow_matrix,
        data.dirty_prices,
        data.node_times,
        weights=weights,
        quote_widths=data.quote_widths,
        smoothness=smoothness,
        minimum_discount=minimum_discount,
        monotone=monotone,
        method=method,
        tolerance=tolerance,
        compute_loo=compute_loo,
        compare_solver=compare_solver,
        observation_ids=data.bond_ids,
        node_time_unit=data.node_time_unit,
        cashflow_unit=data.cashflow_unit,
        price_unit=data.price_unit,
    )
