"""Supervised fine-tuning (instruction tuning) — spec §21.

Format (special tokens shared with pretraining, ids 4/5):
    <BOS> <USER> {instruction} <ASSISTANT> {response} <EOS>

Two loss regimes compared:
- assistant_only: loss masked to the response tokens (+ EOS) — the model is
  only trained to PRODUCE answers, not to model the prompts
- full_sequence: loss on every token (prompt + response)

Masking uses cross-entropy ignore_index=-100 (the model's loss already honors
it). The comparison shows that SFT mainly changes OUTPUT FORMAT/policy, not
stored knowledge.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import torch

from ..tokenization.base import ASSISTANT_ID, BOS_ID, EOS_ID, USER_ID
from ..training.train_config import TrainConfig
from ..training.trainer import make_optimizer
from ..utils.seed import make_generator, set_seed

IGNORE = -100


def format_example(tokenizer, instruction: str, response: str) -> tuple[list[int], int]:
    """Return (token_ids, n_prompt_tokens). Prompt = up to and incl <ASSISTANT>."""
    prompt = [BOS_ID, USER_ID, *tokenizer.encode(instruction), ASSISTANT_ID]
    body = [*tokenizer.encode(response), EOS_ID]
    return prompt + body, len(prompt)


def build_batch(
    examples: list[tuple[str, str]], tokenizer, context_len: int, assistant_only: bool, device: str
) -> tuple[torch.Tensor, torch.Tensor]:
    """Pad/truncate to context_len; targets masked per regime."""
    xs, ys = [], []
    for instruction, response in examples:
        ids, n_prompt = format_example(tokenizer, instruction, response)
        ids = ids[: context_len + 1]
        x = ids[:-1]
        y = ids[1:]
        if assistant_only:
            # mask targets that PREDICT a prompt token (positions < n_prompt-1)
            y = [(t if i >= n_prompt - 1 else IGNORE) for i, t in enumerate(y)]
        pad = context_len - len(x)
        x = x + [0] * pad
        y = y + [IGNORE] * pad
        xs.append(x)
        ys.append(y)
    return torch.tensor(xs, device=device), torch.tensor(ys, device=device)


@dataclass
class SFTResult:
    regime: str
    steps: int
    final_loss: float
    curve: list[dict]


def run_sft(
    model,
    examples: list[tuple[str, str]],
    tokenizer,
    assistant_only: bool,
    steps: int = 300,
    batch_size: int = 16,
    context_len: int = 256,
    lr: float = 3e-4,
    device: str = "cpu",
    seed: int = 0,
) -> SFTResult:
    set_seed(seed)
    model.to(device).train()
    opt = make_optimizer(model, TrainConfig(lr=lr, weight_decay=0.0))
    gen = make_generator(seed + 1)
    curve = []
    t0 = time.perf_counter()
    n = len(examples)
    for step in range(1, steps + 1):
        idx = torch.randint(0, n, (batch_size,), generator=gen)
        batch = [examples[int(i)] for i in idx]
        x, y = build_batch(batch, tokenizer, context_len, assistant_only, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % max(1, steps // 15) == 0 or step == 1:
            curve.append({"step": step, "loss": float(loss.detach()), "sec": round(time.perf_counter() - t0, 1)})
    return SFTResult(
        regime="assistant_only" if assistant_only else "full_sequence",
        steps=steps,
        final_loss=curve[-1]["loss"],
        curve=curve,
    )
