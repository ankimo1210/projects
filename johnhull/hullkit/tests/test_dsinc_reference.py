"""Checks of the independently derived two-dimensional obstacle reference."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from hullkit._dsinc_types import PricingFailure, PutContract, VarianceModel
from hullkit.bsm import put_price
from hullkit.trees import crr_price


def _reference():
    path = Path(__file__).resolve().parents[2] / "research" / "DSINC" / "reference_fd.py"
    assert path.is_file(), "missing independent finite-difference reference"
    spec = importlib.util.spec_from_file_location("dsinc_independent_reference", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _model():
    return VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04)


def _config(module, **changes):
    base = module.FDConfig(121, 61, 60, (-1.2, 1.2), (np.log(0.0002), np.log(2)), "european")
    return replace(base, **changes)


def test_fd_generator_from_three_halves_sde():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    x = np.linspace(-0.002, 0.002, 5)
    z = np.log(0.04) + np.linspace(-0.002, 0.002, 5)
    coefficients = ref._sde_coefficients(contract, _model(), z)
    matrix, left, right = ref._assemble_operator(contract, x, z, coefficients)
    function = np.exp(x[:, None] - z[None, :])
    actual = matrix @ function[1:-1].ravel()
    actual[:5] += left @ function[0]
    actual[-5:] += right @ function[-1]
    # Direct Ito generator of S/v, including discount: (-.82 + 38*v)*S/v.
    expected = (-0.82 + 38 * np.exp(z[2])) * function[1:-1, 2]
    np.testing.assert_allclose(actual.reshape(3, 5)[:, 2], expected, rtol=2e-6)


@pytest.mark.parametrize("style", ["european", "american"])
def test_fd_constant_variance_control(style):
    ref = _reference()
    contract = PutContract(1, 1, 0.05, 0)
    config = ref.FDConfig(1001, 5, 400, (-2, 2), (-5, -2), style)
    coefficients = {
        "variance": np.full(5, 0.04),
        "x_drift": np.full(5, 0.03),
        "z_variance": np.zeros(5),
        "z_drift": np.zeros(5),
        "cross": np.zeros(5),
    }
    result = ref._solve_fd(contract, np.array([1.0]), 0.04, config, coefficients)
    wanted = (
        put_price(1, 1, 0.05, 0.2, 1)
        if style == "european"
        else crr_price(1, 1, 0.05, 0.2, 1, 4000, kind="put", american=True)
    )
    assert abs(result.prices[0] - wanted) <= (5e-6 if style == "european" else 2e-5)
    assert result.diagnostics["ordering"] == "z_fast"


def test_fd_obstacle_and_complementarity():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    result = ref.reference_put(
        contract, _model(), np.array([0.9, 1.0, 1.1]), _config(ref, exercise="american")
    )
    diagnostic = result.diagnostics
    assert diagnostic["minimum_payoff_gap"] >= -1e-12
    assert diagnostic["minimum_lambda"] >= 0
    assert diagnostic["max_complementarity"] <= 1e-10
    assert diagnostic["positive_lambda_count"] > 0
    assert diagnostic["positive_time_value_count"] > 0
    assert np.isfinite(diagnostic["max_equation_defect"])
    assert np.all(result.prices >= np.array([0.1, 0, 0]) - 1e-6)


def test_fd_refinement_and_domain_expansion():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    results = [
        ref.reference_put(contract, _model(), np.array([1.0]), _config(ref, n_x=n))
        for n in (61, 121, 241)
    ]
    diagnostic = ref.assess_refinement(results, tolerance=1e-10)
    assert diagnostic["scope"] == "single_axis"
    assert diagnostic["supported"] is False
    assert diagnostic["changes"][1] < diagnostic["changes"][0]
    expanded = ref.reference_put(
        contract, _model(), np.array([1.0]), _config(ref, n_x=241, log_spot_bounds=(-2.4, 2.4))
    )
    assert abs(expanded.prices[0] - results[1].prices[0]) < 2e-4


def test_fd_geometry_mask_and_time_map():
    ref = _reference()
    config = ref.FDConfig(21, 4, 6, (-1, 1), (np.log(0.005), np.log(0.32)), "american")
    contract = PutContract(1, 1, 0.05, 0.02)
    base = ref.FDResult(
        prices=np.array([0.06]),
        x=np.linspace(-1, 1, 21),
        log_variances=np.log([0.005, 0.02, 0.08, 0.32]),
        times=np.linspace(0, 1, 7),
        boundary_brackets=np.tile([-0.3, -0.2], (7, 4, 1)),
        boundary_valid=np.ones((7, 4), dtype=bool),
        diagnostics={},
        config=config,
        contract=contract,
        problem_hash="geometry-fixture",
    )
    times = np.linspace(0, 1, 5)
    z = np.log([0.02, 0.04, 0.08])
    boundary = np.full((5, 3), -0.25)
    comparison = ref.boundary_comparison(times, z, boundary, base)
    assert comparison["target_count"] == 3  # Only t=.5 is common and inside [.1,.9].
    assert comparison["coverage"] == 1
    assert comparison["accepted"] is True
    edge = ref.boundary_comparison(times, z, np.full((5, 3), -0.8), base)
    assert edge["accepted"] is False
    assert edge["reasons"]["near_x_edge"] == 3
    invalid = replace(base, boundary_valid=np.zeros((7, 4), dtype=bool))
    assert ref.boundary_comparison(times, z, boundary, invalid)["coverage"] == 0


def test_fd_time_budget_failure():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    with pytest.raises(PricingFailure) as failure:
        ref.reference_put(contract, _model(), np.array([1.0]), _config(ref), time_limit_seconds=0)
    assert failure.value.code == "time_budget_exceeded"
    assert "prices" not in failure.value.details
    with pytest.raises(PricingFailure) as failure:
        ref.reference_put(
            contract, _model(), np.array([1.0]), _config(ref), memory_limit_bytes=1024
        )
    assert failure.value.code == "memory_budget_exceeded"


def test_unequal_variance_refinement_uses_actual_spacing():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    base = ref.reference_put(contract, _model(), np.array([1.0]), _config(ref))
    results = []
    for n in (101, 151, 201):
        cfg = replace(base.config, n_var=n)
        h = (cfg.log_var_bounds[1] - cfg.log_var_bounds[0]) / (n - 1)
        results.append(replace(base, config=cfg, prices=np.array([0.05 + 0.02 * h**2])))
    assessment = ref.assess_refinement(results)
    np.testing.assert_allclose(assessment["observed_orders"], [2.0], atol=1e-10)
    np.testing.assert_allclose(assessment["second_order_extrapolations"], [0.05], atol=1e-13)


def test_contact_brackets_require_multiplier_and_contiguous_contact():
    ref = _reference()
    x = np.linspace(-1, 1, 9)
    payoff = np.maximum(1 - np.exp(x[1:-1, None]), 0) * np.ones((1, 2))
    value = payoff.copy()
    value[2:] += 0.01
    multiplier = np.zeros_like(value)
    multiplier[:2] = 0.03
    brackets, valid = ref._boundary_brackets(value, multiplier, payoff, x, 1)
    np.testing.assert_array_equal(valid, [True, True])
    np.testing.assert_allclose(brackets, np.tile(x[2:4], (2, 1)))
    multiplier[1, 1] = 0  # A hole before later contact is not a valid frontier.
    multiplier[2, 1] = 0.03
    value[2, 1] = payoff[2, 1]
    assert not ref._boundary_brackets(value, multiplier, payoff, x, 1)[1][1]


def test_reference_rejects_extrapolation_and_handles_expiry():
    ref = _reference()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    with pytest.raises(ValueError):
        ref.reference_put(contract, _model(), np.array([10.0]), _config(ref))
    with pytest.raises(ValueError):
        ref.reference_put(contract, replace(_model(), kind="heston"), np.array([1.0]), _config(ref))
    result = ref.reference_put(
        replace(contract, expiry=0), _model(), np.array([1.25, 0.75]), _config(ref)
    )
    np.testing.assert_array_equal(result.prices, [0.0, 0.25])
