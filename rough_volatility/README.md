# Rough Volatility Visual Lab

`rough_volatility` is a synthetic, CPU-only research and visualization lab for fractional paths, rough log-volatility, rough Bergomi-style pricing, a Heston benchmark, short-maturity implied-volatility skew, and Hawkes-driven volatility microstructure.

It is educational and quantitatively careful, but it is not a production calibration library. It downloads no market data and needs no network service after dependencies are installed.

## What “rough” means

For fractional Brownian motion, increments scale locally as

\[
\mathbb E\left[|B^H_{t+\Delta}-B^H_t|^2\right]\propto \Delta^{2H}.
\]

A small Hurst exponent such as \(H=0.1\) means low local regularity: magnifying the path reveals rapid fine-scale variation. This is not the same as high volatility, which describes amplitude. It is also not the same as long memory: for \(H<1/2\), fBM increments are anti-persistent even though transformed volatility levels may appear persistent.

The project demonstrates these distinctions with locally generated data and then asks how they affect volatility paths, option smiles, ATM skew, and roughness estimation.

## Quick start

From the workspace root:

```bash
cd /home/kazumasa/projects
uv sync --all-packages
uv run --no-sync pytest rough_volatility/tests -q -m "not slow"
make rough-vol
```

From this directory:

```bash
make test
make demo CONFIG=configs/quick.yaml
```

`make demo` runs experiments A–G, exports 24 figures in PNG and SVG, builds the self-contained interactive report, executes the 26-section notebook, and exports the executed notebook to HTML.

For a standalone editable install outside the workspace:

```bash
uv venv
uv pip install -e .
```

Python 3.12 or newer is required by this workspace member.

## Commands

```bash
python -m rough_volatility.cli paths --config configs/quick.yaml
python -m rough_volatility.cli options --config configs/quick.yaml
python -m rough_volatility.cli microstructure --config configs/quick.yaml
python -m rough_volatility.cli all --config configs/quick.yaml
python -m rough_volatility.cli report --config configs/quick.yaml
python scripts/execute_notebook.py --config configs/quick.yaml
```

Add `--force` to an experiment command to ignore matching cached artifacts. A manifest is reused only when its 12-character configuration fingerprint matches.

## Profiles

| Profile | fBM steps | H replications | rBergomi/Heston paths | Main grid | Strikes | Maturities |
|---|---:|---:|---:|---:|---:|---|
| `quick` | 2,048 | 100 | 10,000 | 200 | 11 | 0.05–1.00 years |
| `default` | 4,096 | 200 | 30,000 | 500 | 17 | 0.02–1.00 years |
| `full` | 8,192 | 500 | 100,000 | 500 | 21 | 0.02–1.00 years |

The full profile uses 20,000-path chunks. Runtime depends strongly on BLAS performance and notebook/figure export; no GPU is required.

## Experiments

- **A — Path roughness:** matched-scale fBM paths, local zooms, increments, ACF, and structure functions for several H values.
- **B — Estimator recovery:** variogram, madogram, and aggregated-variance estimates across truth and sample size, with bias, RMSE, and nominal coverage.
- **C — OU versus fOU:** ordinary and fractional OU log-volatility at broadly matched scale.
- **D — rBergomi versus Heston:** common-random-number spot/variance paths, terminal distributions, realized variance, leverage, smiles, and surfaces.
- **E — Short-maturity skew:** adaptive local strike windows and weighted power-law fits across H.
- **F — Hawkes microstructure:** Poisson, stable, and near-critical bivariate order flow, intensity, signed price, and rolling RV proxy.
- **G — Estimation fragility:** shared latent paths under observation noise, sampling strides, and raw/aggregated/pre-averaged processing.

## Outputs

```text
artifacts/
├── data/       # CSV evidence, each with provenance columns
├── metrics/    # provenance-stamped JSON metrics and validation gates
├── figures/    # 24 PNG + 24 SVG static figures
└── manifest.json
notebooks/
└── 01_rough_volatility_visual_lab.ipynb
reports/
├── rough_volatility_report_en.html
├── rough_volatility_report_ja.html
└── 01_rough_volatility_visual_lab.html
```

The standalone report embeds Plotly JavaScript once, has no remote script or stylesheet attributes, and opens directly from disk. LaTeX math in the report prose (callouts, the variable-definition table, the literature section) is converted to inline MathML at build time via `latex2mathml`, so equations render without MathJax/KaTeX or any network access; the equation gallery itself is rendered to inline SVG with matplotlib mathtext. The Japanese report additionally carries three report-only sections that the English edition omits until their locale entries are written: a prior-literature section (problems, proposals, results, and open questions of the rough-volatility literature, with a per-paper table and cards), a practical hedging/Greeks Q&A (distilled from `docs/HEDGING_HANDOFF.md`), and a short margin note on roughness and `H`. The nbconvert notebook export is a separate artifact and may retain nbconvert's default MathJax reference for equation rendering; the notebook code, data, and static figures themselves are local.

Every metrics JSON records seed, profile, parameter fingerprint, sample size, UTC timestamp, Git commit when available, and package version. CSVs repeat the same provenance fields.

## How to read the main charts

- **fBM paths and zoom:** compare local texture, not vertical range alone.
- **Structure functions:** the second-order log–log slope estimates \(2H\); only a bounded lag range is fitted.
- **Estimator recovery:** finite samples remain dispersed even before observation noise is added.
- **Variance paths:** rBergomi and Heston reuse the same standardized spot shocks, so visible differences primarily reflect dynamics.
- **IV smiles and skew:** read Monte Carlo uncertainty before comparing wings; skew power-law fits are finite-maturity diagnostics.
- **Hawkes panels:** clustering can produce a rough-looking RV proxy, but the effective H is descriptive only.
- **Noise heatmap:** an observed \(\widehat H<1/2\) can move substantially under sampling and preprocessing choices.

## Numerical choices worth knowing

- fBM uses Davies–Harte with recorded eigenvalue clipping diagnostics and a small-grid Cholesky fallback.
- rBergomi uses an exact grid-level joint Gaussian covariance and a Schur factorization, not a left-point Volterra kernel.
- The specification's 252-step grid was replaced by 500 steps (`default`/`full`) and 200 (`quick`) so every configured maturity lies exactly on the grid.
- Short-skew experiments use a separately refined grid for every maturity.
- Heston uses a projected full-truncation Euler scheme. Its default equity-like parameters violate the Feller condition by design.
- Hawkes kernels are simulated with scalar Ogata thinning; compensators and truncation flags are recorded.

See [Methodology](docs/METHODOLOGY.md), [Numerical methods](docs/NUMERICAL_METHODS.md), and [Limitations and next steps](docs/LIMITATIONS_AND_NEXT_STEPS.md) for details.

## Validation

```bash
uv run --no-sync ruff check rough_volatility/src rough_volatility/tests rough_volatility/scripts
uv run --no-sync pytest rough_volatility/tests -q -m "not slow"
uv run --no-sync pytest rough_volatility/tests -q -m slow
uv run --no-sync pytest -q
```

Acceptance checks cover covariance reconstruction, H recovery, Black–Scholes references, implied-volatility inversion, forward-variance and spot moments, Heston moments, skew fits, Hawkes stability/compensators, offline report structure, and notebook execution.

## Limits

No result here identifies a real-market data-generating process. There is no calibration, quote cleaning, nonstationary regime model, asynchronous trade/quote handling, or production risk control. The simulations are evidence about the implemented models and measurement procedures only.
