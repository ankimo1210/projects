"""Financial identities and explicit support for the private RB-F04 surface."""

from dataclasses import replace
from importlib import import_module

import numpy as np
import pytest
from hullkit import bsm, heston, stochastic_volatility


def _surface_module():
    return import_module("hullkit._heston_local_surface")


def _parameters(**changes):
    parameters = _surface_module().HestonParameters(
        spot=100.0,
        rate=0.03,
        dividend_yield=0.0,
        v0=0.04,
        kappa=2.0,
        theta=0.04,
        xi=0.3,
        rho=-0.7,
    )
    return replace(parameters, **changes)


def test_zero_vol_of_variance_is_the_exact_constant_variance_bsm_surface():
    parameters = _parameters(xi=0.0, dividend_yield=0.01)
    strikes = np.array([80.0, 100.0, 120.0])
    result = _surface_module().fourier_surface(strikes, 0.75, parameters)
    expected = bsm.call_price(100.0, strikes, 0.03, 0.2, 0.75, 0.01)
    assert result["price"] == pytest.approx(expected, abs=1e-12)
    assert result["local_variance"] == pytest.approx(np.full(3, 0.04), abs=1e-14)
    assert np.all(result["supported"])


def test_deterministic_mean_reverting_variance_uses_terminal_variance():
    parameters = _parameters(xi=0.0, v0=0.09, theta=0.04)
    result = _surface_module().fourier_surface([100.0], 0.5, parameters)
    # Integral and terminal value independently evaluated from the ODE solution.
    integrated = 0.04 * 0.5 + 0.05 * (1 - np.exp(-1.0)) / 2
    expected_price = bsm.call_price(100.0, 100.0, 0.03, np.sqrt(integrated / 0.5), 0.5)
    assert parameters.integrated_variance(0.5) == pytest.approx(integrated, abs=1e-15)
    assert result["price"][0] == pytest.approx(expected_price, abs=1e-12)
    assert result["local_variance"][0] == pytest.approx(0.04 + 0.05 * np.exp(-1), abs=1e-14)


def test_fourier_prices_match_existing_cos_with_dividends_and_cf():
    parameters = _parameters(dividend_yield=0.015)
    strikes = np.array([80.0, 100.0, 120.0])
    result = _surface_module().fourier_surface(strikes, 0.75, parameters)
    expected = [
        stochastic_volatility.heston_price(
            100.0, strike, 0.03, 0.75, 0.04, 2.0, 0.04, 0.3, -0.7, 0.015
        )
        for strike in strikes
    ]
    assert result["price"] == pytest.approx(expected, abs=2e-9)
    u = np.array([0.0, 0.1, 1.0, 20.0, 100.0])
    actual, _ = _surface_module()._characteristic_and_time_derivative(u, 0.75, parameters)
    independent = heston.heston_cf(u, 0.015, 0.75, 0.04, 2.0, 0.04, 0.3, -0.7)
    assert actual == pytest.approx(independent, abs=2e-14)


@pytest.mark.parametrize("strike_step,time_step", [(0.1, 5e-4), (0.05, 2.5e-4)])
def test_surface_derivatives_match_two_central_difference_widths(strike_step, time_step):
    parameters = _parameters(dividend_yield=0.01)
    surface = _surface_module().fourier_surface
    strikes = np.array([90.0, 100.0, 110.0])
    result = surface(strikes, 0.5, parameters)
    low_k = surface(strikes - strike_step, 0.5, parameters)["price"]
    high_k = surface(strikes + strike_step, 0.5, parameters)["price"]
    low_t = surface(strikes, 0.5 - time_step, parameters)["price"]
    high_t = surface(strikes, 0.5 + time_step, parameters)["price"]
    assert result["ck"] == pytest.approx((high_k - low_k) / (2 * strike_step), abs=2e-6)
    assert result["ckk"] == pytest.approx(
        (high_k - 2 * result["price"] + low_k) / strike_step**2, abs=2e-7
    )
    assert result["ct"] == pytest.approx((high_t - low_t) / (2 * time_step), abs=2e-6)


def test_riccati_time_derivative_matches_existing_cf_time_difference():
    parameters = _parameters(dividend_yield=0.01)
    u = np.array([0.0, 0.1, 1.0, 10.0, 50.0])
    _, derivative = _surface_module()._characteristic_and_time_derivative(u, 0.5, parameters)
    low = heston.heston_cf(u, 0.02, 0.5 - 1e-5, 0.04, 2.0, 0.04, 0.3, -0.7)
    high = heston.heston_cf(u, 0.02, 0.5 + 1e-5, 0.04, 2.0, 0.04, 0.3, -0.7)
    assert derivative == pytest.approx((high - low) / 2e-5, abs=2e-9)


def test_weighted_characteristic_at_stock_moment_has_the_tilted_variance_mean():
    parameters = _parameters()
    _, _, weighted = _surface_module()._characteristic_terms(np.array([0.0, -1j]), 0.5, parameters)
    tilted_reversion = 2.0 + 0.7 * 0.3
    expected = np.exp(0.03 * 0.5) * (
        0.04 * np.exp(-tilted_reversion * 0.5)
        + 2 * 0.04 * (1 - np.exp(-tilted_reversion * 0.5)) / tilted_reversion
    )
    assert weighted[0] == pytest.approx(0.04, abs=1e-15)
    assert weighted[1] == pytest.approx(expected, abs=1e-15)


