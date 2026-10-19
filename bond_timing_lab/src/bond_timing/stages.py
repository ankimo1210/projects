"""Shared stage helpers and the first two stages: G0 data checks and the dev-period P1 (design §3, §8).

Every stage runner takes ``(study, workers, prior)`` and returns a JSON-ready dict; ``prior``
holds the results of the stages it depends on (see ``cli.REQUIRES``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict

import numpy as np
import pandas as pd

from . import evaluate as ev
from .backtest import (
    REAL_TIME,
    Forecasts,
    Rules,
    build_tasks,
    run_forecasts,
    signal_weights,
    strategy_returns,
)
from .data import etf, liuwu
from .features import slope, trailing_sum
from .models import ladder
from .returns import INSTRUMENTS, daily_synthetic_returns, holding_log_return
from .study import DEV, TRAIN_START, Study

PRIMARY = {"P2": "ols_p", "P3": "ols_pm", "P4": "nn_fm", "P5": "et"}
RULES = ("slope", "trend", "cp")
COST_BP = 2.0
COST_HIGH_BP = 4.0
G0_MIN_CORR = 0.95


def window(first: pd.Period, last: pd.Period) -> pd.PeriodIndex:
    return pd.period_range(first, last, freq="M")


def as_frame(series: pd.Series) -> pd.DataFrame:
    return series.to_frame(name=0)


def summary(returns: pd.Series, weights: pd.Series) -> dict:
    r = returns.dropna()
    w = weights.reindex(r.index - 1)
    return {
        "cer": ev.cer(r),
        "sharpe": ev.sharpe(r),
        "mean": float(12 * r.mean()),
        "vol": float(np.sqrt(12) * r.std(ddof=1)),
        "months": len(r),
        "switches": int((w.diff().abs() > 0).sum()),
        "hold_share": float(w.mean()),
    }


def forecast(
    study: Study,
    targets: pd.DataFrame,
    models: Sequence[str],
    *,
    decisions: pd.PeriodIndex,
    horizon: int,
    macro,
    rules: Rules = REAL_TIME,
    nn_seeds: int = 20,
    workers: int = 1,
    fixed: Mapping | None = None,
    yields: pd.DataFrame | None = None,
    full_end: pd.Period | None = None,
    refit_every: int = 12,
) -> Forecasts:
    specs = ladder(nn_seeds)
    tasks = build_tasks(
        study.yields if yields is None else yields,
        targets,
        macro,
        refit_years=range(decisions[0].year, decisions[-1].year + 1),
        window=(decisions[0], decisions[-1]),
        horizon=horizon,
        rules=rules,
        full_end=full_end,
        refit_every=refit_every,
    )
    return run_forecasts(tasks, [specs[name] for name in models], workers=workers, fixed=fixed)


def first_column(forecasts: Forecasts | None, model: str) -> pd.Series | None:
    if forecasts is None or model not in forecasts.predictions:
        return None
    return forecasts.predictions[model][0]


def rule_signals(study, outcomes, instrument: str, cp: pd.Series | None) -> dict[str, pd.Series]:
    """L1: the slope (10-year zero minus the bill), the trailing 12-month excess return, and CP."""
    return {
        "slope": slope(study.zeros, study.bey),
        "trend": trailing_sum(outcomes.excess[instrument]),
        "cp": cp if cp is not None else pd.Series(np.nan, index=study.zeros.index),
    }


def strategy_weights(
    study,
    outcomes,
    decisions: pd.PeriodIndex,
    forecasts: Forecasts | None,
    cp: Forecasts | None,
    instrument: str,
) -> dict[str, pd.Series]:
    weights = {"hold": pd.Series(1.0, index=decisions), "cash": pd.Series(0.0, index=decisions)}
    for name, signal in rule_signals(study, outcomes, instrument, first_column(cp, "cp")).items():
        weights[name] = signal_weights(signal, decisions)
    if forecasts is not None:
        for model, frame in forecasts.predictions.items():
            weights[model] = signal_weights(frame[0], decisions)
    return weights


def primary_names(p1: str) -> dict[str, str]:
    return {"P1": p1, **PRIMARY}


def primary_tests(returns: Mapping[str, pd.Series], p1: str, *, seed: int = ev.SEED) -> dict:
    """H_A: P1-P5 against always-hold (Holm over 5); H_B: P4, P5 against P1 (Holm over 2)."""
    names = primary_names(p1)
    vs_hold = {k: ev.diff_test(returns[v], returns["hold"], seed=seed) for k, v in names.items()}
    vs_p1 = {k: ev.diff_test(returns[names[k]], returns[p1], seed=seed) for k in ("P4", "P5")}
    holm_hold = ev.holm({k: t.p_cer for k, t in vs_hold.items()})
    holm_p1 = ev.holm({k: t.p_cer for k, t in vs_p1.items()})
    return {
        "vs_hold": {k: {**asdict(t), "p_holm": holm_hold[k]} for k, t in vs_hold.items()},
        "vs_p1": {k: {**asdict(t), "p_holm": holm_p1[k]} for k, t in vs_p1.items()},
    }


def run_g0(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    out: dict = {"etf": {}, "daily_outliers": {}, "gsw_vs_liuwu_bp": {}}
    for instrument, ticker in (("tlt", "TLT"), ("ief", "IEF")):
        prices = etf.load_prices(ticker, study.raw_root)
        synthetic = np.expm1(holding_log_return(study.zeros, INSTRUMENTS[instrument]))
        joint = pd.concat(
            {"synthetic": synthetic, "etf": etf.monthly_total_returns(prices)}, axis=1
        ).dropna()
        corr = float(joint.corr().iloc[0, 1])
        gap = joint["synthetic"] - joint["etf"]
        out["etf"][instrument] = {
            "first": str(joint.index[0]),
            "last": str(joint.index[-1]),
            "months": len(joint),
            "corr": corr,
            "pass": corr >= G0_MIN_CORR,
            "mean_gap_annual": float(12 * gap.mean()),
            "tracking_error_annual": float(np.sqrt(12) * gap.std(ddof=1)),
        }
        daily = pd.concat(
            {
                "synthetic": daily_synthetic_returns(
                    study.curve, INSTRUMENTS[instrument], prices.index[0].date()
                ),
                "etf": etf.daily_returns(prices),
            },
            axis=1,
        ).dropna()
        diff = daily["etf"] - daily["synthetic"]
        far = diff[diff.abs() > 5 * diff.std(ddof=1)]
        out["daily_outliers"][instrument] = {
            "days": len(daily),
            "count": len(far),
            "largest": [
                {
                    "date": str(day.date()),
                    "etf": float(daily.loc[day, "etf"]),
                    "synthetic": float(daily.loc[day, "synthetic"]),
                }
                for day in far.abs().sort_values(ascending=False).index[:20]
            ],
        }
    lw = liuwu.load_liuwu(study.raw_root)
    for n in range(1, 11):
        gap = ((study.zeros[12 * n] - lw[12 * n]) * 1e4).dropna()
        gap = gap[gap.index >= TRAIN_START]
        out["gsw_vs_liuwu_bp"][str(n)] = {
            "months": len(gap),
            "mean": float(gap.mean()),
            "sd": float(gap.std(ddof=1)),
            "max_abs": float(gap.abs().max()),
            "at": str(gap.abs().idxmax()),
        }
    bil = etf.monthly_total_returns(etf.load_prices("BIL", study.raw_root))
    cash = pd.concat({"bil": bil, "dtb3": study.cash}, axis=1).dropna()
    out["cash_bil_vs_dtb3"] = {
        "months": len(cash),
        "corr": float(cash.corr().iloc[0, 1]),
        "mean_gap_annual": float(12 * (cash["bil"] - cash["dtb3"]).mean()),
    }
    months = study.bey.index[study.bey.index >= TRAIN_START]
    out["dtb3_missing_months"] = [
        str(m) for m in months[study.bey.reindex(months).isna().to_numpy()]
    ]
    out["pass"] = all(row["pass"] for row in out["etf"].values())
    return out


def run_dev(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    """Pick P1: the best L1 rule by TLT-like CER (2 bp) over the dev months all three rules share."""
    decisions = window(*DEV)
    cp = forecast(
        study,
        as_frame(study.outcomes.rxbar),
        ["cp"],
        decisions=decisions,
        horizon=12,
        macro=None,
        workers=workers,
    )
    out: dict = {"window": [str(decisions[0]), str(decisions[-1])], "instruments": {}}
    for instrument in ("tlt", "ief"):
        signals = rule_signals(study, study.outcomes, instrument, first_column(cp, "cp"))
        excess = study.outcomes.excess[instrument]
        defined = (
            pd.concat([s.reindex(decisions) for s in signals.values()], axis=1).notna().all(axis=1)
        )
        defined &= excess.reindex(decisions + 1).notna().to_numpy()
        common = decisions[defined.to_numpy()]
        table = {}
        for name, signal in signals.items():
            weights = signal_weights(signal, common)
            table[name] = summary(strategy_returns(weights, excess, COST_BP), weights)
        hold = pd.Series(1.0, index=common)
        table["hold"] = summary(strategy_returns(hold, excess, COST_BP), hold)
        out["instruments"][instrument] = {
            "common": [str(common[0]), str(common[-1]), len(common)],
            "rules": table,
        }
    tlt = out["instruments"]["tlt"]["rules"]
    out["p1"] = max(RULES, key=lambda name: tlt[name]["cer"])
    out["cp_refits"] = sorted(cp.params.get("cp", {}))
    return out
