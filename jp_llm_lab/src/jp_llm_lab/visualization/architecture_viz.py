"""Architecture diagrams: whole-model data flow and block-internals zoom.

Both figures draw Plotly `shapes` (boxes/circles) and `annotations` (labels,
arrows) over a hidden [0,1]x[0,1] coordinate system, with one invisible
`Scatter` trace per figure supplying per-box hover text — the standard way
to make Plotly `shapes` hoverable (shapes themselves carry no hover events).
"""

from __future__ import annotations

import plotly.graph_objects as go

from .style import GROUP_COLORS

_LINE = "#1a1a2e"
_ARROW = "#5a5a72"


def _norm_name(model_cfg: dict) -> str:
    return "RMSNorm" if model_cfg["norm"] == "rmsnorm" else "LayerNorm"


def _mlp_name(model_cfg: dict) -> str:
    return "SwiGLU" if model_cfg["mlp"] == "swiglu" else "GELU MLP"


def _hidden_square_axes(fig: go.Figure) -> None:
    fig.update_xaxes(range=[0, 1], visible=False)
    fig.update_yaxes(range=[0, 1], visible=False)


def model_flow_figure(model_cfg: dict) -> go.Figure:
    """Whole-model flow: embeddings -> N transformer blocks -> head -> logits."""
    norm_name = _norm_name(model_cfg)
    mlp_name = _mlp_name(model_cfg)
    pos_label = "token_emb + pos_emb" if model_cfg["pos"] == "learned" else "token_emb<br>(RoPEはAttn内で適用)"

    boxes = [
        {
            "x0": 0.28, "x1": 0.72, "y0": 0.84, "y1": 0.98,
            "color": GROUP_COLORS["token_emb"],
            "label": pos_label,
            "hover": f"vocab_size={model_cfg['vocab_size']}<br>d_model={model_cfg['d_model']}"
                     f"<br>context_len={model_cfg['context_len']}",
        },
        {
            "x0": 0.16, "x1": 0.84, "y0": 0.50, "y1": 0.76,
            "color": GROUP_COLORS["attn_qkv"],
            "label": "TransformerBlock<br>LN→Attn→(+)→LN→MLP→(+)",
            "hover": f"n_layers={model_cfg['n_layers']}<br>n_heads={model_cfg['n_heads']}"
                     f"<br>norm={norm_name}<br>mlp={mlp_name}",
        },
        {
            "x0": 0.28, "x1": 0.72, "y0": 0.18, "y1": 0.32,
            "color": GROUP_COLORS["lm_head"],
            "label": "final_norm → lm_head",
            "hover": f"norm={norm_name}<br>vocab_size={model_cfg['vocab_size']}"
                     f"<br>tie_weights={model_cfg.get('tie_weights', True)}",
        },
    ]

    shapes = [
        dict(type="rect", x0=b["x0"], x1=b["x1"], y0=b["y0"], y1=b["y1"],
             line=dict(color=_LINE, width=1.5), fillcolor=b["color"], opacity=0.85, layer="below")
        for b in boxes
    ]
    annotations = [
        dict(x=(b["x0"] + b["x1"]) / 2, y=(b["y0"] + b["y1"]) / 2, text=b["label"],
             showarrow=False, font=dict(size=13, color=_LINE))
        for b in boxes
    ]
    annotations += [
        dict(ax=0.5, ay=0.84, x=0.5, y=0.76, xref="x", yref="y", axref="x", ayref="y",
             showarrow=True, arrowhead=2, arrowwidth=2, arrowcolor=_ARROW),
        dict(ax=0.5, ay=0.50, x=0.5, y=0.32, xref="x", yref="y", axref="x", ayref="y",
             showarrow=True, arrowhead=2, arrowwidth=2, arrowcolor=_ARROW),
        dict(ax=0.5, ay=0.18, x=0.5, y=0.05, xref="x", yref="y", axref="x", ayref="y",
             showarrow=True, arrowhead=2, arrowwidth=2, arrowcolor=_ARROW),
        dict(x=0.86, y=0.63, text=f"× {model_cfg['n_layers']}", showarrow=False,
             font=dict(size=13, color=_LINE), xanchor="left"),
        dict(x=0.5, y=1.0, text="input_ids [B,T]", showarrow=False,
             font=dict(size=11, color=_ARROW)),
        dict(x=0.5, y=0.02, text=f"logits [B,T,{model_cfg['vocab_size']}]", showarrow=False,
             font=dict(size=11, color=_ARROW)),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[(b["x0"] + b["x1"]) / 2 for b in boxes],
        y=[(b["y0"] + b["y1"]) / 2 for b in boxes],
        mode="markers", marker=dict(size=60, opacity=0),
        hovertext=[b["hover"] for b in boxes], hoverinfo="text", showlegend=False,
    ))
    fig.update_layout(
        shapes=shapes, annotations=annotations,
        title="モデル全体のデータフロー（Model L, Modern構成）",
        template="plotly_white", height=520,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    _hidden_square_axes(fig)
    return fig


def block_internals_figure(model_cfg: dict) -> go.Figure:
    """Zoom into one TransformerBlock's pre-LN residual structure.

    Mirrors the docstring diagram in models/blocks.py:
        x ── LN1 ─ Attention ──(+)── LN2 ─ MLP ──(+)──▶
        └────────────────────────┴──────────────────┘   (residual bypass)
    """
    norm_name = _norm_name(model_cfg)
    mlp_name = _mlp_name(model_cfg)
    y_mid = 0.55

    boxes = [
        {"x0": 0.14, "x1": 0.26, "color": GROUP_COLORS["norm"], "label": norm_name,
         "hover": f"pre-LN: {norm_name}(x) — attention分岐に入る前の正規化"},
        {"x0": 0.32, "x1": 0.46, "color": GROUP_COLORS["attn_qkv"], "label": "Attention",
         "hover": "causal multi-head self-attention（詳細は attention.html）"},
        {"x0": 0.58, "x1": 0.70, "color": GROUP_COLORS["norm"], "label": norm_name,
         "hover": f"pre-LN: {norm_name}(x) — MLP分岐に入る前の正規化"},
        {"x0": 0.76, "x1": 0.90, "color": GROUP_COLORS["mlp"], "label": mlp_name,
         "hover": f"{mlp_name} feed-forward"},
    ]
    junctions = [
        {"x": 0.52, "hover": "残差加算 #1: x + attn_out"},
        {"x": 0.94, "hover": "残差加算 #2: x + mlp_out"},
    ]

    shapes = [
        dict(type="rect", x0=b["x0"], x1=b["x1"], y0=y_mid - 0.12, y1=y_mid + 0.12,
             line=dict(color=_LINE, width=1.5), fillcolor=b["color"], opacity=0.85, layer="below")
        for b in boxes
    ] + [
        dict(type="circle", x0=j["x"] - 0.025, x1=j["x"] + 0.025, y0=y_mid - 0.06, y1=y_mid + 0.06,
             line=dict(color=_LINE, width=1.5), fillcolor="#ffffff", layer="below")
        for j in junctions
    ]

    annotations = [
        dict(x=(b["x0"] + b["x1"]) / 2, y=y_mid, text=b["label"], showarrow=False,
             font=dict(size=12, color=_LINE))
        for b in boxes
    ] + [
        dict(x=j["x"], y=y_mid, text="+", showarrow=False, font=dict(size=14, color=_LINE))
        for j in junctions
    ]

    def arrow(x0, y0, x1, y1):
        return dict(ax=x0, ay=y0, x=x1, y=y1, xref="x", yref="y", axref="x", ayref="y",
                     showarrow=True, arrowhead=2, arrowwidth=1.6, arrowcolor=_ARROW)

    annotations += [
        arrow(0.04, y_mid, 0.14, y_mid),                  # x -> LN1
        arrow(0.26, y_mid, 0.32, y_mid),                  # LN1 -> Attn
        arrow(0.46, y_mid, 0.495, y_mid),                 # Attn -> add1
        arrow(0.545, y_mid, 0.58, y_mid),                 # add1 -> LN2
        arrow(0.70, y_mid, 0.76, y_mid),                  # LN2 -> MLP
        arrow(0.90, y_mid, 0.915, y_mid),                 # MLP -> add2
        arrow(0.965, y_mid, 0.99, y_mid),                 # add2 -> output
        dict(x=0.52, y=0.25, ax=0.04, ay=0.25, xref="x", yref="y", axref="x", ayref="y",
             showarrow=True, arrowhead=0, arrowwidth=1.6, arrowcolor=_ARROW),  # bypass #1 horizontal run
        arrow(0.52, 0.25, 0.52, y_mid - 0.065),                                # bypass #1 rise into add1
        dict(x=0.94, y=0.25, ax=0.52, ay=0.25, xref="x", yref="y", axref="x", ayref="y",
             showarrow=True, arrowhead=0, arrowwidth=1.6, arrowcolor=_ARROW),  # bypass #2 horizontal run
        arrow(0.94, 0.25, 0.94, y_mid - 0.065),                                # bypass #2 rise into add2
    ]
    annotations.append(dict(x=0.04, y=y_mid + 0.20, text="x", showarrow=False,
                             font=dict(size=13, color=_LINE)))
    annotations.append(dict(x=0.99, y=y_mid + 0.20, text="output", showarrow=False,
                             font=dict(size=11, color=_ARROW)))
    annotations.append(dict(x=0.28, y=y_mid - 0.38, text="残差バイパス（恒等写像）",
                             showarrow=False, font=dict(size=10, color=_ARROW)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[(b["x0"] + b["x1"]) / 2 for b in boxes] + [j["x"] for j in junctions],
        y=[y_mid] * (len(boxes) + len(junctions)),
        mode="markers", marker=dict(size=50, opacity=0),
        hovertext=[b["hover"] for b in boxes] + [j["hover"] for j in junctions],
        hoverinfo="text", showlegend=False,
    ))
    fig.update_layout(
        shapes=shapes, annotations=annotations,
        title="TransformerBlock 内部（pre-LN 残差構造）",
        template="plotly_white", height=320,
        margin=dict(l=20, r=20, t=60, b=40),
    )
    _hidden_square_axes(fig)
    return fig
