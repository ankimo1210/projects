"""Information-coefficient diagnostics — how predictive a signal is, and for how long.

The cross-sectional rank IC at horizon ``h`` is the Spearman correlation, computed
per date across assets, between the signal and the **forward** return over the next
``h`` bars (:func:`quantkit.labels.forward_return`), then averaged over dates. Sweeping
``h`` traces the **IC decay** curve: a fast-decaying signal must be traded quickly
(high turnover, more cost); a slow-decaying one can be held. Forward returns are
genuinely future by construction, so this measures predictiveness, not leakage.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from ..labels import forward_return


def _panel_rank_ic(signal: pd.DataFrame, fwd: pd.DataFrame) -> float:
    """Mean over dates of the cross-sectional rank correlation of two aligned panels."""
    sig, fr = signal.align(fwd, join="inner")
    ics: list[float] = []
    for date in sig.index:
        s, f = sig.loc[date], fr.loc[date]
        mask = s.notna() & f.notna()
        if mask.sum() < 2:
            continue
        ic = s[mask].rank().corr(f[mask].rank())
        if pd.notna(ic):
            ics.append(float(ic))
    return float(np.mean(ics)) if ics else float("nan")


def rank_ic(signal: pd.DataFrame, prices: pd.DataFrame, horizon: int = 1) -> float:
    """Mean cross-sectional rank IC of ``signal`` vs the ``horizon``-bar forward return."""
    return _panel_rank_ic(signal, forward_return(prices, horizon))


def ic_decay(
    signal: pd.DataFrame,
    prices: pd.DataFrame,
    horizons: Sequence[int] = (1, 5, 10, 21, 63),
) -> pd.Series:
    """IC decay curve: mean rank IC at each forward horizon, indexed by horizon."""
    out = {int(h): rank_ic(signal, prices, int(h)) for h in horizons}
    s = pd.Series(out, name="rank_ic")
    s.index.name = "horizon"
    return s
