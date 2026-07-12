"""The instrumented training loop — written flat so it can be read top-to-bottom.

One optimizer step =
    grad_accum × [ sample batch → autocast forward → backward(loss/grad_accum) ]
    → gradient stats → clip → (snapshot) → AdamW step → (update ratios)

Everything observable is appended to `metrics.jsonl` in the run directory:
    {"type":"train", step, tokens_seen, elapsed_sec, loss, lr, grad_norm,
     grad_norms:{group:…}, clip_hit, tokens_per_sec, vram_gb, update_ratios?}
    {"type":"eval",  step, tokens_seen, train_eval:{loss,ppl,…},
     val_eval:{…}, activation_stats:{point:{rms,…}}}
    {"type":"checkpoint", step, frac, path}

Checkpoints are written at fixed fractions of training (0%, 1%, 5%, …, 100%)
and each checkpoint also samples the same fixed prompts (greedy + T=0.7), so
"what does the model say at 1% vs 100% of training" is directly comparable.
"""

from __future__ import annotations

import math
import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from ..data.batches import sample_batch
from ..evaluation.eval_lm import estimate_loss
from ..generation.sampler import SamplingConfig, generate
from ..instrumentation.activation_stats import ActivationRecorder
from ..instrumentation.grad_stats import find_nonfinite, grad_stats, snapshot_params, update_ratios
from ..utils.io import append_jsonl, save_json
from ..utils.runmeta import collect_run_metadata
from ..utils.seed import make_generator, set_seed
from .train_config import TrainConfig


@dataclass
class RunResult:
    run_dir: Path
    steps: int
    tokens_seen: int
    wallclock_sec: float
    final_train_loss: float
    final_eval: dict


def lr_at(step: int, total_steps: int, cfg: TrainConfig) -> float:
    """Linear warmup → cosine decay to lr·min_lr_frac."""
    warmup = max(1, int(cfg.warmup_frac * total_steps))
    if step < warmup:
        return cfg.lr * step / warmup
    progress = (step - warmup) / max(1, total_steps - warmup)
    min_lr = cfg.lr * cfg.min_lr_frac
    return min_lr + 0.5 * (cfg.lr - min_lr) * (1 + math.cos(math.pi * progress))


