"""Learning-rate range test (spec §14.2).

Run a short training with the LR increasing geometrically each step:

    η_t = η_min · (η_max/η_min)^(t/T)

and record loss, gradient norm, update ratio, activation RMS vs LR. The loss
typically falls, flattens, then diverges; a robust suggestion is ~1/10 of the
LR at the steepest smoothed-loss descent (well before the divergence point).
"""

from __future__ import annotations

import math

import torch

from ..data.batches import sample_batch
from ..instrumentation.grad_stats import snapshot_params, update_ratios
from ..training.train_config import TrainConfig
from ..training.trainer import make_optimizer
from ..utils.seed import make_generator, set_seed


def lr_range_test(
    model: torch.nn.Module,
    tokens: torch.Tensor,
    lr_min: float = 1e-6,
    lr_max: float = 1.0,
    n_steps: int = 100,
    batch_size: int = 16,
    context_len: int = 256,
    device: str = "cpu",
    seed: int = 0,
) -> dict:
    set_seed(seed)
    model.to(device).train()
    cfg = TrainConfig(lr=lr_min, weight_decay=0.0)
    opt = make_optimizer(model, cfg)
    gen = make_generator(seed + 1)
    records = []
    diverged_at = None
    best_loss = math.inf
    for t in range(n_steps):
        lr = lr_min * (lr_max / lr_min) ** (t / (n_steps - 1))
        for g in opt.param_groups:
            g["lr"] = lr
        x, y = sample_batch(tokens, batch_size, context_len, gen, device)
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss_val = float(loss.detach())
        loss.backward()
        gnorm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1e9))  # measure, don't clip
        snap = snapshot_params(model)
        opt.step()
        ratio = update_ratios(snap, model)
        mean_ratio = sum(ratio.values()) / len(ratio)
        records.append({"step": t, "lr": lr, "loss": loss_val, "grad_norm": gnorm, "update_ratio": mean_ratio})
        best_loss = min(best_loss, loss_val)
        if not math.isfinite(loss_val) or loss_val > 4 * best_loss + 5:
            diverged_at = lr
            break

    # smoothed loss & steepest descent (suggestion = lr at steepest / 10)
    lrs = [r["lr"] for r in records]
    losses = [r["loss"] for r in records if math.isfinite(r["loss"])]
    n = len(losses)
    smoothed = []
    for i in range(n):
        lo, hi = max(0, i - 2), min(n, i + 3)
        smoothed.append(sum(losses[lo:hi]) / (hi - lo))
    steepest_idx = 1
    steepest = 0.0
    for i in range(1, n):
        d = (smoothed[i] - smoothed[i - 1]) / (math.log(lrs[i]) - math.log(lrs[i - 1]) + 1e-12)
        if d < steepest:
            steepest, steepest_idx = d, i
    suggested = lrs[steepest_idx] / 10
    return {
        "records": records,
        "diverged_at_lr": diverged_at,
        "steepest_descent_lr": lrs[steepest_idx],
        "suggested_lr": suggested,
        "logic": "suggested = LR at steepest smoothed-loss descent / 10 (safety margin before divergence)",
    }
