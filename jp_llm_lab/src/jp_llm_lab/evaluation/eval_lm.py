"""Language-model evaluation on held-out tokens.

Reports (all in nats unless stated):
- loss: mean cross-entropy of next-token prediction
- ppl:  exp(loss) — "effective branching factor" the model is choosing among
- entropy: mean entropy of the predictive distribution (model uncertainty)
- top1_conf: mean max probability (raw confidence; calibration in M5 asks
  whether this confidence is EARNED)

The batch generator is re-seeded identically on every call, so successive
evaluations see the SAME batches — eval curves move because the model moved,
not because the eval set was resampled.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F

from ..data.batches import sample_batch
from ..utils.seed import make_generator


@torch.no_grad()
def estimate_loss(
    model: torch.nn.Module,
    tokens: torch.Tensor,
    n_batches: int,
    batch_size: int,
    context_len: int,
    device: str | torch.device,
    seed: int = 1234,
) -> dict[str, float]:
    was_training = model.training
    model.eval()
    gen = make_generator(seed)  # fixed batches across calls (see docstring)
    losses, entropies, confidences = [], [], []
    for _ in range(n_batches):
        x, y = sample_batch(tokens, batch_size, context_len, generator=gen, device=device)
        logits, loss = model(x, y)
        probs = F.softmax(logits.float(), dim=-1)
        entropies.append(float(-(probs * torch.log(probs.clamp(min=1e-12))).sum(-1).mean()))
        confidences.append(float(probs.max(dim=-1).values.mean()))
        losses.append(float(loss))
    if was_training:
        model.train()
    mean_loss = sum(losses) / len(losses)
    return {
        "loss": mean_loss,
        "ppl": math.exp(mean_loss),
        "entropy": sum(entropies) / len(entropies),
        "top1_conf": sum(confidences) / len(confidences),
    }
