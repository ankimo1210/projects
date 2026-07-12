# Architecture Diagram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two Plotly diagrams (whole-model data flow, and a zoomed pre-LN
block-internals view) to the `architecture.html` page of the `jp_llm_lab`
static report site, replacing the current ASCII-text sketch.

**Architecture:** A new `visualization/architecture_viz.py` module exposes
two pure functions, `model_flow_figure(model_cfg)` and
`block_internals_figure(model_cfg)`, each building a `go.Figure` from
Plotly `shapes` (boxes/circles), `annotations` (labels + arrows), and one
invisible `Scatter` trace per figure that carries hover text at each box's
center (the standard technique for making Plotly `shapes` hoverable).
`site.py:page_architecture()` calls both and threads their HTML into the
existing block-list page schema.

**Tech Stack:** Python 3.11+, Plotly (`plotly.graph_objects`), pytest. No new
dependencies.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-12-architecture-diagram-design.md`
  (read for full rationale; this plan carries every value needed to implement
  it, so implementers do not need to open the spec).
- No new third-party dependency. Plotly is already a project dependency.
- Reuse `visualization/style.py`'s `GROUP_COLORS` dict (keys:
  `token_emb`, `pos_emb`, `attn_qkv`, `attn_proj`, `mlp`, `norm`, `lm_head`)
  for box fill colors — do not invent a parallel color scheme.
- Both new figures must render fully offline (no external requests) — this
  is automatic as long as no code adds a `<script src="http...">`; Plotly
  itself is already vendored via `assets/plotly.min.js` and `_fig()`'s
  `include_plotlyjs=False`.
- `model_cfg` is always the `"model_config"` sub-dict of a run's
  `config.json` (see exact keys in Task 1's test fixture below) — never the
  whole `config.json`.
- Diagrams depict the Modern preset as actually built (no Classical/Modern
  toggle). Component display names are computed from `model_cfg["norm"]`
  (`"rmsnorm"` → `"RMSNorm"`, else `"LayerNorm"`) and `model_cfg["mlp"]`
  (`"swiglu"` → `"SwiGLU"`, else `"GELU MLP"`) so the same functions would
  render correctly if ever pointed at a Classical run's config.
- All new prose in `site.py` blocks is Japanese, matching every existing page
  (this site is single-language; do not introduce i18n machinery).
- Run tests with `uv run --no-sync pytest jp_llm_lab/tests/<file> -v` from
  the workspace root (`/home/kazumasa/projects`) — this workspace's root
  `conftest.py` already imports `jp_llm_lab` explicitly to avoid the
  namespace-package collection bug; do not touch `conftest.py`.

---

### Task 1: `model_flow_figure` — whole-model data flow diagram

**Files:**
- Create: `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py`
- Create: `/home/kazumasa/projects/jp_llm_lab/tests/test_architecture_viz.py`

**Interfaces:**
- Consumes: `visualization/style.py`'s `GROUP_COLORS: dict[str, str]` (already
  exists, keys listed above).
- Produces: `model_flow_figure(model_cfg: dict) -> go.Figure` — a figure whose
  `layout.shapes` has exactly 3 `"rect"` entries (embedding box, transformer
  block box, final-norm+head box), positioned in a hidden `x∈[0,1], y∈[0,1]`
  data coordinate system (both axes `range=[0,1]`, `visible=False`), plus one
  `go.Scatter` trace (`mode="markers"`, `marker.opacity=0`) carrying
  `hovertext` per box center. Task 2 and Task 3 both import this function
  from `jp_llm_lab.visualization.architecture_viz`.

- [ ] **Step 1: Write the failing tests**

Create `/home/kazumasa/projects/jp_llm_lab/tests/test_architecture_viz.py`:

```python
"""Tests for architecture diagram figures.

Spec: docs/superpowers/specs/2026-07-12-architecture-diagram-design.md
"""
from __future__ import annotations

import json

import plotly.graph_objects as go

