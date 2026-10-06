"""Hull 19.2 stop-loss and financed/unfinanced conventions on shared paths."""

import math

import numpy as np
import pytest
from hullkit import _greeks_hedging as greeks
from hullkit.mc import simulate_gbm_paths


def test_source_naked_and_covered_terminal_losses():
    naked = greeks.written_call_terminal(49, 60, 50, 100000, 300000)
    covered = greeks.written_call_terminal(49, 40, 50, 100000, 300000, covered=True)
    assert [naked["option_cash"], naked["profit"]] == pytest.approx([1000000, -700000])
    assert [covered["stock_gain"], covered["profit"]] == pytest.approx([-900000, -600000])


def test_stop_loss_one_round_trip_costs_two_epsilon():
    paths = np.array([[49, 50.1, 49.9, 49]])
    times = np.arange(4) / 10
    holdings = greeks.stop_loss_holdings(paths, 50)
    result = greeks.hedge_cash_replay(paths, times, 50, 0, holdings)
    assert result["no_interest_cost"] == pytest.approx([0.2], abs=1e-14)
    assert result["trade_cash"] == pytest.approx(np.array([[0, 50.1, -49.9, 0]]), abs=1e-14)


@pytest.mark.parametrize("strategy", ["naked", "covered", "stop"])
def test_cash_recurrence_against_independent_discounted_and_undiscounted_gains(strategy):
    paths = np.array([[49, 55, 47, 60], [49, 44, 52, 40]], dtype=float)
    times = np.array([0, 0.1, 0.25, 0.4])
    if strategy == "stop":
        holdings = greeks.stop_loss_holdings(paths, 50)
    else:
        holdings = np.full((2, 3), float(strategy == "covered"))
    result = greeks.hedge_cash_replay(paths, times, 50, 0.05, holdings, quantity=100000)
    payoff = np.maximum(paths[:, -1] - 50, 0)
    discounted_stock = paths * np.exp(-0.05 * times)
    independent_pv = 100000 * (
        payoff * math.exp(-0.05 * 0.4)
        - np.sum(holdings * np.diff(discounted_stock, axis=1), axis=1)
    )
    independent_raw = 100000 * (payoff - np.sum(holdings * np.diff(paths, axis=1), axis=1))
    assert result["present_cost"] == pytest.approx(independent_pv, abs=1e-8)
    assert result["no_interest_cost"] == pytest.approx(independent_raw, abs=1e-8)
    assert result["terminal_cost"] == pytest.approx(
        result["present_cost"] * math.exp(0.05 * 0.4), abs=1e-8
    )
    assert result["terminal_cost"] == pytest.approx(
        result["trade_cash"].sum(axis=1)
        + result["interest_cash"].sum(axis=1)
        + result["close_cash"]
        + 100000 * payoff,
        abs=1e-8,
    )


def test_all_table_19_1_performances_with_common_paths_seed_and_standard_errors():
    time, count = 20 / 52, 60000
    paths = simulate_gbm_paths(49, 0.13, 0.2, time, 80, count, rng=np.random.default_rng(1902))
    initial = greeks.sold_option_valuation(49, 50, 0.05, 0.2, time, 1, 3)["unit_value"]
    for steps, printed in zip(
        [4, 5, 10, 20, 40, 80], [0.98, 0.93, 0.83, 0.79, 0.77, 0.76], strict=True
    ):
        coarse = paths[:, :: 80 // steps]
        holdings = greeks.stop_loss_holdings(coarse, 50)
        result = greeks.hedge_cash_replay(
            coarse, np.linspace(0, time, steps + 1), 50, 0.05, holdings
        )
        cost = result["no_interest_cost"]
        sd = cost.std(ddof=1)
        performance = sd / initial
        sd_se = ((cost - cost.mean()) ** 2).std(ddof=1) / (2 * sd * math.sqrt(count))
        assert abs(performance - printed) <= 6 * sd_se / initial + 0.005
        independent = np.maximum(coarse[:, -1] - 50, 0) - np.sum(
            holdings * np.diff(coarse, axis=1), axis=1
        )
        assert cost == pytest.approx(independent, abs=1e-11)


def test_hedge_grid_requires_increasing_times_and_matching_holdings():
    with pytest.raises(ValueError):
        greeks.hedge_cash_replay([[49, 50]], [0, 0], 50, 0.05, [[0]])
    with pytest.raises(ValueError):
        greeks.hedge_cash_replay([[49, 50]], [0, 0.1], 50, 0.05, [[0, 1, 1]])
