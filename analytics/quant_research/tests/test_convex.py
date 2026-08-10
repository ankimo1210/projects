import numpy as np
import pytest
import quant_textbook.convex as convex
from quant_textbook import (
    QuadraticProgram,
    check_inequality_sensitivity,
    evaluate_kkt,
    quadratic_objective,
    solve_quadratic_program,
    validate_quadratic_program,
)


def _reference_problem(*, objective_scale=1.0, constraint_scale=1.0):
    return QuadraticProgram(
        P=objective_scale * 2.0 * np.eye(2),
        q=objective_scale * np.array([-2.0, -4.0]),
        G=constraint_scale * np.array([[1.0, 1.0]]),
        h=constraint_scale * np.array([2.5]),
        lower_bounds=np.zeros(2),
        variable_units=("position", "position"),
        inequality_units=("position",),
        objective_unit="risk-adjusted return",
        name="small_portfolio_qp",
    )


def test_empty_equality_system_has_an_empty_independent_row_subset() -> None:
    indices = convex._independent_row_indices(np.empty((0, 2)))

    np.testing.assert_array_equal(indices, np.empty(0, dtype=int))
    assert solve_quadratic_program(_reference_problem()).success


@pytest.mark.parametrize("method", ["SLSQP", "trust-constr"])
def test_reference_qp_has_primal_dual_certificate_and_known_solution(method) -> None:
    problem = _reference_problem()
    validation = validate_quadratic_program(problem)
    solution = solve_quadratic_program(problem, method=method)

    assert validation.convex_qp
    assert validation.positive_semidefinite
    np.testing.assert_allclose(solution.x, [0.75, 1.75], atol=2e-6)
    assert solution.success
    assert solution.diagnostics.optimizer_success
    assert solution.diagnostics.kkt.passed
    assert solution.status >= 0
    assert solution.iterations > 0
    assert solution.message
    assert solution.inequality_duals[0] == pytest.approx(0.5, abs=2e-6)
    assert solution.primal_objective == pytest.approx(-4.875, abs=2e-9)
    assert solution.dual_objective == pytest.approx(solution.primal_objective, abs=2e-6)
    assert solution.diagnostics.kkt.raw_primal_inequality <= 1e-10
    assert solution.diagnostics.kkt.raw_duality_gap <= 2e-6
    assert quadratic_objective(problem, solution.x) == pytest.approx(solution.primal_objective)


def test_inequality_shadow_price_matches_centered_rhs_sensitivity() -> None:
    problem = _reference_problem()
    solution = solve_quadratic_program(problem)
    sensitivity = check_inequality_sensitivity(
        problem,
        solution,
        0,
        perturbation=1e-4,
    )

    assert sensitivity.predicted_derivative == pytest.approx(-0.5, abs=2e-6)
    assert sensitivity.finite_difference_derivative == pytest.approx(-0.5, abs=2e-4)
    assert sensitivity.relative_error < 2e-4
    assert "dv/dh_i = -lambda_i" in sensitivity.sign_convention


@pytest.mark.parametrize("constraint_scale", [1e-20, 1.0, 1e20])
def test_sensitivity_perturbation_scales_with_constraint_rhs_units(constraint_scale) -> None:
    problem = _reference_problem(constraint_scale=constraint_scale)
    solution = solve_quadratic_program(problem)
    sensitivity = check_inequality_sensitivity(problem, solution, 0)

    assert sensitivity.rhs_scale == pytest.approx(
        3.0 * constraint_scale,
        rel=1e-14,
        abs=0.0,
    )
    assert sensitivity.perturbation == pytest.approx(
        sensitivity.relative_perturbation * sensitivity.rhs_scale
    )
    assert sensitivity.finite_difference_derivative == pytest.approx(
        sensitivity.predicted_derivative,
        rel=2e-4,
    )
    assert sensitivity.relative_error < 2e-4


@pytest.mark.parametrize("method", ["SLSQP", "trust-constr"])
@pytest.mark.parametrize("objective_scale", [1e-20, 1.0, 1e20])
@pytest.mark.parametrize("constraint_scale", [1e-20, 1.0, 1e20])
def test_qp_solution_and_kkt_gate_are_invariant_to_positive_unit_scaling(
    method,
    objective_scale,
    constraint_scale,
) -> None:
    problem = _reference_problem(
        objective_scale=objective_scale,
        constraint_scale=constraint_scale,
    )
    solution = solve_quadratic_program(problem, method=method)

    np.testing.assert_allclose(solution.x, [0.75, 1.75], atol=2e-6)
    assert solution.success
    assert solution.diagnostics.kkt.passed