def test_stock_moment_removable_singularity_has_zero_tilted_reversion_limit():
    parameters = _parameters(xi=4.0, rho=0.5)
    with np.errstate(all="raise"):
        phi, phi_t, weighted = _surface_module()._characteristic_terms(
            np.array([-1j]), 0.5, parameters
        )
    assert phi[0] == pytest.approx(np.exp(0.015), abs=1e-15)
    assert phi_t[0] == pytest.approx(0.03 * np.exp(0.015), abs=1e-15)
    assert weighted[0] == pytest.approx(np.exp(0.015) * (0.04 + 2 * 0.04 * 0.5), abs=1e-15)


def test_conditional_variance_ratio_equals_dupire_price_derivatives():
    parameters = _parameters(dividend_yield=0.01)
    strikes = np.array([80.0, 90.0, 100.0, 110.0, 120.0])
    result = _surface_module().fourier_surface(strikes, 0.75, parameters)
    numerator = result["ct"] + 0.01 * result["price"] + 0.02 * strikes * result["ck"]
    dupire = 2 * numerator / (strikes**2 * result["ckk"])
    assert result["local_variance"] == pytest.approx(dupire, abs=1e-12)
    assert result["local_variance"] == pytest.approx(
        result["weighted_density"] / result["density"], abs=1e-14
    )


@pytest.mark.parametrize("maturity", [1 / 4096, 0.25, 1.0])
def test_frequency_cutoff_and_order_refine_separately_at_short_times_and_wings(maturity):
    parameters = _parameters()
    z = np.array([-5.0, -3.0, 0.0, 3.0, 5.0])
    strikes = 100 * np.exp(0.03 * maturity + np.sqrt(0.04 * maturity) * z)
    surface = _surface_module().fourier_surface
    base = surface(strikes, maturity, parameters)
    higher_order = surface(strikes, maturity, parameters, order=2048)
    wider = surface(
        strikes, maturity, parameters, order=2048, max_frequency=1024 / np.sqrt(maturity)
    )
    for alternative in (higher_order, wider):
        assert base["price"] == pytest.approx(alternative["price"], abs=2e-8)
        assert base["density"] == pytest.approx(alternative["density"], abs=2e-7)
        jointly_supported = base["supported"] & alternative["supported"]
        assert base["local_variance"][jointly_supported] == pytest.approx(
            alternative["local_variance"][jointly_supported], abs=2e-5
        )


def test_low_density_retains_raw_diagnostics_but_cannot_supply_local_variance():
    result = _surface_module().fourier_surface([1.0, 100.0, 10000.0], 0.25, _parameters())
    assert result["supported"].tolist() == [False, True, False]
    assert np.isnan(result["local_variance"][[0, 2]]).all()
    assert np.isfinite(result["density"]).all()
    assert np.isfinite(result["weighted_density"]).all()


def test_unresolved_frequency_tail_is_unsupported_even_with_positive_density():
    result = _surface_module().fourier_surface([100.0], 0.5, _parameters(), max_frequency=1)
    assert result["density"][0] > 0
    assert not result["supported"][0]
    assert np.isnan(result["local_variance"][0])


@pytest.mark.parametrize(
    "changes",
    [
        {"spot": 0},
        {"v0": -0.01},
        {"kappa": 0},
        {"theta": 0},
        {"xi": -1},
        {"rho": 1},
        {"rate": np.nan},
    ],
)
def test_invalid_parameters_fail_before_numerical_work(changes):
    with pytest.raises(ValueError):
        _parameters(**changes)


@pytest.mark.parametrize(
    "strikes,maturity,options",
    [
        ([0.0], 1.0, {}),
        ([np.nan], 1.0, {}),
        ([100.0], 0.0, {}),
        ([100.0], 1.0, {"order": 1}),
        ([100.0], 1.0, {"order": True}),
        ([100.0], 1.0, {"max_frequency": 0}),
        ([100.0], 1.0, {"density_floor": -1}),
    ],
)
def test_invalid_surface_inputs_raise(strikes, maturity, options):
    with pytest.raises(ValueError):
        _surface_module().fourier_surface(strikes, maturity, _parameters(), **options)


def _grid():
    return _surface_module().LocalVarianceGrid(
        [0.25, 0.75], [-1.0, 0.0, 1.0], [[0.02, 0.04, 0.06], [0.04, 0.06, 0.08]], _parameters()
    )


def test_grid_interpolates_in_standardized_log_spot_and_calendar_time():
    grid = _grid()
    spots = 100 * np.exp(0.03 * 0.5 + np.sqrt(0.04 * 0.5) * np.array([[-0.5], [0.5]]))
    result = grid.evaluate(0.5, spots)
    assert result["variance"] == pytest.approx(np.array([[0.04], [0.06]]), abs=1e-14)
    assert result["status"].tolist() == [["interior"], ["interior"]]


