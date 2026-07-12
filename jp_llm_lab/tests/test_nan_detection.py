import math

import torch
from jp_llm_lab.instrumentation.grad_stats import find_nonfinite
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT


def _model():
    return ClassicalGPT(ModelConfig(vocab_size=30, d_model=32, n_heads=2, n_layers=1, context_len=8))


def test_clean_model_reports_nothing():
    assert find_nonfinite(_model()) == []


def test_nan_in_param_is_named():
    model = _model()
    with torch.no_grad():
        model.blocks[0].mlp.fc.weight[0, 0] = math.nan
    bad = find_nonfinite(model)
    assert "param:blocks.0.mlp.fc.weight" in bad


def test_inf_in_grad_is_named():
    model = _model()
    x = torch.randint(0, 30, (1, 8))
    _, loss = model(x, x)
    loss.backward()
    model.tok_emb.weight.grad[0, 0] = math.inf
    assert "grad:tok_emb.weight" in find_nonfinite(model)
