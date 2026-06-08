# johnhull 05_vol_smile_estimation Design — Hull 11e Ch.20, 23

Date: 2026-06-08
Status: Approved (recommended allocation auto-applied under the user's
"complete all milestones" goal directive; per-volume cycle per parent spec)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

## Goal

Volume 5: `johnhull/volumes/05_vol_smile_estimation/` covering Ch.20
(volatility smiles/surfaces, implied distributions) and Ch.23 (EWMA/GARCH
estimation). One hullkit addition: `volatility.py`.

## hullkit addition: `volatility.py` (TDD)

- `implied_vol(price, S, K, r, T, q=0.0, kind="call")` — brentq inversion of
  `bsm.call_price`/`put_price` on [1e-6, 5.0]; ValueError when the price is
  outside no-arbitrage bounds (brentq sign check) or kind invalid.
- `ewma_variance(returns, lam=0.94, init=None)` — variance series, Hull eq
  (23.7) recursion (var[i] = λ·var[i−1] + (1−λ)·u²[i−1]; var[0] = init or u²[0]).
- `garch11_variance(returns, omega, alpha, beta, init=None)` — conditional
  variance series, eq (23.9).
- `garch11_long_run(omega, alpha, beta)` — V_L = ω/(1−α−β); ValueError if α+β≥1.
- `garch11_forecast(sigma2_n, k, omega, alpha, beta)` — eq (23.13).
- `garch11_fit(returns, x0=(2e-6, 0.10, 0.85))` — MLE maximizing eq (23.12)
  via scipy minimize (Nelder-Mead with stationarity/positivity penalties —
  gradient-free is more robust for this likelihood); returns (ω, α, β).

pytest pins (hand-verified; Hull prints in parens):
IV round-trip (price at σ=0.27 → 0.27 within 1e-8) + call/put IV equality +
bounds ValueError; EWMA update (Hull Ex 23.1, λ=0.90) with σ_{n−1}=1%/day, u=2% → var 0.00013, σ=1.1402%/day (1.14%); GARCH(ω=2e-6, α=0.13, β=0.86) update with
σ_{n−1}=1.6%/day, u=1% → var 0.00023516, σ=1.5335% (1.53%); V_L=0.0002,
σ_L=1.4142%/day (1.4%); 10-day forecast from σ_n=1.6%/day → 2.5065e-4;
forecast → V_L as k→∞; fit on seeded synthetic GARCH series (n=4000)
recovers α+β within ±0.05.

## Notebook: `volumes/05_vol_smile_estimation/` (build_vol_smile_notebook.py → vol_smile.ipynb)

27 cells (cap 35), Japanese prose, conventions per parent spec; GE-PDF
citation review at notebook-review time.

| Sec | Ch | Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / `%matplotlib widget` / imports |
| 1 | 20 | 10 | IV definition + parity ⇒ identical call/put IV (eq 20.1/20.2); synthetic smile round-trip (price with skewed σ(K) → re-extract IV; equity skew vs FX U-shape panels); volatility surface heatmap + ATM term structure; Breeden-Litzenberger implied density (eq 20A.1/20A.2: flat σ reproduces lognormal — printed max error; skewed smile → fat left tail vs lognormal overlay); sticky strike/delta + minimum-variance delta (md); interactive smile explorer (ATM vol / skew slope / curvature sliders → smile + implied density) |
| 2 | 23 | 11 | historical vol + EWMA (eq 23.7, hand-example check) with regime-shift tracking chart vs rolling window; GARCH(1,1) (eq 23.8/23.9, Hull params update example, V_L); MLE fit (eq 23.12) on synthetic series with recovered-params table; multi-period forecast (eq 23.13) + annualized term structure (eq 23.14); EWMA correlation via Cholesky-correlated returns (ρ=0.6 tracking); interactive λ slider (responsiveness vs smoothness) |
| 3 | — | 3 | assertion cell / exercises / summary |

Assertion cell: IV round-trip + parity-equality; EWMA/GARCH/V_L/forecast
pins above; BL flat-σ density vs lognormal max rel error < 1% (central grid);
GARCH fit persistence in (0.9, 1.0) on the seeded series.

## Verification (DoD — as volumes 01–04)

Build via uv run; headless nbconvert zero errors + 全チェック合格; hullkit
pytest green (45 → ~52); ruff clean (johnhull); GE-PDF citation review;
widget interactivity = user check; ROADMAP/PROGRESS updated.

## Out of scope

- SABR/local-vol/Heston parameterizations (vol smile MODELING — Hull defers
  to Ch.27; brief md pointer only)
- Real market data downloads; risk-reversal/butterfly FX quoting beyond md
- GARCH variants (GJR, EGARCH); Ljung-Box testing (md mention)
- vanna/vomma smile hedging (md pointer, deferred from volume 03)
