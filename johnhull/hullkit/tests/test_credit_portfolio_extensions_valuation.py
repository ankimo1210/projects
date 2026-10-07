"""Hull §25.10 all printed cells, direct-default-time MC, and constrained loss interpolation."""

import math

import numpy as np
import pytest
from hullkit import _credit_portfolio_extensions as e
from hullkit import cds
from hullkit import credit_portfolio as cp


@pytest.fixture(scope="module")
def mezz():
    hazard = cds.implied_hazard(0.005, 0.4, 0.035, 5, freq=4)
    return hazard, e.cdo_valuation_table(hazard, 0.4, 0.035, 5, 0.03, 0.06, 125, 0.15)


def test_all_75_example_25_2_and_table_25_7_values(mezz):
    hazard, table = mezz
    val = table["valuation"]
    assert hazard == pytest.approx(0.0083, abs=0.00005)
    assert table["default_boundaries"] == pytest.approx([6.25, 12.5])
    columns = [np.argmin(abs(val.factor_nodes - x)) for x in [0.2020, -0.2020, -0.6060, -1.0104]]
    assert val.factor_nodes[columns] == pytest.approx(
        [0.2020, -0.2020, -0.6060, -1.0104], abs=0.00005
    )
    assert val.factor_weights[columns] == pytest.approx(
        [0.1579, 0.1579, 0.1342, 0.0969], abs=0.00005
    )
    for row, expected in [
        (1, [1, 1, 1, 1]),
        (19, [0.9953, 0.9687, 0.8636, 0.6134]),
        (20, [0.9936, 0.9600, 0.8364, 0.5648]),
    ]:
        assert val.expected_principal[columns, row] == pytest.approx(expected, abs=0.00005)
    expected_rows = {
        "annuity_rows": [
            [0.2478] * 4,
            [0.2107, 0.2051, 0.1828, 0.1299],
            [0.2085, 0.2015, 0.1755, 0.1185],
        ],
        "accrual_rows": [
            [0] * 4,
            [0.0001, 0.0008, 0.0026, 0.0051],
            [0.0002, 0.0009, 0.0029, 0.0051],
        ],
        "protection_rows": [
            [0] * 4,
            [0.0011, 0.0062, 0.0211, 0.0412],
            [0.0014, 0.0074, 0.0230, 0.0410],
        ],
    }
    for key, rows in expected_rows.items():
        for row, expected in zip([0, 18, 19], rows, strict=True):
            assert table[key][columns, row] == pytest.approx(expected, abs=0.00005)
    assert val.annuity_by_factor[columns] == pytest.approx(
        [4.5624, 4.5345, 4.4080, 4.0361], abs=0.00005
    )
    assert val.accrual_by_factor[columns] == pytest.approx(
        [0.0007, 0.0043, 0.0178, 0.0478], abs=0.00005
    )
    assert val.protection_by_factor[columns] == pytest.approx(
        [0.0055, 0.0346, 0.1423, 0.3823], abs=0.00005
    )
    assert [val.annuity, val.accrual, val.protection] == pytest.approx(
        [4.2846, 0.0187, 0.1496], abs=0.00005
    )
    assert val.spread * 10000 == pytest.approx(348, abs=0.5)


def test_all_27_example_25_3_values():
    table = e.kth_valuation_table(3, 10, 0.02, 0.4, 0.05, 5, 0.3, frequency=1)
    val = table["valuation"]
    i = np.argmin(abs(val.factor_nodes + 1.0104))
    assert table["marginal_pd"] == pytest.approx(
        [0.0198, 0.0392, 0.0582, 0.0769, 0.0952], abs=0.00005
    )
    assert table["conditional_pd"][i] == pytest.approx(
        [0.0361, 0.0746, 0.1122, 0.1484, 0.1830], abs=0.00005
    )
    assert val.cumulative_prob[i, 1:] == pytest.approx(
        [0.0047, 0.0335, 0.0928, 0.1757, 0.2717], abs=0.00005
    )
    assert table["trigger_probability"][i] == pytest.approx(
        [0.0047, 0.0289, 0.0593, 0.0829, 0.0960], abs=0.00005
    )
    assert [
        val.payoff_by_factor[i],
        val.annuity_by_factor[i],
        val.accrual_by_factor[i],
    ] == pytest.approx([0.1379, 3.8443, 0.1149], abs=0.00005)
    assert [val.payoff, val.annuity, val.accrual] == pytest.approx(
        [0.0629, 4.0580, 0.0524], abs=0.00005
    )
    assert val.spread * 10000 == pytest.approx(153, abs=0.5)


