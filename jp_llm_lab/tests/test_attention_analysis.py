import torch
from jp_llm_lab.instrumentation import attention_analysis as aa
from jp_llm_lab.instrumentation.causal_analysis import head_ablation_effect
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def _maps():
    torch.manual_seed(0)
    model = ClassicalGPT(ModelConfig(vocab_size=50, d_model=32, n_heads=4, n_layers=2, context_len=16))
    return model, model.attention_maps(torch.randint(0, 50, (2, 12)))


def test_statistics_shapes_and_ranges():
    _model, maps = _maps()
    for m in maps:
        assert m.shape == (2, 4, 12, 12)
    ent = aa.entropy_per_head(maps[0])
    dist = aa.mean_attention_distance(maps[0])
    prev = aa.prev_token_ratio(maps[0])
    assert ent.shape == (4,) and (ent >= 0).all()
    assert dist.shape == (4,) and (dist >= 0).all()
    assert prev.shape == (4,) and (prev >= 0).all() and (prev <= 1).all()


def test_ratios_are_probabilities():
    _, maps = _maps()
    for m in maps:
        total = aa.prev_token_ratio(m) + aa.first_token_ratio(m) + aa.self_token_ratio(m)
        # each is mean mass on one key; the three keys are distinct for t>=2 so
        # the sum cannot exceed 1 (equality only if all mass on these 3 keys)
        assert (total <= 1.0 + 1e-5).all()


def test_head_similarity_diagonal_is_one():
    _, maps = _maps()
    sim = aa.head_similarity(maps[0])
    assert sim.shape == (4, 4)
    assert torch.allclose(sim.diagonal(), torch.ones(4), atol=1e-5)
    assert torch.allclose(sim, sim.t(), atol=1e-6)


def test_summarize_json_friendly():
    _, maps = _maps()
    s = aa.summarize(maps)
    assert s["n_layers"] == 2 and s["n_heads"] == 4
    assert len(s["entropy"]) == 2 and len(s["entropy"][0]) == 4


def test_head_ablation_increases_loss_somewhere():
    torch.manual_seed(1)
    model = ClassicalGPT(ModelConfig(vocab_size=40, d_model=32, n_heads=4, n_layers=2, context_len=16))
    idx = torch.randint(0, 40, (4, 12))
    eff = head_ablation_effect(model, idx, idx)
    assert eff.shape == (2, 4)
    # zeroing heads should not, on average, reduce loss below baseline much
    assert eff.max() > 0  # at least one head matters
