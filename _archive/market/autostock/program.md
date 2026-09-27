# autostock

An experiment in autonomous trading-strategy research, ported from autoresearch.
The agent edits only `strategy.py`; the metric in `prepare.py` is read-only.

## Setup

1. **Agree a run tag** (e.g. `jun9`). Branch `autostock/<tag>` must not exist.
2. **Create the branch**: `git checkout -b autostock/<tag>`.
3. **Read in-scope files**: `prepare.py` (read-only metric), `strategy.py` (you edit).
4. **Verify data**: ensure `~/.cache/autostock/prices.parquet` exists; else run `uv run prepare.py`.
5. **Init results.tsv** with just the header row (leave it untracked by git).
6. **Confirm and go.**

## The metric

The goal is the **highest out-of-sample test Sharpe** (TEST_START..TEST_END).
Higher is better. The engine enforces: a 1-day execution lag (no same-day
lookahead), turnover costs, gross leverage <= 1.0, per-name <= 0.5. You may NOT
modify `prepare.py` and you may NOT index future bars (`prices.shift(-1)` etc.).

## What you CAN / CANNOT do

- CAN: rewrite `generate_weights()` and tune its hyperparameters — momentum, mean-reversion, vol-targeting, cross-sectional ranking, regime filters, etc.
- CANNOT: modify `prepare.py`, add dependencies, peek at the lockbox during the loop, or use future data.

## Robustness over a single number

A high test Sharpe with a negative `roll_sharpe_min` or a wildly negative single
year in `annual_sharpe` is fragile (regime-fit), and a large `train_sharpe` vs
`sharpe` gap means overfit. Prefer strategies that are high AND stable. Simpler is
better (the autoresearch simplicity criterion).

## Output format

`uv run strategy.py > run.log 2>&1`, then read:
`grep "^sharpe:\|^train_sharpe:\|^max_drawdown:\|^turnover:" run.log`

## Logging results

Append to `results.tsv` (TAB-separated, untracked by git). Columns:

    commit	sharpe	train_sharpe	max_dd	turnover	status	description

status is `keep`, `discard`, or `crash`. Example:

    commit	sharpe	train_sharpe	max_dd	turnover	status	description
    a1b2c3d	0.812000	0.910000	-0.245	0.010	keep	baseline equal-weight
    b2c3d4e	1.050000	1.300000	-0.300	0.450	keep	126d xs-momentum top2/bottom2

## The experiment loop

LOOP FOREVER:
1. Look at the git state (current branch/commit).
2. Edit `strategy.py` with one experimental idea.
3. `git commit`.
4. `uv run strategy.py > run.log 2>&1`.
5. `grep "^sharpe:" run.log`. Empty => crashed; `tail -n 50 run.log`, fix if easy.
6. Record the row in `results.tsv`.
7. If test Sharpe improved (and isn't an obvious overfit/fragile spike), advance. Else `git reset` back to where you started.

**NEVER STOP** to ask whether to continue. Try momentum, mean-reversion, vol
scaling, combinations, different lookbacks. Only when finalizing a chosen
strategy do you run `uv run strategy.py --reveal-lockbox` once to sanity-check
the truly-untouched segment.
