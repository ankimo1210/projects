# johnhull 06_numerical_methods Design — Hull 11e Ch.21, 27

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 6: `johnhull/volumes/06_numerical_methods/` covering Ch.21 (trees
extensions, Monte Carlo, finite differences) and Ch.27 (alternative models,
LSM). hullkit additions: new `fd.py` + Monte Carlo extensions in `mc.py`.

## hullkit additions (TDD)

### fd.py (new)

- `fd_vanilla(S0, K, r, sigma, T, q=0.0, kind="call", american=False,
  method="cn", n_s=200, n_t=200, s_max_mult=4.0)` — theta-scheme finite
  difference on a uniform ln-S grid (θ=1 implicit, θ=0.5 Crank-Nicolson),
  tridiagonal solve via scipy solve_banded, Dirichlet asymptotic boundaries,
  American via post-step projection max(f, intrinsic); price interpolated at
  S0 (grid centered so ln S0 is a node). kind/method validation.

### mc.py extensions

- `price_european_mc(S0, K, r, sigma, T, q=0.0, kind="call",
  n_paths=100_000, antithetic=False, rng=None)` → (price, standard_error);
  terminal-sampling risk-neutral MC (Hull eq. 21.16 / §21.6 SE); antithetic
  pairs averaged before the SE (Hull §21.7).
- `price_american_lsm(S0, K, r, sigma, T, q=0.0, kind="put", n_steps=50,
  n_paths=100_000, rng=None)` — Longstaff-Schwartz least-squares MC
  (quadratic basis on ITM paths, Hull §27.8), paths from simulate_gbm_paths
  with risk-neutral drift r−q.

pytest (cross-method consistency is the gate for a numerical-methods volume):
fd CN European call/put ≈ BSM (abs 2e-2 at 200×200); fd American put ≈
trees.crr_price(N=500, american) (abs 2e-2); CN error ≤ implicit error on the
same grid (European); kind/method ValueError; MC price within 3·SE of BSM and
SE ≈ theoretical magnitude; antithetic SE < plain SE (same n_paths, seeds);
LSM American put ≈ CRR(500) (abs 5e-2, deterministic default seed); LSM ≥
European BSM (early-exercise premium ≥ 0 within noise).

## Notebook: `volumes/06_numerical_methods/` (build_numerical_notebook.py → numerical.ipynb)

29 cells (cap 35), Japanese prose, equation-number-first citations
(GE-PDF review at notebook-review time). Running example for American puts:
S=50, K=50, r=10%, σ=40%, T=5/12 (Hull Ch.21 example parameters; any
Hull-printed value claims to be verified against the PDF by the reviewer).

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 21 | 4 | trees extensions md (q/time-varying a, control variate f* = f_Am,tree + f_Eu,BSM − f_Eu,tree) + control-variate demo (CRR N=100 plain vs CV vs N=2000 reference); trinomial tree md (p_u/p_m/p_d, explicit-FD equivalence) + inline trinomial pricer vs CRR |
| 2 | 21 | 5 | MC pricing + SE + CI (eq 21.16) demo vs BSM; variance reduction md (antithetic/control variate/importance/quasi-random); antithetic SE-vs-n chart; Greeks-via-MC md note |
| 3 | 21 | 6 | FD mechanics md (grids, implicit/explicit/CN, stability); European convergence chart (error vs grid, CN vs implicit); American put FD + **early-exercise boundary extracted from the FD grid**; interactive boundary explorer (σ, r sliders) |
| 4 | 27 | 8 | alternative-models map md (CEV/Merton/VG/Heston/SABR/local-vol table); inline Merton jump-diffusion series pricer + **the smile it generates** (re-extract IV via hullkit.volatility across K); jump-path simulation chart (fat tails); LSM md + demo table (LSM vs CRR vs FD — three methods, one option); convertibles/barrier/adaptive-mesh md pointer |
| 5 | — | 3 | assertion cell / exercises / summary |

Assertion cell: fd-CN Euro vs BSM; fd American vs CRR; CV beats plain at
N=100; MC within 3·SE; antithetic SE smaller; LSM vs CRR; Merton λ→0 ≡ BSM
(1e-6); Merton put-call parity (series put via parity identity); trinomial vs
CRR (abs 5e-2).

## Verification (DoD — as volumes 01–05)

Build via uv run; headless nbconvert zero errors + 全チェック合格; hullkit
pytest green (51 → ~60); ruff clean (johnhull); GE-PDF citation review;
widget = user check; ROADMAP/PROGRESS updated (module list gains `fd`).

## Out of scope

- CEV closed form (noncentral χ² — md formula only), Heston/SABR
  implementations (md), variance-gamma, rough vol
- Implicit American via PSOR/penalty beyond simple projection
- Quasi-random (Sobol) implementation; importance sampling code
- Convertible-bond tree, barrier adaptive mesh (md pointers)
