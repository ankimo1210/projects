"""No-future-leakage at the FULL MODEL level (spec §27).

Changing tokens strictly after position t must leave logits at positions ≤ t
unchanged — for both attention implementations.
"""

import pytest
import torch
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


@pytest.mark.parametrize("impl", ["explicit", "sdpa"])
def test_no_future_leakage(impl):
    torch.manual_seed(0)
    cfg = ModelConfig(vocab_size=50, d_model=32, n_heads=2, n_layers=2, context_len=16, attn_impl=impl)
    model = ClassicalGPT(cfg).eval()

    idx1 = torch.randint(0, 50, (2, 16))
    idx2 = idx1.clone()
    idx2[:, 10:] = (idx2[:, 10:] + 1) % 50  # perturb only the future

    with torch.no_grad():
        l1, _ = model(idx1)
        l2, _ = model(idx2)

    assert torch.allclose(l1[:, :10], l2[:, :10], atol=1e-6)
    assert not torch.allclose(l1[:, 10:], l2[:, 10:], atol=1e-3)  # sanity: change did propagate
