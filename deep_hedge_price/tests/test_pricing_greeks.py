from __future__ import annotations

import torch
from torch import nn

from deep_hedge_price.greeks import autodiff_greeks


class QuadraticPrice(nn.Module):
    def forward(self, inputs):
        x, tau, rate, _dividend, sigma = inputs.unbind(dim=-1)
        return x**2 + 3 * sigma - 2 * tau + 4 * rate


def test_autodiff_greeks_have_financial_sign_convention():
    inputs = torch.tensor([[1.2, 0.5, 0.02, 0.0, 0.3]], dtype=torch.float64)
    greeks = autodiff_greeks(QuadraticPrice(), inputs)
    assert greeks["delta"].item() == 2.4
    assert greeks["gamma"].item() == 2.0
    assert greeks["vega"].item() == 3.0
    assert greeks["theta"].item() == 2.0
    assert greeks["rho"].item() == 4.0
