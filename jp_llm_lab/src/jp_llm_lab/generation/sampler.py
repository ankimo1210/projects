"""Autoregressive generation loop with per-step observability.

The loop is deliberately explicit: crop context → forward → last-position
logits → temperature → top-k → top-p → softmax → choose (argmax | multinomial).
Every step optionally records the chosen token's probability, the top-10
candidates and the distribution entropy, feeding the generation-anatomy
analyses (spec §16) without any second implementation.

Order of operations matters and is fixed here: temperature FIRST reshapes the
distribution, THEN top-k/top-p truncate it. Greedy ignores temperature/seed by
definition (tested: deterministic across seeds).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn.functional as F


@dataclass
class SamplingConfig:
    max_new_tokens: int = 100
    temperature: float = 1.0
    top_k: int | None = None
    top_p: float | None = None
    greedy: bool = False
    seed: int | None = None
    stop_id: int | None = None  # stop early when the (single) sequence emits this id


@dataclass
class StepRecord:
    index: int
    chosen_id: int
    chosen_prob: float
    entropy: float  # nats, of the FINAL (post top-k/top-p) distribution
    cum_logprob: float
    top_ids: list[int] = field(default_factory=list)
    top_probs: list[float] = field(default_factory=list)


def _apply_top_k(logits: torch.Tensor, k: int) -> torch.Tensor:
    kth = torch.topk(logits, min(k, logits.size(-1)), dim=-1).values[..., -1:]
    return logits.masked_fill(logits < kth, float("-inf"))


def _apply_top_p(logits: torch.Tensor, p: float) -> torch.Tensor:
    sorted_logits, sorted_idx = torch.sort(logits, descending=True, dim=-1)
    probs = F.softmax(sorted_logits, dim=-1)
    cum = probs.cumsum(dim=-1)
    # Drop tokens once the cumulative mass BEFORE them already reaches p —
    # the first token crossing the threshold is kept.
    drop = (cum - probs) >= p
    sorted_logits = sorted_logits.masked_fill(drop, float("-inf"))
    return torch.full_like(logits, float("-inf")).scatter(-1, sorted_idx, sorted_logits)


@torch.no_grad()
def generate(
    model: torch.nn.Module,
    idx: torch.Tensor,
    cfg: SamplingConfig,
    record_steps: bool = False,
) -> tuple[torch.Tensor, list[StepRecord]]:
    """Extend idx [B,T0] by cfg.max_new_tokens. Step records only for B==1."""
    was_training = model.training
    model.eval()
    device = idx.device
    context_len = getattr(getattr(model, "cfg", None), "context_len", None)

    gen = None
    if cfg.seed is not None and not cfg.greedy:
        gen = torch.Generator(device=device)
        gen.manual_seed(cfg.seed)

    records: list[StepRecord] = []
    cum_logprob = 0.0
    for i in range(cfg.max_new_tokens):
        idx_cond = idx if context_len is None else idx[:, -context_len:]
        logits, _ = model(idx_cond)
        logits = logits[:, -1, :].float()  # next-token logits [B,V]

        if cfg.greedy:
            probs = F.softmax(logits, dim=-1)
            next_id = probs.argmax(dim=-1, keepdim=True)
        else:
            logits = logits / max(cfg.temperature, 1e-8)
            if cfg.top_k is not None:
                logits = _apply_top_k(logits, cfg.top_k)
            if cfg.top_p is not None:
                logits = _apply_top_p(logits, cfg.top_p)
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1, generator=gen)

        if record_steps and idx.size(0) == 1:
            p = probs[0]
            chosen = int(next_id[0, 0])
            chosen_p = float(p[chosen])
            cum_logprob += float(torch.log(torch.clamp(p[chosen], min=1e-12)))
            top = torch.topk(p, k=min(10, p.numel()))
            entropy = float(-(p * torch.log(torch.clamp(p, min=1e-12))).sum())
            records.append(
                StepRecord(
                    index=i,
                    chosen_id=chosen,
                    chosen_prob=chosen_p,
                    entropy=entropy,
                    cum_logprob=cum_logprob,
                    top_ids=top.indices.tolist(),
                    top_probs=[round(float(v), 6) for v in top.values],
                )
            )

        idx = torch.cat([idx, next_id], dim=1)
        if cfg.stop_id is not None and idx.size(0) == 1 and int(next_id[0, 0]) == cfg.stop_id:
            break

    if was_training:
        model.train()
    return idx, records
