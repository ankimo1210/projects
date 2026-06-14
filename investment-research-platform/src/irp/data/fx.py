"""Base-currency conversion for multi-market panels.

Cross-market research (e.g. US + JP equities together) must be in one currency.
``to_base_currency`` converts a price panel whose columns may be in different
quote currencies into a single base currency, using an FX table expressed as
**base per 1 unit of each currency** (so ``fx[base] == 1``). Conversion is a plain
multiply aligned on dates with **no forward-fill** — a date missing an FX rate
yields NaN for that asset, consistent with the platform's no-silent-fill rule.

Helpers: ``invert_quote`` turns a market quote like USDJPY (JPY per USD) into the
USD-per-JPY rate; ``fx_adjusted_returns`` combines a local return with its FX
return: ``(1+r_local)(1+r_fx) - 1``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def invert_quote(quote: pd.Series) -> pd.Series:
    """Invert an FX quote (e.g. USDJPY=JPY-per-USD -> USD-per-JPY). Zeros -> NaN."""
    return 1.0 / quote.where(quote != 0)


def to_base_currency(
    prices: pd.DataFrame,
    ccy_of: dict[str, str],
    fx_to_base: pd.DataFrame,
    *,
    base: str = "USD",
) -> pd.DataFrame:
    """Convert a price panel to ``base`` currency.

    Parameters
    ----------
    prices : dates × assets, each column in its own (local) quote currency.
    ccy_of : asset -> quote currency code (assets absent default to ``base``).
    fx_to_base : dates × currency, value = ``base`` per 1 unit of that currency
        (``fx_to_base[base]`` is implicitly 1). Aligned to ``prices.index`` WITHOUT
        filling — missing rates propagate as NaN.
    """
    out = {}
    for asset in prices.columns:
        ccy = ccy_of.get(asset, base)
        if ccy == base:
            out[asset] = prices[asset]
        elif ccy in fx_to_base.columns:
            out[asset] = prices[asset] * fx_to_base[ccy].reindex(prices.index)
        else:
            out[asset] = pd.Series(np.nan, index=prices.index, dtype="float64")
    return pd.DataFrame(out, index=prices.index)


def fx_adjusted_returns(local_returns: pd.Series | pd.DataFrame, fx_returns: pd.Series | pd.DataFrame):
    """Total return in base = (1 + local return)(1 + FX return) - 1 (no fill)."""
    return (1.0 + local_returns) * (1.0 + fx_returns) - 1.0
