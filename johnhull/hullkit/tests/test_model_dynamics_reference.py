"""Independent PDE and Heston integration checks for research RB-F04."""

import importlib.util
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

REFERENCE_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "RB-F04" / "reference_methods.py"
)


def _reference():
    assert REFERENCE_PATH.is_file(), "RB-F04 independent numerical reference is not implemented"
    spec = importlib.util.spec_from_file_location("rb_f04_reference", REFERENCE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _black_call(spot, strikes, expiry, integrated_variance, rate, q):
    """Own analytic expectation for a lognormal terminal stock, using math.erf."""
    strikes = np.asarray(strikes, dtype=float)
    if integrated_variance == 0.0:
        return np.maximum(spot * math.exp(-q * expiry) - strikes * math.exp(-rate * expiry), 0)
    width = math.sqrt(integrated_variance)
    result = []
    for strike in strikes:
        d1 = (math.log(spot / strike) + (rate - q) * expiry + integrated_variance / 2) / width
        d2 = d1 - width
        cdf1 = (1 + math.erf(d1 / math.sqrt(2))) / 2
        cdf2 = (1 + math.erf(d2 / math.sqrt(2))) / 2
        result.append(
            spot * math.exp(-q * expiry) * cdf1 - strike * math.exp(-rate * expiry) * cdf2
        )
    return np.array(result)


def _constant_variance(value, status="interior"):
    def evaluate(t, spots):
        return {
            "variance": np.full_like(spots, value),
            "status": np.full(spots.shape, status),
        }

    return evaluate


def test_pde_prices_lognormal_calls_with_dividends():
    reference = _reference()
    # Dropping q in the PDE drift or upper boundary breaks this analytic check.
    strikes = np.array([80.0, 100.0, 120.0])
    result = reference.pde_call(100.0, strikes, 1.0, _constant_variance(0.04), 0.03, 0.02)
    expected = _black_call(100.0, strikes, 1.0, 0.04, 0.03, 0.02)
    np.testing.assert_allclose(result["price"], expected, atol=0.003, rtol=0)
    assert result["supported"]
    assert result["failure"] is None
    assert result["status_counts"]["interior"] > 0
    assert result["grid"]["space_nodes"] == 601
    values = result["grid"]["values"]
    np.testing.assert_array_equal(values[:, 0], 0.0)
    np.testing.assert_allclose(
        values[:, -1],
        result["grid"]["spots"][-1] * math.exp(-0.02) - strikes * math.exp(-0.03),
        atol=1e-12,
    )


def test_pde_calendar_variance_and_positive_midpoints():
    reference = _reference()
    # Using backward time as calendar time changes the cubic term structure.
    visited = []

    def variance(t, spots):
        assert 0.0 < t < 1.0
        visited.append(t)
        return {
            "variance": np.full_like(spots, 0.02 + 0.08 * t**3),
            "status": np.full(spots.shape, "early_time" if t < 0.01 else "interior"),
        }

    result = reference.pde_call(100.0, [90.0, 100.0, 110.0], 1.0, variance, 0.03, 0.01)
    expected = _black_call(100.0, [90.0, 100.0, 110.0], 1.0, 0.04, 0.03, 0.01)
    np.testing.assert_allclose(result["price"], expected, atol=0.003, rtol=0)
    assert visited[0] == pytest.approx(1 - 1 / (4 * 384))
    assert visited[1] == pytest.approx(1 - 3 / (4 * 384))
    assert min(visited) == pytest.approx(1 / (2 * 384))
    assert result["grid"]["min_calendar_time"] == pytest.approx(min(visited))
    assert result["grid"]["rannacher_half_steps"] == 2
    assert result["status_counts"]["early_time"] > 0


@pytest.mark.parametrize(
    ("value", "status", "failure"),
    [
        (-0.04, "interior", "negative_variance"),
        (float("nan"), "interior", "nonfinite_variance"),
        (0.04, "unsupported_time", "unsupported_variance"),
    ],
)
def test_pde_preserves_failed_coefficients(value, status, failure):
    reference = _reference()
    result = reference.pde_call(
        100.0, [90.0, 100.0], 1.0, _constant_variance(value, status), 0.03, 0.0
    )
    assert not result["supported"]
    assert result["failure"] == failure
    assert np.isnan(result["price"]).all()
    assert result["status_counts"][status] > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"space_nodes": 4},
        {"time_steps": 0},
        {"log_half_width": 0.0},
        {"spot": 0.0},
        {"T": 0.0},
        {"strikes": [float("nan")]},
    ],
)
def test_pde_rejects_invalid_grid_and_market(kwargs):
    reference = _reference()
    args = {
        "spot": 100.0,
        "strikes": [100.0],
        "T": 1.0,
        "variance": _constant_variance(0.04),
        "rate": 0.03,
        "q": 0.01,
    }
    args.update(kwargs)
    with pytest.raises(ValueError):
        reference.pde_call(**args)


