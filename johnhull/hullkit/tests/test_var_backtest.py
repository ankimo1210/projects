"""Tests for hullkit.var_backtest: Kupiec POF, Christoffersen, Basel traffic light."""

import math

import numpy as np
import pytest
from hullkit import var_backtest
from scipy.stats import binom, chi2


def _hand_kupiec_pof(x, n, alpha):
    """Independent re-derivation of LR_pof from the raw formula (brief Sec.4.2)."""
    p = 1.0 - alpha
    pi_hat = x / n
    log_num = (n - x) * math.log(1.0 - p) + x * math.log(p)
    log_den = (n - x) * math.log(1.0 - pi_hat) + x * math.log(pi_hat)
    return -2.0 * (log_num - log_den)


# --- exceedance_series -------------------------------------------------


def test_exceedance_series_strict_inequality():
    pnl = np.array([1.0, -5.0, -10.0, 0.0])
    var_forecasts = np.array([2.0, 5.0, 10.0, 1.0])
    # day0: -1 > 2 False; day1: 5 > 5 False (strict); day2: 10 > 10 False; day3: 0 > 1 False
    exc = var_backtest.exceedance_series(pnl, var_forecasts)
    assert exc.tolist() == [0, 0, 0, 0]
    assert set(np.unique(exc).tolist()) <= {0, 1}


def test_exceedance_series_detects_breach():
    pnl = np.array([-11.0, -3.0])
    var_forecasts = np.array([10.0, 10.0])
    exc = var_backtest.exceedance_series(pnl, var_forecasts)
    assert exc.tolist() == [1, 0]


def test_exceedance_series_length_mismatch_raises():
    with pytest.raises(ValueError, match="length"):
        var_backtest.exceedance_series([1.0, 2.0], [1.0])


def test_exceedance_series_empty_raises():
    with pytest.raises(ValueError):
        var_backtest.exceedance_series([], [])


# --- kupiec_pof ----------------------------------------------------------


def test_kupiec_pof_hand_computed():
    lr, p_value = var_backtest.kupiec_pof(5, 250, alpha=0.99)
    expected_lr = _hand_kupiec_pof(5, 250, 0.99)
    assert lr == pytest.approx(expected_lr, abs=1e-10)
    assert p_value == pytest.approx(float(chi2.sf(expected_lr, df=1)), abs=1e-10)


def test_kupiec_pof_near_expected_count_is_small():
    n = 250
    alpha = 0.99
    x_expected = round(n * (1.0 - alpha))
    lr_at_expected, _ = var_backtest.kupiec_pof(x_expected, n, alpha=alpha)
    assert lr_at_expected < 1.0


def test_kupiec_pof_p_value_decreases_as_x_deviates():
    n = 250
    alpha = 0.99
    x_expected = round(n * (1.0 - alpha))
    _, p_near = var_backtest.kupiec_pof(x_expected, n, alpha=alpha)
    _, p_far = var_backtest.kupiec_pof(x_expected + 5, n, alpha=alpha)
    _, p_farther = var_backtest.kupiec_pof(x_expected + 15, n, alpha=alpha)
    assert p_near > p_far > p_farther


def test_kupiec_pof_edge_cases_finite():
    lr0, p0 = var_backtest.kupiec_pof(0, 250, alpha=0.99)
    assert math.isfinite(lr0)
    assert math.isfinite(p0)
    lrn, pn = var_backtest.kupiec_pof(250, 250, alpha=0.99)
    assert math.isfinite(lrn)
    assert math.isfinite(pn)


def test_kupiec_pof_invalid_alpha_raises():
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(5, 250, alpha=0.0)
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(5, 250, alpha=1.0)
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(5, 250, alpha=-0.1)


def test_kupiec_pof_invalid_counts_raise():
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(-1, 250, alpha=0.99)
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(251, 250, alpha=0.99)
    with pytest.raises(ValueError):
        var_backtest.kupiec_pof(5, 0, alpha=0.99)


# --- christoffersen_independence ------------------------------------------


def test_christoffersen_independence_requires_two_obs():
    with pytest.raises(ValueError):
        var_backtest.christoffersen_independence([1])
    with pytest.raises(ValueError):
        var_backtest.christoffersen_independence([])


def test_christoffersen_independence_degenerate_series():
    lr0, p0 = var_backtest.christoffersen_independence([0, 0, 0, 0, 0])
    assert lr0 == 0.0
    assert p0 == 1.0
    lr1, p1 = var_backtest.christoffersen_independence([1, 1, 1, 1])
    assert lr1 == 0.0
    assert p1 == 1.0


def test_christoffersen_independence_clustered_exceeds_spread():
    # n=20, 4 exceedances: clustered (adjacent) vs evenly spread (no two adjacent)
    clustered = np.zeros(20, dtype=int)
    clustered[0:4] = 1
    spread = np.zeros(20, dtype=int)
    spread[[0, 5, 10, 15]] = 1
    lr_clustered, _ = var_backtest.christoffersen_independence(clustered)
    lr_spread, _ = var_backtest.christoffersen_independence(spread)
    assert lr_clustered > lr_spread


def test_christoffersen_independence_rejects_exceedance_counts():
    # Counts (not 0/1 flags) must not silently truncate via int cast --
    # this would otherwise be misread as a clean "independent" series.
    counts = [0, 2, 0, 0, 2, 0, 0, 0, 1, 0]
    with pytest.raises(ValueError, match="binary"):
        var_backtest.christoffersen_independence(counts)


def test_christoffersen_independence_rejects_probabilities():
    probs = [0.4, 0.6, 0.1, 0.9, 0.2, 0.3]
    with pytest.raises(ValueError, match="binary"):
        var_backtest.christoffersen_independence(probs)


