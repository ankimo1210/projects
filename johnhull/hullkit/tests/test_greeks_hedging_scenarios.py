"""Hull 19.11: quoted illustrative table vs calculated synthetic option book."""

import math

import numpy as np
import pytest
from hullkit import _greeks_hedging as greeks
from scipy.integrate import quad
from scipy.stats import norm


def density(spot, strike, rate, sigma, time, kind, yield_rate=0):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )


def test_table_19_5_illustrative_cells_and_worst_scenario_without_inventing_book():
    table = np.array(
        [
            [102, 55, 25, 6, -10, -34, -80],
            [80, 40, 17, 2, -14, -38, -85],
            [60, 25, 9, -2, -18, -42, -90],
        ],
        dtype=float,
    )
    result = greeks.scenario_extremes(
        [-0.06, -0.04, -0.02, 0, 0.02, 0.04, 0.06], [-0.02, 0, 0.02], table
    )
    assert [result["worst_pnl"], result["spot_change"], result["vol_change"]] == pytest.approx(
        [-90, 0.06, 0.02]
    )
    # Source does not give holdings, strikes or maturities, so these are quoted
    # $m cells, not a claimed pricing reconstruction of Table19.5.


def test_two_week_cartesian_book_repricing_against_independent_payoff_density():
    book = [(300, "call", 1.1, 0.5, 0.1), (-200, "put", 1.05, 0.75, 0.13)]
    spot, rate, yield_rate = 1.08, 0.04, 0.02
    dx = np.array([-0.06, -0.04, -0.02, 0, 0.02, 0.04, 0.06])
    dv = np.array([-0.02, 0, 0.02])
    result = greeks.scenario_reprice(
        book, spot, rate, dx, dv, elapsed=2 / 52, yield_rate=yield_rate
    )
    initial = sum(
        n * density(spot, k, rate, sig, t, kind, yield_rate) for n, kind, k, t, sig in book
    )
    reference = np.array(
        [
            [
                sum(
                    n * density(spot + x, k, rate, sig + v, t - 2 / 52, kind, yield_rate)
                    for n, kind, k, t, sig in book
                )
                - initial
                for x in dx
            ]
            for v in dv
        ]
    )
    assert result["initial_value"] == pytest.approx(initial, abs=1e-10)
    assert result["pnl"] == pytest.approx(reference, abs=1e-9)


def test_no_spot_vol_shock_still_has_calendar_time_pnl():
    args = (49, 50, 0.05, 0.2, 0.3846)
    dt = 1e-4
    result = greeks.scenario_reprice([(1, "call", 50, 0.3846, 0.2)], 49, 0.05, [0], [0], elapsed=dt)
    expected = greeks.theta_units(*args)["annual"] * dt
    assert result["pnl"][0, 0] == pytest.approx(expected, abs=5e-8)
    assert result["pnl"][0, 0] < 0


def test_short_butterfly_worst_loss_is_inside_scenario_range():
    book = [(-1, "call", 90, 0.1, 0.2), (2, "call", 100, 0.1, 0.2), (-1, "call", 110, 0.1, 0.2)]
    result = greeks.scenario_reprice(book, 100, 0, [-20, 0, 20], [0], elapsed=0.1)
    exact = (
        -np.maximum(np.array([80, 100, 120]) - 90, 0)
        + 2 * np.maximum(np.array([80, 100, 120]) - 100, 0)
        - np.maximum(np.array([80, 100, 120]) - 110, 0)
    )
    assert result["scenario_values"][0] == pytest.approx(exact, abs=1e-12)
    assert result["worst"]["spot_change"] == pytest.approx(0, abs=1e-12)
    assert result["pnl"][0, 1] < result["pnl"][0, 0]
    assert result["pnl"][0, 1] < result["pnl"][0, 2]


def test_two_percent_iv_shift_is_absolute_10_to_12_percent():
    result = greeks.scenario_reprice([(1, "call", 50, 0.4, 0.1)], 49, 0.05, [0], [0.02])
    initial = density(49, 50, 0.05, 0.1, 0.4, "call")
    absolute = density(49, 50, 0.05, 0.12, 0.4, "call") - initial
    relative = density(49, 50, 0.05, 0.102, 0.4, "call") - initial
    assert result["pnl"][0, 0] == pytest.approx(absolute, abs=1e-11)
    assert abs(result["pnl"][0, 0] - relative) > 0.1


@pytest.mark.parametrize("dx,dv,elapsed", [([-50], [0], 0), ([0], [-0.3], 0), ([0], [0], 0.6)])
def test_scenarios_reject_nonpositive_spot_negative_vol_and_expired_book(dx, dv, elapsed):
    with pytest.raises(ValueError):
        greeks.scenario_reprice([(1, "call", 50, 0.4, 0.2)], 49, 0.05, dx, dv, elapsed=elapsed)


def test_elapsed_time_equal_to_maturity_up_to_rounding_is_accepted():
    book = [(1, "call", 50, 7/52, .2)]
    exact = greeks.scenario_reprice(book, 49, .05, [0], [0], elapsed=7/52)
    rounded = greeks.scenario_reprice(book, 49, .05, [0], [0], elapsed=7*(1/52))
    assert rounded["pnl"] == pytest.approx(exact["pnl"], abs=1e-12)
