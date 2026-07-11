"""Modern-GPT components: RMSNorm, RoPE, SwiGLU, and the combined model."""

import torch
from jp_llm_lab.generation.sampler import SamplingConfig, generate
from jp_llm_lab.models.blocks import MLP, SwiGLU
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.norms import RMSNorm
from jp_llm_lab.models.rope import apply_rope, rope_angles
from jp_llm_lab.models.transformer import ClassicalGPT


def test_rmsnorm_matches_formula():
    torch.manual_seed(0)
    norm = RMSNorm(16)
    with torch.no_grad():
        norm.weight.mul_(1.7)
    x = torch.randn(3, 5, 16)
    expected = x / torch.sqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6) * norm.weight
    assert torch.allclose(norm(x), expected, atol=1e-5)


def test_rope_preserves_norm():
    cos, sin = rope_angles(32, 8)
    x = torch.randn(2, 4, 32, 8)
    y = apply_rope(x, cos, sin)
    assert torch.allclose(x.norm(dim=-1), y.norm(dim=-1), atol=1e-4)


def test_rope_scores_depend_only_on_relative_position():
    """⟨R(t)q, R(j)k⟩ must equal ⟨R(t+s)q, R(j+s)k⟩ — same q,k placed at
    shifted positions give the same attention score."""
    cos, sin = rope_angles(64, 8)
    q = torch.randn(8)
    k = torch.randn(8)

    def score(t: int, j: int) -> float:
        qt = apply_rope(q.view(1, 1, 1, 8).repeat(1, 1, 64, 1), cos, sin)[0, 0, t]
        kj = apply_rope(k.view(1, 1, 1, 8).repeat(1, 1, 64, 1), cos, sin)[0, 0, j]
        return float(qt @ kj)

    assert abs(score(10, 4) - score(30, 24)) < 1e-4  # both distance 6
    assert abs(score(10, 4) - score(10, 5)) > 1e-4  # different distance differs


def test_swiglu_param_parity_with_gelu():
    d = 256
    gelu = sum(p.numel() for p in MLP(d, bias=False).parameters())
    swiglu = sum(p.numel() for p in SwiGLU(d, bias=False).parameters())
    assert abs(swiglu - gelu) / gelu < 0.02, (gelu, swiglu)


def _modern(V=60):
    torch.manual_seed(0)
    return ClassicalGPT(
        ModelConfig.modern(vocab_size=V, d_model=32, n_heads=2, n_layers=2, context_len=16)
    )


def test_modern_no_future_leakage():
    model = _modern().eval()
    model.set_attn_impl("explicit")
    idx1 = torch.randint(0, 60, (2, 16))
    idx2 = idx1.clone()
    idx2[:, 10:] = (idx2[:, 10:] + 1) % 60
    with torch.no_grad():
        l1, _ = model(idx1)
        l2, _ = model(idx2)
    assert torch.allclose(l1[:, :10], l2[:, :10], atol=1e-5)


def test_modern_has_no_positional_parameters():
    model = _modern()
    names = [n for n, _ in model.named_parameters()]
    assert not any("pos_emb" in n for n in names)
    assert "pos_emb" not in model.param_breakdown()["groups"]
    # biasless: no .bias parameters anywhere
    assert not any(n.endswith(".bias") for n in names)


def test_modern_trace_and_generation():
    model = _modern()
    trace = model.trace_forward(torch.randint(0, 60, (1, 8)))
    assert "position_embeddings" not in trace
    assert trace["logits"].shape == (1, 8, 60)
    out, _ = generate(model, torch.randint(0, 60, (1, 4)), SamplingConfig(max_new_tokens=10, greedy=True))
    assert out.shape == (1, 14)


def test_modern_explicit_matches_sdpa():
    model = _modern().eval()
    idx = torch.randint(0, 60, (2, 12))
    model.set_attn_impl("explicit")
    with torch.no_grad():
        l1, _ = model(idx)
    model.set_attn_impl("sdpa")
    with torch.no_grad():
        l2, _ = model(idx)
    assert torch.allclose(l1, l2, atol=1e-5)
