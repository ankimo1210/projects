import pytest
import torch
from jp_llm_lab.models.attention import CausalSelfAttention


def _attn(impl="explicit", d=64, h=4, ctx=32):
    torch.manual_seed(0)
    return CausalSelfAttention(d, h, ctx, dropout=0.0, attn_impl=impl)


def test_attention_rows_sum_to_one():
    a = _attn()
    x = torch.randn(2, 16, 64)
    w = a.attention_weights(x)  # [B,H,T,T]
    assert w.shape == (2, 4, 16, 16)
    assert torch.allclose(w.sum(dim=-1), torch.ones(2, 4, 16), atol=1e-5)


def test_future_positions_have_zero_weight():
    a = _attn()
    w = a.attention_weights(torch.randn(2, 16, 64))
    future = torch.triu(torch.ones(16, 16, dtype=torch.bool), diagonal=1)
    assert (w[..., future] == 0).all()


def _parity(device):
    torch.manual_seed(1)
    a = _attn("explicit").to(device)
    x = torch.randn(2, 16, 64, device=device)

    x1 = x.clone().requires_grad_(True)
    y1 = a(x1)
    y1.square().sum().backward()

    a.set_attn_impl("sdpa")
    x2 = x.clone().requires_grad_(True)
    y2 = a(x2)
    y2.square().sum().backward()

    assert torch.allclose(y1, y2, atol=1e-5), (y1 - y2).abs().max()
    assert torch.allclose(x1.grad, x2.grad, atol=1e-4)


def test_explicit_matches_sdpa_cpu():
    _parity("cpu")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_explicit_matches_sdpa_cuda():
    _parity("cuda")


def test_trace_forces_explicit_records():
    a = _attn("sdpa")  # even in sdpa mode, tracing yields explicit tensors
    t: dict = {}
    a(torch.randn(1, 8, 64), trace=t, prefix="p")
    for key in ["p.q", "p.k", "p.v", "p.scores", "p.attn_weights", "p.out"]:
        assert key in t
    assert t["p.scores"].shape == (1, 4, 8, 8)
