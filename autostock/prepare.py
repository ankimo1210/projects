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