@pytest.mark.parametrize("constraint_scale", [1e-20, 1.0, 1e20])
def test_scaled_primal_violation_cannot_pass_the_kkt_audit(constraint_scale) -> None:
    problem = _reference_problem(constraint_scale=constraint_scale)
    residuals = evaluate_kkt(
        problem,
        [1.0, 2.0],
        [0.0],
        [],
        [0.0, 0.0],
        [0.0, 0.0],
        dual_objective=-5.0,
    )

    assert residuals.raw_primal_inequality == pytest.approx(0.5 * constraint_scale)
    assert residuals.primal_inequality == pytest.approx(1.0 / 6.0)
    assert not residuals.passed


@pytest.mark.parametrize("irrelevant_coordinate", [1e6, 1e20])
def test_unrelated_large_coordinate_cannot_hide_a_rowwise_constraint_violation(
    irrelevant_coordinate,
) -> None:
    problem = QuadraticProgram(
        P=np.zeros((2, 2)),
        q=np.zeros(2),
        G=np.array([[1.0, 0.0]]),
        h=np.array([0.0]),
    )
    residuals = evaluate_kkt(
        problem,
        [1.0, irrelevant_coordinate],
        [0.0],
        [],
        [0.0, 0.0],
        [0.0, 0.0],
        dual_objective=0.0,
    )

    assert residuals.raw_primal_inequality == pytest.approx(1.0)
    assert residuals.primal_inequality == pytest.approx(1.0)
    assert not residuals.passed


def test_infeasible_stationary_reference_cannot_hide_complementarity_or_gap() -> None:
    problem = QuadraticProgram(
        P=np.array([[1e-20]]),
        q=np.array([-1.0]),
        G=np.array([[1.0]]),
        h=np.array([0.0]),
    )
    residuals = evaluate_kkt(
        problem,
        [-1.0],
        [1.0],
        [],
        [0.0],
        [0.0],
        dual_objective=0.0,
    )

    assert residuals.raw_complementarity == pytest.approx(1.0)
    assert residuals.raw_duality_gap == pytest.approx(1.0)
    assert residuals.complementarity == pytest.approx(1.0)
    assert residuals.duality_gap == pytest.approx(1.0)
    assert not residuals.passed


def test_linear_program_with_singular_hessian_has_valid_dual_certificate() -> None:
    problem = QuadraticProgram(
        P=np.zeros((1, 1)),
        q=np.array([-1.0]),
        G=np.array([[1.0]]),
        h=np.array([2.0]),
        lower_bounds=np.array([0.0]),
    )
    validation = validate_quadratic_program(problem)
    solution = solve_quadratic_program(problem)

    assert validation.positive_semidefinite
    assert validation.hessian_rank == 0
    assert np.isinf(validation.hessian_condition_number)
    assert solution.x[0] == pytest.approx(2.0, abs=2e-7)
    assert solution.inequality_duals[0] == pytest.approx(1.0, abs=2e-7)
    assert solution.success


def test_infeasible_qp_returns_failed_diagnostics_instead_of_false_success() -> None:
    problem = QuadraticProgram(
        P=np.eye(1),
        q=np.zeros(1),
        G=np.array([[1.0]]),
        h=np.array([0.0]),
        lower_bounds=np.array([1.0]),
    )
    solution = solve_quadratic_program(problem)

    assert not solution.success
    assert not solution.diagnostics.kkt.passed
    assert solution.diagnostics.kkt.raw_primal_inequality >= 0.9


def test_validation_distinguishes_nonconvexity_and_inconsistent_equalities() -> None:
    tiny_nonconvex = QuadraticProgram(P=np.array([[-1e-20]]), q=np.zeros(1))
    validation = validate_quadratic_program(tiny_nonconvex)
    assert not validation.positive_semidefinite
    assert not validation.convex_qp
    with pytest.raises(ValueError, match="positive-semidefinite"):
        solve_quadratic_program(tiny_nonconvex)

    inconsistent = QuadraticProgram(
        P=np.eye(2),
        q=np.zeros(2),
        A=np.array([[1.0, 1.0], [1.0, 1.0]]),
        b=np.array([1.0, 2.0]),
    )
    equality_validation = validate_quadratic_program(inconsistent)
    assert equality_validation.equality_rank == 1
    assert equality_validation.equality_augmented_rank == 2
    assert not equality_validation.equality_system_consistent
    assert not equality_validation.equality_rows_independent


