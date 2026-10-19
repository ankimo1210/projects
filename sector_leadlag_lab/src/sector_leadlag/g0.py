"""G0: data checks, and the ETF-only replication that picks the pairing (design §8).

Nothing here reads an ETF value after B1 (2026-07-23), and nothing relates the signal to stock
returns: stock prices enter only the data checks.
"""

from __future__ import annotations

import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import cross_standardize
from .stages import (
    build_signal,
    cut,
    etf_long_short,
    etf_returns,
    fit_summary,
    h1_baskets,
)
from .study import B1, ORIGINAL, A, Study
from .timing import VARIANTS

PUBLISHED = {
    "ar": 0.2379,  # strategy paper, PCA SUB, monthly x 12
    "risk": 0.1070,
    "rr": 2.22,
    "mdd": 0.0958,
    "mean_a": 0.3018,  # decay paper, ETF open to close, daily x 252
    "mean_b1": -1.0707,
    "cumulative_b1": -0.3079,
    "c2o_a": 0.3515,
    "c2o_b1": 1.1682,
    "beta_a_1e4": 4.75,
    "beta_b1_1e4": -18.31,
    "days_a": 2737,
    "days_b1": 85,
}
OUTLIER = 0.2  # |O2C| or |C2O| above this is listed (never removed)
LIST_MAX = 100
END = B1[1]


def replicate(study: Study, variant: str) -> dict:
    """The paper's ETF long-short and the ETF panel regression under one pairing."""
    signal = build_signal(study, variant).loc[:END]
    sz = cross_standardize(signal)
    etf = etf_returns(study)
    o2c = etf_long_short(signal, study, etf.o2c)
    c2o = etf_long_short(signal, study, etf.c2o)
    fit_a = ev.panel_fit(cut(etf.o2c, A), cut(sz, A))
    b1 = ev.describe(cut(o2c, B1))
    return {
        "original": ev.monthly_metrics(cut(o2c, ORIGINAL)),
        "a": ev.describe(cut(o2c, A)),
        "b1": b1,
        "c2o_a": ev.describe(cut(c2o, A))["mean_ann"],
        "c2o_b1": ev.describe(cut(c2o, B1))["mean_ann"],
        "fit_a": fit_summary(fit_a),
        "fit_b1": fit_summary(ev.panel_fit(cut(etf.o2c, B1), cut(sz, B1))),
        "pass": bool(fit_a.p < ev.ALPHA and b1["mean_ann"] < 0),
    }


def choose(variants: dict[str, dict]) -> str | None:
    """Of the pairings that pass, the one whose 2015-2025 AR is closest to the paper's 23.79%."""
    passing = [name for name in VARIANTS if variants[name]["pass"]]
    if not passing:
        return None
    return min(passing, key=lambda name: abs(variants[name]["original"]["ar"] - PUBLISHED["ar"]))


def zero_volume(panel: bk.Panel, period) -> dict:
    """Per ETF: days with a price, days without trades, and how often such a day kept the
    previous close."""
    zero = (panel.volume.fillna(0.0) == 0) & panel.close.notna()
    same = panel.close.eq(panel.close.shift(1))
    zero, same, close = cut(zero, period), cut(same, period), cut(panel.close, period)
    out = {}
    for column in panel.close.columns:
        priced, flat = int(close[column].notna().sum()), int(zero[column].sum())
        out[str(column)] = {
            "days": priced,
            "zero": flat,
            "share": flat / priced if priced else 0.0,
            "stale": float(same[column][zero[column]].mean()) if flat else 0.0,
        }
    return out


def outliers(frames: dict[str, pd.DataFrame]) -> dict:
    rows = []
    for kind, frame in frames.items():
        stacked = frame.stack()
        for (day, name), value in stacked[stacked.abs() > OUTLIER].items():
            rows.append({"kind": kind, "date": str(day.date()), "name": str(name), "value": value})
    rows.sort(key=lambda row: -abs(row["value"]))
    return {"count": len(rows), "largest": rows[:LIST_MAX]}


def split_events(panel: bk.Panel, period) -> dict:
    """Every split: the adjusted close-to-open of its ex-date should look like any other day."""
    c2o = cut(bk.close_to_open(panel), period)
    events = cut(panel.splits, period).where(lambda s: s > 0).stack().dropna()
    rows = [
        {"name": str(name), "date": str(day.date()), "ratio": ratio, "c2o": c2o.at[day, name]}
        for (day, name), ratio in events.items()
    ]
    flagged = [row for row in rows if not abs(row["c2o"]) <= OUTLIER]  # a NaN is flagged too
    return {"events": len(rows), "flagged_count": len(flagged), "flagged": flagged[:LIST_MAX]}


def dividend_events(panel: bk.Panel, period) -> dict:
    """Ex-dates: adding the dividend back should bring the overnight return closer to 0."""
    with_dividend = cut(bk.close_to_open(panel), period)
    without = cut((panel.open / panel.close.shift(1) - 1.0).where(bk.traded(panel)), period)
    ex = cut(panel.dividends, period) > 0

    def mean_abs(frame: pd.DataFrame) -> float | None:
        values = frame[ex].stack().dropna()
        return float(values.abs().mean()) if len(values) else None

    return {
        "events": int(ex.to_numpy().sum()),
        "mean_abs_c2o_with": mean_abs(with_dividend),
        "mean_abs_c2o_without": mean_abs(without),
    }


def coverage(study: Study, weights: pd.DataFrame, period) -> dict:
    """Correlation of the ETF and the H1 basket close-to-close returns, by sector and year."""
    etf = cut(bk.close_to_close(study.etf), period)
    basket = cut(
        bk.basket_returns(weights, bk.close_to_close(study.stocks), study.stocks.sector), period
    )
    out = {}
    for sector in bk.SECTORS:
        both = pd.concat([etf[sector], basket[sector]], axis=1).dropna()
        by_year = both.groupby(both.index.year)
        out[str(sector)] = {
            str(year): float(f.iloc[:, 0].corr(f.iloc[:, 1])) for year, f in by_year if len(f) > 2
        }
    return out


def data_checks(study: Study) -> dict:
    period = (A[0], END)
    baskets = h1_baskets(study)
    first = cut(baskets.median, period).iloc[0]
    counts = (first > 0).groupby(study.stocks.sector).sum()
    return {
        "names": {
            "topix500": len(study.stocks.sector) + len(study.missing),
            "with_prices": len(study.stocks.sector),
            "missing": list(study.missing),
            "per_sector_on_first_a_day": {str(k): int(v) for k, v in counts.items()},
        },
        "etf_zero_volume": zero_volume(study.etf, period),
        "outliers": outliers(
            {
                "etf_o2c": cut(bk.open_to_close(study.etf), period),
                "etf_c2o": cut(bk.close_to_open(study.etf), period),
                "stock_o2c": cut(bk.open_to_close(study.stocks), period),
                "stock_c2o": cut(bk.close_to_open(study.stocks), period),
            }
        ),
        "splits": split_events(study.stocks, period),
        "dividends": dividend_events(study.stocks, period),
        "coverage": coverage(study, baskets.main, period),
    }


def run_g0(study: Study, prior: dict) -> dict:
    variants = {name: replicate(study, name) for name in VARIANTS}
    selected = choose(variants)
    return {
        "published": PUBLISHED,
        "variants": variants,
        "selected": selected,
        "pass": selected is not None,
        "verdict": None if selected else "replication_failed",
        "checks": data_checks(study),
    }
