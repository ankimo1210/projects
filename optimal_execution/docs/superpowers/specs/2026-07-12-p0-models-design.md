# P0 reference models: report blocks + implementations

Date: 2026-07-12
Status: approved (conversation), implemented alongside this spec

## Goal

Add the four P0 reference works to the standalone report's "Model
mathematics and intuition" section with the same structure as the existing
five blocks (description / typeset MathML equations / variable glossary /
strengths & weaknesses / "behavior when adopted" note / parameter-sweep
chart), and implement each as code:

1. **Lehalle–Neuman (2019)** — signal-adaptive execution (full new module)
2. **Huberman–Stanzl (2004)** — no-manipulation round-trip diagnostic
3. **Moallemi–Yuan (2016)** — queue-position value
4. **España et al. (2025)** — the queue-reactive × RL composition (this
   lab's own architecture; descriptive block, no new engine code)

These are report diagnostics, NOT new pipeline strategies: the experiment
artifact set, the strategy universe, and the EN/JA quantitative fingerprint
are unchanged.

## Components

### 1. `src/optimal_execution/signal_adaptive.py` (new)

Stylized discrete Lehalle–Neuman: an OU predictive signal tilts a
linear-quadratic execution program.

- `expected_signal_path(alpha0, kappa_alpha, T, n_steps)` —
  `ᾱ_k = α₀ e^{−κ_α t_k}` (currency/share/second drift expected at t_k).
- `ln_schedule(cfg, alpha0, kappa_alpha, n_steps=None, lam=None)` —
  minimize `J(q) = η Σ q_k²/Δt + λσ² Σ Δt x_{k+1}² − Σ ᾱ_k x_{k+1} Δt`
  s.t. `Σq = X`, `q ≥ 0`, with `x = X·1 − Lq` (L lower-triangular ones).
  Solved as an equality-constrained KKT system plus the same active-set
  loop as `ow_numeric`. `α₀ = 0` reduces exactly to the discrete AC
  program (and to TWAP when additionally `λ = 0`).
- Sign convention: sell program; `α₀ > 0` (price expected to rise) defers
  execution, `α₀ < 0` front-loads. The `q ≥ 0` constraint keeps it a pure
  liquidation (no round trips), consistent with the lab's safety layer.

### 2. `impact.py` additions (Huberman–Stanzl diagnostic)

- `permanent_power_impact(z, gamma, delta)` — `g(z) = γ·sign(z)·|z|^δ`.
- `round_trip_pnl(z, gamma, delta)` — P&L of a signed trade sequence with
  permanent-only impact and the lab's half-own-impact execution
  convention: `P_k = P₀ + Σ_{j<k} g(z_j) + ½g(z_k)`, `PnL = −Σ z_k P_k`
  (arrival price cancels when `Σz = 0`).
- `manipulation_profit(cfg, delta, n_pieces=10, quantity=None)` — best of
  the two pump-and-dump directions (n small trades then one block, and the
  reverse), with γ normalized as `γ_δ = γ·Q^{1−δ}` so the block impact is
  held fixed across δ. Analytically `PnL = (γQ²/2)(n^{1−δ} − 1)` for the
  pieces-then-block direction; δ = 1 → exactly 0 (the HS theorem).

### 3. `fills.py` addition (Moallemi–Yuan, stylized)

- `queue_position_value(queue_ahead, order_qty, opposite_rate_per_s,
  mean_order_size, horizon_s, half_spread, target_depth)` —
  `V(Q_a) = P_fill(Q_a) · (s/2 − c_adv(Q_a))` with
  `c_adv(Q_a) = s·(1 − e^{−Q_a/Q̄})`: filling earns the half-spread, but
  deeper queue positions are filled increasingly only when swept by
  informed flow. Value crosses zero at `Q_a = Q̄·ln 2`; front of queue is
  worth ≈ `P_fill(0)·s/2`. Reuses `passive_fill_probability`.
  Clearly labeled a reduced form "in the spirit of" Moallemi–Yuan.

### 4. España et al. block (report-only)

Describes the lab's own composition (queue-reactive simulator + PPO +
paired CRN evaluation) against the paper's DDQN-in-QR result; one DDQN
target equation for contrast. Chart: cross-regime mean IS of the RL
policies vs the scripted comparators, read from `frames["stress"]`.

### 5. `report.py` wiring

- `eq` dict: new keys `hs`, `ln`, `my`, `espana` (all LaTeX pre-validated
  through latex2mathml before writing).
- `models` lists (JA and EN, same order): ac, impact, **hs**, ow, **ln**,
  lob, **my**, rl, **espana**.
- `behaviors` dicts: one behavior note per new block, both locales.
- `_model_theory_figures(cfg, t, frames)` (signature gains `frames`):
  new figures `mt_hs` (round-trip P&L vs δ, zero at 1), `mt_ln`
  (inventory paths for α₀ ∈ {−,0,+}), `mt_my` (queue value vs queue-ahead
  for flow multipliers), `mt_espana` (RL vs scripted IS across regimes).
  `mt_ac` stays first so the inline Plotly bundle still lands on the first
  DOM chart.
- No locale-key changes (model-theory prose lives in Python), so EN/JA
  key parity and the quantitative fingerprint are untouched.

## Testing

- `tests/test_signal_adaptive.py` (new): sums to X and q ≥ 0; α₀=0
  matches the discrete AC objective within tolerance and is never worse
  (it is the discrete optimum); λ=0, α₀=0 → TWAP; α₀>0 defers (inventory
  area grows), α₀<0 front-loads.
- `tests/test_impact.py` additions: δ=1 → round-trip P&L ≈ 0 (both
  directions); δ<1 → pieces-then-block profitable; δ>1 → block-then-pieces
  profitable; closed-form check of `manipulation_profit`.
- `tests/test_fills.py` additions: V(0) > 0 and ≈ P_fill(0)·s/2; front of
  queue is the maximum; sign change at Q̄·ln 2.
- Full suite + ruff + rebuild of both reports; verify chart/math counts,
  no CDN, EN/JA fingerprint parity.

## Non-goals

- No new strategies in the experiment pipeline (no artifact/fingerprint
  changes).
- No notebook changes (the JA survey already carries the P0 references).
- Full Lehalle–Neuman singular optimal control (HJB) — the implemented
  version is the stylized discrete LQ form, labeled as such in the report.
