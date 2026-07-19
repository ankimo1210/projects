# JohnHull Vol 27 Risk Desk (Advanced VaR/ES) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Date:** 2026-07-20
**Target project:** `johnhull`
**Spec:** `docs/superpowers/specs/2026-07-20-johnhull-vol27-risk-desk-design.md`
**Implementation scope for this execution:** Phase 1 through Phase 6
**Planned volume:** `volumes/27_risk_desk`

## 1. Objective

Add a tested daily-risk-management stack to `hullkit` and a reproducible teaching
volume covering:

1. VaR backtesting statistics: Kupiec POF, Christoffersen independence and
   conditional coverage, and the quantified Basel traffic-light framework;
2. filtered historical simulation (FHS) reusing the existing EWMA/GARCH teachers;
3. extreme value theory: peaks-over-threshold GPD fitting and closed-form tail
   VaR/ES;
4. risk decomposition: marginal/component/incremental VaR and ES with exact Euler
   additivity, both analytic-normal and simulation-based;
5. P&L explain: factor mapping, delta-gamma-vega Taylor attribution versus full
   revaluation, and limit utilization;
6. a desk-run capstone assembling a reproducible daily risk report;
7. an artifact-only vol.27 notebook backed by versioned synthetic JSON/NPZ
   references and semantic tests.

The implementation must remain torch-free, require no new production dependency,
and preserve the `synthetic-offline` release policy. Existing `hullkit.risk`
(vol 08, Hull-pinned) and `hullkit.volatility` are reused **unchanged**.

FRTB IMA (liquidity-horizon ES aggregation, NMRF, P&L attribution tests, IMA/SA
comparison) is out of scope and recorded in `ROADMAP.md` as a vol 28 candidate.

## 2. Sources of truth

- Kupiec (1995), *Techniques for Verifying the Accuracy of Risk Measurement
  Models* — POF likelihood ratio.
- Christoffersen (1998), *Evaluating Interval Forecasts* — independence and
  conditional-coverage LR tests.
- BCBS (1996), *Supervisory Framework for the Use of "Backtesting"* — traffic
  light zones and multiplier add-ons (250-day, 99%).
- Barone-Adesi, Giannopoulos, Vosper (1999) — filtered historical simulation.
- McNeil & Frey (2000); McNeil, Frey, Embrechts *QRM* — POT/GPD tail VaR/ES.
- Tasche (1999/2008) — Euler allocation and component risk measures.
- Hull RMFI provides conceptual framing only; validation is G8-style acceptance
  (self-contained numerical identities), not textbook pins.

## 3. Architecture and ownership

```text
hullkit.risk (vol 08, unchanged) ──┬─> hullkit.var_backtest
hullkit.volatility (unchanged) ────┼─> hullkit.tail_risk
                                   ├─> hullkit.risk_allocation
hullkit.bsm (unchanged) ───────────┴─> hullkit.pnl_explain
                                            │
                                            └─> vol.27 reference + notebook + portal page
```

| Module | Responsibility |
|---|---|
| `hullkit.var_backtest` | Exceedance series, Kupiec POF, Christoffersen independence/CC, Basel traffic light |
| `hullkit.tail_risk` | FHS VaR/ES, GPD MLE (POT), closed-form EVT VaR/ES, mean-excess diagnostics |
| `hullkit.risk_allocation` | Analytic-normal marginal/component, historical incremental, simulation Euler ES components |
| `hullkit.pnl_explain` | Factor exposure aggregation, delta-gamma-vega Taylor P&L, attribution, limits, desk report |

Notebook builders remain presentation layers. Financial identities and hard
validation belong to `hullkit` and its tests.

## 4. Global mathematical contract

### 4.1 Conventions (shared with `hullkit.risk`)

- P&L arrays have **gains positive**; VaR and ES are returned as **positive loss
  amounts**.
- `alpha` is the coverage level (default `0.99`); the exceedance probability is
  `p = 1 - alpha`.
- Historical tail selection everywhere reuses the vol 08 convention:
  `k = max(1, ceil((1-alpha)*n - 1e-9))`, VaR = k-th worst loss, ES = mean of the
  k worst losses. Simulation-based allocation MUST use this exact selection so
  Euler additivity is exact by construction.
- An exceedance on day i means `-pnl[i] > var_forecast[i]` (strict).

