# johnhull Beyond-Hull A5–A8 — Final Validation

- Date: 2026-07-18
- Overall gate: **PASS**
- Model performance approved: **NO**
- Scope: integration, numerical identities, reproducibility, and offline delivery
- Data policy: fixed-seed synthetic references; no market-performance claim

`PASS` は vol 18–25 の教材・実装・成果物が再現可能で、定義した数値恒等式と
integration gate を満たすことだけを表す。実市場での予測力、収益性、較正品質、
または production readiness の承認ではない。

## Gate matrix

| Gate | Evidence | Result |
|---|---|:---:|
| G0 | owner boundary、JSON+NPZ schema、split audit、torch-free `hullkit`、checkpoint/data policy | PASS |
| G1 / vol 18 | 8 hard checks、BS price/delta、OOD、pathwise MC uncertainty、CPU report | PASS |
| G2 / vol 19 | Heston/COS・SABR/Hagan・rBergomi teacher、multi-start two-step calibration、hard surface checks、actual variance refits | PASS |
| G3 / vol 20 | 1/5/21-day purged folds、train-only scaler/PCA、10-model ladder、regime/bootstrap diagnostics、common-path hedge | PASS |
| G4 / vol 21–22 | four-family SPX/VIX joint objective、teacher/Greek/OOD/timing、0DTE clock/event/expiry checks | PASS |
| G5 / vol 23 | RFR conventions、multi-curve/policy/collateral、Bachelier/SABR/MC ladder、Bartlett hedge | PASS |
| G6 / vol 24 | perpetual payoff/funding、margin/liquidation waterfall、oracle、CPMM/LVR identities | PASS |
| G7 / vol 25 | carbon model ladder、risk premia、OU/fOU weather basis、PPA CFaR/CVaR sensitivity | PASS |
| G8 | artifact/notebook/report/book/release integration and isolated full-workspace audit | PASS (tracked release) |

Canonical reference acceptance is recomputed from the committed arrays by
`johnhull/scripts/frontier_acceptance.py`; it is not trusted as a copied JSON flag.

| Volume | Acceptance checks | Integration | Performance approval |
|---:|---:|:---:|:---:|
| 18 | 8 | PASS | NO |
| 19 | 11 | PASS | NO |
| 20 | 12 | PASS | NO |
| 21 | 8 | PASS | NO |
| 22 | 6 | PASS | NO |
| 23 | 9 | PASS | NO |
| 24 | 10 | PASS | NO |
| 25 | 9 | PASS | NO |

## Numerical evidence

- vol 18: normalized price MAE `5.593846268355811e-4`; delta MAE
  `1.7494819891811248e-3`; split overlap `0`; all 8 hard-check violations `0`.
  Price/delta/vega 20-seed CI coverage is `0.9/1.0/0.9`; the 4x-path standard-error
  ratios are `0.503652/0.500068/0.501859`.
- vol 19: all 4 SABR calibration starts succeed; repricing RMSE
  `5.2012449229271927e-11`; three distinct actual Heston variance refits; hard surface
  report passes all four applicable checks. A separate validation-only CPU benchmark
  measured median `1743.168745 ms` over 3 repeats after 1 warm-up (4 starts,
  74 objective evaluations); wall time is excluded from the byte-stable artifact.
- vol 20: horizons `1/5/21`, 3 folds each, 10 models each, and low/middle/high
  train-tercile regimes have QLIKE/RMSE/MAE block-bootstrap intervals. The stored
  default uses 512 common hedge paths and a common premium/cost convention.
- vol 21: all four SPX/VIX/VIX-option/variance objective components are finite;
  measured CPU timings are positive and preserved as a benchmark sample.
- vol 22: calendar and adjacent-expiry violations are both `0`; the event/non-event
  sample is `7/6` with open/midday/close diagnostics.
- vol 23: daily-compounding and zero-rate hand-check errors are `0`; quadrature
  hand-check error is `6.938893903907228e-18`; all four Hagan static checks pass at
  tolerance `1e-10`.
- vol 24: funding/cash-flow/solvency/insurance and both liquidation-method
  conservation identities pass within `1e-12`; stale and dislocated oracle states
  are explicitly represented.
- vol 25: Black-76/GBM/Heston/SV+jump prices and MC standard errors are aligned;
  fractional-OU lag-1 autocorrelation exceeds OU in the fixed fixture; weather basis
  and PPA risk sensitivities are finite.

## Fresh validation record

Environment:

```text
Python 3.12.3
Linux 6.18.33.1-microsoft-standard-WSL2 x86_64
NumPy 2.4.6 / SciPy 1.17.1 / PyTorch 2.11.0+cu128
Pricing and release benchmarks: CPU
```

