"""Multi-head causal self-attention, written to be read.

Two interchangeable code paths over the SAME parameters:

- "explicit": every intermediate materialized —
      scores  = Q K^T / sqrt(d_h)          [B,H,T,T]
      scores  = scores + causal mask (future → -inf)
      weights = softmax(scores, dim=-1)    rows sum to 1 (tested)
      out     = weights V
- "sdpa": torch.nn.functional.scaled_dot_product_attention(is_causal=True) —
  identical math in a fused kernel that never materializes [B,H,T,T].

Passing `trace=` forces the explicit path and records q/k/v/scores/weights,
which is how the forward-pass notebook and attention visualizations get their
tensors without a second, divergent implementation.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn


class CausalSelfAttention(nn.Module):
    def __init__(
        self,
        d_model: int,
        n_heads: int,
        context_len: int,
        dropout: float = 0.0,
        attn_impl: str = "explicit",
        bias: bool = True,
        pos: str = "learned",
    ):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.dropout = dropout
        self.attn_impl = attn_impl
        self.use_rope = pos == "rope"
        # One fused linear producing Q,K,V (3·D outputs) — cheaper than three
        # separate matmuls and standard practice; split happens in forward.
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=bias)
        self.proj = nn.Linear(d_model, d_model, bias=bias)
        self.resid_dropout = nn.Dropout(dropout)
        # Cached boolean lower-triangular mask [1,1,Tmax,Tmax]; True = allowed.
        mask = torch.tril(torch.ones(context_len, context_len, dtype=torch.bool))
        self.register_buffer("causal_mask", mask.view(1, 1, context_len, context_len), persistent=False)
        if self.use_rope:
            from .rope import rope_angles

            cos, sin = rope_angles(context_len, self.d_head)
            self.register_buffer("rope_cos", cos, persistent=False)
            self.register_buffer("rope_sin", sin, persistent=False)

    def set_attn_impl(self, impl: str) -> None:
        assert impl in ("explicit", "sdpa")
        self.attn_impl = impl

    def forward(self, x: torch.Tensor, trace: dict | None = None, prefix: str = "attn") -> torch.Tensor:
        B, T, D = x.shape
        assert T <= self.causal_mask.shape[-1], "sequence longer than context_len"

        q, k, v = self.qkv(x).split(D, dim=2)  # each [B,T,D]
        # [B,T,D] → [B,H,T,d_h]: heads become a batch dimension so each head
        # attends independently with its own d_h-dimensional queries/keys.
        q = q.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        k = k.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = v.view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        if self.use_rope:
            from .rope import apply_rope

            q = apply_rope(q, self.rope_cos, self.rope_sin)
            k = apply_rope(k, self.rope_cos, self.rope_sin)

        use_explicit = self.attn_impl == "explicit" or trace is not None
        if use_explicit:
            # (1) similarity of every query with every key, scaled by sqrt(d_h)
            #     to keep score variance ~1 regardless of head width.
            scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_head)  # [B,H,T,T]
            # (2) causal mask: position t may look at j <= t only.
            scores = scores.masked_fill(~self.causal_mask[:, :, :T, :T], float("-inf"))
            # (3) softmax over keys → each row is a probability distribution.
            weights = F.softmax(scores, dim=-1)
            if trace is not None:
                for name, val in [("q", q), ("k", k), ("v", v), ("scores", scores), ("attn_weights", weights)]:
                    trace[f"{prefix}.{name}"] = val.detach()
            # (4) attention-weighted average of values.
            att = F.dropout(weights, p=self.dropout, training=self.training)
            y = att @ v  # [B,H,T,d_h]
        else:
            y = F.scaled_dot_product_attention(
                q, k, v, dropout_p=self.dropout if self.training else 0.0, is_causal=True
            )

        # heads re-concatenated, then mixed by the output projection.
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        y = self.resid_dropout(self.proj(y))
        if trace is not None:
            trace[f"{prefix}.out"] = y.detach()
        return y

    @torch.no_grad()
    def attention_weights(self, x: torch.Tensor) -> torch.Tensor:
        """Convenience: [B,H,T,T] attention weights for analysis."""
        t: dict = {}
        self.forward(x, trace=t, prefix="a")
        return t["a.attn_weights"]
