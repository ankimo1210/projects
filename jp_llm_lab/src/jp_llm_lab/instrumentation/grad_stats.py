"""Gradient / parameter / update statistics per architectural group (spec §12).

Key quantity: the update-to-weight ratio
    u_g = ‖ΔW_g‖₂ / ‖W_g‖₂
(aggregated over all parameters of group g). Healthy AdamW training typically
sits around 1e-3 per step; ≫1e-2 hints at a too-large learning rate, ≈0 at a
dead group.
"""

from __future__ import annotations

import math

import torch
from torch import nn

from ..models.config import param_group_of


def grad_stats(model: nn.Module) -> dict[str, dict[str, float]]:
    """Per-group L2 norms of gradients and parameters (call after backward)."""
    acc: dict[str, dict[str, float]] = {}
    for name, p in model.named_parameters():
        g = param_group_of(name)
        slot = acc.setdefault(g, {"grad_sq": 0.0, "param_sq": 0.0, "n_params": 0})
        slot["param_sq"] += float(p.detach().float().pow(2).sum())
        slot["n_params"] += p.numel()
        if p.grad is not None:
            slot["grad_sq"] += float(p.grad.detach().float().pow(2).sum())
    return {
        g: {
            "grad_norm": math.sqrt(v["grad_sq"]),
            "param_norm": math.sqrt(v["param_sq"]),
            "n_params": v["n_params"],
        }
        for g, v in acc.items()
    }


def snapshot_params(model: nn.Module) -> dict[str, torch.Tensor]:
    """Clone all parameters (small models only — Model S/M/L are ≤50M)."""
    return {name: p.detach().clone() for name, p in model.named_parameters()}


def update_ratios(before: dict[str, torch.Tensor], model: nn.Module) -> dict[str, float]:
    """u_g = ‖W_now − W_before‖ / ‖W_before‖ per group."""
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    for name, p in model.named_parameters():
        g = param_group_of(name)
        d = (p.detach() - before[name]).float()
        num[g] = num.get(g, 0.0) + float(d.pow(2).sum())
        den[g] = den.get(g, 0.0) + float(before[name].float().pow(2).sum())
    return {g: math.sqrt(num[g]) / max(math.sqrt(den[g]), 1e-12) for g in num}


def find_nonfinite(model: nn.Module) -> list[str]:
    """Names of parameters/gradients/buffers containing NaN or Inf."""
    bad: list[str] = []
    for name, p in model.named_parameters():
        if not torch.isfinite(p).all():
            bad.append(f"param:{name}")
        if p.grad is not None and not torch.isfinite(p.grad).all():
            bad.append(f"grad:{name}")
    for name, b in model.named_buffers():
        if b.is_floating_point() and not torch.isfinite(b).all():
            bad.append(f"buffer:{name}")
    return bad