| Check | Command / evidence | Result |
|---|---|:---:|
| Deep pricing tests | `uv run --no-sync --package deep-hedge-price pytest -s -q deep_hedge_price/tests` — 88 passed | PASS |
| Notebook builder regression | `pytest .../test_pricing_report.py` — 3 passed | PASS |
| Phase-2 HTML export | direct artifact-only execute/export smoke; Notebook 02 and quick report both have 0 remote runtime dependencies | PASS |
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -s -q johnhull/hullkit/tests johnhull/report/tests` — 294 passed, 2 dependency deprecation warnings | PASS |
| Scoped lint/format | Ruff over deep pricing, hullkit, release scripts, portal, tests, and Notebook 02 | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–25 semantic match and second-build byte identity | PASS |
| Notebook execution | `make hull-notebooks-check` — vol 18–25 artifact-only execution | PASS |
| Portal | `make hull-report` — 11 themes / 70 figures; exact generated HTML set; no external URL | PASS |
| Jupyter Book | clean `make hull-book` — 28 pages | PASS with legacy warnings |
| Release contract | `make hull-release-check` | PASS |
| Full-workspace test | final one-shot: 1388 passed, 41 skipped, 6 isolated failures, 33 warnings | ACCEPTED WITH EXCEPTIONS |
| Tracked release | `make hull-release-check HULL_RELEASE_FLAGS=--require-tracked` | PASS |

The clean Book build completed with 29 pre-existing legacy warnings/errors located in
vol 13–17/legacy chapter 15 sources (header levels, old Plotly MIME outputs, and one
transition diagnostic). No warning originates in vol 18–25. The new pages use vendored
RequireJS and add no remote runtime asset. Legacy pages retain the explicitly allowlisted
MathJax CDN dependency; therefore the repository does not claim that every legacy page is
fully offline.

### Full-workspace exception isolation

The one required full-workspace run was executed last and was not repeated. Its six
failures do not invalidate the scoped release candidate:

| Project | Failures | Isolation |
|---|---:|---|
| `gto` | 4 | API tests reached `gto_py.equity` / `flop_dense_table_gb`, but the Rust extension is not built in this workspace environment. The same run skipped 29 other binding-dependent GTO tests for that reason. |
| `johnhull/hullkit` | 1 | The order-dependent test inspected global `sys.modules` after earlier projects had already imported PyTorch. The fresh-process hullkit/report run passed 294 tests, and the release verifier independently imports hullkit and asserts that this import does not pull in torch. |
| `rough_volatility` | 1 | Its notebook kernel inherited Windows TEMP under WSL; Jupyter rejected NTFS mode `0o677` instead of `0o600`. The failure is outside johnhull and occurs before notebook code execution. |

There were no functional failures in the scoped `deep_hedge_price`, `hullkit`, portal,
artifact, or vol 18–25 notebook gates. These exceptions are recorded rather than hidden
or used to claim a green workspace-wide suite.

## Negative results and residual model risk

- vol 18: the quick soft penalty did not reduce the hard-check count, and no neural
  CPU break-even batch was observed.
- vol 19: the soft-constrained stress surface remains hard-arbitrage violating; the
  hard repair is a feasible cumulative projection rather than a joint-L2 optimum;
  rBergomi uses only a small antithetic MC sample.
- vol 20: PCA-ridge QLIKE `0.522245` does not beat EWMA `0.457612` at the compatibility
  5-day view. Real Phase-1 checkpoint positions were not supplied, so the policy status
  is correctly `not_evaluated`. Attention/permutation/occlusion/IG are non-causal
  diagnostics, and all forecast data are synthetic.
- vol 21: polynomial-surrogate Greek RMSE is `25.3594`; the manufactured target has
  SPX RMSE `0.0364061` and VIX RMSE `4.13935`. This is not a Greek-performance pass.
- vol 22: the intraday teacher and event schedule are synthetic, not causal dealer-flow
  evidence. DML/PIDE and point-process research tracks remain disabled.
- vol 23: Hagan worst quick-grid error is `60.6352 bp`; the free-boundary fixture is an
  explicit shift boundary, not an endogenous boundary solve; MC SE omits time-step bias.
- vol 24: the cascade is synthetic, not an event reconstruction. Dynamic fees do not
  reduce gross LVR in this fixture; fee compensation is reported separately.
- vol 25: weather and PPA values depend on the selected premium principle because the
  market is incomplete. Real-market calibration, out-of-sample tests, and storage real
  options remain outside the core gate.

Foundation models, diffusion/VAE/flow/SBI, signature/POT, and other cited frontier work
remain optional research tracks. Preprints are identified as such in the design/spec and
cannot fail or silently substitute for the core reference implementation.

## Release decision

The implementation and integration evidence are complete, with the workspace-wide
exceptions isolated above. After explicit authorization, the release files were committed,
the strict tracked-file release check passed, and branch
`codex/johnhull-beyond-hull-g8` was published. `PASS` denotes the tracked integration and
reproducibility release; it does not approve model performance or production readiness.
