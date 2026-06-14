"""Portfolio constraints — held in config, applied as a projection.

The constraints (long-only, gross cap, per-name cap, vol target, cash floor) live
in ``configs/backtest_config.yaml`` and are applied to a raw weight vector by
:func:`apply_constraints`. Per-name capping and gross normalization interact, so
they are iterated to a fixed point; an optional ``target_vol`` then scales the
whole book (overriding the gross cap — leverage to hit the vol budget).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Constraints:
    long_only: bool = False
    max_gross: float = 1.0
    max_name_weight: float | None = 0.25
    cash_min: float = 0.0
    target_vol: float | None = None
    max_turnover: float | None = None

    @classmethod
    def from_config(cls, cfg: dict) -> Constraints:
        c = (cfg or {}).get("constraints", {})
        return cls(
            long_only=bool(c.get("long_only", False)),
            max_gross=float(c.get("max_gross", 1.0)),
            max_name_weight=c.get("max_name_weight", 0.25),
            cash_min=float(c.get("cash_min", 0.0)),
            target_vol=c.get("target_vol"),
            max_turnover=c.get("max_turnover"),
        )


def _cap_and_normalize(w: pd.Series, cap: float, gross_target: float) -> pd.Series:
    """Exact water-filling: |wᵢ| ≤ cap and Σ|wᵢ| = gross_target (if feasible).

    Repeatedly scale the uncapped names to fill the remaining gross; any that
    exceed ``cap`` are pinned at ``cap`` and the rest re-share the remainder.
    Signs are preserved. Converges in at most ``len(w)`` passes (no oscillation).
    """
    sign = np.sign(w)
    mag = w.abs()
    capped = pd.Series(False, index=w.index)
    for _ in range(len(w) + 1):
        free = ~capped
        s = mag[free].sum()
        budget = gross_target - cap * int(capped.sum())
        if s <= 0 or budget <= 0:
            break
        scaled = mag[free] * (budget / s)
        newly = scaled.index[scaled > cap + 1e-15]
        if len(newly) == 0:
            mag.loc[free] = scaled
            break
        capped.loc[newly] = True
    mag[capped] = cap
    return mag * sign


def apply_constraints(
    weights: pd.Series,
    c: Constraints,
    *,
    cov: pd.DataFrame | None = None,
    periods: int = 252,
) -> pd.Series:
    """Project ``weights`` onto the feasible set defined by ``c``.

    Order: long-only clip → per-name cap + gross normalization (exact
    water-filling) → optional vol target. Returns weights indexed like the input.
    """
    w = weights.fillna(0.0).astype("float64").copy()
    if c.long_only:
        w = w.clip(lower=0.0)

    cap, gross_target = c.max_name_weight, c.max_gross
    if cap is not None and gross_target is not None:
        w = _cap_and_normalize(w, cap, gross_target)
    elif gross_target is not None:
        gross = w.abs().sum()
        if gross > 0:
            w = w * (gross_target / gross)
    elif cap is not None:
        w = w.clip(lower=-cap, upper=cap)

    if c.target_vol is not None and cov is not None:
        aligned = cov.reindex(index=w.index, columns=w.index).fillna(0.0)
        var = float(w.to_numpy() @ aligned.to_numpy() @ w.to_numpy())
        pv = np.sqrt(max(var, 0.0)) * np.sqrt(periods)
        if pv > 0:
            w = w * (c.target_vol / pv)
    return w
