# autostock

Autonomous trading-strategy research, ported from
[autoresearch](https://github.com/karpathy/autoresearch) to a quant setting: an
agent edits one file (`strategy.py`) to maximize a cheat-proof out-of-sample
Sharpe over the Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA).

## Files

- `prepare.py` — **read-only**: constants, yfinance data prep, and the fixed backtest engine + `evaluate()` metric (1-day execution lag, turnover costs, leverage caps, train/test/lockbox segments, rolling/annual Sharpe).
- `strategy.py` — **the agent edits this**: `generate_weights(prices)` + hyperparams.
- `program.md` — the human-edited autonomous research loop.

## Quick start

    cd ~/projects/autostock
    uv run prepare.py          # download + cache 15y of Mag-7 prices (one-time)
    uv run strategy.py         # run one backtest, print the summary block

Then point an agent at `program.md` to start the autonomous loop. The metric is
**OOS test Sharpe** (higher is better). The lockbox segment is withheld until you
run `uv run strategy.py --reveal-lockbox` when finalizing a strategy.

## Why a read-only metric

In a backtest the easy way to "win" is to cheat: peek at the future, ignore
costs, or pile on leverage. `prepare.py` makes those impossible — the engine
lags every position by a day, charges turnover, and caps gross/per-name weight —
so any Sharpe the loop reports is at least structurally honest. Survivorship in
the hand-picked Mag-7 still makes absolute levels optimistic; the point of the
demo is the autonomous *search loop*, not deployable alpha.