from jp_llm_lab.visualization.architecture_viz import model_flow_figure

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest jp_llm_lab/tests/test_architecture_viz.py -v`
(from `/home/kazumasa/projects`)
Expected: FAIL with `ModuleNotFoundError: No module named
'jp_llm_lab.visualization.architecture_viz'`

- [ ] **Step 3: Write the minimal implementation**

Create `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest jp_llm_lab/tests/test_architecture_viz.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py jp_llm_lab/tests/test_architecture_viz.py
git commit -m "feat(jp_llm_lab): add whole-model architecture flow diagram"
```

---

### Task 2: `block_internals_figure` — pre-LN residual zoom diagram

**Files:**
- Modify: `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py`
- Modify: `/home/kazumasa/projects/jp_llm_lab/tests/test_architecture_viz.py`

**Interfaces:**
- Consumes: `_norm_name`, `_mlp_name`, `_hidden_square_axes` helpers and the
  `GROUP_COLORS`/`_LINE`/`_ARROW` module constants defined in Task 1 (same
  file).
- Produces: `block_internals_figure(model_cfg: dict) -> go.Figure` — a figure
  whose `layout.shapes` has exactly 6 entries (4 `"rect"` component boxes:
  LN1, Attn, LN2, MLP; 2 `"circle"` residual-add junctions). Task 3 imports
  this alongside `model_flow_figure`.

- [ ] **Step 1: Write the failing tests**

Append to `/home/kazumasa/projects/jp_llm_lab/tests/test_architecture_viz.py`
(add this import at the top alongside the existing one):

```python
from jp_llm_lab.visualization.architecture_viz import block_internals_figure, model_flow_figure
```

(replace the Task-1 single-name import line with the two-name line above),
then append these test functions at the end of the file:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest jp_llm_lab/tests/test_architecture_viz.py -v`
Expected: FAIL — `ImportError: cannot import name 'block_internals_figure'`

- [ ] **Step 3: Write the minimal implementation**

Append to `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py`:

```python
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
        arrow(0.04, y_mid - 0.20, 0.52, y_mid - 0.065),   # residual bypass #1 (x -> add1)
        arrow(0.52, y_mid - 0.20, 0.94, y_mid - 0.065),   # residual bypass #2 (add1 -> add2)
    ]
    annotations.append(dict(x=0.04, y=y_mid + 0.20, text="x", showarrow=False,
                             font=dict(size=13, color=_LINE)))
    annotations.append(dict(x=0.99, y=y_mid + 0.20, text="output", showarrow=False,
                             font=dict(size=11, color=_ARROW)))
    annotations.append(dict(x=0.28, y=y_mid - 0.30, text="残差バイパス（恒等写像）",
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest jp_llm_lab/tests/test_architecture_viz.py -v`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add jp_llm_lab/src/jp_llm_lab/visualization/architecture_viz.py jp_llm_lab/tests/test_architecture_viz.py
git commit -m "feat(jp_llm_lab): add block-internals residual diagram"
```

---

### Task 3: wire both figures into `architecture.html`

**Files:**
- Modify: `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/reporting/site.py:21` (import line)
- Modify: `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/reporting/site.py:151-164` (`page_architecture`)
- Test: `/home/kazumasa/projects/jp_llm_lab/tests/test_architecture_viz.py` (no new file; this task is verified by rebuilding the real site, per Step 4 below — there is no existing `test_site.py` to extend, see Global Constraints/spec)

**Interfaces:**
- Consumes: `model_flow_figure(model_cfg: dict) -> go.Figure` and
  `block_internals_figure(model_cfg: dict) -> go.Figure` from Tasks 1-2;
  the existing `_fig(fig) -> str`, `interp(...) -> dict`, and
  `params_viz.param_breakdown_figure(breakdown: dict) -> go.Figure` already
  defined in `site.py` / `visualization/params_viz.py`.
- Produces: `SiteBuilder.page_architecture(self) -> dict` returning 4 blocks
  (prose, model-flow figure, block-internals figure, param-breakdown figure)
  instead of the current 2.

- [ ] **Step 1: Add the import**

In `/home/kazumasa/projects/jp_llm_lab/src/jp_llm_lab/reporting/site.py`,
change line 21 from:

```python
from ..visualization import comparison, curves, params_viz
```

to:

```python
from ..visualization import architecture_viz, comparison, curves, params_viz
```

- [ ] **Step 2: Replace `page_architecture`**

In the same file, replace the existing `page_architecture` method (currently
lines 151-164):

```python
    def page_architecture(self) -> dict:
        cfg = load_json(self.L / "config.json")
        return {"blocks": [
            {"html": "<p>Decoder-only Transformer を全て手書き実装（attention, block, 学習/評価/生成ループ, 計測フック）。"
                     "SDPA は explicit 実装と出力一致を検証した上で高速パスとしてのみ使用。</p>"
                     "<pre>residual stream: x → Norm → Attn → (+) → Norm → MLP → (+) → …\n"
                     "Classical: LayerNorm + learned pos + GELU + bias\n"
                     "Modern   : RMSNorm + RoPE + SwiGLU + bias-free</pre>"},
            {"figure": _fig(params_viz.param_breakdown_figure(cfg["param_breakdown"])), "meta": interp(
                "Model L のパラメータ構成比。", "容量の配分を知ることはスケーリングの前提。",
                "棒が高いほどパラメータが多い。", "MLP と token embedding が支配的。",
                "隠れ次元512・語彙8192では MLP が最大。",
                "パラメータ≠FLOPs。", "NB08 で FLOPs 内訳。")},
        ]}