def test_christoffersen_independence_rejects_non_finite():
    with pytest.raises(ValueError, match="finite"):
        var_backtest.christoffersen_independence([0, 1, np.nan, 0, 1])


# --- christoffersen_cc -----------------------------------------------------


def test_christoffersen_cc_matches_sum_of_parts():
    rng = np.random.default_rng(42)
    exc = rng.integers(0, 2, size=300)
    alpha = 0.99

    lr_cc, p_cc = var_backtest.christoffersen_cc(exc, alpha=alpha)

    lr_ind, _ = var_backtest.christoffersen_independence(exc)
    n = len(exc)
    x_trans = int(np.asarray(exc)[1:].sum())
    lr_pof_trans, _ = var_backtest.kupiec_pof(x_trans, n - 1, alpha=alpha)

    assert lr_cc == pytest.approx(lr_pof_trans + lr_ind, abs=1e-12)
    assert p_cc == pytest.approx(float(chi2.sf(lr_cc, df=2)), abs=1e-12)


def test_christoffersen_cc_rejects_exceedance_counts():
    # Same guard as christoffersen_independence: counts summed raw would
    # silently break the LR_cc = LR_pof + LR_ind identity documented above.
    counts = [0, 2, 0, 0, 2, 0, 0, 0, 1, 0]
    with pytest.raises(ValueError, match="binary"):
        var_backtest.christoffersen_cc(counts, alpha=0.99)


# --- basel_traffic_light ----------------------------------------------------


@pytest.mark.parametrize(
    "x, expected_zone, expected_multiplier",
    [
        (4, "green", 3.00),
        (5, "yellow", 3.40),
        (9, "yellow", 3.85),
        (10, "red", 4.00),
    ],
)
def test_basel_traffic_light_standard_table(x, expected_zone, expected_multiplier):
    result = var_backtest.basel_traffic_light(x, n_obs=250, alpha=0.99)
    assert result.zone == expected_zone
    assert result.multiplier == pytest.approx(expected_multiplier)
    assert result.cumulative_probability == pytest.approx(
        float(binom.cdf(x, 250, 0.01)), abs=1e-12
    )


def test_basel_traffic_light_invalid_inputs_raise():
    with pytest.raises(ValueError):
        var_backtest.basel_traffic_light(5, n_obs=250, alpha=0.0)
    with pytest.raises(ValueError):
        var_backtest.basel_traffic_light(5, n_obs=250, alpha=1.5)
    with pytest.raises(ValueError):
        var_backtest.basel_traffic_light(-1, n_obs=250, alpha=0.99)
    with pytest.raises(ValueError):
        var_backtest.basel_traffic_light(251, n_obs=250, alpha=0.99)
    with pytest.raises(ValueError):
        var_backtest.basel_traffic_light(5, n_obs=0, alpha=0.99)


# --- input contract: non-finite, shape, and count types ----------------


@pytest.mark.parametrize(
    ("pnl", "var_forecasts"),
    [
        ([-100.0], [np.nan]),
        ([np.nan], [1.0]),
        ([-100.0], [np.inf]),
        ([-np.inf], [1.0]),
    ],
)
def test_exceedance_series_rejects_non_finite(pnl, var_forecasts):
    """A missing P&L or VaR must raise, not silently become a non-exceedance."""
    with pytest.raises(ValueError, match="finite"):
        var_backtest.exceedance_series(pnl, var_forecasts)


def test_exceedance_series_rejects_negative_forecast():
    with pytest.raises(ValueError, match="non-negative"):
        var_backtest.exceedance_series([-1.0, 2.0], [-5.0, 3.0])


def test_exceedance_series_allows_zero_forecast():
    """A zero-risk day is legitimate: any loss on it is an exceedance."""
    result = var_backtest.exceedance_series([-1.0, 1.0], [0.0, 0.0])
    np.testing.assert_array_equal(result, np.array([1, 0]))


def test_exceedance_series_rejects_two_dimensional():
    with pytest.raises(ValueError, match="one-dimensional"):
        var_backtest.exceedance_series([[1.0, 2.0]], [[1.0, 1.0]])


def test_christoffersen_rejects_two_dimensional_series():
    exc = np.array([[0, 1, 0], [1, 0, 1]])
    with pytest.raises(ValueError, match="one-dimensional"):
        var_backtest.christoffersen_independence(exc)
    with pytest.raises(ValueError, match="one-dimensional"):
        var_backtest.christoffersen_cc(exc)


@pytest.mark.parametrize(
    ("n_exceedances", "n_obs"),
    [
        (0.5, 250),
        (5, 250.5),
        (True, 250),
        (5, False),
        (np.nan, 250),
        (np.inf, 250),
        (5, np.nan),
    ],
)
def test_kupiec_pof_rejects_non_integer_counts(n_exceedances, n_obs):
    with pytest.raises(ValueError, match="integer"):
        var_backtest.kupiec_pof(n_exceedances, n_obs, alpha=0.99)


def test_basel_traffic_light_rejects_non_integer_counts():
    with pytest.raises(ValueError, match="integer"):
        var_backtest.basel_traffic_light(5.5, 250)


def test_numpy_integer_counts_match_python_ints():
    """np.int64 is a legitimate count type and must give identical numbers."""
    numpy_result = var_backtest.kupiec_pof(np.int64(5), np.int64(250), alpha=0.99)
    python_result = var_backtest.kupiec_pof(5, 250, alpha=0.99)
    assert numpy_result == python_result
    assert var_backtest.basel_traffic_light(np.int64(5), np.int64(250)) == (
        var_backtest.basel_traffic_light(5, 250)
    )
