"""OOS-A: the pre-registered test on decisions 2000-01..2018-12 (design §3.4-3.5, PREREG §1).

Reported beside the verdict inputs: IEF-like and 10-year-zero results, the secondary target,
0-100 % weights, R2oos, and the same signals on actual TLT/IEF returns.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from . import evaluate as ev
from .backtest import (
    Forecasts,
    delayed_returns,
    fractional_weights,
    signal_weights,
    strategy_returns,
)
from .data import etf
from .returns import INSTRUMENTS, delayed_switch_excess
from .stages import (
    COST_BP,
    COST_HIGH_BP,
    as_frame,
    forecast,
    primary_names,
    primary_tests,
    strategy_weights,
    summary,
    window,
)
from .study import OOS_A, Study

MODELS = ["ols_p", "ols_pm", "en", "et", "hgb", "nn_f", "nn_fm"]


def _cer(r: pd.Series) -> float:
    return ev.cer(r.dropna())


def evaluate_instrument(
    study,
    outcomes,
    decisions: pd.PeriodIndex,
    primary: Forecasts,
    cp: Forecasts | None,
    p1: str,
    instrument: str,
    legs: pd.DataFrame | None,
) -> dict:
    weights = strategy_weights(study, outcomes, decisions, primary, cp, instrument)
    excess = outcomes.excess[instrument]
    base = {name: strategy_returns(w, excess, COST_BP) for name, w in weights.items()}
    high = {name: strategy_returns(w, excess, COST_HIGH_BP) for name, w in weights.items()}
    entry = {
        "summary": {name: summary(base[name], weights[name]) for name in weights},
        "summary_4bp": {name: summary(high[name], weights[name]) for name in weights},
        "tests": primary_tests(base, p1),
    }
    names = primary_names(p1)
    robust = {
        k: {
            "vs_hold_4bp": _cer(high[v]) - _cer(high["hold"]),
            "vs_p1_4bp": _cer(high[v]) - _cer(high[p1]),
        }
        for k, v in names.items()
    }
    if legs is not None:
        delayed = {name: delayed_returns(w, excess, legs, COST_BP) for name, w in weights.items()}
        entry["summary_delay"] = {name: summary(delayed[name], weights[name]) for name in weights}
        for k, v in names.items():
            robust[k]["vs_hold_delay"] = _cer(delayed[v]) - _cer(delayed["hold"])
            robust[k]["vs_p1_delay"] = _cer(delayed[v]) - _cer(delayed[p1])
    entry["robust"] = robust
    return entry


def run_oos_a(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(*OOS_A)
    macro = study.realtime_macro()
    primary = forecast(
        study,
        as_frame(study.outcomes.rx12[10]),
        MODELS,
        decisions=decisions,
        horizon=12,
        macro=macro,
        workers=workers,
    )
    secondary = forecast(
        study,
        as_frame(study.outcomes.xr1),
        MODELS,
        decisions=decisions,
        horizon=1,
        macro=macro,
        workers=workers,
    )
    cp = forecast(
        study,
        as_frame(study.outcomes.rxbar),
        ["cp"],
        decisions=decisions,
        horizon=12,
        macro=None,
        workers=workers,
    )
    out: dict = {"window": [str(decisions[0]), str(decisions[-1])], "p1": p1, "instruments": {}}
    for instrument in ("tlt", "ief", "z10"):
        legs = None
        if instrument != "z10":
            legs = delayed_switch_excess(study.curve, INSTRUMENTS[instrument], study.cash)
        out["instruments"][instrument] = evaluate_instrument(
            study, study.outcomes, decisions, primary, cp, p1, instrument, legs
        )
    out["secondary"] = _secondary(study, decisions, secondary)
    out["fractional"] = _fractional(study, decisions, primary)
    out["r2_oos"] = _r2(study, decisions, primary, secondary)
    out["etf"] = _etf(study, decisions, primary, cp, p1)
    tlt = strategy_weights(study, study.outcomes, decisions, primary, cp, "tlt")
    out["weights"] = {
        "decisions": [str(d) for d in decisions],
        **{k: tlt[v].astype(int).tolist() for k, v in primary_names(p1).items()},
    }
    out["params"] = primary.params
    out["params_secondary"] = secondary.params
    return out


def _secondary(study: Study, decisions: pd.PeriodIndex, secondary: Forecasts) -> dict:
    out = {}
    for instrument in ("tlt", "ief"):
        excess = study.outcomes.excess[instrument]
        weights = {m: signal_weights(f[0], decisions) for m, f in secondary.predictions.items()}
        out[instrument] = {
            m: summary(strategy_returns(w, excess, COST_BP), w) for m, w in weights.items()
        }
    return out


def _fractional(study: Study, decisions: pd.PeriodIndex, primary: Forecasts) -> dict:
    out: dict = {}
    for instrument in ("tlt", "ief"):
        excess = study.outcomes.excess[instrument]
        out[instrument] = {}
        for model, frame in primary.predictions.items():
            w = fractional_weights(frame[0], excess, decisions)
            out[instrument][model] = summary(strategy_returns(w, excess, COST_BP), w)
    return out


def _r2(study: Study, decisions: pd.PeriodIndex, primary: Forecasts, secondary: Forecasts) -> dict:
    rx, xr = study.outcomes.rx12[10], study.outcomes.xr1
    rx_bench = ev.prevailing_mean(rx, decisions, 12)
    xr_bench = ev.prevailing_mean(xr, decisions, 1)
    return {
        "rx12_10": {
            m: ev.r2_oos(rx.reindex(decisions), f[0].reindex(decisions), rx_bench)
            for m, f in primary.predictions.items()
        },
        "xr1_10": {
            m: ev.r2_oos(xr.reindex(decisions), f[0].reindex(decisions), xr_bench)
            for m, f in secondary.predictions.items()
        },
    }


def _etf(
    study: Study, decisions: pd.PeriodIndex, primary: Forecasts, cp: Forecasts, p1: str
) -> dict:
    out = {}
    for instrument, ticker in (("tlt", "TLT"), ("ief", "IEF")):
        actual = etf.monthly_total_returns(etf.load_prices(ticker, study.raw_root))
        excess = (actual - study.cash).dropna()
        span = decisions[np.asarray((decisions + 1).isin(excess.index))]
        weights = strategy_weights(study, study.outcomes, span, primary, cp, instrument)
        base = {name: strategy_returns(w, excess, COST_BP) for name, w in weights.items()}
        out[instrument] = {
            "window": [str(span[0]), str(span[-1])],
            "summary": {name: summary(base[name], weights[name]) for name in weights},
            "tests": primary_tests(base, p1),
        }
    return out
