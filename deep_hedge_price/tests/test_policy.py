from __future__ import annotations

import torch

from deep_hedge_price.pnl import rollout_policy
from deep_hedge_price.policy import MLPHedgePolicy
from deep_hedge_price.simulation import simulate_gbm


def test_output_shape_and_smooth_bounds(tiny_config):
    policy = MLPHedgePolicy(tiny_config.market, tiny_config.policy)
    state = torch.randn(128, 5)
    output = policy(state)
    assert output.shape == (128,)
    assert torch.all(output >= tiny_config.policy.action_min * tiny_config.market.short_quantity)
    assert torch.all(output <= tiny_config.policy.action_max * tiny_config.market.short_quantity)


def test_gradient_flows_through_full_rollout(tiny_config):
    policy = MLPHedgePolicy(tiny_config.market, tiny_config.policy)
    paths = simulate_gbm(tiny_config.market, 64, seed=12)
    result = rollout_policy(policy, paths, tiny_config.market)
    result.loss_excluding_premium.square().mean().backward()
    gradients = [parameter.grad for parameter in policy.parameters()]
    assert result.deltas.shape == (64, tiny_config.market.n_steps)
    assert all(gradient is not None for gradient in gradients)
    assert all(torch.isfinite(gradient).all() for gradient in gradients if gradient is not None)
    assert any(torch.any(gradient != 0) for gradient in gradients if gradient is not None)
