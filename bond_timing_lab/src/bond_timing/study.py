"""Every input of the study in one object (design §4), and W2's planted macro factor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import TRAIN_START
from .data import fred, fredmd, gsw
from .data.store import MACROKIT_RAW, RAW_ROOT, indicators, read_latest
from .features import YIELD_MONTHS, MacroCleaner, Pca
from .returns import Outcomes, grid_months, real_outcomes

__all__ = ["DEV", "FINAL_VINTAGE", "OOS_A", "OOS_B_START", "TRAIN_START", "Study", "load_study"]

DEV = (pd.Period("1971-08", "M"), pd.Period("1999-12", "M"))
OOS_A = (pd.Period("2000-01", "M"), pd.Period("2018-12", "M"))
OOS_B_START = pd.Period("2019-01", "M")
FINAL_VINTAGE = pd.Period("2019-02", "M")


@dataclass
class Study:
    curve: gsw.GswCurve
    zeros: pd.DataFrame
    bey: pd.Series
    cash: pd.Series
    outcomes: Outcomes
    vintage_payloads: dict[pd.Period, bytes]
    raw_root: Path
    _vintages: dict[pd.Period, fredmd.Vintage] = field(default_factory=dict, repr=False)

    @property
    def yields(self) -> pd.DataFrame:
        return self.zeros[list(YIELD_MONTHS)]

    def vintage(self, month: pd.Period) -> fredmd.Vintage:
        if month not in self._vintages:
            self._vintages[month] = fredmd.parse_vintage(month, self.vintage_payloads[month])
        return self._vintages[month]

    def realtime_macro(self) -> fredmd.RealTimeMacro:
        return fredmd.RealTimeMacro(self.vintage)

    def final_macro(self) -> fredmd.FinalMacro:
        return fredmd.FinalMacro(self.vintage(FINAL_VINTAGE))

    def last_decision(self) -> pd.Period:
        return self.outcomes.excess["tlt"].dropna().index[-1] - 1


def load_vintage_payloads(root: Path) -> dict[pd.Period, bytes]:
    payloads: dict[pd.Period, bytes] = {}
    for indicator in fredmd.HISTORICAL:
        payloads.update(fredmd.zip_vintages(read_latest(root, "fredmd", indicator)))
    for indicator in indicators(root, "fredmd"):
        if indicator.startswith("monthly_"):
            month = pd.Period(indicator.removeprefix("monthly_"), "M")
            payloads[month] = read_latest(root, "fredmd", indicator)
    return dict(sorted(payloads.items()))


def load_study(raw_root: Path = RAW_ROOT, macrokit_root: Path = MACROKIT_RAW) -> Study:
    curve = gsw.load_curve(macrokit_root)
    zeros = gsw.month_end_zeros(curve, grid_months())
    bey = fred.load_dtb3_bey(raw_root).reindex(zeros.index)
    cash = fred.cash_returns(bey)
    return Study(
        curve,
        zeros,
        bey,
        cash,
        real_outcomes(zeros, cash),
        load_vintage_payloads(raw_root),
        raw_root,
    )


def macro_pc1(
    vintage: fredmd.Vintage,
    start: pd.Period,
    end: pd.Period,
    *,
    lag: int = 2,
    anchor: str = "INDPRO",
) -> pd.Series:
    """First PC of a cleaned vintage, seen ``lag`` months late at each decision, unit variance."""
    rows = pd.period_range(start - lag, end, freq="M")
    data = vintage.transformed.reindex(rows).to_numpy(dtype=float)
    cleaner = MacroCleaner().fit(data)
    cleaned = cleaner.transform(data)
    score = Pca(1).fit(cleaned).transform(cleaned)[:, 0]
    kept = list(vintage.transformed.columns[cleaner.keep_])
    if anchor in kept and np.corrcoef(score, cleaned[:, kept.index(anchor)])[0, 1] < 0:
        score = -score
    factor = pd.Series(score / score.std(), index=rows)
    return factor.shift(lag).reindex(pd.period_range(start, end, freq="M"))