```

with:

```python
    def page_architecture(self) -> dict:
        cfg = load_json(self.L / "config.json")
        mcfg = cfg["model_config"]
        norm_name = "RMSNorm" if mcfg["norm"] == "rmsnorm" else "LayerNorm"
        mlp_name = "SwiGLU" if mcfg["mlp"] == "swiglu" else "GELU MLP"
        return {"blocks": [
            {"html": "<p>Decoder-only Transformer を全て手書き実装（attention, block, 学習/評価/生成ループ, 計測フック）。"
                     "SDPA は explicit 実装と出力一致を検証した上で高速パスとしてのみ使用。"
                     "Classical（LayerNorm + learned pos + GELU + bias）→ Modern（RMSNorm + RoPE + SwiGLU + bias-free）"
                     "への切替アブレーションは <a href=\"ablation.html\">アブレーション</a> ページで比較。</p>"},
            {"figure": _fig(architecture_viz.model_flow_figure(mcfg)), "meta": interp(
                "Model L（Modern構成）の全体データフロー図。",
                "入力から出力までテンソルがどう変換されるかを一目で把握するため。",
                "上から下へ矢印の順にテンソルが流れる。箱にカーソルを合わせると実寸（次元・層数等）を表示。",
                f"d_model={mcfg['d_model']}, n_layers={mcfg['n_layers']}, n_heads={mcfg['n_heads']}, "
                f"vocab_size={mcfg['vocab_size']}。",
                "パラメータの大半はMLPとtoken embeddingに集中する（下図参照）が、計算量はブロックの繰り返しに支配される。",
                "簡略図であり、dropout・attn_implの分岐等の実装細部は省略。",
                "ブロック内部の詳細は次の図。")},
            {"figure": _fig(architecture_viz.block_internals_figure(mcfg)), "meta": interp(
                "TransformerBlock 内部の pre-LN 残差構造。",
                "「ブロックは入力を置き換えるのでなく、2つの分岐出力を足し込むだけ」という設計原理を可視化するため。",
                "x から右に読む。上段が主経路（Norm→Attn/MLP）、下段が残差バイパス（恒等写像）。",
                f"norm={mcfg['norm']}, mlp={mcfg['mlp']}（{norm_name}/{mlp_name}）。",
                "残差パスが恒等写像であることが、深いスタックでも学習が安定する理由（pre-LN の既知挙動）。",
                "1ブロック分の模式図。層間の違い（活性化の蓄積等）は training.html の RMS ヒートマップ参照。",
                "パラメータ配分の実測値は次の図。")},
            {"figure": _fig(params_viz.param_breakdown_figure(cfg["param_breakdown"])), "meta": interp(
                "Model L のパラメータ構成比。", "容量の配分を知ることはスケーリングの前提。",
                "棒が高いほどパラメータが多い。", "MLP と token embedding が支配的。",
                "隠れ次元512・語彙8192では MLP が最大。",
                "パラメータ≠FLOPs。", "NB08 で FLOPs 内訳。")},
        ]}