def test_grid_marks_constant_edge_wings_and_minimum_time_proxy():
    grid = _grid()
    spots = 100 * np.exp(0.03 * 0.25 + np.sqrt(0.04 * 0.25) * np.array([-2.0, 0.0, 2.0]))
    result = grid.evaluate(0.1, spots)
    assert result["variance"] == pytest.approx([0.02, 0.04, 0.06], abs=1e-14)
    assert result["status"].tolist() == [
        "early_time_wing_left",
        "early_time",
        "early_time_wing_right",
    ]
    ordinary = grid.evaluate(0.25, spots)
    assert ordinary["status"].tolist() == ["wing_left", "interior", "wing_right"]


def test_time_zero_defines_only_the_given_initial_state():
    result = _grid().evaluate(0, [100.0, 100.0001, 0.0])
    assert result["variance"][0] == 0.04
    assert np.isnan(result["variance"][[1, 2]]).all()
    assert result["status"].tolist() == [
        "initial_state",
        "unsupported_initial_state",
        "unsupported_spot",
    ]


def test_grid_retains_unsupported_time_and_invalid_spots_as_nan():
    beyond = _grid().evaluate(0.8, [90.0, 100.0])
    assert np.isnan(beyond["variance"]).all()
    assert beyond["status"].tolist() == ["unsupported_time", "unsupported_time"]
    invalid = _grid().evaluate(0.5, [0.0, np.nan, np.inf, -1.0])
    assert np.isnan(invalid["variance"]).all()
    assert invalid["status"].tolist() == ["unsupported_spot"] * 4


def test_grid_supports_scalar_spots_without_losing_output_shape():
    result = _grid().evaluate(0, 100.0)
    assert result["variance"].shape == ()
    assert result["status"].shape == ()
    assert result["variance"].item() == 0.04


@pytest.mark.parametrize(
    "times,z,values",
    [
        ([0, 1], [-1, 1], [[0.04] * 2] * 2),
        ([1, 0.5], [-1, 1], [[0.04] * 2] * 2),
        ([0.5, 1], [1, -1], [[0.04] * 2] * 2),
        ([0.5, 1], [-1, 1], [[0.04], [0.04]]),
        ([0.5, 1], [-1, 1], [[0.04, 0], [0.04, 0.04]]),
        ([0.5, 1], [-1, 1], [[0.04, np.nan], [0.04, 0.04]]),
    ],
)
def test_grid_rejects_invalid_axes_or_nonpositive_unsupported_values(times, z, values):
    with pytest.raises(ValueError):
        _surface_module().LocalVarianceGrid(times, z, values, _parameters())


@pytest.mark.parametrize("time", [-0.1, np.nan, np.inf])
def test_grid_rejects_invalid_time(time):
    with pytest.raises(ValueError):
        _grid().evaluate(time, [100.0])


def test_row_wing_boundaries_preserve_nan_cells_and_extend_each_row_before_time_interpolation():
    values = np.array([[0.02, 0.04, 0.06, np.nan], [np.nan, 0.06, 0.08, 0.10]])
    grid = _surface_module().LocalVarianceGrid(
        [0.25, 0.75],
        [-1.0, 0.0, 1.0, 2.0],
        values,
        _parameters(),
        wing_boundaries=[[0, 2], [1, 3]],
    )
    z = np.array([-0.5, 0.5, 1.5])
    spots = 100 * np.exp(0.03 * 0.5 + np.sqrt(0.04 * 0.5) * z)
    result = grid.evaluate(0.5, spots)
    assert result["variance"] == pytest.approx([0.045, 0.060, 0.075], abs=1e-14)
    assert result["status"].tolist() == ["wing_left", "interior", "wing_right"]
    assert np.isnan(grid.values[0, 3]) and np.isnan(grid.values[1, 0])
    assert grid.support_mask.tolist() == [[True, True, True, False], [False, True, True, True]]
    assert grid.wing_boundaries.tolist() == [[0, 2], [1, 3]]
    # An exact grid time uses only that row, without inheriting an inactive row's wing.
    at_first = grid.evaluate(0.25, 100 * np.exp(0.03 * 0.25 - 0.5 * np.sqrt(0.04 * 0.25)))
    assert at_first["status"].item() == "interior"


@pytest.mark.parametrize(
    "values,bounds",
    [
        ([[np.nan, 0.04, 0.06]], [[0, 2]]),
        ([[0.02, np.nan, 0.06]], [[0, 2]]),
        ([[0.02, 0.04, 0.06]], [[0, 0]]),
        ([[0.02, 0.04, 0.06]], [[0.5, 2]]),
        ([[0.02, 0.04, 0.06]], [[0, 3]]),
    ],
)
def test_explicit_support_bounds_reject_holes_single_points_or_missing_nodes(values, bounds):
    with pytest.raises(ValueError):
        _surface_module().LocalVarianceGrid(
            [0.25], [-1, 0, 1], values, _parameters(), wing_boundaries=bounds
        )
