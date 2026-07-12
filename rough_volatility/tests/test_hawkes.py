"""Tests for bivariate sum-of-exponentials Hawkes simulation."""

from dataclasses import replace

import numpy as np
import pytest
from rough_volatility.config import HawkesConfig
from rough_volatility.hawkes import (
    integrated_intensity,
    intensity_on_grid,
    make_scenario,
    power_law_weights,
    simulate_thinning,
)


def test_power_law_mixture_weights_and_tail_slope() -> None:
    betas = np.geomspace(0.1, 1000.0, 6)
    alpha = 0.5
    weights = power_law_weights(betas, alpha)
    assert weights.sum() == pytest.approx(1.0)
    times = np.geomspace(3 / betas.max(), 0.3 / betas.min(), 300)
    kernel = np.sum(weights[:, None] * betas[:, None] * np.exp(-betas[:, None] * times), axis=0)
    slope = np.polyfit(np.log(times), np.log(kernel), 1)[0]
    assert slope == pytest.approx(-(1 + alpha), abs=0.1)


def test_scenario_branching_ratios_and_rate_matching() -> None:
    config = HawkesConfig(target_rate=7.0)
    for name, branching in [("poisson", 0.0), ("stable", 0.6), ("critical", 0.97)]:
        model = make_scenario(name, config)
        assert model.kernel.spectral_radius() == pytest.approx(branching)
        np.testing.assert_allclose(model.mu, 7.0 * (1.0 - branching))
    assert make_scenario("stable", config).kernel.betas.size == 1
    assert make_scenario("critical", config).kernel.betas.size == len(config.betas)


def test_poisson_limit_count_rate_and_strict_event_order() -> None:
    config = HawkesConfig(horizon=1000.0, target_rate=3.0, max_events=20_000)
    model = make_scenario("poisson", config)
    result = simulate_thinning(
        model, config.horizon, np.random.default_rng(100), max_events=config.max_events
    )
    expected = 2 * config.target_rate * config.horizon
    assert abs(result.times.size - expected) < 5 * np.sqrt(expected)
    assert np.all(np.diff(result.times) > 0)
    assert not result.truncated
    assert result.realized_rate == pytest.approx(result.times.size / (2 * config.horizon))


def test_stable_hawkes_compensator_and_event_budget() -> None:
    config = HawkesConfig(horizon=1000.0, target_rate=5.0, max_events=30_000)
    model = make_scenario("stable", config)
    result = simulate_thinning(
        model, config.horizon, np.random.default_rng(101), max_events=config.max_events
    )
    expected = 2 * config.target_rate * config.horizon
    assert abs(result.times.size - expected) < 0.30 * expected
    compensator = integrated_intensity(model, result.times, result.marks, config.horizon)
    assert abs(compensator.sum() - result.times.size) < 0.03 * result.times.size
    assert np.all(np.diff(result.times) > 0)


def test_intensity_reconstruction_shape_baseline_and_nonnegativity() -> None:
    config = replace(HawkesConfig(), horizon=10.0, target_rate=1.0)
    model = make_scenario("stable", config)
    event_times = np.array([1.0, 1.5, 4.0])
    marks = np.array([0, 1, 0])
    grid = np.linspace(0.0, 10.0, 101)
    intensity = intensity_on_grid(model, event_times, marks, grid)
    assert intensity.shape == (2, 101)
    np.testing.assert_allclose(intensity[:, 0], model.mu)
    assert np.all(intensity >= model.mu[:, None] - 1e-12)
    assert intensity[:, 11].sum() > intensity[:, 9].sum()


def test_near_supercritical_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="branching"):
        replace(HawkesConfig(), branching_critical=0.999).validate()
