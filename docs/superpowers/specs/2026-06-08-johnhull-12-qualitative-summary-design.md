# johnhull 12_qualitative_summary Design — Hull 11e Ch.1, 8, 16, 35, 36, 37

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the goal directive)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 12 (final): `johnhull/volumes/12_qualitative_summary/` covering the
qualitative / case-study chapters — Ch.1 (introduction), Ch.8 (securitization
& the financial crisis), Ch.16 (employee stock options), Ch.35 (energy &
commodity derivatives), Ch.36 (real options), Ch.37 derivatives mishaps.
Markdown-centric with small compute cells where a chapter has a model.
**No new hullkit module** — reuses trees / rates / credit / exotics. Completing
this volume means all 37 chapters of Hull 11e are covered.

## hullkit additions

None. Compute cells reuse existing modules.

## Notebook: `volumes/12_qualitative_summary/` (build_summary_notebook.py → qualitative_summary.ipynb)

26 cells (cap 35), Japanese prose, markdown-heavy.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / magic / imports |
| 1 | 1 | 2 | derivatives landscape md (exchanges/OTC, hedgers/speculators/arbitrageurs, forwards/futures/options/swaps map) + long/short forward payoff chart |
| 2 | 8 | 4 | securitization md (ABS, tranches, ABS CDO, agency-problem/originate-to-distribute); waterfall loss-allocation demo (pool loss → equity/mezz/senior, reuse the vol09 tranche idea) + the 2007–08 crisis lessons md |
| 3 | 16 | 3 | ESO md (vesting, dilution, expensing FAS123R) + ESO valuation demo (BSM on expected life + dilution factor N/(N+M)) |
| 4 | 35 | 5 | commodity/energy md (mean reversion, convenience yield, electricity non-storable, weather/CAT) + cost-of-carry backwardation demo (F0=S0 e^{(r+u−y)T}) + Schwartz one-factor mean-reversion simulation chart |
| 5 | 36 | 4 | real options md (NPV ignores flexibility; risk-neutral extension via λ) + abandonment option = American put on project value (reuse trees) showing option adds value vs static NPV + embedded-option taxonomy table |
| 6 | 37 | 3 | mishaps md (rogue traders, front/middle/back separation, model & liquidity risk, LTCM, lessons table) |
| 7 | — | 2 | assertion cell + **series capstone** (37-chapter coverage map, hullkit module inventory, closing) |

Assertion cell: commodity F0 = 97.0446 (S=100, r=5%, u=2%, y=10%, T=1,
backwardation F0<S0); abandonment American put = 8.3427 (V0=100, K=90, r=5%,
σ=30%, T=2, N=500) and project-with-option > static NPV; waterfall allocation
(pool loss 12% → equity 5% wiped, mezz 7%, senior 0); Schwartz sim late-window
mean of ln S ≈ θ (seeded, tolerance); ESO dilution factor 0<N/(N+M)<1.

## Verification (DoD — as previous volumes + series completion)

Build; headless zero errors + 全チェック合格; hullkit pytest (96, unchanged —
no new module); ruff clean; GE-PDF citation review; ROADMAP volume 12 → done
(**all 14 rows done → all 37 chapters covered**); PROGRESS updated; final
ROADMAP note that the series is complete.

## Out of scope

- Gibson-Schwartz two-factor, swing options, full CAT-bond pricing,
  weather-derivative HDD/CDD pricing (md only); compound real options &
  option interaction (md); ESO with exercise-multiple barrier model (simple
  expected-life BSM only); detailed mishap case mechanics (lessons table only).
