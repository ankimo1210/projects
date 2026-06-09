# autostock — Design Spec

**Date:** 2026-06-09
**Status:** Approved for planning
**Topic:** A demo project that ports Karpathy's `autoresearch` autonomous-research
loop from LLM pretraining to quantitative trading-strategy search over the
"Magnificent 7" stocks.

## 1. Overview

`autoresearch` (in `~/repos/autoresearch`) is an autonomous-research harness: a
human edits only `program.md` (the instructions), and an AI agent edits only one
code file (`train.py`), running a fixed-budget experiment, measuring a single
ground-truth metric (`val_bpb`, lower is better), keeping the change if the metric
improved and reverting otherwise, looping forever.

`autostock` ports this pattern to systematic trading. The agent searches for a
**cross-sectional long/short strategy** over the Magnificent 7 that maximizes an
**out-of-sample Sharpe ratio** (higher is better). The single most important
design property carried over from `autoresearch` is that **the evaluation metric
lives in a read-only file the agent cannot modify** — here, a backtest engine that
is cheat-proof against the classic ways a backtest produces fake performance
(lookahead, ignored costs, unbounded leverage, peeking at the test set).

### Magnificent 7 universe

`AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA`

Note IPO/listing dates: META trades from 2012-05, TSLA from 2010-06; the others
have longer history. The engine handles assets without a valid price on a given
date by forcing their weight to 0 and renormalizing (see §3).

## 2. Architecture — mapping to autoresearch

| autoresearch | autostock | role |
|---|---|---|
| `prepare.py` (read-only) | `prepare.py` (read-only) | constants, yfinance data prep, **`evaluate()` = fixed metric** |
| `train.py` (agent edits) | `strategy.py` (agent edits) | signal/weight generation + tunable hyperparameter block + runs and prints summary |
| `program.md` (human edits) | `program.md` (human edits) | autonomous research-loop instructions |
| `results.tsv` | `results.tsv` | experiment log (untracked by git) |
| metric `val_bpb` (lower better) | metric **OOS test Sharpe** (higher better) | drives keep/discard |

**Location:** `~/projects/autostock/`, added as a member of the root uv workspace
(`[tool.uv.workspace]` in `~/projects/pyproject.toml`). Dependencies: `yfinance`,
`pandas`, `numpy`, `pyarrow`, `matplotlib`. No torch / no GPU.

**Entry points (mirror autoresearch):**
- `uv run prepare.py` — one-time data download + cache (re-runnable, idempotent).
- `uv run strategy.py` — run one backtest experiment, print the summary block.

## 3. Evaluation harness — `prepare.py` (read-only, the crux)

This is the analog of `evaluate_bpb`: the agent must not modify it, and it makes
cheating physically impossible.

### Data prep
- Download daily **adjusted close** for the 7 tickers via `yfinance`
  (`auto_adjust=True`), ~15 years (2011-06 → today).
- Cache to `~/.cache/autostock/prices.parquet`. Idempotent: skip if present.
- Compute simple daily returns from adjusted close.

### Cheat-proof backtest engine (`backtest(weights_df)`)
1. **No lookahead (enforced):** the weights a strategy emits for day *t* are
   **shifted forward by one day** by the engine before being multiplied into day
   *t+1* returns. Even if `strategy.py` returns same-day weights, it cannot peek —
   the lag is applied here, not in the strategy.
2. **Transaction costs:** `cost_t = COST_BPS * sum(|w_t - w_{t-1}|)` (turnover
   charge, per unit notional traded). Default `COST_BPS = 5` (0.05%). Excess churn
   is penalized automatically.
3. **Constraints (clipped/normalized by the engine):** long/short allowed; gross
   leverage `sum(|w|) <= 1.0`; per-name cap `|w_i| <= 0.5`. Residual is cash at
   `RF = 0`. The agent cannot manufacture returns with unbounded leverage.
4. **Missing-asset handling:** an asset with no valid prior price on a date gets
   weight 0, and remaining weights are renormalized within the gross cap. This
   absorbs META's later start and blocks NaN-mediated lookahead.
5. **Portfolio return:** `ret_t = sum(w_shifted_t * asset_ret_t) - cost_t`.

### Time segments
- **train** 2011-06 → 2020-12-31 (~9.5y): the region where the agent implicitly
  fits parameters; freely inspectable.
- **test** 2021-01-01 → 2025-06-30 (~4.5y): **headline OOS metric**. Sharpe here
  drives keep/discard. The honest analog of autoresearch's held-out val shard.
- **lockbox** 2025-07-01 → today (~11mo): **never inspected during the loop**.
  The harness withholds its numbers during normal runs and reveals them only on an
  explicit final call (`uv run strategy.py --reveal-lockbox`). This is the final
  guardrail against multiple-testing overfit accumulated across many experiments.

