"""Apparent predictability, one point-in-time rule at a time (design §7; reported, not judged).

V0  paper-like: final vintage 2019-02 with the publication lag ignored, unrealized targets in
    training (s <= t-1), no embargo, transforms on the full 1971-08..2018-12 sample; Liu-Wu and GSW
V1  V0 + R2;  V2  V1 + R3 + R4;  V3  V2 + R1 (real-time vintages), 2000-01..2018-12 only.
Targets rx12 for 2..10 years (one multi-output model) and their average; R2oos is against the
prevailing mean the same setting could compute.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from . import evaluate as ev
from .backtest import V0, V1, V2, V3, Forecasts, Rules
from .data import liuwu
from .features import YIELD_MONTHS
from .returns import RX_YEARS, rx12
from .stages import forecast, window
from .study import OOS_A, Study

MODELS = ["ols_p", "en", "et", "nn_fm"]
FULL_END = pd.Period("2018-12", "M")
EARLY = (pd.Period("1990-01", "M"), pd.Period("2018-12", "M"))
SETTINGS: dict[str, tuple[str, str, Rules, tuple[pd.Period, pd.Period]]] = {
    "V0_liuwu": ("liuwu", "final", V0, EARLY),
    "V0_gsw": ("gsw", "final", V0, EARLY),
    "V1": ("gsw", "final", V1, EARLY),
    "V2": ("gsw", "final", V2, EARLY),
    "V3": ("gsw", "realtime", V3, OOS_A),
}


def r2_table(
    targets: pd.DataFrame, forecasts: Forecasts, decisions: pd.PeriodIndex, *, complete: bool
) -> dict:
    average = targets.mean(axis=1, skipna=False)
    average_bench = ev.prevailing_mean(average, decisions, 12, complete=complete)
    table = {}
    for model, frame in forecasts.predictions.items():
        prediction = frame.reindex(decisions)
        prediction.columns = list(targets.columns)
        row = {}
        for n in targets.columns:
            bench = ev.prevailing_mean(targets[n], decisions, 12, complete=complete)
            row[str(n)] = ev.r2_oos(targets[n].reindex(decisions), prediction[n], bench)
        row["avg"] = ev.r2_oos(average.reindex(decisions), prediction.mean(axis=1), average_bench)
        table[model] = row
    return table


def run_decomposition(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    curves = {"gsw": study.zeros, "liuwu": liuwu.load_liuwu(study.raw_root)}
    out: dict = {}
    for name, (curve, macro_kind, rules, span) in SETTINGS.items():
        zeros = curves[curve]
        targets = pd.concat({n: rx12(zeros, n) for n in RX_YEARS}, axis=1)
        macro = study.final_macro() if macro_kind == "final" else study.realtime_macro()
        decisions = window(*span)
        fc = forecast(
            study,
            targets,
            MODELS,
            decisions=decisions,
            horizon=12,
            macro=macro,
            rules=rules,
            workers=workers,
            yields=zeros[list(YIELD_MONTHS)],
            full_end=FULL_END,
        )
        out[name] = r2_table(targets, fc, decisions, complete=rules.complete_targets)
        if name == "V2":
            out["V2_from_2000"] = r2_table(
                targets, fc, decisions[decisions >= OOS_A[0]], complete=True
            )
    return out