### 4.2 Backtest likelihood ratios

With `n` observations, `x` exceedances, `p = 1 - alpha`, `pi_hat = x/n`:

```math
LR_{pof} = -2\ln\frac{(1-p)^{n-x}p^{x}}{(1-\hat\pi)^{n-x}\hat\pi^{x}} \sim \chi^2(1)
```

with the convention `0 \cdot \ln 0 = 0`. For independence, count transitions
`n_{00}, n_{01}, n_{10}, n_{11}` over the `n-1` transition pairs and let
`\pi_{01} = n_{01}/(n_{00}+n_{01})`, `\pi_{11} = n_{11}/(n_{10}+n_{11})`,
`\bar\pi = (n_{01}+n_{11})/(n-1)`:

```math
LR_{ind} = -2\ln\frac{(1-\bar\pi)^{n_{00}+n_{10}}\bar\pi^{\,n_{01}+n_{11}}}
{(1-\pi_{01})^{n_{00}}\pi_{01}^{n_{01}}(1-\pi_{11})^{n_{10}}\pi_{11}^{n_{11}}}
\sim \chi^2(1)
```

Conditional coverage is computed on the **transition-conditioned sample** so the
decomposition is an exact identity:

```math
LR_{cc} = LR_{pof}^{(n-1)} + LR_{ind} \sim \chi^2(2)
```

where `LR_{pof}^{(n-1)}` is the POF statistic evaluated on the `n-1` transition
observations. The standalone `kupiec_pof` uses the full sample; docstrings state
the conditioning difference.

### 4.3 Basel traffic light

Zones from the binomial cumulative probability `P(X \le x)`, `X \sim B(n, p)`:
green `< 0.95`, yellow `[0.95, 0.9999)`, red `\ge 0.9999` (BCBS values; at
`n=250, p=0.01` this reproduces green `x \le 4`, yellow `5 \le x \le 9`, red
`x \ge 10`). Multiplier: green `3.00`; yellow `3.40/3.50/3.65/3.75/3.85` for
`x = 5..9`; red `4.00`. The count-keyed multiplier table is the 250-day BCBS
schedule and is documented as such when `n != 250`.

### 4.4 GPD tail (POT)

Exceedances `y_i = L_i - u > 0` over threshold `u`, `N_u` of `n` total losses.
Log-likelihood (`xi != 0`, `beta > 0`, support `1 + xi*y/beta > 0`):

```math
\ell(\xi,\beta) = -N_u\ln\beta - (1 + 1/\xi)\sum_i \ln(1 + \xi y_i/\beta)
```

MLE via Nelder-Mead with penalty for constraint violations (same style as
`garch11_fit`). `|xi| < 1e-6` switches to the exponential-limit formulas.
Tail measures for coverage `alpha` (with `xi < 1`):

```math
VaR_\alpha = u + \frac{\beta}{\xi}\Big[\Big(\frac{n}{N_u}(1-\alpha)\Big)^{-\xi} - 1\Big],
\qquad
ES_\alpha = \frac{VaR_\alpha + \beta - \xi u}{1 - \xi}
```

`xi >= 1` (infinite-mean regime) raises `ValueError` from `evt_var_es`.

### 4.5 Euler allocation

Normal-analytic with `C = corr \circ (v v^T)`, `\sigma_P = \sqrt{a^T C a}`:

```math
\frac{\partial VaR}{\partial a_i} = z_\alpha \frac{(Ca)_i}{\sigma_P},
\qquad
CVaR_i = a_i \frac{\partial VaR}{\partial a_i},
\qquad
\sum_i CVaR_i = z_\alpha \sigma_P = VaR
```

