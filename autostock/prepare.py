"""
One-time data prep + the FIXED evaluation harness for autostock.

READ-ONLY: the agent must NOT modify this file. It is the ground-truth metric,
analogous to autoresearch's prepare.py / evaluate_bpb. It downloads the
Magnificent-7 prices and defines the cheat-proof backtest engine + Sharpe metric.

Usage:
    uv run prepare.py            # download + cache prices (idempotent)
    uv run prepare.py --force    # re-download
"""

import argparse
import math
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
START_DATE = "2011-06-01"
TRAIN_END = "2020-12-31"      # train segment: START_DATE .. TRAIN_END
TEST_START = "2021-01-01"     # test (OOS, headline metric): TEST_START .. TEST_END
TEST_END = "2025-06-30"
LOCKBOX_START = "2025-07-01"  # lockbox: withheld until --reveal-lockbox

COST_BPS = 5.0                # transaction cost (basis points) per unit turnover
RF = 0.0                      # daily risk-free rate (0 for the demo)
ANNUALIZATION = 252           # trading days per year
MAX_GROSS = 1.0               # cap on sum(|w|)
MAX_NAME = 0.5                # cap on |w_i|
ROLL_WINDOW = 252             # rolling-Sharpe window (trading days)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autostock")
PRICES_PATH = os.path.join(CACHE_DIR, "prices.parquet")

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _sharpe(ret):
    """Annualized Sharpe of a daily-return series. 0.0 if degenerate."""
    ret = ret.dropna()
    if len(ret) < 2:
        return 0.0
    sd = ret.std()
    if sd == 0 or math.isnan(sd):
        return 0.0
    return float((ret.mean() - RF) / sd * math.sqrt(ANNUALIZATION))


def _max_drawdown(ret):
    """Most-negative peak-to-trough drawdown of the equity curve (<= 0)."""
    ret = ret.dropna()
    if len(ret) == 0:
        return 0.0
    equity = (1.0 + ret).cumprod()
    dd = equity / equity.cummax() - 1.0
    return float(dd.min())


def _rolling_sharpe(ret, window=ROLL_WINDOW):
    """Vectorized rolling annualized Sharpe series."""
    rmean = ret.rolling(window).mean()
    rstd = ret.rolling(window).std()
    return (rmean - RF) / rstd * math.sqrt(ANNUALIZATION)


# ---------------------------------------------------------------------------
# Position constraints (enforced by the engine — the agent cannot bypass these)
# ---------------------------------------------------------------------------


def enforce_constraints(weights, tradeable):
    """Zero non-tradeable assets, cap per-name to +/-MAX_NAME, then scale the
    row down (never up) so gross sum(|w|) <= MAX_GROSS."""
    w = weights.where(tradeable, 0.0).fillna(0.0)
    w = w.clip(lower=-MAX_NAME, upper=MAX_NAME)
    gross = w.abs().sum(axis=1)
    scale = (MAX_GROSS / gross.replace(0.0, np.nan)).clip(upper=1.0).fillna(0.0)
    return w.mul(scale, axis=0)


# ---------------------------------------------------------------------------
# Returns + backtest engine (the FIXED metric — do not modify)
# ---------------------------------------------------------------------------


def compute_returns(prices):
    """Simple daily returns from adjusted close."""
    return prices.pct_change(fill_method=None)


def _net_returns(weights, prices):
    """Portfolio daily net-return series and per-day turnover.

    Enforces constraints, then applies a 1-day execution lag (weights decided
    at close of day t are held starting day t+1 — no same-day lookahead), and
    charges COST_BPS on turnover. Returns (net_return_series, turnover_series).
    """
    returns = compute_returns(prices)
    tradeable = prices.notna()
    wc = enforce_constraints(weights.reindex_like(prices), tradeable)
    w_held = wc.shift(1).fillna(0.0)                          # 1-day lag
    turnover = (w_held - w_held.shift(1).fillna(0.0)).abs().sum(axis=1)
    gross = (w_held * returns).sum(axis=1)
    net = gross - (COST_BPS / 1e4) * turnover
    return net, turnover