def _heston_parameters(**changes):
    parameters = {
        "spot": 100.0,
        "rate": 0.03,
        "dividend_yield": 0.02,
        "v0": 0.04,
        "kappa": 2.0,
        "theta": 0.04,
        "xi": 0.3,
        "rho": -0.7,
    }
    return parameters | changes


def test_independent_heston_integral_matches_cos_and_separate_cutoffs():
    # A sign error in either Gil-Pelaez exercise probability changes these prices.
    from hullkit._heston_local_surface import HestonParameters, fourier_surface
    from hullkit.stochastic_volatility import heston_price

    reference = _reference()
    parameters = _heston_parameters()
    strikes = np.array([80.0, 90.0, 100.0, 110.0, 120.0])
    coarse = reference.independent_heston_call(strikes, 1.0, parameters, upper=250)
    fine = reference.independent_heston_call(strikes, 1.0, parameters, upper=500)
    cos = [
        heston_price(100.0, k, 0.03, 1.0, 0.04, 2.0, 0.04, 0.3, -0.7, dividend_yield=0.02)
        for k in strikes
    ]
    np.testing.assert_allclose(coarse, cos, atol=1e-8, rtol=0)
    np.testing.assert_allclose(fine, coarse, atol=1e-9, rtol=0)
    surface = fourier_surface(strikes, 1.0, HestonParameters(**parameters))
    np.testing.assert_allclose(surface["price"], fine, atol=1e-8, rtol=0)


def test_independent_heston_deterministic_variance_matches_own_black_formula():
    # xi=0 with v0!=theta must integrate mean reversion, rather than freeze v0.
    from types import SimpleNamespace

    reference = _reference()
    parameters = _heston_parameters(v0=0.09, theta=0.02, xi=0.0)
    integrated = 0.02 + (0.09 - 0.02) * (1 - math.exp(-2.0)) / 2.0
    expected = _black_call(100.0, [80.0, 100.0, 120.0], 1.0, integrated, 0.03, 0.02)
    prices = reference.independent_heston_call(
        [80.0, 100.0, 120.0], 1.0, SimpleNamespace(**parameters)
    )
    np.testing.assert_allclose(prices, expected, atol=1e-10, rtol=0)


@pytest.mark.parametrize(
    ("changes", "integrated"),
    [
        ({"kappa": 0.0, "xi": 0.0, "v0": 0.09}, 0.09),
        ({"v0": 0.0, "theta": 0.0, "xi": 0.0}, 0.0),
    ],
)
def test_independent_heston_degenerate_variance_limits(changes, integrated):
    reference = _reference()
    prices = reference.independent_heston_call([90.0, 110.0], 1.0, _heston_parameters(**changes))
    np.testing.assert_allclose(
        prices, _black_call(100.0, [90.0, 110.0], 1.0, integrated, 0.03, 0.02), atol=1e-10, rtol=0
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"spot": 0.0},
        {"xi": -0.1},
        {"rho": 1.1},
        {"v0": float("nan")},
        {"kappa": -1.0},
        {"theta": -0.1},
    ],
)
def test_independent_heston_rejects_invalid_parameters(changes):
    reference = _reference()
    with pytest.raises(ValueError):
        reference.independent_heston_call([100.0], 1.0, _heston_parameters(**changes))


