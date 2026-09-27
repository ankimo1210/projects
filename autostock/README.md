# autostock

Autonomous trading-strategy research, ported from
[autoresearch](https://github.com/karpathy/autoresearch) to a quant setting: an
agent edits one file (`strategy.py`) to maximize a fixed out-of-sample
Sharpe over the Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA).

## Files

- `prepare.py` — **read-only**: constants, yfinance data prep, and the fixed backtest engine + `evaluate()` metric (1-day execution lag, turnover costs, leverage caps, train/test/lockbox segments, rolling/annual Sharpe).
- `strategy.py` — **the agent edits this**: `generate_weights(prices)` + hyperparams.
- `program.md` — the human-edited autonomous research loop.

## Quick start

    cd ~/projects
    uv run --no-sync python autostock/prepare.py   # 2011-06-01 以降の価格を取得・保存
    uv run --no-sync python autostock/strategy.py  # バックテスト1回、指標を表示

Then point an agent at `program.md` to start the autonomous loop. The metric is
**OOS test Sharpe** (higher is better). The lockbox metric is hidden until you
run `uv run --no-sync python autostock/strategy.py --reveal-lockbox` from the workspace root when finalizing a strategy.

## Why a read-only metric

`prepare.py` は翌日執行、売買コスト、銘柄別・総ウェイト上限を評価時に適用します。
ただし、`generate_weights(prices)` には全期間の価格が渡され、lockbox も読み込み対象です。
`--reveal-lockbox` が制御するのは指標の表示であり、戦略から将来の価格へアクセスすることは防ぎません。
先読みの有無は戦略コードで別途確認する必要があります。
固定 OOS 期間で探索を繰り返すことによる過適合と、現在の Mag7 を選ぶ生存者バイアスも残ります。
これは自律探索ループの研究デモです。
