# johnhull 02_options_basics Design — Hull 11e Ch.10–12, 17, 18

Date: 2026-06-08
Status: Approved (strategy-centric allocation confirmed with user)
Parent spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`
(architecture, notebook conventions, DoD inherited — this is a per-volume short spec)

## Goal

Volume 2 of the johnhull series: `johnhull/volumes/02_options_basics/` covering
Ch.10 (options mechanics), Ch.11 (option properties), Ch.12 (trading
strategies — the centerpiece), Ch.17 (index/currency options), Ch.18 (futures
options / Black-76). One new hullkit module: `payoffs.py`.

## hullkit addition: `payoffs.py`

- `leg_payoff(S, qty, kind, K=None)` — terminal payoff of one leg;
  kind ∈ {"call", "put", "stock"} (stock ignores K); ValueError otherwise
  (consistent with `trees.binomial_tree` kind validation).
- `strategy_payoff(S, legs)` — sum of legs; legs = list of `(qty, kind, K)`.
- `STRATEGIES` — registry dict `name -> legs factory` shared with the notebook
  dropdown: bull_call_spread(K1,K2), bear_put_spread(K1,K2),
  butterfly(K1,K2,K3, calls), straddle(K), strangle(K1,K2), strip(K), strap(K),
  covered_call(K), protective_put(K).
- `box_spread_value(K1, K2, r, T)` = (K2−K1)e^{−rT}.
- pytest: piecewise formulas from Ch.12 (bull-spread clip, butterfly spike,
  straddle |S−K|, strangle), box value, parity equivalence
  (covered call ≡ short put + bond ⇒ payoff difference is constant in S),
  kind validation error.

Deliberately NOT in scope: pricing inside payoffs.py (premiums come from
`bsm` in the notebook), American logic, multi-expiry (calendar/diagonal
spreads are explained in markdown only — payoff-at-one-expiry framework
cannot draw them honestly).

## Notebook: `volumes/02_options_basics/` (build_options_basics_notebook.py → options_basics.ipynb)

~34 cells (cap 35), Japanese prose, conventions per parent spec
(standalone `%matplotlib widget`, `nbplot.setup()`, ≤35 cells, assertion cell).
Figure/example references checked against the repo's 11e **Global Edition** PDF
(volume-01 lesson; flag any US/GE numeric differences in a note).

| Section | Ch | ~Cells | Content |
|---|---|---|---|
| 0 | — | 3 | intro / `%matplotlib widget` / imports |
| 1 | 10 | 2 | mechanics digest (md) + 4 basic positions profit diagrams (2×2 static, premium included) |
| 2 | 11 | 7 | bounds (interactive: BSM price inside no-arbitrage band as S varies) / put-call parity + arbitrage demo (S=31, K=30, r=10%, T=0.25, c=3 ⇒ p=1.2592; mispriced put 2.25 arbitrage P&L) / early exercise: C=c for no-dividend calls, P>p via hullkit.trees premium chart / six-factors table (md) |
| 3 | 12 | 10 | strategy builder (dropdown from STRATEGIES + K sliders, premiums via bsm, breakevens & max P/L annotated) / spreads panel (bull/bear/box/butterfly) / combinations panel (straddle/strangle/strip/strap) / principal-protected note demo / butterfly-as-building-block payoff replication |
| 4 | 17 | 4 | index options with q + portfolio insurance (β·P/(S·100) example: $500k, β=2, index 1000 ⇒ 10 contracts) / currency options q=r_f (Garman-Kohlhagen) |
| 5 | 18 | 4 | futures options mechanics + Black-76 via bsm(S=F, q=r) equivalence check / futures put-call parity c+Ke^{−rT}=p+F₀e^{−rT} |
| 6 | — | 4 | textbook assertion cell / exercises / summary |

Assertion-cell reference values (recomputed exactly at plan time, Hull-printed
approximations in parentheses): parity put 1.2592; call lower bound 3.91
(S=51,K=50,r=12%,T=0.5); put lower bound 1.01 (S=38,K=40,r=10%,T=0.25);
index call ≈51.83 (S=930,K=900,r=8%,q=3%,σ=20%,T=2/12); GK currency call
≈0.0285 (S=K=1.60,r=8%,r_f=11%,σ≈14%,T=4/12); Black-76 put ≈1.12
(F=K=20,r=9%,σ=25%,T=4/12); Black-76 ATM c=p identity; box spread value.

## Verification (DoD — same as volume 01)

1. Build via `uv run`; 2. headless nbconvert: zero error outputs + assertion
cell prints 全チェック合格; 3. hullkit pytest green (incl. new payoffs tests);
4. ruff check/format clean on johnhull (workspace-wide `make lint` has known
pre-existing failures outside johnhull — out of scope); 5. widget
interactivity = user check in live Jupyter; 6. ROADMAP/PROGRESS updated.

## Out of scope

- rates.py (volume 04/07), Greeks (volume 03), calendar-spread payoff charts
  (needs pricing at intermediate dates — would pull in time-value plots better
  suited to volume 03), existing notebooks/modules changes beyond payoffs.py.