### Metric + diagnostics (returned by `evaluate()`)
- **Headline:** `sharpe` = annualized Sharpe on **test** = `mean(daily_ret)/std *
  sqrt(252)`, `RF = 0`.
- **Overfitting diagnostic:** `train_sharpe` (same calc on train). A large
  train↔test gap is an immediate overfit signal.
- **Rolling analysis (the "some rolling analysis" requirement):**
  - Rolling 252-trading-day Sharpe over the whole non-lockbox sample.
  - Summary over windows ending in the test period: `roll_sharpe_mean`,
    `roll_sharpe_std`, `roll_sharpe_min`, `roll_sharpe_pos_frac` (fraction of
    windows with Sharpe > 0).
  - **Per-calendar-year Sharpe table** for human-readable regime inspection.
  - Rationale: the agent's "fitting" is manual code editing, not an automated
    optimizer, so a formal re-fitting walk-forward does not map cleanly. A
    same-strategy rolling-window evaluation is what actually surfaces
    regime-dependence and fragility. Headline metric stays a single clean number
    (`sharpe`) like `val_bpb`; rolling stats inform robustness preference in
    `program.md`.
- **Auxiliary:** `ann_return`, `ann_vol`, `max_drawdown`, `turnover` (avg daily
  `sum(|w_t - w_{t-1}|)`).

## 4. `strategy.py` (agent edits)

- `generate_weights(prices) -> weights_df`: returns a date×asset weight panel using
  **past data only** (rolling/expanding ops). The engine applies the 1-day lag, so
  even a buggy same-day signal cannot leak the future.
- A **hyperparameter block** at the bottom (lookback windows, thresholds, vol
  target, etc.) as module-level constants — mirrors `train.py`'s HP block.
- Running `uv run strategy.py` loads cached prices, builds weights, calls the
  engine, and prints a `---`-delimited summary:
  ```
  ---
  sharpe:          <test OOS sharpe>
  train_sharpe:    <train sharpe>
  ann_return:      <test annualized return>
  ann_vol:         <test annualized vol>
  max_drawdown:    <test max drawdown>
  turnover:        <avg daily turnover>
  roll_sharpe_mean: <...>
  roll_sharpe_min:  <...>
  roll_sharpe_pos_frac: <...>
  ```
- **Baseline strategy:** equal-weight long-only (1/7 each, daily rebalanced to
  equal weight). The first experiment always runs the baseline unmodified.

## 5. `program.md` (human-edited autonomous loop)

Ported from autoresearch's `program.md`:
- **Setup:** agree a run tag → branch `autostock/<tag>` → read in-scope files →
  verify `~/.cache/autostock/prices.parquet` exists (else run `prepare.py`) →
  init `results.tsv` header → confirm.
- **Goal:** maximize **test Sharpe** (higher is better).
- **Loop forever:** edit `strategy.py` → `git commit` → `uv run strategy.py >
  run.log 2>&1` → `grep '^sharpe:' run.log` → if improved, advance; else `git
  reset` → record to `results.tsv` (untracked) → never pause to ask.
- **Integrity rules baked in:** the metric file is read-only; prefer strategies
  that are robust (high test Sharpe **and** stable rolling Sharpe — a high test
  Sharpe with a negative worst-rolling-year is fragile, treat with suspicion);
  costs are real; simpler is better (the autoresearch simplicity criterion); never
  touch the lockbox until a strategy is finalized.
- **`results.tsv` schema (TSV):**
  `commit  sharpe  train_sharpe  max_dd  turnover  status  description`
  status ∈ `keep | discard | crash`.

## 6. Validation / Definition of Done

- `uv run prepare.py` downloads 15y for all 7 tickers; observe and quote real row
  counts / date range.
- `uv run strategy.py` (baseline) runs and prints a real **test Sharpe**; quote the
  actual summary lines.
- **No-lookahead test:** a deliberately future-peeking dummy strategy must NOT earn
  an inflated test Sharpe (the engine's 1-day lag neutralizes it). Add as a check.
- **Cost test:** a high-turnover strategy shows materially reduced Sharpe vs a
  zero-cost run, confirming the cost model bites.
- **Short research run:** starting from baseline, iterate `strategy.py` a handful of
  times and surface at least one candidate whose OOS test Sharpe beats baseline,
  reporting the train↔test gap and rolling stability honestly (no cherry-picking).

## 7. Known caveats (documented, not hidden)

- Even with a lockbox, running ~100s of experiments against a fixed test period
  invites some multiple-testing overfit; the lockbox bounds, not eliminates, this.
- 7 assets over ~15y is a small, regime-heavy sample (2020 crash, 2022 drawdown,
  2023-24 AI rally). Sharpe estimates are noisy; rolling/annual breakdowns are there
  precisely to keep this visible.
- Survivorship: the Mag7 is a hand-picked set of winners, so absolute Sharpe levels
  are optimistic. The demo's point is the *autonomous search loop*, not a deployable
  alpha.
