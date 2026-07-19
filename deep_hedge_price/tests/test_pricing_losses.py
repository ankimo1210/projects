from __future__ import annotations

import torch

from deep_hedge_price.pricing_losses import differential_delta_loss, scale_balanced_mse


def test_scale_balanced_loss_and_differential_delta():
    assert scale_balanced_mse(torch.tensor([2.0]), torch.tensor([1.0]), 2.0) == 0.25
    inputs = torch.tensor([[2.0, 1.0, 0.0, 0.0, 0.2]], requires_grad=True)
    price = inputs[:, 0] ** 2
    loss, derivative = differential_delta_loss(price, inputs, torch.tensor([4.0]))
    assert derivative.item() == 4.0
    assert loss.item() == 0.0
