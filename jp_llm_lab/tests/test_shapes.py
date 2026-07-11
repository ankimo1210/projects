"""Tensor-shape trace matches the spec §8.4 table."""

import torch
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def test_trace_shapes():
    B, T, V, D, H, L = 2, 8, 100, 32, 2, 2
    cfg = ModelConfig(vocab_size=V, d_model=D, n_heads=H, n_layers=L, context_len=16)
    model = ClassicalGPT(cfg)
    trace = model.trace_forward(torch.randint(0, V, (B, T)))

    dh = D // H
    expected = {
        "input_ids": (B, T),
        "token_embeddings": (B, T, D),
        "position_embeddings": (1, T, D),
        "embeddings": (B, T, D),
        "block0.attn.q": (B, H, T, dh),
        "block0.attn.k": (B, H, T, dh),
        "block0.attn.v": (B, H, T, dh),
        "block0.attn.scores": (B, H, T, T),
        "block0.attn.attn_weights": (B, H, T, T),
        "block0.attn.out": (B, T, D),
        "block0.resid_after_attn": (B, T, D),
        "block0.mlp_out": (B, T, D),
        "block0.resid_after_mlp": (B, T, D),
        "final_norm": (B, T, D),
        "logits": (B, T, V),
        "probabilities": (B, T, V),
    }
    for name, shape in expected.items():
        assert name in trace, f"missing {name}"
        assert tuple(trace[name].shape) == shape, f"{name}: {tuple(trace[name].shape)} != {shape}"
    # every layer traced
    for i in range(L):
        assert f"block{i}.attn.attn_weights" in trace


def test_probabilities_sum_to_one():
    cfg = ModelConfig(vocab_size=30, d_model=32, n_heads=2, n_layers=1, context_len=8)
    model = ClassicalGPT(cfg)
    trace = model.trace_forward(torch.randint(0, 30, (1, 8)))
    sums = trace["probabilities"].sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5)


def test_model_s_param_count_in_range():
    cfg = ModelConfig(vocab_size=3000)  # defaults: d=128, L=4, H=4, ctx=256
    model = ClassicalGPT(cfg)
    total = model.param_breakdown()["total"]
    assert 1_000_000 <= total <= 2_000_000, total


def test_param_breakdown_sums_to_total():
    cfg = ModelConfig(vocab_size=200, d_model=64, n_heads=2, n_layers=3, context_len=32)
    model = ClassicalGPT(cfg)
    bd = model.param_breakdown()
    assert sum(bd["groups"].values()) == bd["total"]


def test_weight_tying_shares_storage():
    cfg = ModelConfig(vocab_size=200, d_model=32, n_heads=2, n_layers=1, context_len=8, tie_weights=True)
    model = ClassicalGPT(cfg)
    assert model.lm_head.weight is model.tok_emb.weight
    assert "lm_head" not in model.param_breakdown()["groups"]  # deduped

    untied = ClassicalGPT(
        ModelConfig(vocab_size=200, d_model=32, n_heads=2, n_layers=1, context_len=8, tie_weights=False)
    )
    assert untied.lm_head.weight is not untied.tok_emb.weight
    assert untied.param_breakdown()["groups"]["lm_head"] == 200 * 32
