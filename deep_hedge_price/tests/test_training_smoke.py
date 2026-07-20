from __future__ import annotations

import torch

from deep_hedge_price.training import load_policy, train_policy


@torch.no_grad()
def _state_vector(policy):
    return torch.cat([value.detach().cpu().reshape(-1) for value in policy.state_dict().values()])


def test_smoke_training_reduces_validation_loss_and_loads(tiny_config, tmp_path):
    result = train_policy(tiny_config, tmp_path, force=True)
    initial = result.history.iloc[0]["validation_objective"]
    best = result.history["validation_objective"].min()
    assert best < initial
    assert result.checkpoint_path.exists()
    assert (result.checkpoint_path.parent / "config.yaml").exists()
    loaded, _ = load_policy(tiny_config, result.checkpoint_path, device="cpu")
    assert torch.allclose(_state_vector(result.policy), _state_vector(loaded))


def test_fixed_seed_training_is_reproducible(tiny_config, tmp_path):
    first = train_policy(tiny_config, tmp_path / "one", force=True)
    second = train_policy(tiny_config, tmp_path / "two", force=True)
    assert torch.allclose(_state_vector(first.policy), _state_vector(second.policy), atol=1e-7)
    assert first.history["validation_objective"].equals(second.history["validation_objective"])
