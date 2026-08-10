from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.state_space import (
    extract_nelson_siegel_factors,
    filter_dynamic_nelson_siegel,
    fit_dynamic_nelson_siegel,
    forecast_dynamic_nelson_siegel,
    kalman_filter,
    kalman_smoother,
    nelson_siegel_loadings,
)


def test_kalman_filter_tracks_local_level_and_smoother_uses_future_information() -> None:
    rng = np.random.default_rng(7201)
    n = 400
    state = np.zeros(n)
    for index in range(1, n):
        state[index] = state[index - 1] + rng.normal(scale=0.1)
    observations = state + rng.normal(scale=0.3, size=n)
    result = kalman_filter(
        observations,
        [[1.0]],
        [[1.0]],
        [[0.01]],
        [[0.09]],
        [0.0],
        [[1.0]],
    )
    smoother = kalman_smoother(result, [[1.0]])
    filtered_rmse = np.sqrt(np.mean((result.filtered_means[:, 0] - state) ** 2))
    smoothed_rmse = np.sqrt(np.mean((smoother.smoothed_means[:, 0] - state) ** 2))
    assert smoothed_rmse < filtered_rmse
    np.testing.assert_allclose(smoother.smoothed_means[-1], result.filtered_means[-1])


def test_kalman_filter_handles_missing_observation_without_fake_update() -> None:
    observations = np.array([0.0, 0.1, np.nan, 0.2])
    result = kalman_filter(observations, [[1.0]], [[1.0]], [[0.01]], [[0.04]], [0.0], [[1.0]])
    assert not result.observed_mask[2, 0]
    np.testing.assert_allclose(result.filtered_means[2], result.predicted_means[2])
    np.testing.assert_allclose(result.filtered_covariances[2], result.predicted_covariances[2])


def test_nelson_siegel_factor_extraction_reconstructs_curve() -> None:
    maturities = np.array([0.25, 2.0, 5.0, 10.0, 30.0])
    loadings = nelson_siegel_loadings(maturities, 0.5)
    factors = np.array([[3.0, -1.0, 0.5], [3.1, -0.8, 0.3]])
    yields = factors @ loadings.T
    estimated = extract_nelson_siegel_factors(yields, maturities, 0.5)
    np.testing.assert_allclose(estimated, factors, atol=1e-12)


def test_dynamic_nelson_siegel_fit_filter_and_forecast_have_valid_shapes() -> None:
    rng = np.random.default_rng(7202)
    maturities = np.array([0.25, 2.0, 5.0, 10.0, 30.0])
    loadings = nelson_siegel_loadings(maturities, 0.5)
    factors = np.zeros((700, 3))
    transition = np.diag([0.98, 0.9, 0.8])
    for index in range(1, factors.shape[0]):
        factors[index] = (
            np.array([0.05, 0.0, 0.0])
            + transition @ factors[index - 1]
            + rng.normal(scale=[0.03, 0.04, 0.05])
        )
    yields = factors @ loadings.T + rng.normal(scale=0.01, size=(700, 5))
    model = fit_dynamic_nelson_siegel(yields[:500], maturities, decay=0.5)
    filtered = filter_dynamic_nelson_siegel(model, yields[:510])
    forecast = forecast_dynamic_nelson_siegel(
        model,
        filtered.filtered_means[-1],
        filtered.filtered_covariances[-1],
        5,
    )
    assert forecast.mean.shape == (5,)
    assert forecast.covariance.shape == (5, 5)
    assert np.linalg.eigvalsh(forecast.covariance).min() >= -1e-12


@pytest.mark.parametrize(
    "call",
    [
        lambda: kalman_filter([1.0], [[1.0, 0.0]], [[1.0]], [[1.0]], [[1.0]], [0.0], [[1.0]]),
        lambda: nelson_siegel_loadings([1.0, 2.0], 0.5),
        lambda: nelson_siegel_loadings([1.0, 2.0, 3.0], 0.0),
        lambda: fit_dynamic_nelson_siegel(np.ones((20, 5)), [0.25, 2, 5, 10, 30], decay=0.5),
    ],
)
def test_state_space_contracts_reject_invalid_inputs(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
