"""Quantitative attention analysis (spec §9), computed from real attention maps.

Everything here operates on the [B,H,T,T] weight tensors returned by
`model.attention_maps` (which forces the explicit path). These are DESCRIPTIVE
statistics of where attention mass goes — deliberately separated from the
CAUSAL tests (head ablation / activation patching in causal_analysis.py),
because "attention is not explanation": high weight ≠ high causal contribution.
"""

from __future__ import annotations

import torch


def entropy_per_head(weights: torch.Tensor) -> torch.Tensor:
    """[H] mean row-entropy (nats). Row t has ≤ t+1 nonzero entries."""
    w = weights.float().clamp(min=1e-12)
    h = -(w * w.log()).sum(dim=-1)  # [B,H,T]
    return h.mean(dim=(0, 2))


def mean_attention_distance(weights: torch.Tensor) -> torch.Tensor:
    """[H] average |t − j| weighted by attention — how far back each head looks."""
    _B, _H, T, _ = weights.shape
    idx = torch.arange(T)
    dist = (idx[:, None] - idx[None, :]).abs().float()  # [T,T]
    w = weights.float()
    per = (w * dist).sum(-1)  # [B,H,T]
    return per.mean(dim=(0, 2))


def _query_key_mass(weights: torch.Tensor, key_fn) -> torch.Tensor:
    """Mean mass on selected keys over queries t>=1. key_fn(q_index)->key_index."""
    _B, _H, T, _ = weights.shape
    q = torch.arange(1, T)
    k = key_fn(q).clamp(min=0)
    sel = weights[:, :, q, k]  # [B,H,T-1]
    return sel.float().mean(dim=(0, 2))


def prev_token_ratio(weights: torch.Tensor) -> torch.Tensor:
    """[H] mean attention on the immediately preceding token (key = t-1)."""
    return _query_key_mass(weights, lambda q: q - 1)


def first_token_ratio(weights: torch.Tensor) -> torch.Tensor:
    """[H] mean attention on position 0 (BOS-like sink) from queries t>=1."""
    return _query_key_mass(weights, lambda q: torch.zeros_like(q))


def self_token_ratio(weights: torch.Tensor) -> torch.Tensor:
    """[H] mean attention a token pays to itself (diagonal), queries t>=1."""
    return _query_key_mass(weights, lambda q: q)


def head_similarity(weights: torch.Tensor) -> torch.Tensor:
    """[H,H] cosine similarity between heads' flattened weight patterns."""
    _B, H, _T, _ = weights.shape
    flat = weights.float().mean(0).reshape(H, -1)  # avg over batch → [H, T*T]
    flat = flat / flat.norm(dim=1, keepdim=True).clamp(min=1e-12)
    return flat @ flat.t()


def layer_head_matrix(maps: list[torch.Tensor], fn) -> torch.Tensor:
    """Apply a per-head statistic fn to every layer → [L,H] tensor."""
    return torch.stack([fn(m) for m in maps])


def summarize(maps: list[torch.Tensor]) -> dict:
    """All per-(layer,head) statistics as nested lists (JSON-friendly)."""
    return {
        "entropy": layer_head_matrix(maps, entropy_per_head).tolist(),
        "distance": layer_head_matrix(maps, mean_attention_distance).tolist(),
        "prev_token_ratio": layer_head_matrix(maps, prev_token_ratio).tolist(),
        "first_token_ratio": layer_head_matrix(maps, first_token_ratio).tolist(),
        "self_token_ratio": layer_head_matrix(maps, self_token_ratio).tolist(),
        "n_layers": len(maps),
        "n_heads": maps[0].shape[1],
    }
