"""Transformer building blocks: GELU MLP and the pre-LN residual block.

Residual-stream view (spec §8.2): the block never replaces its input, it only
ADDS two branch outputs to it —

    x ── LN1 ─ Attention ──(+)── LN2 ─ MLP ──(+)──▶
    └────────────────────────┴──────────────────┘   (residual stream)

Pre-LN (normalize the branch INPUT, not the sum) keeps the residual path an
identity, which is why deep stacks train stably without warmup tricks.
"""

from __future__ import annotations

import torch
from torch import nn

from .attention import CausalSelfAttention
from .config import ModelConfig


class MLP(nn.Module):
    """Position-wise 2-layer MLP with GELU, hidden width 4·d_model (GPT-2)."""

    def __init__(self, d_model: int, dropout: float = 0.0, bias: bool = True, hidden_mult: int = 4):
        super().__init__()
        self.fc = nn.Linear(d_model, hidden_mult * d_model, bias=bias)
        self.act = nn.GELU()
        self.proj = nn.Linear(hidden_mult * d_model, d_model, bias=bias)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.proj(self.act(self.fc(x))))


class TransformerBlock(nn.Module):
    def __init__(self, cfg: ModelConfig, layer_idx: int):
        super().__init__()
        self.layer_idx = layer_idx
        self.ln1 = nn.LayerNorm(cfg.d_model)
        self.attn = CausalSelfAttention(
            cfg.d_model, cfg.n_heads, cfg.context_len, cfg.dropout, cfg.attn_impl, cfg.bias
        )
        self.ln2 = nn.LayerNorm(cfg.d_model)
        self.mlp = MLP(cfg.d_model, cfg.dropout, cfg.bias)

    def forward(self, x: torch.Tensor, trace: dict | None = None) -> torch.Tensor:
        pfx = f"block{self.layer_idx}"
        attn_out = self.attn(self.ln1(x), trace=trace, prefix=f"{pfx}.attn")
        x = x + attn_out  # residual add #1
        if trace is not None:
            trace[f"{pfx}.resid_after_attn"] = x.detach()
        mlp_out = self.mlp(self.ln2(x))
        x = x + mlp_out  # residual add #2
        if trace is not None:
            trace[f"{pfx}.mlp_out"] = mlp_out.detach()
            trace[f"{pfx}.resid_after_mlp"] = x.detach()
        return x
