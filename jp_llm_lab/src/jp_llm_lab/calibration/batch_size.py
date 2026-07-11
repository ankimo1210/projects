"""Batch-size calibration (spec §14.4).

Train the same model to the same TOKEN budget with different effective batch
sizes (tokens per optimizer step), and compare convergence per step, per
token, and per wall-clock second. Guards against the "fewer steps = faster"
illusion: fewer steps at a larger batch see the same tokens.
"""

from __future__ import annotations

import time

import torch

from ..data.batches import sample_batch
from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT
from ..training.train_config import TrainConfig
from ..training.trainer import make_optimizer
from ..utils.seed import make_generator, set_seed


def batch_size_calibration(
    vocab_size: int,
    train_tokens: torch.Tensor,
    val_tokens: torch.Tensor,
    effective_token_targets: list[int],
    total_tokens: int = 2_000_000,
    context_len: int = 256,
    micro_batch: int = 16,
    lr: float = 6e-4,
    device: str = "cpu",
    seed: int = 0,
    d_model: int = 256,
    n_layers: int = 4,
    n_heads: int = 8,
) -> list[dict]:
    from ..evaluation.eval_lm import estimate_loss

    results = []
    for eff_tokens in effective_token_targets:
        grad_accum = max(1, eff_tokens // (micro_batch * context_len))
        tokens_per_step = micro_batch * context_len * grad_accum
        n_steps = total_tokens // tokens_per_step

        set_seed(seed)
        model = ClassicalGPT(
            ModelConfig(vocab_size=vocab_size, d_model=d_model, n_layers=n_layers,
                        n_heads=n_heads, context_len=context_len)
        ).to(device)
        opt = make_optimizer(model, TrainConfig(lr=lr, weight_decay=0.1))
        gen = make_generator(seed + 1)
        curve = []
        t0 = time.perf_counter()
        for step in range(1, n_steps + 1):
            opt.zero_grad(set_to_none=True)
            for _ in range(grad_accum):
                x, y = sample_batch(train_tokens, micro_batch, context_len, gen, device)
                _, loss = model(x, y)
                (loss / grad_accum).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            if step % max(1, n_steps // 10) == 0 or step == n_steps:
                vloss = estimate_loss(model, val_tokens, 8, micro_batch, context_len, device)["loss"]
                curve.append(
                    {
                        "step": step,
                        "tokens": step * tokens_per_step,
                        "wallclock": round(time.perf_counter() - t0, 2),
                        "val_loss": round(vloss, 4),
                    }
                )
        results.append(
            {
                "effective_tokens": eff_tokens,
                "grad_accum": grad_accum,
                "tokens_per_step": tokens_per_step,
                "n_steps": n_steps,
                "final_val_loss": curve[-1]["val_loss"],
                "wallclock_sec": curve[-1]["wallclock"],
                "curve": curve,
            }
        )
    return results