@pytest.mark.parametrize(
    "T, upper, strikes", [(0.0, 250, [100]), (1.0, 0.0, [100]), (1.0, 250, [-1])]
)
def test_independent_heston_rejects_invalid_integral(T, upper, strikes):
    reference = _reference()
    with pytest.raises(ValueError):
        reference.independent_heston_call(strikes, T, _heston_parameters(), upper=upper)


def test_pde_spatial_refinement_at_fixed_time_and_domain():
    # A missing dx squared in diffusion prevents second-order spatial convergence.
    reference = _reference()
    expected = _black_call(100.0, [100.0], 1.0, 0.04, 0.03, 0.02)[0]
    errors = []
    for nodes in (101, 201, 401, 801):
        result = reference.pde_call(
            100.0,
            [100.0],
            1.0,
            _constant_variance(0.04),
            0.03,
            0.02,
            space_nodes=nodes,
            time_steps=768,
            log_half_width=1.5,
        )
        errors.append(abs(result["price"][0] - expected))
    assert all(fine < 0.3 * coarse for coarse, fine in pairwise(errors))
    assert errors[-1] < 0.0004


def test_pde_time_refinement_at_fixed_space_and_domain():
    # Omitting the two implicit half steps leaves the payoff kink undamped.
    reference = _reference()
    expected = _black_call(100.0, [100.0], 1.0, 0.04, 0.03, 0.02)[0]

    def variance(t, spots):
        return {"variance": np.full_like(spots, 0.02 + 0.08 * t**3), "status": "interior"}

    errors = []
    for steps in (12, 24, 48, 96):
        result = reference.pde_call(
            100.0,
            [100.0],
            1.0,
            variance,
            0.03,
            0.02,
            space_nodes=1201,
            time_steps=steps,
            log_half_width=1.5,
        )
        errors.append(abs(result["price"][0] - expected))
    assert all(fine < 0.35 * coarse for coarse, fine in pairwise(errors))
    assert errors[-1] < 0.0006


def test_pde_domain_refinement_preserves_dx_and_time_steps():
    # The lower boundary at a narrow domain loses the call's remaining time value.
    reference = _reference()
    expected = _black_call(100.0, [100.0], 1.0, 0.04, 0.03, 0.02)[0]
    errors = []
    for width, nodes in ((0.2, 161), (0.4, 321), (0.8, 641)):
        result = reference.pde_call(
            100.0,
            [100.0],
            1.0,
            _constant_variance(0.04),
            0.03,
            0.02,
            space_nodes=nodes,
            time_steps=768,
            log_half_width=width,
        )
        assert np.diff(result["grid"]["log_spots"]) == pytest.approx(np.full(nodes - 1, 0.0025))
        errors.append(abs(result["price"][0] - expected))
    assert errors[0] > 0.1
    assert errors[1] < errors[0] / 100
    assert errors[2] < errors[1]
    assert errors[-1] < 0.0002


