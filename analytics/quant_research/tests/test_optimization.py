import numpy as np
import pytest
from quant_textbook import (
    backtracking_gradient_descent,
    finite_difference_gradient_audit,
    gradient_descent,
    newton_method,
    projected_gradient,
    proximal_gradient,
)


def _quadratic_problem():
    hessian = np.diag([1.0, 10.0])
    linear = np.array([-1.0, 2.0])

    def objective(point):
        return 0.5 * point @ hessian @ point + linear @ point

    def gradient(point):
        return hessian @ point + linear

    def curvature(point):
        return hessian

    return objective, gradient, curvature


def test_gradient_backtracking_and_newton_recover_quadratic_optimum() -> None:
    objective, gradient, hessian = _quadratic_problem()
    expected = np.array([1.0, -0.2])
    fixed = gradient_descent(
        objective,
        gradient,
        [5.0, 5.0],
        step_size=0.1,
        max_iterations=1_000,
    )
    backtracking = backtracking_gradient_descent(
        objective,
        gradient,
        [5.0, 5.0],
        max_iterations=1_000,
    )
    newton = newton_method(objective, gradient, hessian, [5.0, 5.0])

    for result in (fixed, backtracking, newton):
        assert result.converged
        np.testing.assert_allclose(result.x, expected, atol=1e-6)
        assert result.gradient_mapping_norm <= 1e-8
        assert result.raw_gradient_mapping_norm >= 0.0
        assert len(result.trace.raw_gradient_mapping_norms) == result.iterations + 1
        assert result.trace.gradient_mapping_scale == pytest.approx(
            result.trace.raw_gradient_mapping_norms[0]
        )
        assert result.feasibility == 0.0
        assert result.raw_feasibility == 0.0
        assert result.trace.feasibility_scale == 0.0
        assert len(result.trace.raw_feasibility_values) == result.iterations + 1
        assert len(result.trace.objective_values) == result.iterations + 1
        assert len(result.trace.step_sizes) == result.iterations + 1
        assert result.trace.step_sizes[0] == 0.0
        assert not result.x.flags.writeable
    assert newton.iterations == 1
    assert backtracking.iterations < fixed.iterations
    assert np.all(np.diff(backtracking.trace.objective_values) <= 1e-12)


def test_backtracking_handles_ill_conditioning_that_breaks_a_large_fixed_step() -> None:
    hessian = np.diag([1.0, 1_000.0])

    def objective(point):
        return 0.5 * point @ hessian @ point

    def gradient(point):
        return hessian @ point

    fixed = gradient_descent(
        objective,
        gradient,
        [1.0, 1.0],
        step_size=1.0,
        max_iterations=20,
    )
    adaptive = backtracking_gradient_descent(
        objective,
        gradient,
        [1.0, 1.0],
        step_size=1.0,
        tolerance=1e-7,
        max_iterations=20_000,
    )

    assert not fixed.converged
    assert adaptive.converged
    assert adaptive.objective < 1e-8
    assert np.min(adaptive.trace.step_sizes[1:]) < 0.01


def test_projected_gradient_records_mapping_and_feasibility_at_every_iteration() -> None:
    objective, gradient, _ = _quadratic_problem()

    def projection(point):
        return np.maximum(point, 0.0)

    def feasibility(point):
        return float(np.max(np.maximum(-point, 0.0)))

    result = projected_gradient(
        objective,
        gradient,
        projection,
        [5.0, -5.0],
        step_size=1.0,
        feasibility=feasibility,
    )

    assert result.converged
    np.testing.assert_allclose(result.x, [1.0, 0.0], atol=1e-9)
    assert result.gradient_mapping_norm <= 1e-8
    assert np.all(result.trace.feasibility_values == 0.0)
    assert len(result.trace.gradient_mapping_norms) == result.iterations + 1