(exact identity, Euler's theorem for the homogeneous `\sigma_P`). Simulation ES
components: select the vol 08 tail set `T` of the **total** P&L, then
`CES_i = mean_{s \in T}(-pnl_{s,i})`; by linearity `\sum_i CES_i = ES(total)`
exactly. Ties are resolved deterministically via stable argsort of total P&L.

## 5. Phase 1 — `var_backtest`

### Files

- Add `johnhull/hullkit/src/hullkit/var_backtest.py`.
- Add `johnhull/hullkit/tests/test_var_backtest.py`.
- Update `johnhull/MODEL_INDEX.md` §6 when the module is added.

### API

```python
exceedance_series(pnl, var_forecasts)
# -> np.ndarray of 0/1 ints; ValueError on length mismatch or empty input

kupiec_pof(n_exceedances, n_obs, alpha=0.99)
# -> (lr_stat, p_value); chi2(1) via scipy.stats.chi2.sf; 0*log0 = 0

christoffersen_independence(exceedances)
# -> (lr_stat, p_value); chi2(1); ValueError if fewer than 2 observations;
#    degenerate all-zero/all-one series returns lr_stat 0.0 with p_value 1.0

christoffersen_cc(exceedances, alpha=0.99)
# -> (lr_stat, p_value); chi2(2); exact sum of transition-sample POF + independence

basel_traffic_light(n_exceedances, n_obs=250, alpha=0.99)
# -> BaselZone(zone: str, cumulative_probability: float, multiplier: float)
#    zone in {"green", "yellow", "red"} from binomial cumulative probability
```

`BaselZone` is a frozen dataclass. All statistics are plain floats.

### Validation (tests)

- Hand-computed `LR_pof` for `(n=250, x=5, alpha=0.99)` matches to `1e-10`.
- `x = round(n*p)` gives `LR_pof` near 0; `p_value` decreases as `|x - np|` grows.
- `x = 0` and `x = n` edge cases are finite (0·log0 convention).
- `christoffersen_cc == kupiec_pof(transitions) + christoffersen_independence`
  to `1e-12`, verified by recomputing the parts on a seeded random series.
- Clustered series (all exceedances adjacent) yields larger `LR_ind` than an
  evenly spread series with the same count.
- Traffic light at `n=250`: `x=4 -> green/3.00`, `x=5 -> yellow/3.40`,
  `x=9 -> yellow/3.85`, `x=10 -> red/4.00`; `cumulative_probability` matches
  `scipy.stats.binom.cdf` to `1e-12`.
- Invalid inputs (`alpha` outside (0,1), `x > n`, negative counts) raise
  `ValueError`.

## 6. Phase 2 — `tail_risk`

### Files

- Add `johnhull/hullkit/src/hullkit/tail_risk.py`.
- Add `johnhull/hullkit/tests/test_tail_risk.py`.
- Update `johnhull/MODEL_INDEX.md` §6.

### API

```python
filtered_historical_var_es(returns, sigma, alpha=0.99, current_sigma=None)
# devolatilize z_i = returns_i / sigma_i, rescale by current_sigma
# (default sigma[-1]), then reuse risk.historical_var_es on the rescaled
# scenarios. sigma is an aligned positive array (e.g. sqrt of ewma_variance
# or garch11_variance). -> (var, es)

@dataclass(frozen=True)
class GPDFit:
    xi: float
    beta: float
    threshold: float
    n_exceedances: int
    n_total: int

fit_gpd_pot(losses, threshold, min_exceedances=30)
# -> GPDFit; Nelder-Mead MLE per §4.4; ValueError if exceedances <
#    min_exceedances or the optimizer does not converge

evt_var_es(fit, alpha=0.99)
# -> (var, es) closed-form per §4.4; ValueError if xi >= 1 or the implied
#    VaR falls below the threshold (alpha not in the tail)

mean_excess(losses, thresholds)
# -> np.ndarray of mean excesses e(u) = mean(L - u | L > u); NaN where no
#    exceedances exist (diagnostic plot data, documented)
```

### Validation (tests)

- Constant `sigma` array: FHS equals plain `historical_var_es` to `1e-12`.
- Doubling `current_sigma` doubles FHS VaR and ES exactly (homogeneity).
- Seeded `scipy.stats.genpareto` sample (`xi=0.2, beta=1.0`, 2000 exceedances):
  recovery within `|xi_hat - xi| <= 0.1` and `|beta_hat/beta - 1| <= 0.15`.
- `evt_var_es` against direct `genpareto.ppf`-based tail quantile to `1e-8`
  (same fitted parameters), and the ES–VaR identity
  `ES == (VaR + beta - xi*u)/(1 - xi)` to `1e-12`.
- Exponential branch: `xi = 0` synthetic data fits `|xi_hat| < 0.1` and the
  `|xi| < 1e-6` formulas are used without error.
- Theoretical GPD mean excess is linear in `u` with slope `xi/(1-xi)`:
  regression slope on exact GPD `e(u)` matches to `1e-6`.
- `xi >= 1` fit raises from `evt_var_es`; too-few exceedances raise from
  `fit_gpd_pot`; non-positive `sigma` raises from `filtered_historical_var_es`.

## 7. Phase 3 — `risk_allocation`

### Files

- Add `johnhull/hullkit/src/hullkit/risk_allocation.py`.
- Add `johnhull/hullkit/tests/test_risk_allocation.py`.
- Update `johnhull/MODEL_INDEX.md` §6.

### API

```python
marginal_var_normal(amounts, vols, corr, alpha=0.99)
# -> np.ndarray dVaR/da_i = z_alpha * (C a)_i / sigma_P; reuses
#    risk.portfolio_sigma internals per §4.5

component_var_normal(amounts, vols, corr, alpha=0.99)
# -> np.ndarray a_i * marginal_i; sums exactly to normal_var(sigma_P, alpha)

incremental_var(pnl_matrix, position_index, alpha=0.99)
# -> float VaR(all positions) - VaR(all except position_index), both via
#    risk.historical_var_es on row-summed P&L

euler_es_components(pnl_matrix, alpha=0.99)
# -> np.ndarray CES_i per §4.5; sums exactly to ES of the total P&L
```

`pnl_matrix` is `(n_scenarios, n_positions)` with gains positive; the portfolio
P&L is the row sum. All functions validate shapes and finiteness.

### Validation (tests)

- `sum(component_var_normal) == normal_var(portfolio_sigma(...), alpha)` to
  `1e-12` on a seeded 5-asset book with non-trivial correlation.
- `marginal_var_normal` matches central finite differences of
  `normal_var(portfolio_sigma(a))` (`eps=1e-6`) to relative `1e-6`.
- `sum(euler_es_components(M)) == historical_var_es(M.sum(axis=1))[1]` to
  `1e-12`, including a tie case (duplicated worst scenario rows).
- `incremental_var` of an uncorrelated small position is smaller than its
  standalone VaR (diversification), and removing a dominant position reduces
  VaR by more than removing a hedged one (seeded book).
- Empty matrices, mismatched shapes, and out-of-range `position_index` raise
  `ValueError`.

## 8. Phase 4 — `pnl_explain`

### Files

- Add `johnhull/hullkit/src/hullkit/pnl_explain.py`.
- Add `johnhull/hullkit/tests/test_pnl_explain.py`.
- Update `johnhull/MODEL_INDEX.md` §6.

### API

```python
aggregate_exposures(weights, deltas, gammas, vegas)
# weights (n_pos,), deltas/gammas/vegas (n_pos, n_factors)
# -> (delta_p, gamma_p, vega_p) each (n_factors,) = weights @ matrix
# Cross-gammas are out of scope (documented).

delta_gamma_vega_pnl(delta_p, gamma_p, vega_p, factor_moves, vol_moves)
# -> dict {"delta": float, "gamma": float, "vega": float, "total": float}
#    delta = delta_p @ dx; gamma = 0.5 * gamma_p @ dx**2; vega = vega_p @ dvol

pnl_attribution(full_pnl, explained_total)
# -> dict {"explained", "unexplained", "unexplained_share"};
#    unexplained_share = |unexplained| / max(|full_pnl|, 1e-12)

limit_utilization(measures, limits)
# measures/limits aligned positive arrays -> dict {"utilization": np.ndarray,
# "breached": np.ndarray[bool]}; ValueError on non-positive limits

desk_report(var, es, components, utilization, backtest)
# -> nested JSON-able dict assembling the daily report (pure function of its
#    inputs; no randomness, no I/O)
```

### Validation (tests)

- Linear book (gamma = vega = 0): delta explain equals full revaluation to
  `1e-12`.
- Pure quadratic payoff: delta+gamma explain is exact to `1e-12`.
- BSM call full revaluation (via `hullkit.bsm`) with small spot/vol moves:
  delta-gamma-vega residual is smaller than delta-only residual, and residuals
  shrink at the documented Taylor order as the move halves.
- Limit logic: utilization ratios, breach flags, and `ValueError` on
  non-positive limits.
- `desk_report` called twice with identical inputs returns equal dicts
  (deterministic reproducibility).

## 9. Phase 5 — volume 27 reference, acceptance, and notebook

### Files

```text
johnhull/volumes/27_risk_desk/
  build_27_risk_desk_notebook.py
  risk_desk.ipynb
  VALIDATION.md
  reference/
    metrics.json
    risk_desk_scenarios.npz
```

Infrastructure modifications (each currently ends at vol 26; extend to 27):

- `johnhull/hullkit/src/hullkit/frontier_reference.py` — add
  `volume27_reference(*, seed: int = 20260745)` and register in
  `build_frontier_reference`.
- `johnhull/scripts/build_frontier_artifacts.py` — `FILES[27] = ("27_risk_desk",
  "metrics.json", "risk_desk_scenarios.npz")`, `UNITS_BY_VOLUME[27]`, docstring
  range.
- `johnhull/scripts/frontier_acceptance.py` — `_volume27(...)`, dispatcher entry
  `27: _volume27`, range message `[18, 27]`, docstring.
- `johnhull/scripts/build_frontier_notebooks.py` — vol 27 entry (mirrors 26).
- `johnhull/scripts/verify_frontier_artifacts.py` /
  `verify_frontier_notebooks.py` — include vol 27, update docstrings/messages.
- `johnhull/hullkit/tests/test_frontier_reference.py` — vol 27 coverage
  following the vol 26 test pattern.
- `johnhull/release_manifest.json` — vol 27 entry (same shape as vol 26):
  `portal_page: "risk_management"`, `portal_figures` (§10), `semantic_sources`
  and `semantic_tests` listing the four new modules and tests, `references`.
- `johnhull/docs/DATA_PROVENANCE.md`, `johnhull/ROADMAP.md`,
  `johnhull/README.md` — vol 27 rows + FRTB vol 28 candidate note.

### Reference artifact contents (all fixed-seed synthetic)

- iid Bernoulli exceedance series and a Markov-clustered series (for §4.2/§4.3
  checks), with their LR statistics and p-values.
- Kupiec size-calibration table: rejection rate over 400 seeded iid replications
  at nominal 5% size.
- GARCH(1,1) return path with true parameters, its conditional sigma, rolling
  plain-HS and FHS VaR forecasts, and both violation series.
- Seeded GPD exceedance sample, fitted `(xi, beta)`, mean-excess curve, and the
  EVT/empirical tail quantile ladder.
- 5-asset allocation inputs (`amounts`, `vols`, `corr`), `pnl_matrix`
  (2000 x 5), component/marginal/incremental arrays.
- Capstone book: positions, per-factor greeks, one day's factor/vol moves, full
  revaluation P&L, Taylor terms, limit table, and the assembled desk report
  scalars.
- Acceptance metrics recorded in `metrics.json` with schema, units, seed,
  semantic source/test paths, companion SHA-256, limitations, negative results.

Heavy computation (the 400-replication size study) runs in
`build_frontier_artifacts.py` only; the notebook reads committed arrays.

### `_volume27` acceptance checks (recomputed from committed arrays)

| Check | Criterion |
|---|---|
| `kupiec_size_calibration` | iid rejection rate within z < 3 of nominal 5% (binomial SE, 400 replications) |
| `christoffersen_detects_clustering` | clustered-series `LR_ind` p-value < 0.05 and smaller than the iid series p-value |
| `fhs_constant_vol_identity` | constant-sigma FHS equals plain HS, error <= 1e-12 |
| `fhs_coverage_improvement` | \|FHS violation rate - (1-alpha)\| < \|plain-HS violation rate - (1-alpha)\| on the GARCH path |
| `gpd_parameter_recovery` | \|xi_hat - xi\| <= 0.1 and \|beta_hat/beta - 1\| <= 0.15 |
| `evt_var_es_identity` | ES == (VaR + beta - xi*u)/(1-xi), error <= 1e-12 |
| `euler_additivity_normal` | sum(components) == normal VaR, error <= 1e-12 |
| `marginal_fd_consistency` | analytic vs central-difference marginals, relative error <= 1e-6 |
| `euler_es_additivity_sim` | sum(ES components) == total historical ES, error <= 1e-12 |
| `pnl_explain_taylor_ordering` | dgv residual < delta-only residual; both shrink when moves halve |
| `desk_report_reproducible` | rebuilt report scalars equal committed values exactly |

Remaining numeric tolerances are fixed from the seeded run with margin and
recorded in the acceptance table (vol 18–26 practice).

### Notebook sections (cells 00–27, deterministic cell ids, Japanese prose)

1. 00–02 — intro (link back to vol 08; the question "can you trust that VaR"),
   synthetic data setup from the committed artifact.
2. 03–07 — backtest statistics: exceedance plots, Kupiec/Christoffersen LR and
   p-values, size/power visualization, quantified traffic light.
3. 08–11 — FHS: volatility clustering, plain-HS violation clustering, FHS
   coverage comparison.
4. 12–15 — EVT: mean-excess threshold diagnostics, GPD fit, EVT vs empirical
   tail quantiles and ES.
5. 16–19 — decomposition: component vs incremental usage, Euler additivity bar
   chart, position-trim decision example.
6. 20–24 — desk-run capstone: factor mapping, P&L explain waterfall, limit
   check, assembled daily report table.
7. 25–27 — verification cell (recomputes the acceptance identities from the
   artifact), exercises, summary + rebuild instructions.

### VALIDATION.md

G8 format (copy vol 26 structure): gate `integration_and_reproducibility`,
model performance approved **no**, synthetic-offline data policy, artifact
evidence table, acceptance table, negative results, rebuild commands,
limitations.

## 10. Phase 6 — portal page and figures

### Files

- Modify `johnhull/report/report_builder/figures.py` — add `BookMeta` page
  `risk_management`（title 「リスク管理デスク」, subtitle
  「バックテスト・EVT・配賦・PnL explain」, accent `#dc2626`) and four
  `FigureSpec` entries on that page.
