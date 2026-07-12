"""Differentiable risk objectives."""

from __future__ import annotations

import math

import torch
from torch import nn

from .config import RiskConfig


def mse_risk(loss: torch.Tensor) -> torch.Tensor:
    """Mean squared hedging loss."""
    return torch.mean(loss.square())


def entropic_risk(loss_normalized: torch.Tensor, gamma: float) -> torch.Tensor:
    """Stable entropic risk of losses already normalized by spot."""
    if gamma <= 0:
        raise ValueError("gamma must be positive")
    values = gamma * loss_normalized
    return (torch.logsumexp(values, dim=0) - math.log(values.numel())) / gamma


def cvar_objective(
    loss_normalized: torch.Tensor,
    q: torch.Tensor,
    alpha: float,
) -> torch.Tensor:
    """Rockafellar--Uryasev CVaR objective at a supplied threshold."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    return q + torch.relu(loss_normalized - q).mean() / (1 - alpha)


class RiskObjective(nn.Module):
    """Configured risk objective, including a trainable CVaR threshold."""

    def __init__(self, config: RiskConfig, s0: float, initial_q: float = 0.03) -> None:
        super().__init__()
        self.config = config
        self.s0 = float(s0)
        if config.objective == "cvar":
            self.q = nn.Parameter(torch.tensor(float(initial_q)))
        else:
            self.register_parameter("q", None)

    def forward(self, loss: torch.Tensor) -> torch.Tensor:
        if self.config.objective == "mse":
            return mse_risk(loss)
        normalized = loss / self.s0
        if self.config.objective == "entropic":
            return entropic_risk(normalized, self.config.entropic_gamma)
        if self.q is None:
            raise RuntimeError("CVaR objective is missing q")
        return cvar_objective(normalized, self.q, self.config.cvar_alpha)
