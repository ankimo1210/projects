"""Forward-hook based activation statistics (spec §11).

ActivationRecorder attaches forward hooks at fixed observation points
(embeddings,每 block's attention/MLP branch outputs, the residual stream after
each block, final norm) and reduces each activation to scalar statistics
immediately — tensors are never stored, so recording is cheap enough to run
during training evals.
"""

from __future__ import annotations

import torch
from torch import nn


def tensor_stats(x: torch.Tensor) -> dict[str, float]:
    x = x.detach().float()
    rms = float(x.pow(2).mean().sqrt())
    mu = float(x.mean())
    std = float(x.std(unbiased=False))
    absmax = float(x.abs().max())
    # kurtosis (non-excess): E[(x-μ)^4]/σ^4 — 3 for a Gaussian; large values
    # signal heavy tails / outlier channels.
    centered = x - x.mean()
    kurt = float(centered.pow(4).mean() / (centered.pow(2).mean().pow(2) + 1e-12))
    zero_frac = float((x.abs() < 1e-8).float().mean())
    outlier_frac = float((x.abs() > 6 * max(rms, 1e-12)).float().mean())
    finite = bool(torch.isfinite(x).all())
    return {
        "rms": rms,
        "mean": mu,
        "std": std,
        "absmax": absmax,
        "kurtosis": kurt,
        "zero_frac": zero_frac,
        "outlier_frac": outlier_frac,
        "finite": finite,
    }


class ActivationRecorder:
    """Usage:
        rec = ActivationRecorder(model)
        with rec:                      # hooks attached
            model(x)
        rec.stats()                    # {point_name: {rms, mean, ...}}
    """

    def __init__(self, model: nn.Module):
        self.model = model
        self.points = self._observation_points(model)
        self._handles: list = []
        self.last: dict[str, dict[str, float]] = {}

    @staticmethod
    def _observation_points(model: nn.Module) -> dict[str, nn.Module]:
        points: dict[str, nn.Module] = {}
        for name, module in model.named_modules():
            if name == "tok_emb" or name == "ln_f":
                points[name] = module
            elif name.endswith(".attn") or name.endswith(".mlp"):
                points[name] = module  # branch outputs
            elif module.__class__.__name__ == "TransformerBlock":
                points[f"{name}.resid"] = module  # block output = residual stream
        return points

    def _make_hook(self, name: str):
        def hook(module: nn.Module, inputs, output):
            out = output[0] if isinstance(output, tuple) else output
            if isinstance(out, torch.Tensor):
                self.last[name] = tensor_stats(out)

        return hook

    def attach(self) -> ActivationRecorder:
        assert not self._handles, "already attached"
        for name, module in self.points.items():
            self._handles.append(module.register_forward_hook(self._make_hook(name)))
        return self

    def detach(self) -> None:
        for h in self._handles:
            h.remove()
        self._handles = []

    def __enter__(self) -> ActivationRecorder:
        return self.attach()

    def __exit__(self, *exc) -> None:
        self.detach()

    def stats(self) -> dict[str, dict[str, float]]:
        return dict(self.last)


def residual_update_ratios(trace: dict[str, torch.Tensor], n_layers: int) -> dict[str, float]:
    """r_l = ‖Δh_l‖₂ / ‖h_l‖₂ per branch (spec §11) from a forward trace.

    Measures how much each attention / MLP branch actually changes the
    residual stream relative to its current size, averaged over positions.
    """

    def ratio(delta: torch.Tensor, base: torch.Tensor) -> float:
        num = delta.float().norm(dim=-1)  # [B,T]
        den = base.float().norm(dim=-1).clamp(min=1e-12)
        return float((num / den).mean())

    out: dict[str, float] = {}
    h = trace["embeddings"]
    for i in range(n_layers):
        attn_out = trace[f"block{i}.attn.out"]
        out[f"block{i}.attn"] = ratio(attn_out, h)
        h_after_attn = trace[f"block{i}.resid_after_attn"]
        mlp_out = trace[f"block{i}.mlp_out"]
        out[f"block{i}.mlp"] = ratio(mlp_out, h_after_attn)
        h = trace[f"block{i}.resid_after_mlp"]
    return out
