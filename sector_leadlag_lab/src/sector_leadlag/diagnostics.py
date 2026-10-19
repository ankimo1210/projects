"""Diagnostics after the verdict (design §9). None of them changes it."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import Spec, cross_standardize
from .stages import (
    Returns,
    basket_long_short,
    basket_series,
    build_signal,
    cash_summary,
    cut,
    etf_long_short,
    etf_returns,
    fit_in,
    h1_baskets,
    h2_series,
)
from .study import B1, B2, LONGER_SESSION, ORIGINAL, A, B, C, Study
from .synthetic import stale_returns

STALE = (("random", 0.1), ("random", 0.2), ("largest_gap", 0.1))
PLACEBO_DAYS = 85  # h, the decay paper's post-publication sample
PLACEBO_MIN_PRE = 250
PERIODS = {"a": A, "b1": B1, "b2": B2}
BASELINES = {"pca_lambda0": Spec(lam=0.0), "momentum": Spec(kind="momentum"), "k1": Spec(k=1)}


def placebo(daily: pd.Series, h: int = PLACEBO_DAYS, min_pre: int = PLACEBO_MIN_PRE) -> dict:
    """The decay paper's §4.2 in mean form: the change from A to the first h days of B1, against
    the same change at every pseudo publication date inside A."""
    a = cut(daily, A).dropna().to_numpy()
    post = cut(daily, B1).dropna().to_numpy()[:h]
    actual = float(post.mean() - a.mean())
    total = np.r_[0.0, np.cumsum(a)]
    starts = np.arange(min_pre, len(a) - h + 1)
    pseudo = (total[starts + h] - total[starts]) / h - total[starts] / starts
    return {
        "actual_ann": ev.YEAR * actual,
        "pseudo_min_ann": ev.YEAR * float(pseudo.min()),
        "share_at_or_below": float((pseudo <= actual).mean()),
        "pseudo_dates": len(pseudo),
        "post_days": len(post),
    }


def stale_opens(study: Study, sz: pd.DataFrame, weights: pd.DataFrame) -> dict:
    """H1 on baskets whose opening values are partly the previous close (design §2.3, §9)."""
    p, sector = study.stocks, study.stocks.sector
    o2c, c2o, price_c2c = bk.open_to_close(p), bk.close_to_open(p), bk.price_close_to_close(p)
    out = {}
    for mode, fraction in STALE:
        stale = stale_returns(o2c, price_c2c, c2o, fraction, mode=mode)
        out[f"{mode}_{round(100 * fraction)}"] = fit_in(
            bk.basket_returns(weights, stale, sector), sz, A
        )
    return out


def decomposition(signal: pd.DataFrame, study: Study, etf: Returns, basket: Returns) -> dict:
    """Annualised long-short means on each leg of the day (the decay paper's table 4)."""
    out: dict[str, dict] = {"etf": {}, "basket": {}}
    for leg in ("c2o", "o2c", "c2c"):
        series = {
            "etf": etf_long_short(signal, study, getattr(etf, leg)),
            "basket": basket_long_short(signal, getattr(basket, leg)),
        }
        for name, daily in series.items():
            out[name][leg] = {
                key: ev.describe(cut(daily, period))["mean_ann"] for key, period in PERIODS.items()
            }
    return out


def run_diagnostics(study: Study, prior: dict) -> dict:
    variant = prior["g0"]["selected"]
    signal = build_signal(study, variant)
    sz = cross_standardize(signal)
    baskets = h1_baskets(study)
    etf, basket = etf_returns(study), basket_series(study, baskets.main)
    top10 = basket_series(study, baskets.top10)
    out: dict = {"variant": variant}
    out["stale_opens"] = {"o2c": fit_in(basket.o2c, sz, A), **stale_opens(study, sz, baskets.main)}
    out["placebo"] = {
        "etf": placebo(etf_long_short(signal, study, etf.o2c)),
        "basket": placebo(basket_long_short(signal, basket.o2c)),
    }
    out["decomposition"] = decomposition(signal, study, etf, basket)
    out["c2o_control"] = {
        "etf": fit_in(etf.o2c, sz, A, [etf.c2o]),
        "basket": fit_in(basket.o2c, sz, A, [basket.c2o]),
    }
    before = (A[0], LONGER_SESSION - pd.Timedelta(days=1))
    after = (LONGER_SESSION, A[1])
    out["session_change"] = {
        name: {"before": fit_in(r.o2c, sz, before), "after": fit_in(r.o2c, sz, after)}
        for name, r in (("etf", etf), ("basket", basket))
    }
    others = {name: build_signal(study, variant, spec=spec) for name, spec in BASELINES.items()}
    others["variant_b"] = build_signal(study, variant, jp_c2c=basket.c2c)
    out["other_signals"] = {
        name: {
            "basket": fit_in(basket.o2c, cross_standardize(other), A),
            "etf": fit_in(etf.o2c, cross_standardize(other), A),
            "etf_original": ev.monthly_metrics(
                cut(etf_long_short(other, study, etf.o2c), ORIGINAL)
            ),
        }
        for name, other in others.items()
    }
    out["top10_basket"] = {"a": fit_in(top10.o2c, sz, A), "b": fit_in(top10.o2c, sz, B)}
    cash, spread = h2_series(study, cut(signal, C), baskets.median)
    out["reference_c"] = {
        "days": len(cut(signal, C)),
        "basket": fit_in(basket.o2c, sz, C),
        "etf": fit_in(etf.o2c, sz, C),
        "etf_long_short": ev.describe(cut(etf_long_short(signal, study, etf.o2c), C)),
        "cash": cash_summary(cash),
        "spread": ev.describe(spread),
    }
    return out
