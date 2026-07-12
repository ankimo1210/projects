"""Tests for event aggregation, volatility proxies and noise fragility."""

from dataclasses import replace

import numpy as np
from rough_volatility.config import NoiseStudyConfig
from rough_volatility.microstructure import (
    bin_events,
    effective_hurst_of_log_rv,
    noise_fragility_study,
    pre_average,
    price_from_events,
    rv_diagnostics,
)


def test_event_binning_is_exact_on_toy_data() -> None:
    times = np.array([0.1, 0.9, 1.0, 1.9, 2.8])
    marks = np.array([0, 1, 0, 0, 1])
    bins = bin_events(times, marks, bin_width=1.0, horizon=3.0)
    np.testing.assert_array_equal(bins["buy_count"], [1, 2, 0])
    np.testing.assert_array_equal(bins["sell_count"], [1, 0, 1])
    np.testing.assert_array_equal(bins["event_count"], [2, 2, 1])
    np.testing.assert_array_equal(bins["imbalance"], [0, 2, -1])


def test_signed_event_price_and_rolling_rv() -> None:
    bins = bin_events(
        np.array([0.2, 1.2, 1.3, 2.2]),
        np.array([0, 0, 1, 1]),
        bin_width=1.0,
        horizon=3.0,
    )
    priced = price_from_events(
        bins, p0=100.0, tick_eps=0.5, noise_std=0.0, rng=np.random.default_rng(110)
    )
    np.testing.assert_allclose(priced["price"], [100.5, 100.5, 100.0])
    diagnosed = rv_diagnostics(priced, window=2)
    assert {"return", "abs_return", "squared_return", "rolling_rv", "rolling_intensity"} <= set(
        diagnosed.columns
    )
    assert np.isnan(diagnosed["rolling_rv"].iloc[0])


def test_pre_averaging_reduces_iid_observation_noise() -> None:
    rng = np.random.default_rng(111)
    latent = np.cumsum(rng.standard_normal(20_000))
    noisy = latent + 2.0 * rng.standard_normal(latent.size)
    raw_error_variance = np.var(noisy - latent)
    averaged_error_variance = np.var(pre_average(noisy, 8) - pre_average(latent, 8))
    assert averaged_error_variance < 0.2 * raw_error_variance


def test_effective_hurst_returns_labeled_estimate() -> None:
    rng = np.random.default_rng(112)
    rv = np.exp(np.cumsum(0.02 * rng.standard_normal(2048)))
    estimate = effective_hurst_of_log_rv(rv)
    assert np.isfinite(estimate.h_hat)
    assert estimate.estimator == "effective_log_rv_variogram"


def test_noise_fragility_study_schema_reproducibility_and_clean_recovery() -> None:
    config = replace(
        NoiseStudyConfig(),
        n_steps=2048,
        n_replications=12,
        noise_stds=(0.0, 0.20),
        strides=(1, 4),
        estimators=("variogram",),
    )
    first = noise_fragility_study(config, 1210)
    second = noise_fragility_study(config, 1210)
    assert list(first.columns) == [
        "noise_std",
        "stride",
        "estimator",
        "mode",
        "h_hat_mean",
        "h_hat_sd",
        "n_rep",
    ]
    assert first.equals(second)
    baseline = first.query(
        "noise_std == 0 and stride == 1 and estimator == 'variogram' and mode == 'raw'"
    ).iloc[0]
    assert abs(baseline["h_hat_mean"] - config.latent_h) < 0.05
    noisy = first.query(
        "noise_std == 0.20 and stride == 1 and estimator == 'variogram' and mode == 'raw'"
    ).iloc[0]
    assert abs(noisy["h_hat_mean"] - config.latent_h) > abs(
        baseline["h_hat_mean"] - config.latent_h
    )
