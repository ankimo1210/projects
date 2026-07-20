"""Price, volume, liquidity and config tests (spec §21.1)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.config import TRADING_YEAR_SECONDS
from optimal_execution.liquidity import initial_depth, spread_paths, stress_paths
from optimal_execution.price_process import (
    alpha_profile,
    sigma_profile,
    simulate_mid_paths,
    u_shape_factor,
)
from optimal_execution.random import scenario_seeds, stream_rng
from optimal_execution.volume import (
    expected_step_volume,
    simulate_step_volumes,
    volume_weights,
    vwap_weights,
)


def test_config_loads_and_extends(cfg, cfg_default):
    assert cfg.profile == "quick"
    assert cfg.n_decision_steps == 30
    # inherited from default.yaml
    assert cfg.impact.temporary_eta == cfg_default.impact.temporary_eta
    assert cfg.side == "sell" and cfg.sign == 1


def test_config_overrides(cfg):
    buy = cfg.with_overrides({"side": "buy"})
    assert buy.sign == -1 and cfg.sign == 1
    stressed = cfg.with_overrides({"impact": {"resilience_rho": 0.5}})
    assert stressed.impact.resilience_rho == 0.5
    # untouched keys survive the merge
    assert stressed.impact.temporary_eta == cfg.impact.temporary_eta
    assert len(cfg.stress_regimes()) == 6


def test_sigma_units(cfg):
    # sigma_abs recovers the annualized vol
    ann = cfg.sigma_abs * TRADING_YEAR_SECONDS**0.5 / cfg.arrival_price
    assert ann == pytest.approx(cfg.annualized_volatility)


def test_fixed_seed_reproducibility(cfg):
    a = simulate_mid_paths(cfg, stream_rng(cfg.seed, "price"), 16)
    b = simulate_mid_paths(cfg, stream_rng(cfg.seed, "price"), 16)
    c = simulate_mid_paths(cfg, stream_rng(cfg.seed + 1, "price"), 16)
    np.testing.assert_array_equal(a, b)
    assert not np.allclose(a, c)


def test_scenario_seeds_disjoint_and_stable(cfg):
    train = scenario_seeds(cfg.seed, "train", 100)
    test = scenario_seeds(cfg.seed, "test", 100)
    assert len(set(train.tolist()) & set(test.tolist())) == 0
    np.testing.assert_array_equal(train, scenario_seeds(cfg.seed, "train", 100))


def test_mid_paths_shape_and_zero_drift(cfg):
    n = 4000
    paths = simulate_mid_paths(cfg, stream_rng(1, "p"), n)
    assert paths.shape == (n, cfg.n_decision_steps + 1)
    np.testing.assert_allclose(paths[:, 0], cfg.arrival_price)
    # zero drift: terminal mean within 4 standard errors of arrival
    total_sd = cfg.sigma_abs * np.sqrt(cfg.horizon_seconds)
    se = total_sd / np.sqrt(n)
    assert abs(paths[:, -1].mean() - cfg.arrival_price) < 4 * se


def test_volatility_scaling(cfg):
    hi = cfg.with_overrides({"annualized_volatility": 0.40})
    lo_paths = simulate_mid_paths(cfg, stream_rng(2, "p"), 2000)
    hi_paths = simulate_mid_paths(hi, stream_rng(2, "p"), 2000)
    ratio = np.diff(hi_paths, axis=1).std() / np.diff(lo_paths, axis=1).std()
    assert ratio == pytest.approx(2.0, rel=0.05)


def test_u_shape_mean_one():
    u = u_shape_factor(64, 0.5)
    assert u.mean() == pytest.approx(1.0)
    assert u[0] > u[32]  # higher at the open than mid-horizon


def test_sigma_profile_constant_vs_ushape(cfg):
    const = cfg.with_overrides({"vol_profile": "constant"})
    assert np.allclose(sigma_profile(const), cfg.sigma_abs)
    u = sigma_profile(cfg)
    assert u.mean() == pytest.approx(cfg.sigma_abs, rel=1e-9)
    assert u[0] > u[len(u) // 2]


def test_alpha_profile(cfg):
    off = alpha_profile(cfg)
    assert np.allclose(off, 0.0)
    on = cfg.with_overrides({"alpha": {"enabled": True, "drift_bps_per_hour": -30.0}})
    a = alpha_profile(on)
    assert np.all(a < 0) and abs(a[0]) > abs(a[-1])  # decaying adverse drift


def test_volume_profile_normalization(cfg):
    w = volume_weights(cfg)
    assert w.mean() == pytest.approx(1.0)
    ev = expected_step_volume(cfg)
    assert ev.sum() == pytest.approx(cfg.expected_interval_volume, rel=1e-9)
    assert vwap_weights(cfg).sum() == pytest.approx(1.0)
    flat = cfg.with_overrides({"volume_profile": "flat"})
    assert np.allclose(volume_weights(flat), 1.0)


def test_simulated_volumes_positive_mean_one(cfg):
    vols = simulate_step_volumes(cfg, stream_rng(3, "v"), 4000)
    assert vols.shape == (4000, cfg.n_decision_steps)
    assert np.all(vols > 0)
    ev = expected_step_volume(cfg)
    np.testing.assert_allclose(vols.mean(axis=0), ev, rtol=0.05)


def test_spread_positive_and_stress(cfg):
    sp = spread_paths(cfg, stream_rng(4, "s"), 500)
    assert np.all(sp >= cfg.tick_size)
    stressed_cfg = cfg.with_overrides({"liquidity": {"stress_prob_per_step": 0.5}})
    stress = stress_paths(stressed_cfg, stream_rng(5, "z"), 500, cfg.n_decision_steps)
    sp_stress = spread_paths(stressed_cfg, stream_rng(4, "s"), 500, stress=stress)
    assert stress.mean() > 0.3
    assert sp_stress.mean() > sp.mean() * 1.5


def test_depth_positive(cfg):
    d = initial_depth(cfg, stream_rng(6, "d"), size=1000)
    assert np.all(d > 0)
    assert d.mean() == pytest.approx(cfg.liquidity.depth_shares, rel=0.1)


def test_invalid_config_rejected(cfg):
    with pytest.raises(ValueError):
        cfg.with_overrides({"side": "hold"})
    with pytest.raises(ValueError, match="unknown top-level"):
        cfg.with_overrides({"annualised_volatility": 0.4})
    with pytest.raises(ValueError, match="in impact"):
        cfg.with_overrides({"impact": {"temporay_eta": 1e-4}})