def make_optimizer(model: nn.Module, cfg: TrainConfig) -> torch.optim.AdamW:
    """AdamW with weight decay only on matrices (embeddings/linear weights);
    biases and norm gains are excluded (standard GPT practice)."""
    decay = [p for p in model.parameters() if p.requires_grad and p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.requires_grad and p.dim() < 2]
    return torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": cfg.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ],
        lr=cfg.lr,
        betas=(cfg.beta1, cfg.beta2),
    )


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None,
    step: int,
    tokens_seen: int,
    extra: dict | None = None,
) -> Path:
    payload = {
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict() if optimizer is not None else None,
        "step": step,
        "tokens_seen": tokens_seen,
        "model_cfg": model.cfg.to_dict() if hasattr(model, "cfg") else None,
        "rng_torch": torch.get_rng_state(),
        "rng_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "extra": extra or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)
    return path


def load_checkpoint(
    path: Path | str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
) -> dict:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model_state"])
    if optimizer is not None and payload["optimizer_state"] is not None:
        optimizer.load_state_dict(payload["optimizer_state"])
    return payload


def _sample_fixed_prompts(model, tokenizer, cfg: TrainConfig, device, step, frac, out_path):
    if tokenizer is None or not cfg.fixed_prompts:
        return
    for prompt in cfg.fixed_prompts:
        ids = torch.tensor([tokenizer.encode(prompt)], dtype=torch.long, device=device)
        greedy_out, _ = generate(model, ids, SamplingConfig(max_new_tokens=cfg.max_new_tokens, greedy=True))
        # Same seed at every checkpoint → sampled continuations differ only
        # because the MODEL changed, not the random draws.
        sampled_out, _ = generate(
            model, ids, SamplingConfig(max_new_tokens=cfg.max_new_tokens, temperature=0.7, seed=cfg.seed + 7)
        )
        append_jsonl(
            {
                "step": step,
                "frac": frac,
                "prompt": prompt,
                "greedy": tokenizer.decode(greedy_out[0].tolist()),
                "temp07": tokenizer.decode(sampled_out[0].tolist()),
            },
            out_path,
        )


def train_lm(
    model: nn.Module,
    train_tokens: torch.Tensor,
    val_tokens: torch.Tensor,
    cfg: TrainConfig,
    run_dir: Path | str,
    tokenizer=None,
    device: str | None = None,
    extra_meta: dict | None = None,
) -> RunResult:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.jsonl"
    samples_path = run_dir / "samples.jsonl"
    ckpt_dir = run_dir / "checkpoints"

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = cfg.dtype == "bf16" and device == "cuda" and torch.cuda.is_bf16_supported()
    autocast_ctx = (
        torch.autocast(device_type="cuda", dtype=torch.bfloat16) if use_bf16 else nullcontext()
    )

    set_seed(cfg.seed)
    data_gen = make_generator(cfg.seed + 1)  # batch sampling stream, isolated from model RNG
    model.to(device)
    optimizer = make_optimizer(model, cfg)
    recorder = ActivationRecorder(model)

    # ---- reproducibility bundle (spec §3.2)
    breakdown = model.param_breakdown() if hasattr(model, "param_breakdown") else None
    save_json(
        {
            "train_config": cfg.to_dict(),
            "model_config": model.cfg.to_dict() if hasattr(model, "cfg") else None,
            "device": device,
            "autocast_bf16": use_bf16,
            "param_breakdown": breakdown,
            "n_train_tokens": len(train_tokens),
            "n_val_tokens": len(val_tokens),
            "planned_tokens": cfg.steps * cfg.batch_size * cfg.context_len * cfg.grad_accum,
        },
        run_dir / "config.json",
    )
    save_json(collect_run_metadata(extra_meta), run_dir / "runmeta.json")

    frac_of = {max(0, min(cfg.steps, round(f * cfg.steps))): f for f in sorted(cfg.checkpoint_fracs)}
    ckpt_steps = set(frac_of)

    def run_eval(step: int, tokens_seen: int) -> dict:
        train_eval = estimate_loss(
            model, train_tokens, cfg.eval_batches, cfg.batch_size, cfg.context_len, device, cfg.eval_seed
        )
        val_eval = estimate_loss(
            model, val_tokens, cfg.eval_batches, cfg.batch_size, cfg.context_len, device, cfg.eval_seed
        )
        with recorder:
            x, _ = sample_batch(val_tokens, min(8, cfg.batch_size), cfg.context_len, make_generator(cfg.eval_seed), device)
            with torch.no_grad():
                model(x)
        bad = find_nonfinite(model)
        rec = {
            "type": "eval",
            "step": step,
            "tokens_seen": tokens_seen,
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "train_eval": train_eval,
            "val_eval": val_eval,
            "activation_stats": recorder.stats(),
            "nonfinite": bad,
        }
        append_jsonl(rec, metrics_path)
        if bad:
            raise RuntimeError(f"non-finite values detected at step {step}: {bad[:5]}")
        return rec

    def do_checkpoint(step: int, tokens_seen: int) -> None:
        frac = frac_of[step]
        path = ckpt_dir / f"ckpt_{round(frac * 100):03d}pct_step{step:06d}.pt"
        save_checkpoint(path, model, optimizer, step, tokens_seen, extra={"frac": frac})
        append_jsonl({"type": "checkpoint", "step": step, "frac": frac, "path": str(path)}, metrics_path)
        _sample_fixed_prompts(model, tokenizer, cfg, device, step, frac, samples_path)

    # ---- initialization snapshot: eval + checkpoint + samples BEFORE any update
    t0 = time.perf_counter()
    run_eval(0, 0)
    if 0 in ckpt_steps:
        do_checkpoint(0, 0)

    tokens_seen = 0
    last_log_t, last_log_tokens = time.perf_counter(), 0
    final_train_loss = float("nan")
    model.train()

    for step in range(1, cfg.steps + 1):
        lr = lr_at(step, cfg.steps, cfg)
        for group in optimizer.param_groups:
            group["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        micro_losses = []
        for _ in range(cfg.grad_accum):
            x, y = sample_batch(train_tokens, cfg.batch_size, cfg.context_len, data_gen, device)
            with autocast_ctx:
                _, loss = model(x, y)
            (loss / cfg.grad_accum).backward()
            micro_losses.append(float(loss.detach()))

        log_now = step % cfg.log_interval == 0 or step == 1 or step == cfg.steps
        gstats = grad_stats(model) if log_now else None
        total_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip))

        measure_ratio = step % cfg.ratio_interval == 0 or step == 1
        snap = snapshot_params(model) if measure_ratio else None
        optimizer.step()
        ratios = update_ratios(snap, model) if snap is not None else None

        tokens_seen += cfg.batch_size * cfg.context_len * cfg.grad_accum
        final_train_loss = sum(micro_losses) / len(micro_losses)

        if log_now:
            now = time.perf_counter()
            tps = (tokens_seen - last_log_tokens) / max(now - last_log_t, 1e-9)
            last_log_t, last_log_tokens = now, tokens_seen
            rec = {
                "type": "train",
                "step": step,
                "tokens_seen": tokens_seen,
                "elapsed_sec": round(now - t0, 3),
                "loss": final_train_loss,
                "lr": lr,
                "grad_norm": total_norm,
                "clip_hit": total_norm > cfg.grad_clip,
                "grad_norms": {g: v["grad_norm"] for g, v in (gstats or {}).items()},
                "tokens_per_sec": round(tps, 1),
                "vram_gb": round(torch.cuda.memory_allocated() / 2**30, 3) if device == "cuda" else None,
            }
            if ratios is not None:
                rec["update_ratios"] = ratios
            append_jsonl(rec, metrics_path)

        if step % cfg.eval_interval == 0 or step in ckpt_steps or step == cfg.steps:
            run_eval(step, tokens_seen)
        if step in ckpt_steps:
            do_checkpoint(step, tokens_seen)

    wallclock = time.perf_counter() - t0
    final_eval = estimate_loss(
        model, val_tokens, cfg.eval_batches, cfg.batch_size, cfg.context_len, device, cfg.eval_seed
    )
    result = RunResult(
        run_dir=run_dir,
        steps=cfg.steps,
        tokens_seen=tokens_seen,
        wallclock_sec=wallclock,
        final_train_loss=final_train_loss,
        final_eval=final_eval,
    )
    save_json(
        {
            "steps": result.steps,
            "tokens_seen": result.tokens_seen,
            "wallclock_sec": round(wallclock, 2),
            "final_train_loss": result.final_train_loss,
            "final_eval": result.final_eval,
        },
        run_dir / "summary.json",
    )
    return result
