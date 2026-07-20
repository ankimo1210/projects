# deep_hedge_price

`deep_hedge_price` is a CPU-capable, reproducible Deep Hedging demonstration for a short European call. It simulates physical-measure GBM paths, rolls one time-shared PyTorch policy across discrete hedge dates, differentiates through trading gains and proportional costs, and compares the learned hedge with no hedge and Black–Scholes baselines.

Phase 1 implements hedging. Phase 2 implements a separately configured and
validated neural-pricing surrogate; its ownership and acceptance criteria live in
[the Phase 2 roadmap](docs/ROADMAP_DEEP_PRICING.md). A hedge loss is never treated
as an option price.

## Financial setup

The simulator uses exact GBM discretization,

\[
S_{t+\Delta t}=S_t\exp\left[(\mu-\tfrac12\sigma^2)\Delta t+\sigma\sqrt{\Delta t}Z_t\right].
\]

With discounted spot \(\widetilde S_t=e^{-rt}S_t\), the net trading gain is

\[
G_T=\sum_{t=0}^{N-1}\delta_t(\widetilde S_{t+1}-\widetilde S_t)
-\sum_{t=0}^{N-1}e^{-rt}\lambda S_t|\delta_t-\delta_{t-1}|,
\qquad \delta_{-1}=0.
\]

For a short call, training loss is \(L_T=\widetilde H-G_T\). Economic reporting adds the time-zero Black–Scholes premium: discounted P&L is `premium - loss`. No terminal liquidation cost is added because it is absent from the supplied convention.

## Installation

Python 3.11 or newer is required.

```bash
cd /home/kazumasa/projects/deep_hedge_price
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Inside the parent uv workspace, the equivalent is:

```bash
cd /home/kazumasa/projects
uv sync --package deep-hedge-price
cd deep_hedge_price
```

## Exact commands

Tests:

```bash
pytest
# or
make test
```

Quick end-to-end demo on CPU:

```bash
make demo
```

Individual quick stages:

```bash
python -m deep_hedge_price.cli train --config configs/quick.yaml
python -m deep_hedge_price.cli evaluate --config configs/quick.yaml
python -m deep_hedge_price.cli sensitivity --config configs/quick.yaml
python -m deep_hedge_price.cli report --config configs/quick.yaml
python scripts/execute_notebook.py --config configs/quick.yaml
```

Canonical and full profiles:

```bash
python -m deep_hedge_price.cli demo --config configs/default.yaml
python -m deep_hedge_price.cli demo --config configs/full.yaml
```

Phase 2 pricing quick pipeline (CPU):

```bash
python -m deep_hedge_price.cli pricing-demo --config configs/pricing_quick.yaml
# or, as explicit artifact-consuming stages:
python -m deep_hedge_price.cli pricing-generate --config configs/pricing_quick.yaml
python -m deep_hedge_price.cli pricing-train --config configs/pricing_quick.yaml
python -m deep_hedge_price.cli pricing-evaluate --config configs/pricing_quick.yaml
python -m deep_hedge_price.cli pricing-report --config configs/pricing_quick.yaml
python -m deep_hedge_price.cli pricing-ablation --config configs/pricing_quick.yaml
```

The equivalent Make targets are `pricing-generate`, `pricing-train`,
`pricing-evaluate`, `pricing-report`, `pricing-ablation`, and `pricing-demo`. The
ablation uses one fixed subset for price-only, direct multi-task, and Differential
ML models across three initialization seeds, and writes the tracked reference
summary to `reports/pricing_ablation_<namespace>.json` without saving checkpoints.
Individual stages fail
with the exact preceding command when an input artifact is missing; they do not
silently regenerate it.

Notebook and HTML generation:

```bash
make notebook
make report
```

## Outputs

- Best policies, resolved configs, histories: `artifacts/checkpoints/`
- JSON metrics and sanity checks: `artifacts/metrics/`
- Path-level and experiment CSVs: `artifacts/data/`
- Matplotlib PNG/SVG figures: `artifacts/figures/`
- Executed notebook: `notebooks/01_deep_hedging_european_call.ipynb`
- Notebook export: `reports/01_deep_hedging_european_call.html`
- Interactive offline report: `reports/deep_hedging_report.html`
- Phase 2 datasets/checkpoints/evaluation: `artifacts/pricing/<namespace>/<fingerprint>/`
- Phase 2 artifact-only notebook: `notebooks/02_neural_pricing_surrogate.ipynb`
- Phase 2 offline report: `reports/neural_pricing_report_<namespace>.html`

The standalone report embeds Plotly JavaScript inline once, has no CDN or Python-server dependency, and switches between Japanese and English in place.

Volume 19/20 reference builders expose calculations without writing release
files. The central John Hull builder can serialize the returned finite arrays
and JSON-ready metrics under its own artifact contract:

```python
from deep_hedge_price.frontier_reference import build_frontier_reference

metrics, arrays = build_frontier_reference(19)  # or volume 20
```

The volume-20 reference compares persistence, EWMA, fitted GARCH(1,1),
Log-HAR, regularized linear, HARNet, TCN, LSTM, and a small encoder-only
Transformer on the same purged folds for 1/5/21-day targets.  QLIKE, RMSE,
MAE, block-bootstrap intervals, train-window volatility regimes, and
non-causal attention/permutation/occlusion/Integrated-Gradients diagnostics
are retained in the returned bundle.

The volume-20 core run records Phase 1 as `not_evaluated` unless real external
policy positions are explicitly supplied through the documented adapter.
Wall-clock calibration timing is kept separate from byte-reproducible volume-19
artifacts and can be measured with `benchmark_vol19_calibration()` for a
validation report.

## Project structure

Core finance, ML, evaluation, plotting, and reporting live under `src/deep_hedge_price/`. Thin scripts orchestrate package APIs. Config profiles are in `configs/`; tests mirror public modules; methodology and the next phase are in `docs/`.

## Reading the charts

- P&L distributions and ECDF use discounted, cost-inclusive economic P&L. Farther left is worse.
- VaR/CVaR operate on `-P&L`, so larger positive tail-loss numbers are worse.
- Policy heatmaps condition on a fixed previous hedge because the actual policy is five-dimensional.
- Cost sensitivity trains a separate policy at each cost but holds test paths fixed.
- Objective comparisons use common test paths and economic metrics, not incomparable raw training objectives.

## Reproducibility and limitations

Training, validation, and test seeds are disjoint. Training uses fresh paths per update; validation paths are fixed; all strategy comparisons use common random numbers. Checkpoints carry the complete resolved configuration and a hash.

Pricing train/validation/test/OOD rows have independent deterministic Latin-hypercube
designs and stored SHA-256 fingerprints. The loader rejects overlap, schema drift,
shape/dtype changes, and NPZ digest changes before torch is imported. Soft penalties
do not imply absence of arbitrage; the torch-free hullkit hard report is authoritative.

CUDA is selected only when `device: auto` and available. Exact CPU/GPU bitwise equality is not guaranteed even with deterministic settings. GBM assumes constant volatility and omits jumps, stochastic volatility, liquidity state, impact, and model uncertainty. Quick-profile tail estimates are less stable than full-profile estimates. This project is educational research, not investment advice.