@pytest.mark.parametrize("residual_scale", [1e-20, 1.0, 1e20])
def test_feasibility_stopping_is_invariant_to_positive_residual_units(
    residual_scale,
) -> None:
    result = gradient_descent(
        lambda point: 0.0,
        lambda point: np.zeros_like(point),
        [1.0],
        feasibility=lambda point: residual_scale * max(point[0], 0.0),
        max_iterations=2,
    )

    assert not result.converged
    assert result.trace.feasibility_values[0] == pytest.approx(1.0)
    assert result.trace.raw_feasibility_values[0] == pytest.approx(residual_scale)
    assert result.trace.feasibility_scale == pytest.approx(residual_scale)


def test_zero_initial_feasibility_scale_accepts_only_exact_zero_residuals() -> None:
    calls = 0

    def feasibility(point):
        nonlocal calls
        calls += 1
        return 0.0 if calls == 1 else 1e-20

    result = gradient_descent(
        lambda point: 0.5 * point[0] ** 2,
        lambda point: point.copy(),
        [1.0],
        feasibility=feasibility,
        max_iterations=1,
    )

    assert not result.converged
    assert result.trace.feasibility_scale == 0.0
    assert result.trace.feasibility_values[0] == 0.0
    assert np.isinf(result.trace.feasibility_values[1])
    assert result.trace.raw_feasibility_values[1] == pytest.approx(1e-20)


def test_proximal_gradient_matches_closed_form_separable_lasso_solution() -> None:
    objective, gradient, _ = _quadratic_problem()
    penalty = 0.5

    def nonsmooth(point):
        return penalty * np.sum(np.abs(point))

    def soft_threshold(point, step_size):
        return np.sign(point) * np.maximum(np.abs(point) - step_size * penalty, 0.0)

    result = proximal_gradient(
        objective,
        gradient,
        nonsmooth,
        soft_threshold,
        [5.0, 5.0],
        step_size=1.0,
        max_iterations=1_000,
    )

    assert result.converged
    np.testing.assert_allclose(result.x, [0.5, -0.15], atol=1e-6)
    assert result.gradient_mapping_norm <= 1e-8
    assert np.all(np.diff(result.trace.objective_values) <= 1e-12)


def test_proximal_gradient_rejects_initial_composite_objective_overflow() -> None:
    with pytest.raises(FloatingPointError, match="smooth_objective \\+ nonsmooth_objective"):
        proximal_gradient(
            lambda point: 1e308,
            lambda point: np.zeros_like(point),
            lambda point: 1e308,
            lambda point, step: point,
            [0.0],
        )


def test_proximal_gradient_rejects_iterate_composite_objective_overflow() -> None:
    def objective_term(point):
        return 0.0 if point[0] == 0.0 else 1e308

    with pytest.raises(FloatingPointError, match="smooth_objective \\+ nonsmooth_objective"):
        proximal_gradient(
            objective_term,
            lambda point: np.array([-1.0]),
            objective_term,
            lambda point, step: point,
            [0.0],
            backtracking=False,
            max_iterations=1,
        )


def test_finite_difference_audit_passes_correct_gradient_and_rejects_wrong_one() -> None:
    objective, gradient, _ = _quadratic_problem()
    correct = finite_difference_gradient_audit(objective, gradient, [0.3, 0.4])
    wrong = finite_difference_gradient_audit(
        objective,
        lambda point: gradient(point) + np.array([0.01, 0.0]),
        [0.3, 0.4],
    )

    assert correct.passed
    assert correct.maximum_absolute_error < 1e-8
    np.testing.assert_allclose(correct.analytic_gradient, [-0.7, 6.0])
    assert not wrong.passed
    assert wrong.maximum_absolute_error == pytest.approx(0.01, rel=1e-6)
    assert correct.finite_difference_gradients.shape == (5, 2)
    assert not correct.cancellation_detected


