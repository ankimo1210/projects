"""Hull22.2 source scenarios, exact tail mass and explicit quantile conventions."""

from decimal import Decimal

import numpy as np
import pytest
from hullkit import _market_risk as market
from scipy.integrate import quad

LEVELS = np.array(
    [
        [5292.90, 8830.23, 16910.33, 322.40],
        [5343.70, 8926.56, 16915.41, 321.24],
        [5354.69, 8982.76, 17065.64, 326.20],
        [5359.66, 8999.31, 17121.67, 328.03],
        [6445.59, 7269.36, 15784.97, 345.40],
        [6496.14, 7255.04, 15540.44, 342.01],
    ]
)
LOSSES = [
    922.484,
    858.423,
    653.541,
    490.215,
    422.291,
    362.733,
    360.532,
    353.788,
    323.505,
    305.216,
    245.151,
    241.561,
    231.269,
    230.626,
    229.683,
]
SCENARIOS = [427, 429, 424, 415, 482, 440, 426, 431, 417, 433, 452, 418, 140, 289, 152]


def test_table_22_3_four_observed_scenarios_and_decimal_cash_ledger():
    printed = [10064.257, 10066.822, 10023.722, 9990.361]
    amounts = np.array([4000, 3000, 1000, 2000])
    for index, expected in zip([0, 1, 2, 4], printed, strict=True):
        result = market.historical_scenarios(
            LEVELS[index : index + 2], current=LEVELS[-1], amounts=amounts
        )
        independent = sum(
            Decimal(str(a)) * Decimal(str(v)) / Decimal(str(old))
            for a, v, old in zip(amounts, LEVELS[index + 1], LEVELS[index], strict=True)
        )
        assert result["values"][0] == pytest.approx(float(independent), abs=1e-9)
        assert result["values"][0] == pytest.approx(expected, abs=0.06)
        assert result["pnl"][0] == pytest.approx(float(independent) - 10000, abs=1e-9)
    # All three source levels are printed to .01; propagate those intervals.
    low = (LEVELS[-1] - 0.005) * (LEVELS[-1] - 0.005) / (LEVELS[-2] + 0.005)
    high = (LEVELS[-1] + 0.005) * (LEVELS[-1] + 0.005) / (LEVELS[-2] - 0.005)
    printed_levels = np.array([6547.09, 7240.75, 15299.71, 338.66])
    assert np.all(printed_levels + 0.005 >= low)
    assert np.all(printed_levels - 0.005 <= high)


def test_table_22_4_rank_pins_and_brw_uses_original_scenario_numbers():
    # Synthetic lower-ranked completion. The known worst ranks determine these tails.
    loss = np.zeros(500)
    loss[np.array(SCENARIOS) - 1] = LOSSES
    plain = market.empirical_risk(-loss)
    assert plain["var"] == pytest.approx(422.291, abs=0.0005)
    assert plain["es"] == pytest.approx(669.391, abs=0.0005)
    weights = market.brw_weights(500, 0.995)
    assert weights[np.array(SCENARIOS[:4]) - 1] == pytest.approx(
        [0.003776, 0.003814, 0.003719, 0.003555], abs=5e-7
    )
    assert weights.sum() == pytest.approx(1, abs=1e-12)
    weighted = market.weighted_tail_risk(loss, weights)
    assert weighted["var"] == pytest.approx(653.541, abs=0.0005)
    assert weighted["es"] == pytest.approx(833.2, abs=0.1)
    assert weights[426] != pytest.approx(0.004833, abs=1e-6)


def test_weighted_es_agrees_with_expanded_integer_multiplicity_distribution():
    loss = np.array([-2, 1, 4, 10])
    multiples = np.array([1, 2, 3, 4])
    weighted = market.weighted_tail_risk(loss, multiples, confidence=0.5)
    expanded = np.repeat(loss, multiples)
    reference = np.sort(expanded)[-5:]
    assert weighted["var"] == pytest.approx(4, abs=1e-12)
    assert weighted["es"] == pytest.approx(reference.mean(), abs=1e-12)
    assert weighted["es"] == pytest.approx(8.8, abs=1e-12)


def test_stressed_250_scenario_midpoint_and_fractional_tail_integral():
    losses = np.r_[10, 8, 6, np.zeros(247)]
    stressed = market.empirical_risk(-losses, var_rule="stressed", es_rule="tail_mass")
    assert stressed["var"] == pytest.approx(7, abs=1e-12)
    assert stressed["es"] == pytest.approx(8.4, abs=1e-12)
    ordered = np.sort(losses)
    integrated = (
        quad(lambda u: ordered[min(int(u * 250), 249)], 0.99, 1, points=[0.992, 0.996])[0] / 0.01
    )
    assert stressed["es"] == pytest.approx(integrated, abs=1e-10)
    assert market.empirical_risk(-losses)["var"] == pytest.approx(6, abs=1e-12)
    assert market.empirical_risk(-losses)["es"] == pytest.approx(8, abs=1e-12)


@pytest.mark.parametrize(
    "rule,expected", [("hull", 496), ("next", 495), ("midpoint", 495.5), ("excel", 495.01)]
)
def test_footnote_2_quantile_rules_are_explicit(rule, expected):
    result = market.empirical_risk(-np.arange(1, 501), var_rule=rule)
    assert result["var"] == pytest.approx(expected, abs=1e-10)
    assert result["tail_rank"] == 5


def test_uniform_brw_limit_rolling_window_and_positive_profit_sign():
    assert market.brw_weights(5, 1) == pytest.approx(np.ones(5) / 5, abs=1e-12)
    first = market.historical_scenarios([[100], [110], [99]])["returns"]
    shifted = market.historical_scenarios([[110], [99], [118.8]])["returns"]
    assert first[:, 0] == pytest.approx([0.1, -0.1], abs=1e-12)
    assert shifted[:, 0] == pytest.approx([-0.1, 0.2], abs=1e-12)
    assert market.empirical_risk(np.arange(1, 11))["var"] < 0
