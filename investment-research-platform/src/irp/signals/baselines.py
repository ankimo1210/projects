"""Baseline signals — simple, transparent, hard to beat.

Each builder takes a price panel (dates × assets) and returns a standardized
:class:`~irp.signals.schema.Signal`. These are the references every fancier model
must be compared against (the platform rule: always benchmark complex models vs a
simple baseline). They are cross-sectional by default: the score ranks assets
against each other on each date.

Families that need data not yet wired (fundamentals for value/quality, term
structure for carry) are exposed as honest stubs that raise — the schema's breadth
is visible without fabricating inputs.
"""

from __future__ import annotations

import pandas as pd

from ..features import price as P
from .schema import Signal, SignalCategory, from_raw


def momentum_signal(
    prices: pd.DataFrame, *, lookback: int = 252, skip: int = 21, method: str = "zscore"
) -> Signal:
    """Cross-sectional momentum: rank assets by ``lookback``-minus-``skip`` return."""
    raw = P.momentum(prices, lookback=lookback, skip=skip)
    return from_raw(
        "momentum",
        SignalCategory.TREND,
        raw,
        direction=1,
        method=method,
        meta={"lookback": lookback, "skip": skip},
    )


def trend_following_signal(
    prices: pd.DataFrame, *, window: int = 200, method: str = "zscore"
) -> Signal:
    """Trend: distance of price above/below its trailing moving average."""
    raw = P.ma_ratio(prices, window)
    return from_raw(
        "trend_following",
        SignalCategory.TREND,
        raw,
        direction=1,
        method=method,
        meta={"window": window},
    )


def low_volatility_signal(
    prices: pd.DataFrame, *, window: int = 63, method: str = "zscore"
) -> Signal:
    """Risk: prefer low-volatility assets (the low-vol anomaly).

    Raw feature is realized volatility; ``direction=-1`` orients it so that *low*
    vol gets the higher oriented score.
    """
    raw = P.realized_volatility(prices, window, annualize=True)
    return from_raw(
        "low_volatility",
        SignalCategory.RISK,
        raw,
        direction=-1,
        method=method,
        meta={"window": window},
    )


def mean_reversion_signal(
    prices: pd.DataFrame, *, window: int = 21, method: str = "zscore"
) -> Signal:
    """Short-term reversal: fade recent relative strength.

    Raw feature is the trailing z-score of price vs its own window; ``direction=-1``
    so that recently *weak* names get the higher oriented score.
    """
    raw = P.rolling_zscore(prices, window)
    return from_raw(
        "mean_reversion",
        SignalCategory.TREND,
        raw,
        direction=-1,
        method=method,
        meta={"window": window},
    )


def macro_trend_signal(
    macro_level: pd.Series, assets, *, window: int = 12, method: str = "zscore"
) -> Signal:
    """A single macro series broadcast as a (degenerate) cross-sectional signal.

    ``macro_level`` should be a point-in-time aligned level (see
    :func:`irp.features.macro.pit_level`). Its trailing change becomes the score,
    applied identically to every asset — a placeholder for regime tilts until
    asset-level macro sensitivities (betas) are estimated in a later phase.
    """
    change = macro_level.pct_change(window, fill_method=None)
    raw = pd.DataFrame({a: change for a in assets})
    return from_raw(
        "macro_trend",
        SignalCategory.MACRO,
        raw,
        direction=1,
        method=method,
        meta={"window": window},
    )


# --- fundamentals / yield driven families -------------------------------------
# These standardize a cross-sectional *metric panel* (rows = dates, cols = assets),
# exactly as momentum standardizes a computed return. The metric itself is produced
# upstream from fundamentals/yields (e.g. earnings yield from irp.data fundamentals,
# carry from a yield curve) — keeping signal construction uniform across families.
def value_signal(value_metric: pd.DataFrame, *, method: str = "zscore") -> Signal:
    """Cross-sectional value: rank by a *cheapness* metric where higher = cheaper.

    Pass e.g. earnings yield (E/P), book-to-market, or FCF yield. (Invert
    price-multiples like P/E upstream so that higher always means cheaper.)
    """
    return from_raw("value", SignalCategory.VALUE, value_metric, direction=1, method=method)


def quality_signal(quality_metric: pd.DataFrame, *, method: str = "zscore") -> Signal:
    """Cross-sectional quality: rank by a metric where higher = higher quality.

    Pass e.g. ROE, gross margin, or low-accruals (sign accruals upstream so that
    higher = better).
    """
    return from_raw("quality", SignalCategory.QUALITY, quality_metric, direction=1, method=method)


def carry_signal(carry_metric: pd.DataFrame, *, method: str = "zscore") -> Signal:
    """Cross-sectional carry: rank by income/yield per unit (higher = more carry).

    Pass e.g. dividend yield, bond yield-to-maturity, futures roll yield, or FX
    forward points — the income earned for holding, all to one sign convention.
    """
    return from_raw("carry", SignalCategory.CARRY, carry_metric, direction=1, method=method)
