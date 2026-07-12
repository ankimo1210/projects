"""Rotary Position Embedding (RoPE) — relative positions via rotation.

Each consecutive pair of head dimensions (2i, 2i+1) is treated as a 2-D plane
and rotated by angle θ_i·t at position t, with θ_i = base^(-2i/d_h):

    q'_t = R(θ·t) q_t ,   k'_j = R(θ·j) k_j
    ⟨q'_t, k'_j⟩ = ⟨R(θ·(t-j)) q_t, k_j⟩      ← depends only on t − j

So attention scores become a function of RELATIVE distance — no learned
position table, and (in principle) better extrapolation to unseen lengths.
Rotation preserves vector norms, so score magnitudes are unchanged.
"""

from __future__ import annotations

import torch


def rope_angles(context_len: int, d_head: int, base: float = 10000.0) -> tuple[torch.Tensor, torch.Tensor]:
    """cos/sin tables, each [T, d_head/2]."""
    assert d_head % 2 == 0
    inv_freq = base ** (-torch.arange(0, d_head, 2, dtype=torch.float32) / d_head)
    t = torch.arange(context_len, dtype=torch.float32)
    angles = t[:, None] * inv_freq[None, :]  # [T, d_head/2]
    return angles.cos(), angles.sin()


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Rotate q or k. x: [B, H, T, d_head]; cos/sin: [Tmax, d_head/2]."""
    T = x.shape[2]
    dtype = x.dtype
    xf = x.float()
    c = cos[:T].view(1, 1, T, -1)
    s = sin[:T].view(1, 1, T, -1)
    x1, x2 = xf[..., 0::2], xf[..., 1::2]
    y1 = x1 * c - x2 * s
    y2 = x1 * s + x2 * c
    return torch.stack((y1, y2), dim=-1).flatten(-2).to(dtype)
