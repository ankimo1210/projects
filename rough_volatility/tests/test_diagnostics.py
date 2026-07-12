"""Tests for reusable time-series diagnostics."""

import numpy as np
from rough_volatility.diagnostics import (
    acf_fft,
    log_spaced_lags,
    rolling_realized_variance,
    structure_function,
)


def test_white_noise_acf_and_ar1_acf() -> None:
    rng = np.random.default_rng(30)
    white = rng.standard_normal(120_000)
    white_acf = acf_fft(white, 4)
    assert white_acf[0] == 1.0
    assert np.max(np.abs(white_acf[1:])) < 0.015

    phi = 0.75
    innovations = rng.standard_normal(120_000)
    ar = np.empty_like(innovations)
    ar[0] = innovations[0] / np.sqrt(1 - phi**2)
    for index in range(1, len(ar)):
        ar[index] = phi * ar[index - 1] + innovations[index]
    np.testing.assert_allclose(acf_fft(ar, 3)[1:], phi ** np.arange(1, 4), atol=0.02)


def test_structure_function_matches_hand_calculation() -> None:
    paths = np.array([[0.0, 1.0, 3.0, 6.0], [0.0, -1.0, -3.0, -6.0]])
    actual = structure_function(paths, q_values=(1.0, 2.0), lags=(1, 2))
    expected = np.array(
        [
            [(1 + 2 + 3) / 3, (3 + 5) / 2],
            [(1 + 4 + 9) / 3, (9 + 25) / 2],
        ]
    )
    np.testing.assert_allclose(actual, expected)


def test_log_spaced_lags_are_unique_bounded_and_increasing() -> None:
    lags = log_spaced_lags(1000, n_lags=15, max_frac=0.1)
    assert lags[0] == 1
    assert lags[-1] <= 100
    assert np.all(np.diff(lags) > 0)


def test_rolling_realized_variance_is_rolling_sum_of_squares() -> None:
    returns = np.array([1.0, 2.0, 3.0, 4.0])
    result = rolling_realized_variance(returns, window=2)
    assert np.isnan(result[0])
    np.testing.assert_allclose(result[1:], [5.0, 13.0, 25.0])
