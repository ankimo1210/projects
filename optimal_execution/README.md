# optimal_execution

`optimal_execution` is a synthetic, reproducible visual laboratory for market
microstructure and optimal execution. It connects interpretable classical
schedules, resilient liquidity, a reactive limit-order-book (LOB) simulator,
transaction-cost analysis (TCA), and bounded reinforcement-learning policies.

The project is educational research software, not a production trading system.
It uses no external market data, API, database, cloud service, or GPU.

## What the project answers

Faster execution lowers exposure to price moves but raises market impact.
Slower execution reduces immediate impact but increases timing risk. The lab
makes this trade-off visible through:

- temporary, permanent, transient, propagator, and square-root impact views;
- the analytical Almgren–Chriss trajectory and efficient frontier;
- an Obizhaeva–Wang-style resilient-liquidity optimizer;
- immediate, TWAP, VWAP-style, POV, AC, and resilience-aware schedules;
- market-only, limit-only, and mixed tactical execution in a reactive LOB;
- residual PPO around an AC baseline and a freer PPO policy;
- common-random-number TCA, stress tests, feature ablation, and model shift.

Market orders in the LOB consume displayed depth, walk deeper liquidity,
widen the spread, and alter future state. Passive orders use a FIFO queue-ahead
proxy and can suffer adverse selection. The no-footprint replay control shares
exogenous random draws but deliberately removes the agent's market reaction.

## Installation and exact reproduction

Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/) are expected. In
this repository workspace:

```bash
cd optimal_execution
make install
make test
make demo
```

`make demo` runs the practical CPU quick profile and creates all numerical
artifacts, eight RL checkpoints, static figures, the executed notebook, and
both standalone reports. Generated outputs are deterministic for a fixed
software environment and seed; generation timestamps and Git metadata differ.

Individual stages are available as:

```bash
python -m optimal_execution.cli classical --config configs/quick.yaml
python -m optimal_execution.cli lob --config configs/quick.yaml
python -m optimal_execution.cli train-rl --config configs/quick.yaml
python -m optimal_execution.cli evaluate --config configs/quick.yaml
python -m optimal_execution.cli report --config configs/quick.yaml --locale en
python -m optimal_execution.cli report --config configs/quick.yaml --locale ja
python -m optimal_execution.cli notebook --config configs/quick.yaml
python -m optimal_execution.cli all --config configs/quick.yaml
```

Existing checkpoints are reused. Add `--force` to `train-rl`, or
`--force-train` to `evaluate`/`all`, to retrain.

## Primary outputs

- Notebook source: `notebooks/01_optimal_execution_visual_lab.ipynb`
- Executed notebook: `notebooks/_executed/01_optimal_execution_visual_lab.ipynb`
- Notebook HTML: `reports/01_optimal_execution_visual_lab.html`
- English report: `reports/optimal_execution_report_en.html`
- Japanese report: `reports/optimal_execution_report_ja.html`
- Static PNG/SVG charts: `artifacts/figures/`
- CSV, Parquet, and compressed scenario data: `artifacts/data/`
- Summaries and provenance manifests: `artifacts/metrics/`
- PPO checkpoints: `artifacts/checkpoints/`

The English and Japanese reports are built from the same saved numbers and
embed the same quantitative fingerprint. Plotly is inlined, so the reports
open directly from disk without a Python server or CDN.

## Project structure

```text
configs/                quick, default, and full experiment profiles
locales/                structured English and Japanese report content
src/optimal_execution/  models, simulator, RL, TCA, experiments, plots, reports
notebooks/              executable visual narrative
scripts/                thin command wrappers
tests/                  deterministic unit and integration tests
docs/                   methodology, numerics, RL environment, limitations
artifacts/               reproducible generated data, metrics, figures, checkpoints
reports/                 standalone generated HTML
```

## Sign convention and interpretation

Inventory (x_t>0) is the number of shares remaining. A child quantity
(q_t\ge 0) reduces inventory:

\[
x_{t+1}=x_t-q_t.
\]

For a sell program, implementation shortfall is

\[
IS = X P_{\mathrm{arrival}}-\sum_i q_iP_i^{\mathrm{exec}}+\mathrm{fees}.
\]

The unified implementation also supports buys. Positive cost always means
worse execution than arrival. Economic implementation shortfall, inventory
risk, and the shaped RL reward are separate fields.

The synthetic TCA decomposition is exact because the simulator exposes latent
timing, spread, impact, fee, adverse-selection, and cleanup channels. These
components are not uniquely identifiable in real data.

## Major chart guide

- **AC trajectories:** higher risk aversion or volatility front-loads trades;
  higher temporary impact moves the schedule toward slower execution.
- **Efficient frontier:** expected impact cost is plotted against timing-risk
  standard deviation on one consistent bps scale.
- **Impact recovery:** resilience controls how quickly transient displacement
  decays after trading stops.
- **Market versus limit:** passive spread capture is read together with fill
  rate, adverse selection, and terminal cleanup.
- **Reactive versus replay:** the difference isolates the configured agent
  footprint under paired exogenous randomness.
- **Stress and ablation:** policy rankings are conditional on the simulator;
  they are not evidence of real-market causal importance or RL superiority.

## Runtime profiles

On the current CPU workspace, the quick profile took roughly 3 seconds for
classical experiments, 25 seconds for LOB experiments, about 4 minutes for a
fresh seven-checkpoint training stage, about 1 minute for evaluation, and a few
seconds for reports/notebook export. Hardware and early stopping change these
figures. A rerun reuses checkpoints and is materially faster.

`configs/full.yaml` is ready for 100,000 classical paths, 5,000 LOB test
episodes, 50,000 training episodes, and three RL seeds. It is intentionally not
run by `make demo` and may require hours on CPU.

## Documentation

- [Methodology](docs/METHODOLOGY.md)
- [Numerical methods](docs/NUMERICAL_METHODS.md)
- [RL environment](docs/RL_ENVIRONMENT.md)
- [Limitations and next steps](docs/LIMITATIONS_AND_NEXT_STEPS.md)

## Limitations

The market is stylized and uncalibrated to real order-level data. It omits
hidden liquidity, venue fragmentation, latency, strategic counterparties,
manipulation controls, multi-asset cross-impact, and most exchange rules.
Queue position and adverse selection are proxies. The quick profile has one RL
seed, so any apparent outperformance is descriptive only. See the limitations
document for the full scope and proposed extensions.
