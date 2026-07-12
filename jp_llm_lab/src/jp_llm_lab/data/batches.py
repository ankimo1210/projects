"""Batch sampling for next-token prediction.

The corpus is one long token stream. A training example is a random crop of
`context_len + 1` tokens: the first `context_len` are the input x, the last
`context_len` (shifted by one) are the targets y. Every position t therefore
trains the model to predict token t+1 — one batch contains B·T supervised
predictions, not just B.
"""

from __future__ import annotations

import torch


def split_tokens(ids: torch.Tensor, val_frac: float) -> tuple[torch.Tensor, torch.Tensor]:
    """Contiguous head/tail split (no shuffling — documents stay intact).

    Note: a contiguous split means train and val can differ in style if the
    text drifts (e.g. novel parts); this caveat is surfaced in the notebooks.
    """
    assert ids.dim() == 1
    n_val = int(len(ids) * val_frac)
    if n_val <= 0:
        raise ValueError("val_frac too small: validation split is empty")
    return ids[:-n_val], ids[-n_val:]


def sample_batch(
    tokens: torch.Tensor,
    batch_size: int,
    context_len: int,
    generator: torch.Generator | None = None,
    device: str | torch.device = "cpu",
) -> tuple[torch.Tensor, torch.Tensor]:
    """Random crops → (x[B,T], y[B,T]) with y[b,t] == x[b,t+1]'s next token."""
    max_start = len(tokens) - context_len - 1
    assert max_start >= 0, "corpus shorter than context_len+1"
    starts = torch.randint(0, max_start + 1, (batch_size,), generator=generator)
    x = torch.stack([tokens[s : s + context_len] for s in starts])
    y = torch.stack([tokens[s + 1 : s + context_len + 1] for s in starts])
    return x.to(device), y.to(device)
