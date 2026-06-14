"""Strategy capacity — how much capital the trade list can absorb.

At each rebalance the strategy must trade ``|Δw_i|`` of book value in name ``i``. If
you cap your participation at ``participation`` of a name's average daily dollar
volume (ADV), the capital the book can run before name ``i`` breaches that cap is
``adv_i * participation / |Δw_i|``. The binding (smallest) name sets the capacity at
that rebalance. This is a first-order proxy — ADV is an assumption and market impact
is not modelled — but it surfaces the real constraint: high turnover in thin names
caps size hard, which a Sharpe number alone never shows.
"""

from __future__ import annotations

import pandas as pd


def capacity(
    weights: pd.DataFrame,
    adv: pd.Series,
    *,
    participation: float = 0.1,
) -> pd.Series:
    """Per-rebalance capital capacity (binding name), in the currency of ``adv``.

    Parameters
    ----------
    weights : dates × assets target weights (fraction of book value).
    adv : per-asset average daily dollar volume.
    participation : max fraction of a name's ADV the book is willing to be.

    The first row trades in from cash (``Δw = w_0``). Dates with no turnover are NaN
    (capacity is unbounded when nothing trades).
    """
    dw = weights.diff()
    dw.iloc[0] = weights.iloc[0]  # enter from cash on the first bar
    traded = dw.abs()
    adv_aligned = adv.reindex(weights.columns)
    per_name = adv_aligned * participation / traded.where(traded > 0)
    cap = per_name.min(axis=1)
    return cap.rename("capacity")
