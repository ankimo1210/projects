"""Execution-environment tests (spec §21.7)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.environment import (
    N_ACTIONS,
    OBS_DIM,
    ExecutionEnv,
    decode_action,
)


def run_episode(env, action, seed=42):
    obs = env.reset(seed)
    total_r = 0.0
    infos = []
    done = False
    while not done:
        act = action(env) if callable(action) else action
        obs, r, done, info = env.step(act)
        assert np.isfinite(r)
        assert obs.shape == (OBS_DIM,)
        assert np.all(np.isfinite(obs))
        assert env.x >= -1e-9  # inventory never negative
        total_r += r
        infos.append(info)
    return total_r, infos[-1]["episode"]


def test_action_decoding():
    mults = {decode_action(a)[0] for a in range(N_ACTIONS)}
    modes = {decode_action(a)[1] for a in range(N_ACTIONS)}
    assert mults == {0.0, 0.5, 1.0, 1.5, 2.0}
    assert modes == {"none", "join", "improve"}
    with pytest.raises(ValueError):
        decode_action(N_ACTIONS)


def test_twap_market_only_completes(cfg):
    env = ExecutionEnv(cfg)
    _, ep = run_episode(env, 2)  # m=1.0 x TWAP slice, no limit order
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    assert ep["executed"] == pytest.approx(cfg.initial_inventory)
    assert np.isfinite(ep["is_total"])


def test_no_overexecution_with_aggressive_actions(cfg):
    env = ExecutionEnv(cfg)
    _, ep = run_episode(env, 14)  # m=2.0 + improve limit: max aggression
    assert ep["executed"] <= cfg.initial_inventory + 1e-6
    assert ep["terminal_inventory"] >= -1e-9


def test_terminal_forced_liquidation(cfg):
    env = ExecutionEnv(cfg)
    _, ep = run_episode(env, 0)  # do nothing: everything forced at the end
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    assert ep["cleanup_qty"] == pytest.approx(cfg.initial_inventory)
    assert ep["cleanup_cost"] > 0  # walking the whole book is punitive
    assert ep["is_total"] > 0


def test_participation_cap_enforced(cfg):
    env = ExecutionEnv(cfg)
    env.reset(1)
    cap = cfg.max_participation_rate * env.vol_ema
    child_cap = cfg.max_child_order_frac * cfg.initial_inventory
    x0 = env.x
    env.step({"market_qty": 1e9, "limit": "none"})
    executed = x0 - env.x
    assert executed <= min(cap, child_cap) + 1e-6
    assert env.violations >= 1


def test_price_collar_caps_walked_average_price(cfg):
    shallow = cfg.with_overrides(
        {
            "liquidity": {"depth_shares": 100.0, "deep_liquidity_mult": 1.0},
            "price_collar_bps": 5.0,
            "max_child_order_frac": 1.0,
            "max_participation_rate": 1.0,
        }
    )
    env = ExecutionEnv(shallow)
    env.reset(7)
    _, _, _, info = env.step({"market_qty": 1000.0, "limit": "none"})
    executed = info["executed"]
    assert 0 < executed < 1000.0
    avg_price = env.cash / executed
    collar = shallow.price_collar_bps * 1e-4 * env.arrival_s0
    assert shallow.sign * (env.arrival_s0 - avg_price) <= collar + 1e-9
    assert env.violations >= 1


def test_economic_vs_shaped_reward_separate(cfg):
    env = ExecutionEnv(cfg)
    total_r, ep = run_episode(env, 2)
    assert total_r == pytest.approx(ep["shaped_reward"], rel=1e-9)
    # shaped reward includes risk penalties; economic IS does not
    assert ep["risk_penalty"] > 0
    assert (
        abs(-(ep["is_total"] + ep["risk_penalty"]) * cfg.rl.reward.cost_scale - ep["shaped_reward"])
        < abs(ep["shaped_reward"]) + 1.0
    )


def test_inventory_risk_uses_current_sigma_profile(cfg):
    env = ExecutionEnv(cfg)
    env.reset(9)
    env.step({"market_qty": 0.0, "limit": "none"})
    assert env.book is not None
    sigma_sq = np.mean(env.book._sigma_sub[: env.n_sub] ** 2)
    expected = cfg.rl.reward.inventory_penalty * cfg.initial_inventory**2 * sigma_sq * env.dt
    assert env.risk_penalty_total == pytest.approx(expected)


def test_invalid_limit_action_is_rejected_and_counted(cfg):
    env = ExecutionEnv(cfg)
    env.reset(7)
    env.step({"market_qty": 0.0, "limit": "typo", "limit_qty": 100.0})
    assert env.limit_posted == 0.0
    assert env.violations == 1

    env.reset(7)
    env.step({"market_qty": 0.0, "limit": "join", "limit_qty": np.nan})
    assert env.limit_posted == 0.0
    assert env.violations == 1


def test_decomposition_identity(cfg):
    """Latent components must sum to the exact implementation shortfall."""
    for action in (2, 5, 7, 11):
        env = ExecutionEnv(cfg)
        _, ep = run_episode(env, action, seed=action)
        tol = 1e-6 * cfg.notional
        assert abs(ep["decomposition_residual"]) < tol, (action, ep["decomposition_residual"])


def test_crn_determinism(cfg):
    env1 = ExecutionEnv(cfg)
    env2 = ExecutionEnv(cfg)
    _, ep1 = run_episode(env1, 7, seed=99)
    _, ep2 = run_episode(env2, 7, seed=99)
    assert ep1["is_total"] == pytest.approx(ep2["is_total"])
    assert ep1["components"] == pytest.approx(ep2["components"])


def test_residual_baseline_schedule(cfg):
    from optimal_execution.almgren_chriss import ac_schedule

    q_ac = ac_schedule(cfg.initial_inventory, cfg.horizon_seconds, cfg.kappa, cfg.n_decision_steps)
    env = ExecutionEnv(cfg, baseline=q_ac)
    _, ep = run_episode(env, 2)  # m=1.0 -> follow AC exactly (market orders)
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    # front-loaded: more than half executed by mid-horizon happens via cap-limited AC
    assert ep["executed"] == pytest.approx(cfg.initial_inventory)


def test_feature_mask_zeroes_features(cfg):
    mask = np.ones(OBS_DIM)
    mask[5] = 0.0  # imbalance
    env = ExecutionEnv(cfg, feature_mask=mask)
    obs = env.reset(3)
    assert obs[5] == 0.0
    obs, *_ = env.step(2)
    assert obs[5] == 0.0


def test_replay_mode_underestimates_impact(cfg):
    """Replay (non-reactive) execution shows lower measured cost for the same
    aggressive strategy because the agent's footprint is invisible."""
    is_react, is_replay = [], []
    for seed in range(25):
        env_r = ExecutionEnv(cfg, reactive=True)
        env_p = ExecutionEnv(cfg, reactive=False)
        _, ep_r = run_episode(env_r, 3, seed=seed)  # m=1.5 market
        _, ep_p = run_episode(env_p, 3, seed=seed)
        is_react.append(ep_r["is_bps"])
        is_replay.append(ep_p["is_bps"])
    assert np.mean(is_react) > np.mean(is_replay)


def test_buy_side_episode(cfg):
    env = ExecutionEnv(cfg.with_overrides({"side": "buy"}))
    _, ep = run_episode(env, 2)
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    assert np.isfinite(ep["is_total"])
    tol = 1e-6 * cfg.notional
    assert abs(ep["decomposition_residual"]) < tol