@pytest.mark.parametrize("objective_scale", [1e-20, 1.0, 1e20])
def test_normalized_stopping_cannot_accept_initial_point_after_objective_rescaling(
    objective_scale,
) -> None:
    def objective(point):
        return 0.5 * objective_scale * (point[0] - 1.0) ** 2

    def gradient(point):
        return np.array([objective_scale * (point[0] - 1.0)])

    def hessian(point):
        return np.array([[objective_scale]])

    def identity(point):
        return point

    methods = (
        gradient_descent(objective, gradient, [10.0], max_iterations=3),
        newton_method(objective, gradient, hessian, [10.0]),
        projected_gradient(
            objective,
            gradient,
            identity,
            [10.0],
            max_iterations=3,
        ),
        proximal_gradient(
            objective,
            gradient,
            lambda point: 0.0,
            lambda point, step: point,
            [10.0],
            max_iterations=3,
        ),
    )

    for result in methods:
        assert not (result.converged and result.iterations == 0)
        assert result.trace.gradient_mapping_norms[0] == pytest.approx(1.0)
        assert result.trace.raw_gradient_mapping_norms[0] > 0.0
    np.testing.assert_allclose(methods[1].x, [1.0], atol=1e-12)
    assert methods[1].converged


@pytest.mark.parametrize("objective_scale", [1e-20, 1.0, 1e20])
def test_gradient_audit_verdict_is_invariant_to_objective_scale(objective_scale) -> None:
    def objective(point):
        return 0.5 * objective_scale * point[0] ** 2

    correct = finite_difference_gradient_audit(
        objective,
        lambda point: np.array([objective_scale * point[0]]),
        [1.0],
    )
    wrong = finite_difference_gradient_audit(
        objective,
        lambda point: np.array([0.0]),
        [1.0],
    )

    assert correct.passed
    assert not wrong.passed
    assert wrong.relative_error == pytest.approx(1.0, rel=1e-6)


def test_gradient_audit_reports_large_constant_cancellation_as_inconclusive() -> None:
    def objective(point):
        return 1e20 + 0.5 * point[0] ** 2

    audit = finite_difference_gradient_audit(
        objective,
        lambda point: np.array([0.0]),
        [1.0],
    )

    assert audit.cancellation_detected
    assert not audit.passed
    assert "absorbed" in audit.diagnostic


def test_newton_reports_indefinite_hessian_without_silently_changing_algorithm() -> None:
    def objective(point):
        return point[0] ** 2 - point[1] ** 2

    def gradient(point):
        return np.array([2.0 * point[0], -2.0 * point[1]])

    def hessian(point):
        return np.diag([2.0, -2.0])

    result = newton_method(objective, gradient, hessian, [1.0, 1.0])

    assert not result.converged
    assert result.iterations == 0
    assert "not positive definite" in result.message


@pytest.mark.parametrize(
    ("operation", "error", "message"),
    [
        (
            lambda: gradient_descent(lambda point: 0.0, lambda point: [0.0], [], step_size=1.0),
            ValueError,
            "non-empty",
        ),
        (
            lambda: gradient_descent(
                lambda point: float(point @ point),
                lambda point: [1.0],
                [1.0, 2.0],
            ),
            ValueError,
            "one finite value",
        ),
        (
            lambda: projected_gradient(
                lambda point: float(point @ point),
                lambda point: 2.0 * point,
                lambda point: point[:-1],
                [1.0, 2.0],
            ),
            ValueError,
            "preserve",
        ),
        (
            lambda: projected_gradient(
                lambda point: float(point @ point),
                lambda point: 2.0 * point,
                lambda point: point,
                [1.0],
                feasibility=lambda point: -1.0,
            ),
            ValueError,
            "non-negative",
        ),
        (
            lambda: gradient_descent(
                lambda point: float(point @ point),
                lambda point: 2.0 * point,
                [1.0],
                step_size=0.0,
            ),
            ValueError,
            "strictly positive",
        ),
    ],
)
def test_optimizer_contract_rejects_invalid_shapes_and_nonfinite_semantics(
    operation,
    error,
    message,
) -> None:
    with pytest.raises(error, match=message):
        operation()