- Modify `johnhull/hullkit/src/hullkit/plotly_viz.py` — four figure builders.
- Extend `johnhull/report/tests/test_report_build.py` following its existing
  page/figure-count assertions.
- Register `portal_page`/`portal_figures` in `release_manifest.json` (§9 entry).

### Figures (built from the committed vol 27 artifact, no recomputation)

| Figure key | Content |
|---|---|
| `var_traffic_light` | exceedance counts vs binomial zones, multiplier steps |
| `fhs_vs_hs_coverage` | rolling VaR forecasts and violations, plain HS vs FHS |
| `gpd_tail_fit` | empirical tail vs fitted GPD quantiles, mean-excess inset |
| `risk_allocation_bars` | component VaR/ES bars with additivity annotation |

`plotly_viz` builders follow the existing `plotly_*` naming and read arrays via
`frontier_reference`/committed artifacts, consistent with current figures.

## 11. Validation commands through Phase 6

Run from the workspace root:

```bash
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_var_backtest.py \
  johnhull/hullkit/tests/test_tail_risk.py \
  johnhull/hullkit/tests/test_risk_allocation.py \
  johnhull/hullkit/tests/test_pnl_explain.py

uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_docstrings.py \
  johnhull/hullkit/tests/test_model_index.py

uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 27
uv run --no-sync --package hullkit python \
  johnhull/volumes/27_risk_desk/build_27_risk_desk_notebook.py

uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests johnhull/report/tests

make hull-artifacts-check
make hull-notebooks-check
make hull-release-check
```

ruff runs under the johnhull scope; `build_*_notebook.py` stays in the existing
ruff exclude.

Commit at the end of every phase (`feat(johnhull): ...` / `docs(johnhull): ...`),
staging only johnhull and plan/spec files — the branch is shared with parallel
sessions and unrelated files must never be swept in.

## 12. Explicitly deferred

- FRTB IMA: liquidity-horizon ES aggregation, stressed ES scaling, NMRF,
  P&L attribution eligibility tests, IMA vs SA capital comparison (vol 28
  candidate, recorded in ROADMAP).
- Integrated market/credit/liquidity/operational risk frameworks.
- Real market data, market calibration, or empirical-performance claims.
- Multivariate EVT, copula tail dependence beyond the existing
  `hullkit.copula`, spectral risk measures.
- Cross-gamma P&L explain and full revaluation grids.

## 13. Completion rule

Phase 1–6 is complete only when all scoped semantic tests pass, the vol.27
reference artifact is byte-reproducible, the artifact-only notebook
fresh-executes, all four gates in §11 pass, and every limitation is visible in
`VALIDATION.md`. A failed numerical validation is repaired with the smallest
relevant change and rerun; after three failed repair attempts on the same
blocker, stop and report the blocker, attempts, and recommended next step.