def test_equality_rank_and_consistency_are_invariant_to_row_units() -> None:
    consistent = QuadraticProgram(
        P=np.eye(2),
        q=np.zeros(2),
        A=np.diag([1.0, 1e-20]),
        b=np.array([1.0, 2e-20]),
    )
    validation = validate_quadratic_program(consistent)
    assert validation.equality_rank == 2
    assert validation.equality_augmented_rank == 2
    assert validation.equality_system_consistent
    assert validation.equality_rows_independent

    inconsistent = QuadraticProgram(
        P=np.eye(2),
        q=np.zeros(2),
        A=np.array([[1.0, 0.0], [0.0, 0.0]]),
        b=np.array([1.0, 1e-20]),
    )
    invalid = validate_quadratic_program(inconsistent)
    assert invalid.equality_rank == 1
    assert invalid.equality_augmented_rank == 2
    assert not invalid.equality_system_consistent


@pytest.mark.parametrize("method", ["SLSQP", "trust-constr"])
def test_consistent_zero_equality_is_removed_from_the_solver_system(method) -> None:
    problem = QuadraticProgram(
        P=np.eye(1),
        q=np.array([-1.0]),
        A=np.zeros((1, 1)),
        b=np.zeros(1),
    )
    validation = validate_quadratic_program(problem)
    solution = solve_quadratic_program(problem, method=method)

    assert validation.convex_qp
    assert validation.equality_system_consistent
    assert not validation.equality_rows_independent
    np.testing.assert_allclose(solution.x, [1.0], atol=2e-7)
    np.testing.assert_array_equal(solution.equality_duals, [0.0])
    assert solution.success


@pytest.mark.parametrize("method", ["SLSQP", "trust-constr"])
def test_consistent_duplicate_equalities_are_reduced_for_the_solver(method) -> None:
    problem = QuadraticProgram(
        P=np.eye(2),
        q=np.array([-2.0, -4.0]),
        A=np.array([[1.0, 1.0], [2.0, 2.0]]),
        b=np.array([1.0, 2.0]),
    )
    validation = validate_quadratic_program(problem)
    solution = solve_quadratic_program(problem, method=method)

    assert validation.convex_qp
    assert validation.equality_rank == 1
    assert not validation.equality_rows_independent
    np.testing.assert_allclose(solution.x, [-0.5, 1.5], atol=2e-6)
    np.testing.assert_allclose(problem.A @ solution.x, problem.b, atol=2e-6)
    assert solution.equality_duals.shape == (2,)
    assert solution.success


@pytest.mark.parametrize("objective_scale", [1e-20, 1.0, 1e20])
def test_trust_constr_zero_lower_bound_is_reconstructed_in_original_units(
    objective_scale,
) -> None:
    problem = QuadraticProgram(
        P=objective_scale * np.eye(1),
        q=objective_scale * np.ones(1),
        lower_bounds=np.array([0.0]),
    )
    solution = solve_quadratic_program(problem, method="trust-constr")

    assert solution.success
    assert solution.diagnostics.active_set_polished
    assert solution.x[0] == pytest.approx(0.0, abs=2e-6)
    assert solution.lower_bound_duals[0] == pytest.approx(objective_scale, rel=2e-6)


@pytest.mark.parametrize(
    ("operation", "error", "message"),
    [
        (
            lambda: QuadraticProgram(
                P=np.array([[1e-20, 1e-21], [0.0, 1e-20]]),
                q=np.zeros(2),
            ),
            ValueError,
            "symmetric",
        ),
        (
            lambda: QuadraticProgram(P=np.eye(2), q=np.zeros(1)),
            ValueError,
            "exactly 2",
        ),
        (
            lambda: QuadraticProgram(
                P=np.eye(2),
                q=np.zeros(2),
                variable_units=("currency",),
            ),
            ValueError,
            "variable_units",
        ),
        (
            lambda: QuadraticProgram(
                P=np.eye(1),
                q=np.zeros(1),
                lower_bounds=[1.0],
                upper_bounds=[0.0],
            ),
            ValueError,
            "must not exceed",
        ),
        (
            lambda: QuadraticProgram(
                P=np.eye(1),
                q=np.zeros(1),
                lower_bounds=[np.inf],
            ),
            ValueError,
            "positive infinity",
        ),
        (
            lambda: QuadraticProgram(
                P=np.eye(1),
                q=np.zeros(1),
                upper_bounds=[-np.inf],
            ),
            ValueError,
            "negative infinity",
        ),
        (
            lambda: check_inequality_sensitivity(
                _reference_problem(),
                solve_quadratic_program(_reference_problem()),
                2,
            ),
            IndexError,
            "out of range",
        ),
    ],
)
def test_qp_contract_rejects_invalid_shapes_units_and_indices(operation, error, message) -> None:
    with pytest.raises(error, match=message):
        operation()