@pytest.fixture(scope="module")
def market():
    bounds = np.array([0, 0.03, 0.06, 0.09, 0.12, 0.22])
    hazard = cds.implied_hazard(0.0023, 0.4, 0.03, 5, freq=4)
    quotes = np.array([0.1034, 41.59e-4, 11.95e-4, 5.60e-4, 2e-4])
    calibration = cp.base_correlations(quotes, bounds, hazard, 0.4, 0.03, 5, 125)
    vals = [
        cp.cdo_tranche_valuation(hazard, 0.4, 0.03, 5, a, b, 125, rho)
        for a, b, rho in zip(bounds[:-1], bounds[1:], calibration.compound, strict=True)
    ]
    # Preserve all standard cashflow curves, not just base-correlation loss PVs.
    losses = np.column_stack(
        [
            np.zeros(21),
            np.cumsum(
                np.column_stack(
                    [
                        (1 - v.factor_weights @ v.expected_principal) * (b - a)
                        for a, b, v in zip(bounds[:-1], bounds[1:], vals, strict=True)
                    ]
                ),
                axis=1,
            ),
        ]
    )
    return hazard, quotes, bounds, calibration, vals, losses


def test_table_25_8_all_11_printed_values_at_rounding_precision(market):
    hazard, _, bounds, calibration, _, _ = market
    assert hazard == pytest.approx(0.00382, abs=0.000005)
    assert calibration.compound == pytest.approx(
        np.array([17.7, 7.8, 14, 18.2, 23.3]) / 100, abs=0.0005
    )
    assert calibration.base == pytest.approx(
        np.array([17.7, 28.4, 36.5, 43.2, 60.5]) / 100, abs=0.0005
    )
    derived = cp.expected_loss_curve(bounds[1:], calibration.base, hazard, 0.4, 0.03, 5, 125)
    assert derived == pytest.approx(
        [0.00888861, 0.00946277, 0.00962836, 0.00970601, 0.00979850], abs=5e-9
    )
    result = e.concave_loss_interpolation(bounds, np.r_[0, derived], [0.04, 0.08])
    expected = np.interp([0.04, 0.08], bounds, np.r_[0, derived])
    assert result == pytest.approx(expected)


def test_standard_leg_repricing_and_nonstandard_four_eight_percent(market):
    _, quotes, bounds, _, vals, losses = market
    times = vals[0].payment_times
    for i, (a, b, val) in enumerate(zip(bounds[:-1], bounds[1:], vals, strict=True)):
        result = e.interpolated_tranche_legs(times, bounds, losses, 0.03, a, b)
        assert [result["annuity"], result["accrual"], result["protection"]] == pytest.approx(
            [val.annuity, val.accrual, val.protection], abs=2e-14
        )
        model = (
            result["protection"] - 0.05 * (result["annuity"] + result["accrual"])
            if i == 0
            else result["spread"]
        )
        assert model == pytest.approx(quotes[i], abs=1e-10)
    result = e.interpolated_tranche_legs(times, bounds, losses, 0.03, 0.04, 0.08)
    # Independent replication: 2/3 of 3–6 plus 2/3 of 6–9, rescale to 4% notional.
    reference = np.array([[v.annuity, v.accrual, v.protection] for v in vals[1:3]]).mean(axis=0)
    assert [result["annuity"], result["accrual"], result["protection"]] == pytest.approx(reference)
    assert np.all(np.diff(result["expected_principal"]) <= 1e-12)
    with pytest.raises(ValueError, match="concave"):
        e.concave_loss_interpolation([0, 0.1, 0.2], [0, 0.01, 0.03], [0.15])


def test_direct_gaussian_default_time_mc_independently_reproduces_cdo(mezz):
    hazard, table = mezz
    default_times = e.gaussian_default_times(
        np.full(125, hazard), math.sqrt(0.15), 70_000, seed=2510
    )
    result = e.default_time_legs(
        default_times, 0.4, 0.035, 5, frequency=4, attach=0.03, detach=0.06
    )
    val = table["valuation"]
    for name, exact in [
        ("annuity", val.annuity),
        ("accrual", val.accrual),
        ("protection", val.protection),
        ("spread", val.spread),
    ]:
        assert abs(result[name] - exact) <= 6 * result[name + "_se"]


def test_direct_gaussian_default_time_mc_independently_reproduces_third_default():
    default_times = e.gaussian_default_times(np.full(10, 0.02), math.sqrt(0.3), 140_000, seed=253)
    result = e.default_time_legs(default_times, 0.4, 0.05, 5, frequency=1, k=3)
    val = cp.kth_to_default_valuation(3, 10, 0.02, 0.4, 0.05, 5, 0.3)
    for name, exact in [
        ("annuity", val.annuity),
        ("accrual", val.accrual),
        ("protection", val.payoff),
        ("spread", val.spread),
    ]:
        assert abs(result[name] - exact) <= 6 * result[name + "_se"]


def test_interpolation_excludes_extrapolation_and_increasing_time_losses():
    with pytest.raises(ValueError):
        e.concave_loss_interpolation([0, 0.1], [0, 0.01], [0.2])
    with pytest.raises(ValueError):
        e.interpolated_tranche_legs([1, 2], [0, 1], [[0, 0], [0, 0.1], [0, 0.05]], 0.03, 0, 1)
