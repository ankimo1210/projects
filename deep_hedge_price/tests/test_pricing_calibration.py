import numpy as np
import pytest

from deep_hedge_price.pricing_calibration import (
    calibrate_parameters,
    calibration_error_metrics,
    compare_forward_models,
    fit_direct_inverse_ridge,
)


def test_multistart_calibration_recovers_synthetic_parameters():
    x = np.linspace(-1, 1, 21)

    def forward(parameters):
        return parameters[0] + parameters[1] * x + parameters[2] * x**2

    truth = np.array([0.2, -0.4, 0.8])
    result = calibrate_parameters(
        forward,
        forward(truth),
        np.array([0.5, 0.0, 0.3]),
        (np.array([-1.0, -1.0, 0.0]), np.array([1.0, 1.0, 2.0])),
        n_starts=4,
        seed=7,
    )
    np.testing.assert_allclose(result.parameters, truth, atol=1e-8)
    assert result.repricing_rmse < 1e-10
    assert len(result.starts) == 4
    assert result.parameter_dispersion.shape == truth.shape
    errors = calibration_error_metrics(result, truth)
    assert errors["repricing_rmse"] < 1e-10
    assert errors["parameter_rmse"] < 1e-8


def test_teacher_surrogate_discrepancy_is_explicit():
    def teacher(p):
        return np.array([p[0], p[0] ** 2])

    def surrogate(p):
        return teacher(p) + np.array([0.1, -0.1])

    metrics = compare_forward_models(teacher, surrogate, np.array([0.4]))
    assert metrics["mae"] == pytest.approx(0.1)
    assert metrics["max_abs_error"] == pytest.approx(0.1)


def test_calibration_rejects_shape_broadcasting_and_nonfinite_weights():
    with pytest.raises(ValueError, match="output must match"):
        calibrate_parameters(
            lambda _parameters: np.array([1.0]),
            np.array([1.0, 2.0]),
            np.array([0.5]),
            (np.array([0.0]), np.array([1.0])),
        )
    with pytest.raises(ValueError, match="weights"):
        calibrate_parameters(
            lambda parameters: np.array([parameters[0]]),
            np.array([1.0]),
            np.array([0.5]),
            (np.array([0.0]), np.array([1.0])),
            weights=np.array([np.nan]),
        )


def test_direct_inverse_is_an_explicit_ablation_with_parameter_error():
    rng = np.random.default_rng(5)
    features = rng.normal(size=(40, 4))
    parameters = np.column_stack(
        [0.2 + 0.5 * features[:, 0], -0.1 + features[:, 1] - 0.3 * features[:, 2]]
    )
    inverse = fit_direct_inverse_ridge(features, parameters, ridge=0.0)
    np.testing.assert_allclose(inverse.predict(features), parameters, atol=1e-10)
