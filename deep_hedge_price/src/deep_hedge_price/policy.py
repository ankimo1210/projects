"""Time-shared neural hedging policies."""

from __future__ import annotations

import math

import torch
from torch import nn

from .config import MarketConfig, PolicyConfig


class FeatureScaler(nn.Module):
    """Deterministic feature normalization stored in model checkpoints."""

    def __init__(self, market: MarketConfig, policy: PolicyConfig) -> None:
        super().__init__()
        quantity = market.short_quantity
        action_mid = quantity * (policy.action_min + policy.action_max) / 2
        action_half = quantity * (policy.action_max - policy.action_min) / 2
        means = torch.tensor([0.0, 0.5, action_mid, 0.20, 0.0005])
        scales = torch.tensor(
            [
                max(market.volatility * math.sqrt(market.maturity_years), 1e-3),
                0.5,
                max(action_half, 1e-3),
                0.10,
                0.0005,
            ]
        )
        self.register_buffer("means", means)
        self.register_buffer("scales", scales)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return (state - self.means) / self.scales


class MLPHedgePolicy(nn.Module):
    """Shared MLP mapping the five-dimensional state to total stock holdings."""

    def __init__(self, market: MarketConfig, config: PolicyConfig) -> None:
        super().__init__()
        self.market = market
        self.config = config
        self.scaler = FeatureScaler(market, config)
        activation: type[nn.Module] = nn.SiLU if config.activation == "silu" else nn.Tanh
        layers: list[nn.Module] = []
        in_features = 5
        for _ in range(config.hidden_layers):
            layers.append(nn.Linear(in_features, config.hidden_units))
            if config.layer_norm:
                layers.append(nn.LayerNorm(config.hidden_units))
            layers.append(activation())
            in_features = config.hidden_units
        layers.append(nn.Linear(in_features, 1))
        self.network = nn.Sequential(*layers)
        self.action_low = market.short_quantity * config.action_min
        self.action_high = market.short_quantity * config.action_max

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        raw = self.network(self.scaler(state)).squeeze(-1)
        midpoint = (self.action_low + self.action_high) / 2
        half_range = (self.action_high - self.action_low) / 2
        return midpoint + half_range * torch.tanh(raw)

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())


def architecture_rows(policy: MLPHedgePolicy) -> list[dict[str, int | str]]:
    """Return a compact architecture summary for reports and notebooks."""
    rows: list[dict[str, int | str]] = []
    for name, layer in policy.network.named_children():
        params = sum(parameter.numel() for parameter in layer.parameters())
        rows.append({"index": name, "layer": layer.__class__.__name__, "parameters": params})
    return rows
