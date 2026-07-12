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
import torch.nn.functional as F
from torch import nn

from .attention import CausalSelfAttention
from .config import ModelConfig
from .norms import make_norm


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


class SwiGLU(nn.Module):
    """Gated MLP (Modern GPT):  w2( silu(w1·x) ⊙ w3·x ).

    Three matrices instead of two, so the hidden width is set to ≈ 8d/3
    (rounded to a multiple of 32) to keep the parameter count equal to the
    4d GELU MLP — otherwise the M3 ablation would confound architecture with
    capacity.
    """

    def __init__(self, d_model: int, dropout: float = 0.0, bias: bool = True):
        super().__init__()
        hidden = 32 * round(8 * d_model / 3 / 32)
        self.w1 = nn.Linear(d_model, hidden, bias=bias)  # value path
        self.w3 = nn.Linear(d_model, hidden, bias=bias)  # gate path
        self.w2 = nn.Linear(hidden, d_model, bias=bias)  # down-projection
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.silu(self.w1(x)) * self.w3(x)))


def make_mlp(cfg: ModelConfig) -> nn.Module:
    if cfg.mlp == "gelu":
        return MLP(cfg.d_model, cfg.dropout, cfg.bias)
    if cfg.mlp == "swiglu":
        return SwiGLU(cfg.d_model, cfg.dropout, cfg.bias)
    raise ValueError(f"unknown mlp kind: {cfg.mlp}")


class TransformerBlock(nn.Module):
    def __init__(self, cfg: ModelConfig, layer_idx: int):
        super().__init__()
        self.layer_idx = layer_idx
        self.ln1 = make_norm(cfg.norm, cfg.d_model)
        self.attn = CausalSelfAttention(
            cfg.d_model, cfg.n_heads, cfg.context_len, cfg.dropout, cfg.attn_impl, cfg.bias, cfg.pos
        )
        self.ln2 = make_norm(cfg.norm, cfg.d_model)
        self.mlp = make_mlp(cfg)

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
