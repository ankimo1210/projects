"""Initialization diagnostics (spec §14.3).

Before any training step, an initialization scheme fixes the distribution of
logits, activations, and gradients. We measure these at init for several
schemes so the choice can be made on evidence, not folklore.

Schemes compared:
- normal_0.02      : GPT-2 default (what the lab uses)
- normal_0.02_noscale : same but WITHOUT the 1/sqrt(2L) residual scaling
- xavier           : Xavier/Glorot uniform on linear weights
- kaiming          : Kaiming/He normal (fan_in, relu gain)
"""

from __future__ import annotations

import math

import torch
from torch import nn

from ..instrumentation.activation_stats import ActivationRecorder
from ..instrumentation.grad_stats import grad_stats
from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT
from ..utils.seed import set_seed


def _reinit(model: ClassicalGPT, scheme: str) -> None:
    for module in model.modules():
        if isinstance(module, nn.Linear):
            if scheme == "xavier":
                nn.init.xavier_uniform_(module.weight)
            elif scheme == "kaiming":
                nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
            else:  # normal variants
                nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, std=0.02)
    if scheme == "normal_0.02":  # re-apply residual scaling
        scaled = 0.02 / math.sqrt(2 * model.cfg.n_layers)
        for name, p in model.named_parameters():
            if name.endswith(("attn.proj.weight", "mlp.proj.weight", "mlp.w2.weight")):
                nn.init.normal_(p, std=scaled)


def diagnose_init(
    vocab_size: int,
    schemes: list[str],
    tokens: torch.Tensor,
    d_model: int = 256,
    n_layers: int = 6,
    n_heads: int = 8,
    context_len: int = 256,
    batch_size: int = 16,
    seed: int = 0,
) -> dict:
    from ..data.batches import sample_batch
    from ..utils.seed import make_generator

    results = {}
    for scheme in schemes:
        set_seed(seed)
        model = ClassicalGPT(
            ModelConfig(vocab_size=vocab_size, d_model=d_model, n_layers=n_layers,
                        n_heads=n_heads, context_len=context_len, attn_impl="explicit")
        )
        _reinit(model, scheme)
        model.eval()
        gen = make_generator(seed + 1)
        x, y = sample_batch(tokens, batch_size, context_len, gen, "cpu")

        rec = ActivationRecorder(model)
        with rec:
            logits, loss = model(x[:, :64], y[:, :64])
        acts = rec.stats()
        resid_rms = [acts[k]["rms"] for k in sorted(acts) if k.endswith(".resid")]

        with torch.no_grad():
            probs = torch.softmax(logits.float(), -1)
            entropy = float(-(probs * probs.clamp(min=1e-12).log()).sum(-1).mean())
            logit_std = float(logits.std())
        loss.backward()
        gstats = grad_stats(model)

        results[scheme] = {
            "init_loss": float(loss),
            "logit_std": logit_std,
            "softmax_entropy": entropy,
            "resid_rms_by_layer": [round(r, 4) for r in resid_rms],
            "grad_norm_total": math.sqrt(sum(v["grad_norm"] ** 2 for v in gstats.values())),
            "grad_norm_by_group": {g: round(v["grad_norm"], 5) for g, v in gstats.items()},
        }
    return results
