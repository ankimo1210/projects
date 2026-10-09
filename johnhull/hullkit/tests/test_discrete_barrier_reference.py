"""Independent density/PDE checks for the fixed discrete up-and-out contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy.special import ndtr

HERE = Path(__file__).resolve().parents[2] / "research/RB-F05/discrete"


def reference():
    path = HERE / "reference_methods.py"
    assert path.exists(), "independent discrete-barrier reference is not implemented"
    spec = importlib.util.spec_from_file_location("discrete_barrier_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def closed_one_monitor(spot, maturity):
    """A test-only normal-CDF decomposition, independent of density integration."""
    v = 0.2 * np.sqrt(maturity)
    d1k = (np.log(spot / 100) + 0.05 * maturity) / v
    d1h = (np.log(spot / 120) + 0.05 * maturity) / v
    discount = np.exp(-0.03 * maturity)
    price = spot * (ndtr(d1k) - ndtr(d1h)) - 100 * discount * (ndtr(d1k - v) - ndtr(d1h - v))
    density_h = np.exp(-0.5 * (d1h - v) ** 2) / np.sqrt(2 * np.pi)
    delta = ndtr(d1k) - ndtr(d1h) - 20 * discount * density_h / (spot * v)
    return price, delta


@pytest.mark.parametrize("spot,maturity", [(80.0, 0.25), (100.0, 1.0), (119.0, 2.0)])
def test_one_monitor_density_price_and_fixed_contract_bump_match_cdf_decomposition(spot, maturity):
    result = reference().one_monitor_integral(spot, maturity)
    price, delta = closed_one_monitor(spot, maturity)
    assert result["price"] == pytest.approx(price, abs=1e-9)
    assert result["delta"] == pytest.approx(delta, abs=1e-7)
    assert result["quadrature_price_error"] < 1e-8


def test_one_monitor_bump_width_converges_without_bumping_strike_or_barrier():
    module = reference()
    _, expected = closed_one_monitor(119.0, 0.25)
    wide = module.one_monitor_integral(119.0, 0.25, bump=0.4)
    narrow = module.one_monitor_integral(119.0, 0.25, bump=0.1)
    assert abs(narrow["delta"] - expected) < abs(wide["delta"] - expected)
    assert narrow["delta"] < 0
    assert narrow["delta_bump_difference"] < wide["delta_bump_difference"]


def test_pde_one_monitor_price_and_delta_converge_to_density_integral():
    module = reference()
    spots = np.array([80.0, 100.0, 119.0, 119.999])
    exact = [module.one_monitor_integral(spot, 1.0, bump=1e-5) for spot in spots]
    price = np.array([item["price"] for item in exact])
    delta = np.array([item["delta"] for item in exact])
    coarse = module.pde_reference(spots, 1.0, monitors=1, space_nodes=600, steps_per_monitor=48)
    fine = module.pde_reference(spots, 1.0, monitors=1, space_nodes=1200, steps_per_monitor=192)
    assert np.max(np.abs(fine["price"] - price)) < np.max(np.abs(coarse["price"] - price))
    assert np.max(np.abs(fine["delta"] - delta)) < np.max(np.abs(coarse["delta"] - delta))
    assert fine["price"] == pytest.approx(price, abs=0.002)
    assert fine["delta"] == pytest.approx(delta, abs=0.0005)
    # Values just below H stay positive: t0 kill must be applied to the query,
    # rather than to the interpolation grid before the final query.
    assert fine["price"][-1] > 1.0


def independent_mc(spot, maturity, *, paths=262144, monitors=12):
    """Direct normal paths; price, first-transition LRM and incorrect PW labels."""
    rng = np.random.default_rng(62053)
    z = rng.standard_normal((paths, monitors))
    dt = maturity / monitors
    log_paths = np.log(spot) + np.cumsum(0.01 * dt + 0.2 * np.sqrt(dt) * z, axis=1)
    stock = np.exp(log_paths)
    alive = np.all(stock < 120, axis=1)
    terminal = stock[:, -1]
    discounted = np.exp(-0.03 * maturity) * np.maximum(terminal - 100, 0) * alive
    delta = discounted * z[:, 0] / (spot * 0.2 * np.sqrt(dt))
    pw = np.exp(-0.03 * maturity) * terminal / spot * alive * (terminal > 100)
    return {
        "price": discounted.mean(),
        "price_se": discounted.std(ddof=1) / np.sqrt(paths),
        "delta": delta.mean(),
        "delta_se": delta.std(ddof=1) / np.sqrt(paths),
        "pw": pw.mean(),
    }


def test_twelve_monitor_pde_matches_independent_paths_and_rejects_naive_pw():
    result = reference().pde_reference(
        [100.0, 119.0], 1.0, monitors=12, space_nodes=1200, steps_per_monitor=32
    )
    for index, spot in enumerate((100.0, 119.0)):
        mc = independent_mc(spot, 1.0)
        assert abs(result["price"][index] - mc["price"]) <= 6 * mc["price_se"] + 0.003
        assert abs(result["delta"][index] - mc["delta"]) <= 6 * mc["delta_se"] + 0.001
        if spot == 119.0:
            assert result["delta"][index] < 0 < mc["pw"]
            assert abs(result["delta"][index] - mc["pw"]) > 0.02
    assert np.max(result["x_grid"]) > np.log(120)
    assert result["metadata"]["monitor_times"] == pytest.approx(np.linspace(0, 1, 13))
    assert result["metadata"]["minimum_unclipped_value"] > -1e-8


def test_space_time_and_remote_boundary_refinements_are_separate():
    module = reference()
    query = [80.0, 100.0, 119.0]
    coarse = module.pde_reference(query, 2.0, space_nodes=600, steps_per_monitor=32)
    fine_space = module.pde_reference(query, 2.0, space_nodes=1200, steps_per_monitor=32)
    fine_time = module.pde_reference(query, 2.0, space_nodes=1200, steps_per_monitor=64)
    wider = module.pde_reference(
        query, 2.0, space_nodes=2000, steps_per_monitor=64, log_half_width=2.5
    )
    assert np.max(np.abs(fine_space["price"] - coarse["price"])) < 0.015
    assert np.max(np.abs(fine_time["price"] - fine_space["price"])) < 0.001
    assert np.max(np.abs(fine_time["delta"] - fine_space["delta"])) < 0.0005
    # 1200/1.5 and 2000/2.5 have the same spatial spacing and H phase.
    assert wider["price"] == pytest.approx(fine_time["price"], abs=1e-6)
    assert wider["delta"] == pytest.approx(fine_time["delta"], abs=1e-6)


def test_node_aligned_monitor_jump_bias_reduces_on_refinement_and_midpoint_improves_it():
    module = reference()
    target = module.one_monitor_integral(100.0, 1.0)["price"]
    node_coarse = module.pde_reference(
        100.0, 1.0, monitors=1, space_nodes=400, steps_per_monitor=128, barrier_phase=0.0
    )
    node_fine = module.pde_reference(
        100.0, 1.0, monitors=1, space_nodes=800, steps_per_monitor=128, barrier_phase=0.0
    )
    midpoint = module.pde_reference(
        100.0, 1.0, monitors=1, space_nodes=400, steps_per_monitor=128, barrier_phase=0.5
    )
    assert abs(node_fine["price"] - target) < abs(node_coarse["price"] - target)
    assert abs(midpoint["price"] - target) < abs(node_coarse["price"] - target) / 5


def test_initial_touch_is_zero_and_has_no_ordinary_delta_but_left_limit_stays_positive():
    module = reference()
    result = module.pde_reference(
        [119.999, 120.0, 121.0], 1.0, space_nodes=1000, steps_per_monitor=32
    )
    assert result["price"][0] > 0.1
    assert result["price"][1:].tolist() == [0.0, 0.0]
    assert np.isnan(result["delta"][1])
    assert result["delta"][2] == 0.0
    touch = module.one_monitor_integral(120.0, 1.0)
    assert touch["price"] == 0.0 and np.isnan(touch["delta"])


@pytest.mark.parametrize(
    "kwargs", [{"maturity": 0}, {"sigma": 0}, {"barrier": 100}, {"monitors": 0}]
)
def test_mathematically_invalid_pde_inputs_are_rejected(kwargs):
    inputs = {"spot": 100.0, "maturity": 1.0, **kwargs}
    with pytest.raises(ValueError):
        reference().pde_reference(**inputs)
