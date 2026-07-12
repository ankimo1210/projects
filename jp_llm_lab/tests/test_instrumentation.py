import torch
from jp_llm_lab.instrumentation.activation_stats import ActivationRecorder, residual_update_ratios
from jp_llm_lab.instrumentation.grad_stats import grad_stats, snapshot_params, update_ratios
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def _model():
    torch.manual_seed(0)
    return ClassicalGPT(ModelConfig(vocab_size=50, d_model=32, n_heads=2, n_layers=2, context_len=16))


def test_recorder_covers_observation_points():
    model = _model()
    rec = ActivationRecorder(model)
    with rec:
        model(torch.randint(0, 50, (2, 8)))
    stats = rec.stats()
    for key in ["tok_emb", "blocks.0.attn", "blocks.0.mlp", "blocks.0.resid", "blocks.1.resid", "ln_f"]:
        assert key in stats, sorted(stats)
        assert stats[key]["rms"] > 0
        assert stats[key]["finite"]


def test_recorder_detaches_cleanly():
    model = _model()
    n_hooks_before = sum(len(m._forward_hooks) for m in model.modules())
    rec = ActivationRecorder(model)
    with rec:
        model(torch.randint(0, 50, (1, 8)))
    n_hooks_after = sum(len(m._forward_hooks) for m in model.modules())
    assert n_hooks_before == n_hooks_after


def test_grad_stats_and_update_ratios():
    model = _model()
    x = torch.randint(0, 50, (2, 8))
    _, loss = model(x, x)
    loss.backward()
    gs = grad_stats(model)
    for group in ["token_emb", "pos_emb", "attn_qkv", "attn_proj", "mlp", "norm"]:
        assert group in gs
        assert gs[group]["grad_norm"] > 0
        assert gs[group]["param_norm"] > 0

    snap = snapshot_params(model)
    torch.optim.SGD(model.parameters(), lr=0.1).step()
    ratios = update_ratios(snap, model)
    assert all(r > 0 for r in ratios.values())


def test_residual_update_ratios_from_trace():
    model = _model()
    trace = model.trace_forward(torch.randint(0, 50, (1, 8)))
    ratios = residual_update_ratios(trace, n_layers=2)
    assert set(ratios) == {"block0.attn", "block0.mlp", "block1.attn", "block1.mlp"}
    assert all(v > 0 for v in ratios.values())
