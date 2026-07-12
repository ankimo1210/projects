# deep_hedge_price

`deep_hedge_price` is a CPU-capable, reproducible Deep Hedging demonstration for a short European call. It simulates physical-measure GBM paths, rolls one time-shared PyTorch policy across discrete hedge dates, differentiates through trading gains and proportional costs, and compares the learned hedge with no hedge and Black–Scholes baselines.

Phase 1 implements hedging only. Deep Pricing is deliberately deferred to [the Phase 2 roadmap](docs/ROADMAP_DEEP_PRICING.md).

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

The standalone report embeds Plotly JavaScript inline once, has no CDN or Python-server dependency, and switches between Japanese and English in place.

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

CUDA is selected only when `device: auto` and available. Exact CPU/GPU bitwise equality is not guaranteed even with deterministic settings. GBM assumes constant volatility and omits jumps, stochastic volatility, liquidity state, impact, and model uncertainty. Quick-profile tail estimates are less stable than full-profile estimates. This project is educational research, not investment advice.
