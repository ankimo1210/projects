"""Temperature seasonality, long memory, premia, and station basis risk."""

import numpy as np
import pytest
from hullkit import weather


def test_seasonal_mean_has_peak_and_trend():
    days = np.array([0.0, 200.0, 365.25])
    mean = weather.seasonal_temperature_mean(
        days,
        intercept=15.0,
        trend_per_year=1.0,
        amplitude=10.0,
        peak_day=200.0,
    )
    assert mean[1] > mean[0]
    assert mean[2] - mean[0] == pytest.approx(1.0, abs=1e-12)


def test_ou_zero_noise_tracks_supplied_seasonal_mean():
    mean = np.linspace(10.0, 15.0, 8)
    paths = weather.simulate_ou_temperature(mean, 10.0, sigma=0.0, n_paths=3)
    np.testing.assert_allclose(paths, np.tile(mean, (3, 1)))


def test_fractional_noise_exposes_long_memory_parameter():
    white = weather.fractional_noise_autocovariance(5, 0.5)
    persistent = weather.fractional_noise_autocovariance(5, 0.8)
    assert white[1] == pytest.approx(0.0, abs=1e-12)
    assert persistent[1] > 0.0
    paths = weather.simulate_fractional_ou_temperature(
        np.zeros(12), 0.0, hurst=0.8, n_paths=5, seed=2
    )
    assert paths.shape == (5, 12)
    assert np.all(np.isfinite(paths))


def test_degree_day_indices_are_hand_checkable():
    temperatures = np.array([[10.0, 18.0, 20.0], [20.0, 25.0, 30.0]])
    np.testing.assert_allclose(weather.degree_day_index(temperatures), [8.0, 0.0])
    np.testing.assert_allclose(
        weather.degree_day_index(temperatures, kind="cdd"),
        [2.0, 21.0],
    )


def test_nontraded_weather_premium_principle_is_explicit():
    payoffs = np.array([0.0, 10.0, 20.0, 40.0])
    expected = weather.weather_contract_premium(payoffs)
    loaded = weather.weather_contract_premium(
        payoffs,
        principle="standard_deviation",
        loading=0.5,
    )
    exponential = weather.weather_contract_premium(
        payoffs,
        principle="exponential",
        risk_aversion=0.05,
    )
    assert expected == pytest.approx(17.5)
    assert loaded > expected
    assert exponential > expected


def test_location_station_basis_risk_and_optimal_hedge():
    target = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
    perfect = weather.optimal_basis_hedge(target, target)
    assert perfect.hedge_ratio == pytest.approx(1.0)
    assert perfect.residual_std == pytest.approx(0.0, abs=1e-12)
    station = np.array([5.0, 8.0, 22.0, 25.0, 35.0])
    mismatch = weather.optimal_basis_hedge(target, station)
    assert mismatch.mismatch_rmse > 0.0
    assert 0.0 < mismatch.residual_std < mismatch.unhedged_std


def test_station_basket_weights_are_auditable():
    stations = np.array([[10.0, 20.0], [20.0, 40.0]])
    np.testing.assert_allclose(weather.station_index(stations, [0.25, 0.75]), [17.5, 35.0])
