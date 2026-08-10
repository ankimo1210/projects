from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.time_series import (
    autocorrelation,
    dickey_fuller_diagnostic,
    fit_ar,
    fit_garch11,
    fit_var,
    forecast_ar,
    forecast_garch_variance,
    forecast_var,
    granger_causality_test,
    impulse_response,
    partial_autocorrelation,
)


def test_acf_and_pacf_identify_ar1_memory() -> None:
    rng = np.random.default_rng(7101)
    values = np.zeros(4000)
    innovations = rng.normal(size=values.size)
    for index in range(1, values.size):
        values[index] = 0.72 * values[index - 1] + innovations[index]
    acf = autocorrelation(values, 5)
    pacf = partial_autocorrelation(values, 5)
    assert acf[1] == pytest.approx(0.72, abs=0.04)
    assert pacf[1] == pytest.approx(0.72, abs=0.04)
    assert np.max(np.abs(pacf[2:])) < 0.06


def test_ar_fit_and_recursive_forecast_recover_deterministic_process() -> None:
    values = np.empty(100)
    values[0] = 2.0
    for index in range(1, values.size):
        values[index] = 0.5 + 0.8 * values[index - 1]
    model = fit_ar(values, 1)
    assert model.intercept == pytest.approx(0.5, abs=1e-10)
    assert model.coefficients[0] == pytest.approx(0.8, abs=1e-10)
    forecast = forecast_ar(model, values, 3)
    expected = []
    current = values[-1]
    for _ in range(3):
        current = 0.5 + 0.8 * current
        expected.append(current)
    np.testing.assert_allclose(forecast, expected, atol=1e-10)


def test_dickey_fuller_statistic_is_more_negative_for_stationary_series() -> None:
    rng = np.random.default_rng(7102)
    stationary = np.zeros(1500)
    random_walk = np.cumsum(rng.normal(size=1500))
    for index in range(1, stationary.size):
        stationary[index] = 0.4 * stationary[index - 1] + rng.normal()
    assert dickey_fuller_diagnostic(stationary).t_statistic < -10.0
    assert dickey_fuller_diagnostic(random_walk).t_statistic > -4.0


def test_var_forecast_and_impulse_response_match_known_system() -> None:
    rng = np.random.default_rng(7103)
    transition = np.array([[0.7, 0.2], [0.0, 0.5]])
    values = np.zeros((4000, 2))
    for index in range(1, values.shape[0]):
        values[index] = transition @ values[index - 1] + rng.normal(scale=0.05, size=2)
    model = fit_var(values, 1)
    np.testing.assert_allclose(model.coefficient_matrices[0], transition, atol=0.025)
    forecast = forecast_var(model, values, 2)
    assert forecast.shape == (2, 2)
    response = impulse_response(model, 2)
    np.testing.assert_allclose(response[1], model.coefficient_matrices[0])


def test_granger_test_detects_directed_predictive_content() -> None:
    rng = np.random.default_rng(7104)
    n = 1500
    cause = rng.normal(size=n)
    effect = np.zeros(n)
    for index in range(1, n):
        effect[index] = 0.4 * effect[index - 1] + 0.8 * cause[index - 1] + rng.normal(scale=0.5)
    forward = granger_causality_test(effect, cause)
    reverse = granger_causality_test(cause, effect)
    assert forward.p_value < 1e-20
    assert reverse.p_value > 0.01


def test_garch_fit_respects_stationarity_and_forecasts_positive_variance() -> None:
    rng = np.random.default_rng(7105)
    n = 3000
    values = np.zeros(n)
    variance = np.empty(n)
    variance[0] = 1.0
    for index in range(1, n):
        variance[index] = 0.05 + 0.1 * values[index - 1] ** 2 + 0.85 * variance[index - 1]
        values[index] = rng.normal(scale=np.sqrt(variance[index]))
    model = fit_garch11(values)
    assert model.converged
    assert 0.0 < model.alpha < 1.0
    assert 0.0 < model.beta < 1.0
    assert model.alpha + model.beta < 1.0
    forecast = forecast_garch_variance(model, values[-1], 10)
    assert np.all(np.isfinite(forecast))
    assert np.all(forecast > 0.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: autocorrelation([1.0, 1.0, 1.0], 1),
        lambda: fit_ar(np.arange(12.0), 0),
        lambda: forecast_ar(fit_ar(np.arange(30.0) ** 2, 1), [1.0], 0),
        lambda: fit_var(np.ones((20, 2))),
        lambda: granger_causality_test(np.arange(20.0), np.arange(19.0)),
        lambda: fit_garch11(np.ones(50)),
    ],
)
def test_time_series_contracts_reject_invalid_inputs(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
