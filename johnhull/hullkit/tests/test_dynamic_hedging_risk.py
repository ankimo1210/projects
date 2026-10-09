"""Independent algebra and refit checks for private dynamic hedge risk."""

import importlib

import numpy as np
import pytest
from scipy.optimize import brentq


def risk_module():
    """Fail explicitly at RED when the implementation has not been created."""
    name = "hullkit._dynamic_hedging_risk"
    assert importlib.util.find_spec(name) is not None, "dynamic hedge risk is not implemented"
    return importlib.import_module(name)


def test_ift_two_asset_coordinates():
    result = risk_module().quote_positions(0.7, 5.0, 0.6, 10.0)
    assert result["stock"] == pytest.approx(0.4)
    assert result["call"] == pytest.approx(0.5)
    assert result["valid"]
    assert result["status"] == "ok"


def test_quote_ift_matches_independent_nonlinear_quote_and_spot_refits():
    # C = .3 S + S theta^2 + 2 theta^3; V = .01 S^2 + theta S + 3 theta^2.
    # A wrong frozen-theta Delta fails the fully re-fitted spot comparison.
    risk = risk_module()
    spot, theta = 100.0, 0.4

    def call(s, state):
        return 0.3 * s + s * state**2 + 2.0 * state**3

    def value(s, state):
        return 0.01 * s**2 + state * s + 3.0 * state**2

    quote = call(spot, theta)

    def refitted_value(s, q):
        state = brentq(lambda z: call(s, z) - q, 0.1, 0.8, xtol=1e-14)
        return value(s, state)

    positions = risk.quote_positions(2.4, 102.4, 0.46, 80.96)
    for step in (0.01, 0.005, 0.0025):
        q_bump = refitted_value(spot, quote + step) - refitted_value(spot, quote - step)
        s_bump = refitted_value(spot + step, quote) - refitted_value(spot - step, quote)
        assert positions["call"] == pytest.approx(q_bump / (2 * step), abs=1e-7)
        assert positions["stock"] == pytest.approx(s_bump / (2 * step), abs=1e-7)


def test_quote_positions_are_invariant_under_log_state_coordinates():
    risk = risk_module()
    physical = risk.quote_positions([0.7, 2.4], [5.0, 102.4], [0.6, 0.46], [10.0, 80.96])
    logstate = risk.quote_positions(
        [0.7, 2.4],
        np.array([5.0, 102.4]) * [0.04, 0.4],
        [0.6, 0.46],
        np.array([10.0, 80.96]) * [0.04, 0.4],
    )
    assert logstate["stock"] == pytest.approx(physical["stock"])
    assert logstate["call"] == pytest.approx(physical["call"])


def test_quote_positions_keep_bad_denominator_unknown_and_raw_error():
    result = risk_module().quote_positions(
        0.7, 5.0, 0.6, [0.0, 0.3, 0.31, np.nan], denominator_error=0.1
    )
    assert result["valid"].tolist() == [False, False, True, False]
    assert np.isnan(result["stock"][[0, 1, 3]]).all()
    assert np.isnan(result["call"][[0, 1, 3]]).all()
    assert result["status"].tolist() == ["unknown", "unknown", "ok", "unknown"]
    assert result["denominator"][:3] == pytest.approx([0.0, 0.3, 0.31])
    assert result["denominator_error"] == pytest.approx(np.full(4, 0.1))


def test_stock_only_uses_minimum_variance_projection_including_heston_correlation():
    risk = risk_module()
    positions = risk.quote_positions(0.7, 5.0, 0.6, 10.0)
    heston = risk.stock_only_target(
        positions, 0.6, 10.0, model="heston", spot=100.0, xi=0.3, rho=-0.7
    )
    local = risk.stock_only_target(positions, 0.6, 10.0, model="local", spot=100.0)
    assert heston == pytest.approx(0.6895)
    assert local == pytest.approx(0.7)


def test_unknown_positions_propagate_to_stock_only():
    risk = risk_module()
    positions = risk.quote_positions(0.7, 5.0, 0.6, 0.0)
    target = risk.stock_only_target(positions, 0.6, 0.0, model="heston", spot=100.0)
    assert np.isnan(target)


def test_heston_covariance_matches_hand_values_and_scales_with_time():
    risk = risk_module()
    result = risk.price_covariance("heston", 100.0, 0.04, 0.6, 10.0, 0.25, xi=0.3, rho=-0.7)
    # Brownian loading rows sqrt(v) * [100, 0] and sqrt(v) * [57.9, 3 sqrt(.51)].
    assert result["covariance"] == pytest.approx(np.array([[100.0, 57.9], [57.9, 33.57]]))
    assert np.linalg.eigvalsh(result["covariance"]).min() > 0
    assert result["rank"] == 2
    doubled = risk.price_covariance("heston", 100.0, 0.04, 0.6, 10.0, 0.5, xi=0.3, rho=-0.7)
    assert doubled["covariance"] == pytest.approx(2 * result["covariance"])


def test_local_covariance_has_multiplier_and_rank_one_without_ridge():
    risk = risk_module()
    local = risk.price_covariance("local", 100.0, 1.5, 0.6, 99.0, 0.25, base_variance=0.04)
    deterministic_heston = risk.price_covariance("heston", 100.0, 0.06, 0.6, 99.0, 0.25)
    assert local["covariance"] == pytest.approx(np.array([[150.0, 90.0], [90.0, 54.0]]))
    assert local["covariance"] == pytest.approx(deterministic_heston["covariance"])
    assert local["rank"] == 1
    assert np.linalg.det(local["covariance"]) == pytest.approx(0.0, abs=1e-11)