```

- [ ] **Step 3: Run the full test suite**

Run: `uv run --no-sync pytest jp_llm_lab/tests -q` (from `/home/kazumasa/projects`)
Expected: all tests pass (previous count + the 7 new tests from Tasks 1-2),
zero failures.

- [ ] **Step 4: Rebuild the real site and visually confirm**

Run: `uv run --no-sync python jp_llm_lab/scripts/build_site.py` (from
`/home/kazumasa/projects`)
Expected: exits 0, rewrites
`/home/kazumasa/projects/jp_llm_lab/reports/site/architecture.html`.

Then confirm the two new figures are actually embedded and box-labeled
correctly without opening a browser:

```bash
grep -o '"TransformerBlock<br>LN' /home/kazumasa/projects/jp_llm_lab/reports/site/architecture.html
grep -o 'RMSNorm' /home/kazumasa/projects/jp_llm_lab/reports/site/architecture.html | head -1
grep -o 'vocab_size=8192' /home/kazumasa/projects/jp_llm_lab/reports/site/architecture.html
```

Expected: all three greps find at least one match (Plotly serializes hover
text into the embedded JSON, so the raw strings are present in the file
even though Plotly renders them into JS at runtime — this only proves the
data made it into the HTML, not that it visually renders correctly).

Then open the file directly in a browser to visually confirm no overlapping
boxes/clipped text:

```
file:///home/kazumasa/projects/jp_llm_lab/reports/site/architecture.html
```

- [ ] **Step 5: Commit**

```bash
git add jp_llm_lab/src/jp_llm_lab/reporting/site.py
git commit -m "feat(jp_llm_lab): wire architecture diagrams into architecture.html"
```

---

## Self-Review Notes (writing-plans skill)

- **Spec coverage:** every spec item has a task — new module (Tasks 1-2),
  `page_architecture` rewiring (Task 3), test file (Tasks 1-2), out-of-scope
  items (no toggle, no ablation.html change, no new dependency) respected
  throughout.
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code.
- **Type/signature consistency:** `model_flow_figure(model_cfg: dict) ->
  go.Figure` and `block_internals_figure(model_cfg: dict) -> go.Figure` are
  defined once in Tasks 1-2 and used with those exact names/signatures in
  Task 3 — no drift.
- Task 3 has no dedicated new unit test file because there is no existing
  `test_site.py` in this project to extend (confirmed absent during
  brainstorming) — Task 3's own verification is the real site rebuild plus
  grep/visual check in Step 4, which is stronger evidence for this
  integration point than a unit test mocking `SiteBuilder`.

## Execution Handoff

Plan complete and saved to
`/home/kazumasa/projects/jp_llm_lab/docs/superpowers/plans/2026-07-12-architecture-diagram.md`.
Two execution options:

1. **Subagent-Driven (recommended for larger plans)** — fresh subagent per
   task, review between tasks.
2. **Inline Execution** — I execute the 3 tasks directly in this session,
   checkpointing after each.

Given this plan is only 3 small, tightly-sequential tasks in one new file
plus one call site, Inline Execution is proportionate and faster here — but
either works. Which approach?
