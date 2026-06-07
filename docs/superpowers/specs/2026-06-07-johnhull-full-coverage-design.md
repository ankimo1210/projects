# johnhull Full Coverage Design — Hull 11e All-Chapter Notebooks

Date: 2026-06-07
Status: Approved (granularity/order/format/lineup confirmed with user)

## Goal

Extend the `johnhull/` project so that every chapter of Hull, "Options, Futures,
and Other Derivatives" (11th edition, 37 chapters) is covered by a learning
notebook. Today only Ch.15 (`notebooks/bsm_chapter15.ipynb`) and Ch.31–33
(`interest_rate_models/ir_models.ipynb`) are covered.

## Decisions (confirmed with user)

| Question | Decision |
|---|---|
| Granularity | Topic-grouped volumes (~12), not per-chapter |
| Qualitative chapters (1, 8, 16, 35, 36, 37) | One lightweight summary volume (markdown-centric) |
| Order | Foundations → applications (dependency order) |
| Format | Keep build-script → ipynb pattern; extract shared code into a common module |

## Architecture

### Directory layout

```
johnhull/
├── ROADMAP.md                  # 37-chapter coverage tracker (new)
├── hullkit/                    # shared module (new, uv workspace member)
│   ├── pyproject.toml
│   ├── src/hullkit/
│   │   ├── bsm.py              # BSM prices + analytic Greeks
│   │   ├── trees.py            # binomial/trinomial tree build + backward induction
│   │   ├── mc.py               # GBM path generation, variance reduction
│   │   ├── rates.py            # discounting, zero curves, forwards (generalize interest_rate_models/market_data.py)
│   │   └── nbplot.py           # ipympl/widget boilerplate (plt.ioff, draw_idle, KDE helpers)
│   └── tests/                  # pytest; reference values cross-checked against hull-derivatives skill
├── volumes/                    # new notebook volumes (1 volume = 1 directory)
│   ├── 01_foundations/
│   │   ├── build_notebook.py
│   │   ├── foundations.ipynb   # generated artifact
│   │   └── PROGRESS.md
│   └── ...
├── notebooks/                  # existing bsm_chapter15 (untouched)
└── interest_rate_models/       # existing ir_models (untouched)
```

- Existing two notebooks are NOT moved or modified.
- `hullkit` is added to the root `pyproject.toml` `[tool.uv.workspace]` members
  and participates in `make lint` / `make test`.
- New volumes build with `uv run` (not the legacy anaconda python used by
  `interest_rate_models`).

### Volume lineup and implementation order (Plan B, approved)

| # | Volume | Chapters | Tier |
|---|---|---|---|
| 1 | `01_foundations` | 13, 14 | foundations — **first sub-project** |
| 2 | `02_options_basics` | 10–12, 17, 18 | foundations |
| 3 | `03_greeks` | 19 | foundations |
| 4 | `04_futures_forwards_rates` | 2–6 | foundations |
| 5 | `05_vol_smile_estimation` | 20, 23 | intermediate |
| 6 | `06_numerical_methods` | 21, 27 | intermediate |
| 7 | `07_swaps` | 7, 34 | intermediate |
| 8 | `08_risk_var` | 22 | intermediate |
| 9 | `09_credit_xva` | 9, 24, 25 | advanced |
| 10 | `10_exotics_martingales` | 26, 28 | advanced |
| 11 | `11_ir_derivatives_market` | 29, 30 | advanced |
| 12 | `12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | summary (markdown-centric; include small compute cells where chapters have models, e.g. Schwartz commodity model, real-option trees) |

Already covered: Ch.15 (`bsm_chapter15`), Ch.31–33 (`ir_models`).
With all 12 volumes done → all 37 chapters covered.

Each volume is an independent sub-project with its own spec → plan →
implementation cycle. **This spec covers the overall architecture plus the
`01_foundations` sub-project in detail.** Later volumes get their own short
specs that reference this document.

### Notebook conventions (inherited from ir_models)

- Structure: title → standalone `%matplotlib widget` cell → imports/shared
  helpers → per-section Japanese markdown + interactive charts → exercises →
  summary.
- Widgets: ipywidgets FloatSlider/Dropdown; updates via `set_data` +
  `fig.canvas.draw_idle()`; `plt.ioff()` to avoid comm_id errors;
  `japanize_matplotlib` for Japanese labels.
- Soft cap of **35 cells per volume** (lesson from ir_models' 49-cell UX
  problem). Split the volume if it would exceed the cap.
- Each volume contains a numerical verification cell that asserts agreement
  with textbook example values (sourced from the hull-derivatives skill
  references).

## First sub-project: 01_foundations (Ch.13–14)

### Ch.13 Binomial Trees
- One-period → multi-period trees; risk-neutral probability `p`;
  CRR parameterization (`u = e^{σ√Δt}`).
- American early exercise on the tree.
- Convergence to BSM with an `n → ∞` slider.
- Delta computed on the tree.

### Ch.14 Wiener Processes and Itô's Lemma
- Wiener process path simulation with a `dt` slider.
- Generalized Wiener / Itô processes; lognormal stock price process.
- Numerical confirmation of Itô's lemma applied to `ln S`.
- Bridge to Ch.15 (existing BSM notebook).

### hullkit initial implementation
- `bsm.py` (needed as the convergence target), `trees.py`, `mc.py` basics.
- pytest suite with textbook reference values (e.g., CRR price converges to
  BSM; Hull example 13.1 numbers).

## Verification (Definition of Done per volume)

1. `uv run python build_notebook.py` regenerates the ipynb.
2. Headless execution of all cells passes (`jupyter nbconvert --execute` or
   nbclient) — real output observed, not just exit code.
3. hullkit pytest green, including textbook reference-value tests.
4. `make lint` / `make test` green workspace-wide.
5. Widget interactivity is verified manually by the user in Jupyter (agent
   verifies through headless execution; widget UX explicitly flagged as
   user-verified).
6. `ROADMAP.md` chapter statuses updated.

## Out of scope

- Modifying or migrating the existing `bsm_chapter15` / `ir_models` notebooks
  (including the ir_models Future Plan backlog — tracked separately in its
  PROGRESS.md).
- Market data downloads (all volumes use synthetic/textbook data).
- English translations of the notebook prose (Japanese only, matching the
  existing notebooks).