def test_covariance_broadcasts_and_marks_nonfinite_states_unknown():
    result = risk_module().price_covariance(
        "heston", [100.0, 100.0], [0.04, np.nan], 0.6, 10.0, 0.0
    )
    assert result["covariance"][0] == pytest.approx(np.zeros((2, 2)))
    assert result["rank"][0] == 0
    assert result["valid"].tolist() == [True, False]
    assert np.isnan(result["covariance"][1]).all()


@pytest.mark.parametrize("kwargs", [{"state": -0.1}, {"rho": 1.1}, {"xi": -0.1}, {"dt": -0.1}])
def test_covariance_rejects_impossible_diffusion_parameters(kwargs):
    inputs = dict(model="heston", spot=100.0, state=0.04, c_s=0.6, c_theta=10.0, dt=0.25)
    inputs.update(kwargs)
    with pytest.raises(ValueError):
        risk_module().price_covariance(**inputs)


def test_band_rank_one_no_costly_null_trade():
    old = np.array([[0.0, 0.0]])
    result = risk_module().band_holdings(old, [[1.0, -2.0]], [[[1.0, 0.5], [0.5, 0.25]]], 0.01)
    assert result["holdings"] == pytest.approx(old)
    assert result["sd"] == pytest.approx([0.0])


def test_band_width_and_zero_width_follow_covariance_geometry():
    risk = risk_module()
    old, target = [[0.0, 0.0]], [[0.6, 0.8]]
    interior = risk.band_holdings(old, target, np.eye(2), 0.25)
    assert interior["sd"] == pytest.approx([1.0])
    assert interior["holdings"] == pytest.approx(np.array([[0.45, 0.6]]))
    assert risk.band_holdings(old, target, np.eye(2), 1.0)["holdings"] == pytest.approx(
        np.array(old)
    )
    assert risk.band_holdings(old, target, np.eye(2), 0.0)["holdings"] == pytest.approx(
        np.array(target)
    )
    assert risk.band_holdings(old, target, np.zeros((2, 2)), 0.0)["holdings"] == pytest.approx(
        np.array(old)
    )


def test_band_saves_raw_targets_and_raw_holdings_before_legal_constraint():
    result = risk_module().band_holdings([[0.0, 0.0]], [[3.0, -4.0]], np.eye(2), 0.0)
    assert result["raw_target"] == pytest.approx(np.array([[3.0, -4.0]]))
    assert result["raw_holdings"] == pytest.approx(np.array([[3.0, -4.0]]))
    assert result["holdings"] == pytest.approx(np.array([[2.0, -2.0]]))
    assert result["constrained"].tolist() == [[True, True]]
    assert result["constraint_count"] == 2


def test_band_unknown_does_not_fallback_to_old_or_zero():
    result = risk_module().band_holdings([[1.0]], [[np.nan]], [[[1.0]]], 0.1)
    assert result["status"].tolist() == ["unknown"]
    assert np.isnan(result["holdings"]).all()
    assert np.isnan(result["raw_target"]).all()


def test_band_rejects_indefinite_covariance_and_negative_width():
    risk = risk_module()
    with pytest.raises(ValueError):
        risk.band_holdings([0.0, 0.0], [1.0, 1.0], [[1.0, 2.0], [2.0, 1.0]], 0.1)
    with pytest.raises(ValueError):
        risk.band_holdings([0.0], [1.0], [[1.0]], -0.1)


def test_improvement_scores_preserve_random_baseline_paired_uncertainty():
    result = risk_module().improvement_scores([1.0, 100.0], [0.95, 95.0])
    assert result["d"] == pytest.approx([-0.05, -5.0])
    assert result["r"] == pytest.approx([0.0, 0.0])
    assert result["absolute"] == pytest.approx(result["d"])
    assert result["relative"] == pytest.approx(result["r"])
    assert result["r_se"] == pytest.approx(0.0, abs=1e-14)
    assert result["d_mean"] == pytest.approx(-2.525)
    assert result["d_se"] == pytest.approx(2.475)
    assert result["original_count"] == 2


def test_improvement_unknown_keeps_original_n_and_nan_scores():
    result = risk_module().improvement_scores([1.0, 4.0, 9.0], [0.9, np.nan, 8.0])
    assert result["original_count"] == 3
    assert result["valid_count"] == 2
    assert result["invalid_count"] == 1
    assert result["status"] == "unknown"
    assert result["d"].shape == (3,)
    assert np.isnan(result["d"][1])
    assert np.isnan(result["d_mean"])
    assert np.isnan(result["r_se"])


def test_improvement_requires_original_pairs_and_nonnegative_squared_losses():
    risk = risk_module()
    with pytest.raises(ValueError):
        risk.improvement_scores([1.0, 2.0], [1.0])
    with pytest.raises(ValueError):
        risk.improvement_scores([1.0, -1.0], [0.9, 1.0])


def test_local_diffusion_null_band_survives_quadratic_roundoff():
    from hullkit._dynamic_hedging_risk import band_holdings, price_covariance

    cov = price_covariance("local", 100.0, 1.0, 0.6, 0.0, 1 / 12, base_variance=0.04)["covariance"]
    old, target = np.array([0.0, 0.0]), np.array([-0.6, 1.0])
    out = band_holdings(old, target, cov, 0.01)
    assert out["valid"]
    assert out["holdings"] == pytest.approx(old, abs=1e-13)
    assert out["sd"] == pytest.approx(0.0, abs=1e-13)
    assert out["roundoff_corrected"]
    assert out["roundoff_correction_count"] == 1
    assert out["raw_squared_sd"] >= -out["squared_sd_roundoff_bound"]
