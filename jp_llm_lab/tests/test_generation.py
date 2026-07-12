import torch
from jp_llm_lab.generation.sampler import SamplingConfig, generate
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def _model(V=60, ctx=16):
    torch.manual_seed(0)
    cfg = ModelConfig(vocab_size=V, d_model=32, n_heads=2, n_layers=2, context_len=ctx)
    return ClassicalGPT(cfg)


def test_greedy_is_deterministic():
    model = _model()
    idx = torch.randint(0, 60, (1, 4))
    out1, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=20, greedy=True, seed=1))
    out2, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=20, greedy=True, seed=999))
    assert torch.equal(out1, out2)


def test_seeded_sampling_reproducible():
    model = _model()
    idx = torch.randint(0, 60, (1, 4))
    a, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=30, temperature=1.0, seed=5))
    b, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=30, temperature=1.0, seed=5))
    c, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=30, temperature=1.0, seed=6))
    assert torch.equal(a, b)
    assert not torch.equal(a, c)  # different seed → different draw (w.h.p.)


def test_context_trimming_allows_long_generation():
    model = _model(ctx=16)
    idx = torch.randint(0, 60, (1, 12))
    out, _ = generate(model, idx, SamplingConfig(max_new_tokens=20, greedy=True))
    assert out.shape == (1, 32)  # 12 + 20, even though context_len is 16


def test_top_k_one_equals_greedy():
    model = _model()
    idx = torch.randint(0, 60, (1, 4))
    greedy, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=15, greedy=True))
    topk1, _ = generate(model, idx.clone(), SamplingConfig(max_new_tokens=15, top_k=1, seed=3))
    assert torch.equal(greedy, topk1)


def test_step_records():
    model = _model()
    idx = torch.randint(0, 60, (1, 4))
    _, recs = generate(
        model, idx, SamplingConfig(max_new_tokens=10, temperature=1.0, seed=0), record_steps=True
    )
    assert len(recs) == 10
    for r in recs:
        assert 0.0 <= r.chosen_prob <= 1.0
        assert r.entropy >= 0.0
        assert len(r.top_ids) == 10
        assert sorted(r.top_probs, reverse=True) == r.top_probs
    # cumulative logprob is non-increasing
    assert all(recs[i + 1].cum_logprob <= recs[i].cum_logprob + 1e-9 for i in range(len(recs) - 1))
