"""Bigram language models — the simplest possible next-token predictors.

P(x_{t+1} = j | x_t = i) depends ONLY on the current token. Two versions:

- CountBigramLM: the closed-form maximum-likelihood estimate from pair counts
  (with additive smoothing α):  p_ij = (c_ij + α) / (Σ_j c_ij + α·V)
- NeuralBigramLM: a V×V logit table trained by SGD on cross-entropy.

Educational point (tested): the neural model has no extra expressive power —
gradient descent just re-derives the count table, so its loss converges to the
count model's loss from above. Everything a Transformer adds (context beyond
one token) is measured against this baseline.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn


class CountBigramLM:
    def __init__(self, vocab_size: int, alpha: float = 0.5):
        self.vocab_size = vocab_size
        self.alpha = alpha
        self.counts = torch.zeros(vocab_size, vocab_size)
        # before fit(): uniform distribution
        self.log_probs = torch.full((vocab_size, vocab_size), -math.log(vocab_size))

    def fit(self, ids: torch.Tensor) -> CountBigramLM:
        assert ids.dim() == 1 and len(ids) >= 2
        V = self.vocab_size
        pair_index = ids[:-1].long() * V + ids[1:].long()
        self.counts = torch.bincount(pair_index, minlength=V * V).view(V, V).float()
        probs = (self.counts + self.alpha) / (self.counts.sum(dim=1, keepdim=True) + self.alpha * V)
        self.log_probs = probs.log()
        return self

    def loss(self, ids: torch.Tensor) -> float:
        """Mean negative log-likelihood (nats/token) of the transitions in ids."""
        return -self.log_probs[ids[:-1].long(), ids[1:].long()].mean().item()

    @torch.no_grad()
    def generate(self, start_id: int, max_new_tokens: int, generator: torch.Generator | None = None) -> list[int]:
        out = [start_id]
        probs = self.log_probs.exp()
        for _ in range(max_new_tokens):
            nxt = torch.multinomial(probs[out[-1]], 1, generator=generator).item()
            out.append(int(nxt))
        return out


class NeuralBigramLM(nn.Module):
    """logits[b,t] = table[idx[b,t]] — an Embedding used as a V×V logit table."""

    def __init__(self, vocab_size: int):
        super().__init__()
        self.vocab_size = vocab_size
        self.logit_table = nn.Embedding(vocab_size, vocab_size)
        nn.init.zeros_(self.logit_table.weight)  # start at the uniform distribution

    def forward(
        self, idx: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        logits = self.logit_table(idx)  # [B,T,V]
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, self.vocab_size), targets.reshape(-1))
        return logits, loss
