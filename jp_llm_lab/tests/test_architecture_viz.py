"""Tests for architecture diagram figures.

Spec: docs/superpowers/specs/2026-07-12-architecture-diagram-design.md
"""
from __future__ import annotations

import json

import plotly.graph_objects as go

from jp_llm_lab.visualization.architecture_viz import block_internals_figure, model_flow_figure

MODEL_CFG = {
    "vocab_size": 8192,
    "d_model": 512,
    "n_heads": 8,
    "n_layers": 8,
    "context_len": 512,
    "dropout": 0.0,
    "attn_impl": "sdpa",
    "bias": False,
    "tie_weights": True,
    "init_std": 0.02,
    "residual_scaled_init": True,
    "norm": "rmsnorm",
    "pos": "rope",
    "mlp": "swiglu",
}


def _all_text(fig: go.Figure) -> str:
    """Concatenate every annotation text and hovertext string in the figure."""
    payload = json.loads(fig.to_json())
    parts = [str(a.get("text", "")) for a in payload["layout"].get("annotations", [])]
    for trace in payload["data"]:
        parts.extend(str(t) for t in (trace.get("hovertext") or []))
    return "\n".join(parts)


def test_model_flow_figure_returns_a_figure():
    fig = model_flow_figure(MODEL_CFG)
    assert isinstance(fig, go.Figure)


def test_model_flow_figure_has_three_boxes():
    fig = model_flow_figure(MODEL_CFG)
    rects = [s for s in fig.layout.shapes if s.type == "rect"]
    assert len(rects) == 3


def test_model_flow_figure_shows_real_config_values():
    text = _all_text(model_flow_figure(MODEL_CFG))
    assert "vocab_size=8192" in text
    assert "d_model=512" in text
    assert "n_layers=8" in text


def test_block_internals_figure_returns_a_figure():
    fig = block_internals_figure(MODEL_CFG)
    assert isinstance(fig, go.Figure)


def test_block_internals_figure_has_six_shapes():
    fig = block_internals_figure(MODEL_CFG)
    rects = [s for s in fig.layout.shapes if s.type == "rect"]
    circles = [s for s in fig.layout.shapes if s.type == "circle"]
    assert len(rects) == 4
    assert len(circles) == 2


def test_block_internals_figure_uses_modern_component_names():
    text = _all_text(block_internals_figure(MODEL_CFG))
    assert "RMSNorm" in text
    assert "SwiGLU" in text
    assert "LayerNorm" not in text
    assert "GELU" not in text


def test_block_internals_figure_uses_classical_component_names():
    classical_cfg = dict(MODEL_CFG, norm="layernorm", mlp="gelu")
    text = _all_text(block_internals_figure(classical_cfg))
    assert "LayerNorm" in text
    assert "GELU" in text
    assert "RMSNorm" not in text
    assert "SwiGLU" not in text
