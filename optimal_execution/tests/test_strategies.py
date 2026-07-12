"""Strategy tests: schedules complete, constraints respected (spec §12)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.environment import ExecutionEnv
from optimal_execution.evaluation import lob_world_run, run_lob_episode
from optimal_execution.random import stream_rng
from optimal_execution.strategies import (
    classical_schedules,
    lob_policies,
    schedule_ac,
    schedule_immediate,
    schedule_ow,
    schedule_pov,
    schedule_twap,
    schedule_vwap,
)
from optimal_execution.volume import simulate_step_volumes, vwap_weights


def test_deterministic_schedules_complete(cfg):
    X = cfg.initial_inventory
    for sched in (schedule_immediate, schedule_twap, schedule_vwap, schedule_ac, schedule_ow):
        q = sched(cfg)
        assert q.sum() == pytest.approx(X), sched.__name__
        assert np.all(q >= -1e-9), sched.__name__
    assert schedule_immediate(cfg)[0] == X
    np.testing.assert_allclose(schedule_vwap(cfg), X * vwap_weights(cfg))


def test_pov_respects_rate_and_deadline(cfg):
    vols = simulate_step_volumes(cfg, stream_rng(1, "v"), 200)
    q = schedule_pov(cfg, vols, rate=0.1)
    X = cfg.initial_inventory
    np.testing.assert_allclose(q.sum(axis=1), X)
    # all steps except the deadline step respect the participation rate
    assert np.all(q[:, :-1] <= 0.1 * vols[:, :-1] + 1e-9)
    assert np.all(q >= -1e-9)


def test_classical_schedule_matrix(cfg):
    vols = simulate_step_volumes(cfg, stream_rng(2, "v"), 50)
    scheds = classical_schedules(cfg, vols)
    assert set(scheds) == {"immediate", "twap", "vwap", "pov", "ac", "ow"}
    for name, q in scheds.items():
        assert q.shape == vols.shape, name
        np.testing.assert_allclose(q.sum(axis=1), cfg.initial_inventory, rtol=1e-9)


@pytest.mark.slow
def test_lob_policies_complete_episodes(cfg):
    policies = lob_policies(cfg)
    frames, _ = lob_world_run(cfg, policies, purpose="unittest", n_episodes=8)
    for name, df in frames.items():
        assert (df["terminal_inventory"].abs() < 1e-6).all(), name
        assert np.isfinite(df["is_bps"]).all(), name
        assert (df["residual"].abs() < 1e-6 * cfg.notional).all(), name


@pytest.mark.slow
def test_heuristic_uses_both_order_types(cfg):
    policies = {"heuristic": lob_policies(cfg)["heuristic"]}
    frames, _ = lob_world_run(cfg, policies, purpose="unittest2", n_episodes=10)
    df = frames["heuristic"]
    assert df["limit_shares"].mean() > 0  # passive fills happen
    assert (df["mkt_shares"] + df["cleanup_qty"]).mean() > 0  # and market orders


@pytest.mark.slow
def test_limit_only_shows_fill_risk(cfg):
    policies = {"limit_only": lob_policies(cfg)["limit_only"]}
    frames, _ = lob_world_run(cfg, policies, purpose="unittest3", n_episodes=10)
    df = frames["limit_only"]
    # some episodes end with cleanup (unfilled remainder) — fill risk is real
    assert df["cleanup_qty"].mean() > 0
    assert df["limit_shares"].mean() > 0


def test_market_schedule_policy_carries_shortfall(cfg):
    """If the cap clips early orders the policy catches up later."""
    tight = cfg.with_overrides({"max_participation_rate": 0.08})
    from optimal_execution.strategies import MarketSchedulePolicy

    policy = MarketSchedulePolicy(schedule_immediate(tight))
    env = ExecutionEnv(tight)
    policy.reset()
    ep = run_lob_episode(env, policy, seed=5)
    # immediate schedule cannot execute in one step under the cap, but the
    # carryover + forced liquidation still complete the parent order
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    assert ep["executed"] == pytest.approx(tight.initial_inventory)
