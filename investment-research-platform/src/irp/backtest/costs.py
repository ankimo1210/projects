"""Transaction-cost model.

Costs are charged on **turnover** — the sum of absolute weight changes between
rebalances. ``cost_bps`` (commission/spread) and ``slippage_bps`` (market impact)
are assumptions held in ``configs/backtest_config.yaml``, never hard-coded, and
must be shown in any report. Real fills are worse than any model; this is a
deliberately simple, transparent drag.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CostModel:
    cost_bps: float = 5.0
    slippage_bps: float = 2.0

    @property
    def per_unit(self) -> float:
        """Cost per 1.0 of turnover (fraction, not bps)."""
        return (self.cost_bps + self.slippage_bps) / 1e4

    def on_turnover(self, turnover: pd.Series) -> pd.Series:
        """Per-period cost = turnover × per-unit cost (>= 0)."""
        return turnover.abs() * self.per_unit

    @classmethod
    def from_config(cls, cfg: dict) -> CostModel:
        ex = (cfg or {}).get("execution", {})
        return cls(
            cost_bps=float(ex.get("cost_bps", 5.0)),
            slippage_bps=float(ex.get("slippage_bps", 2.0)),
        )


def turnover(weights: pd.DataFrame) -> pd.Series:
    """One-way turnover per period: sum_i |w[t,i] - w[t-1,i]|.

    The first row counts as turnover from an all-cash start (entering the book).
    """
    prev = weights.shift(1).fillna(0.0)
    return (weights.fillna(0.0) - prev).abs().sum(axis=1)
