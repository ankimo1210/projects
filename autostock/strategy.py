"""
autostock strategy — the ONLY file the agent edits.

Edit generate_weights() and the hyperparameters below to search for a higher
out-of-sample Sharpe. prepare.py (the metric) is read-only.

Run:
    uv run strategy.py                 # normal experiment (lockbox withheld)
    uv run strategy.py --reveal-lockbox  # final check only, when finalizing
"""

import argparse

import pandas as pd

from prepare import UNIVERSE, evaluate, load_prices

# ---------------------------------------------------------------------------
# Hyperparameters (edit these directly, no CLI flags)
# ---------------------------------------------------------------------------
LOOKBACK = 126


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    mom = prices.pct_change(LOOKBACK, fill_method=None)
    rank = mom.rank(axis=1)
    return rank.div(rank.sum(axis=1), axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal-lockbox", action="store_true")
    args = ap.parse_args()

    prices = load_prices()
    weights = generate_weights(prices)
    m = evaluate(weights, prices, reveal_lockbox=args.reveal_lockbox)

    print("---")
    print(f"sharpe:               {m['sharpe']:.6f}")
    print(f"train_sharpe:         {m['train_sharpe']:.6f}")
    print(f"ann_return:           {m['ann_return']:.6f}")
    print(f"ann_vol:              {m['ann_vol']:.6f}")
    print(f"max_drawdown:         {m['max_drawdown']:.6f}")
    print(f"turnover:             {m['turnover']:.6f}")
    print(f"roll_sharpe_mean:     {m['roll_sharpe_mean']:.6f}")
    print(f"roll_sharpe_min:      {m['roll_sharpe_min']:.6f}")
    print(f"roll_sharpe_pos_frac: {m['roll_sharpe_pos_frac']:.6f}")
    if "lockbox_sharpe" in m:
        print(f"lockbox_sharpe:       {m['lockbox_sharpe']:.6f}")
    print("annual_sharpe:")
    for yr in sorted(m["annual_sharpe"]):
        print(f"  {yr}: {m['annual_sharpe'][yr]:.3f}")


if __name__ == "__main__":
    main()
