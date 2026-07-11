"""RMSNorm — the Modern-GPT normalization (spec §7.2).

LayerNorm:  y = (x - mean(x)) / sqrt(var(x) + ε) · γ + β     (2d params)
RMSNorm:    y = x / sqrt(mean(x²) + ε) · γ                   (d params)

RMSNorm drops the mean-centering and the bias β: only the SCALE of the vector
is normalized, not its position. Empirically this preserves quality while
being cheaper — the ablation in Milestone 3 measures whether that holds here.
"""

from __future__ import annotations

import torch
from torch import nn


class RMSNorm(nn.Module):
    def __init__(self, d_model: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d_model))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        dtype = x.dtype
        xf = x.float()
        normed = xf * torch.rsqrt(xf.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return (normed * self.weight.float()).to(dtype)


def make_norm(kind: str, d_model: int) -> nn.Module:
    if kind == "layernorm":
        return nn.LayerNorm(d_model)
    if kind == "rmsnorm":
        return RMSNorm(d_model)
    raise ValueError(f"unknown norm kind: {kind}")
