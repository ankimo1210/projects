"""RL smoke tests (spec §21.9)."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from optimal_execution.environment import N_ACTIONS, OBS_DIM, ExecutionEnv
from optimal_execution.evaluation import run_lob_episode
from optimal_execution.experiments import _checkpoint_metadata_matches
from optimal_execution.provenance import config_fingerprint, model_fingerprint
from optimal_execution.rl_policy import (
    ActorCritic,
    RLPolicy,
    load_checkpoint,
    save_checkpoint,
)
from optimal_execution.rl_training import train_ppo
from optimal_execution.strategies import schedule_ac


def test_policy_output_bounds():
    model = ActorCritic()
    obs = np.random.default_rng(0).normal(size=OBS_DIM)
    for det in (True, False):
        a, logp, v = model.act(obs, deterministic=det)
        assert 0 <= a < N_ACTIONS
        assert np.isfinite(logp) and np.isfinite(v)
    logits, value = model(torch.zeros(4, OBS_DIM))
    assert logits.shape == (4, N_ACTIONS)
    assert torch.isfinite(logits).all() and torch.isfinite(value).all()


def test_checkpoint_roundtrip(tmp_path):
    model = ActorCritic(hidden=32)
    p = tmp_path / "ck.pt"
    save_checkpoint(model, p, {"variant": "residual", "seed": 1, "hidden": 32})
    model2, meta = load_checkpoint(p)
    assert meta["variant"] == "residual"
    obs = torch.ones(1, OBS_DIM)
    torch.testing.assert_close(model(obs)[0], model2(obs)[0])


def test_deterministic_evaluation(cfg):
    model = ActorCritic()
    policy = RLPolicy(model, deterministic=True)
    env = ExecutionEnv(cfg, baseline=schedule_ac(cfg))
    ep1 = run_lob_episode(env, policy, seed=77)
    ep2 = run_lob_episode(env, policy, seed=77)
    assert ep1["is_total"] == pytest.approx(ep2["is_total"])


def test_checkpoint_reuse_requires_matching_configuration(cfg):
    meta = {
        "config_fingerprint": config_fingerprint(cfg),
        "model_fingerprint": model_fingerprint(),
        "run_id": "residual_quick_s1210",
        "requested_episodes": cfg.rl.training_episodes,
        "feature_mask": None,
    }
    assert _checkpoint_metadata_matches(
        cfg,
        meta,
        run_id="residual_quick_s1210",
        episodes=cfg.rl.training_episodes,
        feature_mask=None,
    )
    changed = cfg.with_overrides({"rl": {"learning_rate": 1e-4}})
    assert not _checkpoint_metadata_matches(
        changed,
        meta,
        run_id="residual_quick_s1210",
        episodes=cfg.rl.training_episodes,
        feature_mask=None,
    )


@pytest.mark.slow
def test_training_smoke_no_nan(cfg, tmp_path):
    small = cfg.with_overrides(
        {
            "rl": {
                "training_episodes": 90,
                "validation_episodes": 12,
                "rollout_steps": 512,
                "eval_every_episodes": 40,
                "early_stop_patience": 50,
            }
        }
    )
    res = train_ppo(small, variant="residual", out_dir=tmp_path, tag="smoke")
    assert res.checkpoint.exists()
    assert res.episodes_run >= 90
    assert np.isfinite(res.best_val_is_bps)
    hist_rewards = [h["train_reward_ma"] for h in res.history]
    assert all(np.isfinite(r) for r in hist_rewards if not np.isnan(r))
    # residual policy respects the safety layer: run a full episode
    policy = RLPolicy.from_checkpoint(res.checkpoint)
    env = ExecutionEnv(small, baseline=schedule_ac(small))
    ep = run_lob_episode(env, policy, seed=5)
    assert ep["terminal_inventory"] == pytest.approx(0.0, abs=1e-6)
    assert ep["executed"] <= small.initial_inventory + 1e-6


@pytest.mark.slow
def test_free_variant_trains(cfg, tmp_path):
    small = cfg.with_overrides(
        {
            "rl": {
                "training_episodes": 40,
                "validation_episodes": 8,
                "rollout_steps": 256,
                "eval_every_episodes": 30,
                "early_stop_patience": 50,
            }
        }
    )
    res = train_ppo(small, variant="free", out_dir=tmp_path, tag="smoke_free")
    assert res.checkpoint.exists()
    assert res.variant == "free"
