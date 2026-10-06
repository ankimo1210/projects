"""Hull 19.4: printed delta-hedge ledgers and independent gain accounting."""

import math

import numpy as np
import pytest
from hullkit import _greeks_hedging as greeks
from hullkit.mc import simulate_gbm_paths
from scipy.integrate import quad
from scipy.stats import norm

TABLE_19_2 = np.array(
    [
        [49, 0.522, 2557.8, 2557.8, 2.5],
        [48.12, 0.458, -308.0, 2252.3, 2.2],
        [47.37, 0.400, -274.7, 1979.8, 1.9],
        [50.25, 0.596, 984.9, 2966.6, 2.9],
        [51.75, 0.693, 502.0, 3471.5, 3.3],
        [53.12, 0.774, 430.3, 3905.1, 3.8],
        [53, 0.771, -15.9, 3893.0, 3.7],
        [51.87, 0.706, -337.2, 3559.5, 3.4],
        [51.38, 0.674, -164.4, 3398.5, 3.3],
        [53, 0.787, 598.9, 4000.7, 3.8],
        [49.88, 0.550, -1182.2, 2822.3, 2.7],
        [48.5, 0.413, -664.4, 2160.6, 2.1],
        [49.88, 0.542, 643.5, 2806.2, 2.7],
        [50.37, 0.591, 246.8, 3055.7, 2.9],
        [52.13, 0.768, 922.7, 3981.3, 3.8],
        [51.88, 0.759, -46.7, 3938.4, 3.8],
        [52.87, 0.865, 560.4, 4502.6, 4.3],
        [54.87, 0.978, 620.0, 5126.9, 4.9],
        [54.62, 0.990, 65.5, 5197.3, 5.0],
        [55.87, 1, 55.9, 5258.2, 5.1],
        [57.25, 1, 0, 5263.3, 0],
    ]
)
TABLE_19_3 = np.array(
    [
        [49, 0.522, 2557.8, 2557.8, 2.5],
        [49.75, 0.568, 228.9, 2789.2, 2.7],
        [52, 0.705, 712.4, 3504.3, 3.4],
        [50, 0.579, -630, 2877.7, 2.8],
        [48.38, 0.459, -580.6, 2299.9, 2.2],
        [48.25, 0.443, -77.2, 2224.9, 2.1],
        [48.75, 0.475, 156, 2383, 2.3],
        [49.63, 0.540, 322.6, 2707.9, 2.6],
        [48.25, 0.420, -579, 2131.5, 2.1],
        [48.25, 0.410, -48.2, 2085.4, 2],
        [51.12, 0.658, 1267.8, 3355.2, 3.2],
        [51.5, 0.692, 175.1, 3533.5, 3.4],
        [49.88, 0.542, -748.2, 2788.7, 2.7],
        [49.88, 0.538, -20, 2771.4, 2.7],
        [48.75, 0.400, -672.7, 2101.4, 2],
        [47.5, 0.236, -779, 1324.4, 1.3],
        [48, 0.261, 120, 1445.7, 1.4],
        [46.25, 0.062, -920.4, 526.7, 0.5],
        [48.13, 0.183, 582.4, 1109.6, 1.1],
        [46.63, 0.007, -820.7, 290, 0.3],
        [48.12, 0, -33.7, 256.6, 0],
    ]
)


def test_source_delta_rebalance_portfolio_and_example_19_1():
    assert greeks.delta_stock_hedge([-2000], [0.6]) == pytest.approx(1200)
    assert greeks.delta_stock_hedge([-2000], [0.65]) - 1200 == pytest.approx(100)
    assert greeks.delta_stock_hedge(
        [100000, -200000, -50000], [0.533, 0.468, -0.508]
    ) == pytest.approx(14900)
    value = greeks.delta_holdings([[49, 49]], [0, 0.3846], 50, 0.05, 0.2)
    assert value[0, 0] == pytest.approx(0.522, abs=0.0005)


