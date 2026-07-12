"""Gradient accumulation equivalence (spec §27).

Mean-reduction cross-entropy over B·T positions: one backward on the full
batch must equal two backwards on equal halves with loss/2 each. Checked in
float64 on CPU so the tolerance can be tight.
"""

import torch
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def test_grad_accumulation_equivalence():
    torch.manual_seed(0)
    model = ClassicalGPT(
        ModelConfig(vocab_size=30, d_model=32, n_heads=2, n_layers=2, context_len=16, dropout=0.0)
    ).double()
    x = torch.randint(0, 30, (8, 16))
    y = torch.randint(0, 30, (8, 16))

    # full batch
    model.zero_grad(set_to_none=True)
    _, loss = model(x, y)
    loss.backward()
    full = {n: p.grad.clone() for n, p in model.named_parameters()}

    # two half batches, loss scaled by 1/2 (equal token counts per half)
    model.zero_grad(set_to_none=True)
    for sl in (slice(0, 4), slice(4, 8)):
        _, loss = model(x[sl], y[sl])
        (loss / 2).backward()

    for n, p in model.named_parameters():
        assert torch.allclose(full[n], p.grad, atol=1e-12, rtol=1e-9), n
