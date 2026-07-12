# Design: architecture design overview & diagram for the HTML report

**Date:** 2026-07-12
**Status:** Approved design
**Scope:** Add a visual architecture diagram to the existing `architecture.html`
page of the `jp_llm_lab` static report site, replacing the current ASCII-text
residual-stream sketch with real Plotly figures.

## Goal

The `architecture` page (`site.py:page_architecture`) currently explains the
decoder-only Transformer design in prose plus one ASCII `<pre>` block, and
shows only a parameter-breakdown bar chart. Readers get no visual sense of
data flow through the model. Add two Plotly diagrams that make the actual
Model L (Modern preset) architecture legible at a glance, consistent with the
rest of the site's figure style.

## Scope decisions (from brainstorming)

- **Diagram technology:** Plotly (`go.Figure` with `shapes`/`annotations`),
  matching every other figure in the report (`_fig()` wrapper, offline
  self-contained HTML, `plotly_white` template, `visualization/style.py`
  palette). Rejected: static inline SVG — would break stylistic consistency
  with the rest of the report's interactive figures for a one-off gain in
  layout precision that Plotly shapes can also achieve.
- **Coverage:** two diagrams.
  1. Whole-model flow: `token_emb (+ pos_emb)` → `TransformerBlock × n_layers`
     → `final_norm → lm_head` → `logits`.
  2. Block-internals zoom: the pre-LN residual structure inside one
     `TransformerBlock` (`x → LN1 → Attn → (+) → LN2 → MLP → (+) → output`),
     visualizing the docstring diagram already in
     `models/blocks.py`.
- **Classical vs. Modern:** diagrams depict the actual built model (Modern:
  RMSNorm + RoPE + SwiGLU + bias-free), not a toggle between variants. The
  Classical→Modern comparison is already the dedicated subject of
  `ablation.html`; duplicating it here would be redundant. The retained prose
  paragraph keeps its one-line Classical/Modern contrast for context.

## Architecture

**New module:** `src/jp_llm_lab/visualization/architecture_viz.py`

- `model_flow_figure(model_cfg: dict) -> go.Figure` — draws the whole-model
  flow as stacked rectangles (Plotly `shapes`, type `"rect"`) connected by
  vertical arrow annotations. `model_cfg` is the `"model_config"` sub-dict of
  a run's `config.json` (keys: `d_model`, `n_heads`, `n_layers`,
  `context_len`, `vocab_size`, `norm`, `pos`, `mlp`, `bias`). Each box's hover
  text reports the real dimensions/config values (e.g. the embedding box
  hovers `vocab_size=8192, d_model=512`; the block box hovers
  `n_layers=8, norm=rmsnorm, pos=rope, mlp=swiglu`). A `"× n_layers"` label
  sits beside the block box.
- `block_internals_figure(model_cfg: dict) -> go.Figure` — draws the
  zoomed single-block residual diagram: input node → `LN1` box → `Attn` box →
  add-junction → `LN2` box → `MLP` box → add-junction → output node, with the
  two residual bypass arrows drawn as curved/offset connector lines beneath
  the main row (mirroring the `blocks.py` docstring ASCII art). Box labels use
  the run's actual component names (`RMSNorm`/`LayerNorm`, `SwiGLU`/`GELU
  MLP`) taken from `model_cfg["norm"]` / `model_cfg["mlp"]`.

Both functions reuse `visualization/style.py`: box fill colors keyed by
`GROUP_COLORS` (already defined: `token_emb`, `pos_emb`, `attn_qkv`,
`attn_proj`, `mlp`, `norm`, `lm_head`) so the new diagrams share a palette
with the existing param-breakdown bar chart on the same page. Figure height
uses the existing `base_layout`-style conventions (`plotly_white` template,
consistent margins/fonts) but without axis lines/ticks (this is a diagram,
not a chart) — axes hidden via `showticklabels=False, showgrid=False,
zeroline=False`, matching how a schematic is normally built in Plotly.

## Changed units

- `src/jp_llm_lab/reporting/site.py` — `page_architecture()`:
  - Add the two new figures as the first two blocks (before the existing
    param-breakdown block), each with a `meta` narrative block in the
    established `interp(...)` 7-tuple house style (what/why/how/observation/
    interpretation/caveat/next) used by every other figure on the site.
  - Call site: `cfg["model_config"]` is passed to both new functions (the
    existing `cfg = load_json(self.L / "config.json")` already loads the full
    run config, which nests `model_config`).
  - The existing prose block's ASCII `<pre>` diagram is removed (superseded
    by the two figures); the surrounding prose sentence about hand-written
    implementation and Classical/Modern component contrast is kept.

## Testing

`tests/test_architecture_viz.py` (new):
- `model_flow_figure`/`block_internals_figure` each return a `go.Figure`.
- Each figure's `layout.shapes` contains the expected fixed count of boxes
  (3 for the flow diagram: emb / block / final+head; 2 add-junctions + 4
  component boxes for the internals diagram) — counts are independent of
  `model_cfg` values, so this is a plain equality assertion, not a
  range/property check.
- Hover text / annotation text contains the actual `model_cfg` values passed
  in (e.g. asserts `"8192"` and `"512"` appear somewhere in the flow figure's
  text when `vocab_size=8192, d_model=512`), proving the figures are
  data-driven rather than static images.
- Component-name assertions: given `norm="rmsnorm", mlp="swiglu"`, the
  internals figure's text contains `"RMSNorm"` and `"SwiGLU"` (not
  `"LayerNorm"`/`"GELU"`).
- No existing test currently references `page_architecture` directly
  (confirmed by search), so no other test needs updating for the block-count
  change.

## Out of scope

- No Classical/Modern toggle or dropdown inside the diagram.
- No changes to `ablation.html`, `training.html`, or any other page.
- No new third-party dependency — Plotly is already a project dependency.
- No changes to `models/blocks.py`, `models/transformer.py`, or any model
  code — this is a reporting-layer, visualization-only change.

## Acceptance criteria

- `make site` (in `jp_llm_lab/Makefile`, running `scripts/build_site.py`)
  renders `architecture.html` with two new interactive figures above the
  existing parameter-breakdown chart, each hoverable with real Model L
  values.
- New `tests/test_architecture_viz.py` passes.
- Full `jp_llm_lab` test suite stays green.
- Visual check in a browser: both diagrams render without overlapping boxes
  or clipped text at the site's default page width.