@pytest.mark.parametrize("table,cost", [(TABLE_19_2, 263338.49), (TABLE_19_3, 256337.59)])
def test_source_all_21_rows_cash_rounding_and_independent_present_cost(table, cost):
    times = np.arange(21) / 52
    result = greeks.hedge_cash_replay(table[:, 0], times, 50, 0.05, table[:, 1], quantity=100000)
    assert result["trade_cash"][0] / 1000 == pytest.approx(table[:, 2], abs=0.050001)
    # Displayed columns have independent 0.1k rounding; compare the displayed
    # recurrence separately, without changing interest to force the final label.
    printed_next = table[:-1, 3] + table[:-1, 4] + table[1:, 2]
    assert printed_next == pytest.approx(table[1:, 3], abs=0.150001)
    assert result["interest_cash"][0, 1:] / 1000 == pytest.approx(table[:-1, 4], abs=0.0505)
    assert result["terminal_cost"] == pytest.approx([cost], abs=0.01)
    discounted = table[:, 0] * np.exp(-0.05 * times)
    reference = 100000 * (
        max(table[-1, 0] - 50, 0) * math.exp(-0.05 * times[-1])
        - np.dot(table[:-1, 1], np.diff(discounted))
    )
    assert result["present_cost"] == pytest.approx([reference], abs=1e-8)
    # Full-precision cash using displayed S/delta differs from Table19.3's
    # 256.6k heading by 262.41 dollars: not claimed as exact reproduction.
    if table is TABLE_19_2:
        assert result["terminal_cost"][0] == pytest.approx(263300, abs=50)
    else:
        assert 256600 - result["terminal_cost"][0] == pytest.approx(262.41, abs=0.01)


def test_source_week_nine_valuation_and_printed_4100_net_change():
    price = greeks.sold_option_valuation(53, 50, 0.05, 0.2, 11 / 52, 100000, 0)["theoretical_value"]
    assert price == pytest.approx(414500, abs=50)
    assert -174500 - 1442900 + (4171100 - 2557800) == pytest.approx(-4100)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_delta_against_independent_payoff_density_pathwise_derivative(kind):
    spot, strike, rate, sigma, time = 49, 50, 0.05, 0.2, 0.3846
    boundary = (math.log(strike / spot) - (rate - sigma * sigma / 2) * time) / (
        sigma * math.sqrt(time)
    )
    low, high = (boundary, 12) if kind == "call" else (-12, boundary)
    sign = 1 if kind == "call" else -1
    reference = (
        sign
        * math.exp(-rate * time)
        * quad(
            lambda z: (
                math.exp((rate - sigma * sigma / 2) * time + sigma * math.sqrt(time) * z)
                * norm.pdf(z)
            ),
            low,
            high,
            epsabs=1e-12,
        )[0]
    )
    assert greeks.delta_holdings([[spot, spot]], [0, time], strike, rate, sigma, kind=kind)[
        0, 0
    ] == pytest.approx(reference, abs=1e-12)


def test_table_19_4_all_six_performances_with_fixed_seed_standard_error():
    time, count = 20 / 52, 60000
    paths = simulate_gbm_paths(49, 0.13, 0.2, time, 80, count, rng=np.random.default_rng(1904))
    initial = greeks.sold_option_valuation(49, 50, 0.05, 0.2, time, 1, 0)["unit_value"]
    performances = []
    for steps, printed in zip(
        [4, 5, 10, 20, 40, 80], [0.42, 0.38, 0.28, 0.21, 0.16, 0.13], strict=True
    ):
        coarse = paths[:, :: 80 // steps]
        times = np.linspace(0, time, steps + 1)
        holdings = greeks.delta_holdings(coarse, times, 50, 0.05, 0.2)
        replay = greeks.hedge_cash_replay(coarse, times, 50, 0.05, holdings)
        costs = replay["no_interest_cost"]
        sd = costs.std(ddof=1)
        se = ((costs - costs.mean()) ** 2).std(ddof=1) / (2 * sd * math.sqrt(count))
        ratio = sd / initial
        assert abs(ratio - printed) <= 6 * se / initial + 0.005
        performances.append(ratio)
        independent = np.maximum(coarse[:, -1] - 50, 0) - np.sum(
            holdings * np.diff(coarse, axis=1), axis=1
        )
        assert costs == pytest.approx(independent, abs=1e-11)
    assert np.all(np.diff(performances) < 0)


def test_delta_holdings_zero_volatility_limit_and_invalid_maturity_grid():
    assert greeks.delta_holdings([[40, 50, 60]], [0, 0.1, 0.2], 50, 0, 0) == pytest.approx(
        np.array([[0, 0.5]])
    )
    with pytest.raises(ValueError):
        greeks.delta_holdings([[49, 50]], [0, -1], 50, 0.05, 0.2)


def test_zero_volatility_delta_uses_the_forward_with_positive_rate():
    # S=49.5 < K=50 today, but the forward 49.5*exp(.05*.3846) > 50, so delta is 1.
    assert greeks.delta_holdings([[49.5, 49.5]], [0, .3846], 50, .05, 0) == pytest.approx(np.array([[1.0]]))
