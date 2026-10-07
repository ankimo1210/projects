"""Hull 20.5: IV bilinear interpolation, explicit axes and separate arbitrage checks."""

import math
from fractions import Fraction

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from hullkit import bsm

TIMES = np.array([1 / 12, 0.25, 0.5, 1, 2, 5.0])
MONEYNESS = np.array([0.90, 0.95, 1, 1.05, 1.10])
VOLS = (
    np.array(
        [
            [14.2, 13, 12, 13.1, 14.5],
            [14, 13, 12, 13.1, 14.2],
            [14.1, 13.3, 12.5, 13.4, 14.3],
            [14.7, 14, 13.5, 14, 14.8],
            [15, 14.4, 14, 14.5, 15.1],
            [14.8, 14.6, 14.4, 14.7, 15],
        ]
    )
    / 100
)


def test_table_20_2_all_thirty_source_grid_values():
    t, m = np.meshgrid(TIMES, MONEYNESS, indexing="ij")
    assert smile.interpolate_iv(TIMES, MONEYNESS, VOLS, t, m) == pytest.approx(VOLS, abs=1e-14)


@pytest.mark.parametrize("time,moneyness,printed", [(0.75, 1.05, 0.137), (1.5, 0.925, 0.14525)])
def test_table_20_2_worked_lookups(time, moneyness, printed):
    assert smile.interpolate_iv(TIMES, MONEYNESS, VOLS, time, moneyness) == pytest.approx(
        printed, abs=1e-14
    )


def test_source_bilinear_value_against_independent_exact_four_corner_weights():
    tw = (Fraction(3, 2) - 1) / (2 - 1)
    mw = (Fraction(925, 1000) - Fraction(9, 10)) / (Fraction(95, 100) - Fraction(9, 10))
    reference = (1 - tw) * ((1 - mw) * Fraction(147, 1000) + mw * Fraction(14, 100)) + tw * (
        (1 - mw) * Fraction(15, 100) + mw * Fraction(144, 1000)
    )
    assert smile.interpolate_iv(TIMES, MONEYNESS, VOLS, 1.5, 0.925) == pytest.approx(
        float(reference), abs=1e-14
    )


def test_interpolation_preserves_independent_bilinear_polynomial_for_broadcast_queries():
    times = np.array([0.25, 1, 3])
    m = np.array([0.8, 1, 1.2])

    def polynomial(t, x):
        return 0.1 + 0.01 * t + 0.02 * x + 0.005 * t * x

    grid = polynomial(times[:, None], m[None, :])
    query_t = np.array([0.5, 1.5, 2.5])[:, None]
    query_m = np.array([0.85, 1.05, 1.15])[None, :]
    assert smile.interpolate_iv(times, m, grid, query_t, query_m) == pytest.approx(
        polynomial(query_t, query_m), abs=1e-14
    )


def test_textbook_interpolates_iv_and_does_not_substitute_total_variance():
    actual = smile.interpolate_iv(TIMES, MONEYNESS, VOLS, 0.75, 1.05)
    variance_interpolation = math.sqrt((0.5 * 0.134**2 + 1 * 0.140**2) / 2 / 0.75)
    assert actual == pytest.approx(0.137, abs=1e-14)
    assert abs(actual - variance_interpolation) > 5e-4


def test_scaled_log_forward_moneyness_direct_definition_and_inverse():
    s, r, q, t = 100, 0.04, 0.07, 1.5
    k = np.array([80, 100, 120.0])
    actual = smile.scaled_log_forward_moneyness(k, s, r, q, t)
    independent = np.log(k / (s * math.exp((r - q) * t))) / math.sqrt(t)
    assert actual == pytest.approx(independent, abs=1e-14)
    inverse = smile.strike_from_smile_axis("scaled_log_forward_moneyness", actual, s, r, q, 0.2, t)
    assert inverse == pytest.approx(k, abs=1e-11)


@pytest.mark.parametrize("time,moneyness", [(0.01, 1), (6, 1), (0.75, 1.2)])
def test_surface_extrapolation_is_explicitly_unsupported(time, moneyness):
    with pytest.raises(ValueError):
        smile.interpolate_iv(TIMES, MONEYNESS, VOLS, time, moneyness)


def test_iv_interpolation_does_not_repair_butterfly_price_arbitrage():
    times, m = [0.5, 1], [0.8, 1, 1.2]
    strikes = 100 * np.array(m)
    bad = np.array([[0.1, 0.5, 0.1], [0.1, 0.5, 0.1]])
    vol = smile.interpolate_iv(times, m, bad, 0.75, m)
    prices = bsm.call_price(100, strikes, 0, vol, 0.75)
    assert np.diff(np.diff(prices) / np.diff(strikes))[0] < 0
    good = smile.interpolate_iv(times, m, np.full((2, 3), 0.2), 0.75, m)
    good_prices = bsm.call_price(100, strikes, 0, good, 0.75)
    assert np.diff(np.diff(good_prices) / np.diff(strikes))[0] > 0


def test_calendar_consistency_is_separate_from_iv_interpolation():
    times, m = [0.5, 1], [0.9, 1.1]
    bad = np.array([[0.4, 0.4], [0.1, 0.1]])
    v = smile.interpolate_iv(times, m, bad, np.array(times), 1)
    total_variance = np.array(times) * v**2
    calls = bsm.call_price(100, 100, 0, v, np.array(times))
    assert total_variance[1] < total_variance[0]
    assert calls[1] < calls[0]  # Fixed forward, r=q=0: a calendar violation.


def test_duplicate_time_nodes_would_make_interpolation_undefined():
    with pytest.raises(ValueError):
        smile.interpolate_iv([0.5, 0.5], [0.9, 1.1], np.full((2, 2), 0.2), 0.5, 1)