@pytest.mark.parametrize(
    ("T", "strikes"),
    [
        (0.25, [80.0, 90.0, 100.0, 110.0, 120.0]),
        (0.5, [80.0, 90.0, 100.0, 110.0, 120.0]),
        (0.75, [80.0, 90.0, 100.0, 110.0, 120.0]),
        (1.0, [80.0, 90.0, 100.0, 110.0, 120.0]),
        (1 / 3, [85.0, 95.0, 105.0, 115.0]),
        (2 / 3, [85.0, 95.0, 105.0, 115.0]),
    ],
)
def test_candidate_quotes_and_holdouts_match_independent_integral(T, strikes):
    from hullkit._heston_local_surface import HestonParameters, fourier_surface
    from hullkit.stochastic_volatility import heston_price

    reference = _reference()
    parameters = _heston_parameters(dividend_yield=0.0)
    coarse = reference.independent_heston_call(strikes, T, parameters, upper=250)
    fine = reference.independent_heston_call(strikes, T, parameters, upper=500)
    cos = [heston_price(100.0, k, 0.03, T, 0.04, 2.0, 0.04, 0.3, -0.7) for k in strikes]
    np.testing.assert_allclose(coarse, fine, atol=1e-8, rtol=0)
    np.testing.assert_allclose(fine, cos, atol=1e-8, rtol=0)
    surface = fourier_surface(strikes, T, HestonParameters(**parameters))
    assert surface["supported"].all()
    np.testing.assert_allclose(surface["price"], fine, atol=1e-8, rtol=0)


@pytest.mark.parametrize(
    ("strike", "rate", "q", "reason"),
    [
        (150.0, 0.03, 0.0, "upper_boundary"),
        (80.0, 0.03, 0.0, "lower_boundary"),
        (110.0, 0.0, 0.3, "upper_boundary"),
        (90.0, 0.3, 0.0, "lower_boundary"),
    ],
)
def test_pde_rejects_domains_that_break_call_boundary_assumptions(strike, rate, q, reason):
    # A finite log domain must keep the upper call boundary ITM and the lower OTM.
    reference = _reference()

    def variance(t, spots):
        pytest.fail("unsupported domain must be detected before variance is evaluated")

    result = reference.pde_call(100.0, [strike], 1.0, variance, rate, q, log_half_width=0.2)
    assert not result["supported"]
    assert result["failure"] == "unsupported_domain"
    assert np.isnan(result["price"]).all()
    assert result["status_counts"] == {"unsupported_domain": 1}
    assert result["grid"]["domain_failure"] == reason
    assert result["grid"]["coefficient_evaluations"] == 0
    assert np.isnan(result["grid"]["min_calendar_time"])
    assert np.isnan(result["grid"]["max_calendar_time"])
    assert result["grid"]["backward_time_completed"] == 0


@pytest.mark.parametrize("width,nodes", [(1.5, 601), (3.0, 1201)])
def test_pde_pilot_domains_remain_supported_and_match_black(width, nodes):
    reference = _reference()
    strikes = [80.0, 90.0, 100.0, 110.0, 120.0]
    result = reference.pde_call(
        100.0,
        strikes,
        1.0,
        _constant_variance(0.04),
        0.03,
        0.0,
        space_nodes=nodes,
        log_half_width=width,
    )
    assert result["supported"]
    assert result["failure"] is None
    assert "domain_failure" not in result["grid"]
    assert "unsupported_domain" not in result["status_counts"]
    np.testing.assert_allclose(
        result["price"], _black_call(100.0, strikes, 1.0, 0.04, 0.03, 0.0), atol=0.003, rtol=0
    )


def test_pde_unsupported_grid_roundtrips_without_pickle():
    # pilot stores every grid field in NPZ, so None/object diagnostics are invalid.
    from io import BytesIO

    reference = _reference()
    result = reference.pde_call(
        100.0, [150.0], 1.0, _constant_variance(0.04), 0.03, 0.0, log_half_width=0.2
    )
    assert not result["supported"]
    stream = BytesIO()
    np.savez(stream, **result["grid"])
    stream.seek(0)
    with np.load(stream, allow_pickle=False) as archive:
        for key, expected in result["grid"].items():
            actual = archive[key]
            assert actual.dtype.kind != "O"
            if actual.dtype.kind in "biufc":
                np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12, equal_nan=True)
            else:
                np.testing.assert_array_equal(actual, expected)
