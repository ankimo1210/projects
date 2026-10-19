"""Apparent predictability, one point-in-time rule at a time (design §7; reported, not judged).

V0  paper-like: final vintage 2019-02 with the publication lag ignored, unrealized targets in
    training (s <= t-1), no embargo, transforms on the full 1971-08..2018-12 sample; Liu-Wu and GSW
V1  V0 + R2;  V2  V1 + R3 + R4;  V3  V2 + R1 (real-time vintages), 2000-01..2018-12 only.
Targets rx12 for 2..10 years (one multi-output model) and their average; R2oos is against the
prevailing mean the same setting could compute.

The settings refit each January (design §6.3). The monthly check (PREREG §5, after OOS-B) refits
V0 and V1 every month, as the paper does, and reads the result against thresholds fixed first.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Mapping

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
MONTHLY_SETTINGS = {
    "V0m_liuwu": SETTINGS["V0_liuwu"],
    "V0m_gsw": SETTINGS["V0_gsw"],
    "V1m_liuwu": ("liuwu", *SETTINGS["V1"][1:]),
    "V1m_gsw": SETTINGS["V1"],
}
REPRODUCED = 0.20  # the lowest pre-correction R2oos of the paper's macro networks (PREREG §5)
LARGE_GAP = 0.10
READINGS = {
    (True, True): "leak_explains_paper",
    (True, False): "reproduced_without_leak",
    (False, True): "leak_partial",
    (False, False): "leak_not_explaining",
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


def monthly_reading(monthly: Mapping[str, dict], annual: Mapping[str, dict]) -> dict:
    """PREREG §5: the maturity-average R2oos of nn_fm on Liu-Wu, refit monthly with and without
    R2, against the paper's level and against the annual-refit V0."""
    v0m = monthly["V0m_liuwu"]["nn_fm"]["avg"]
    v1m = monthly["V1m_liuwu"]["nn_fm"]["avg"]
    v0 = annual["V0_liuwu"]["nn_fm"]["avg"]
    reproduces, leak_large = v0m >= REPRODUCED, v0m - v1m >= LARGE_GAP
    return {
        "v0m": v0m,
        "v1m": v1m,
        "v0_annual": v0,
        "reproduces": reproduces,
        "leak_gap": v0m - v1m,
        "leak_large": leak_large,
        "dilution": v0m - v0,
        "dilution_large": v0m - v0 >= LARGE_GAP,
        "reading": READINGS[(reproduces, leak_large)],
    }


def _forecast_settings(
    study: Study, settings: Mapping[str, tuple], workers: int, refit_every: int = 12
) -> Iterator[tuple[str, pd.DataFrame, Forecasts, pd.PeriodIndex, Rules]]:
    curves = {"gsw": study.zeros, "liuwu": liuwu.load_liuwu(study.raw_root)}
    for name, (curve, macro_kind, rules, span) in settings.items():
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
            refit_every=refit_every,
        )
        yield name, targets, fc, decisions, rules


def run_decomposition(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    out: dict = {}
    for name, targets, fc, decisions, rules in _forecast_settings(study, SETTINGS, workers):
        out[name] = r2_table(targets, fc, decisions, complete=rules.complete_targets)
        if name == "V2":
            out["V2_from_2000"] = r2_table(
                targets, fc, decisions[decisions >= OOS_A[0]], complete=True
            )
    return out


def run_monthly_decomposition(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    out: dict = {}
    settings = _forecast_settings(study, MONTHLY_SETTINGS, workers, refit_every=1)
    for name, targets, fc, decisions, rules in settings:
        out[name] = r2_table(targets, fc, decisions, complete=rules.complete_targets)
        print(f"decompose-monthly {name} done", file=sys.stderr, flush=True)
    return {**out, "reading": monthly_reading(out, prior["decompose"])}
