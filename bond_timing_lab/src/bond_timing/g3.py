"""G3: is the macro contribution larger than a world where macro cannot help? (design §8, PREREG 18)

Statistic: CER(P4) - CER(P2) and CER(P5) - CER(P2) on OOS-A decisions, holding the 10-year zero
against cash y(1)/12 at 2 bp, with P4/P5 hyperparameters fixed to their OOS-A choices and 5 NN
seeds. p = (1 + #{simulated >= real}) / 201.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping

import pandas as pd

from . import evaluate as ev
from .backtest import REAL_TIME, build_tasks, run_forecasts, signal_weights, strategy_returns
from .data.fredmd import PanelMacro
from .features import YIELD_MONTHS, MacroCleaner
from .models import ladder
from .returns import excess_simple, holding_log_return, rx12
from .stages import COST_BP, as_frame, window
from .study import FINAL_VINTAGE, OOS_A, TRAIN_START, Study
from .synthetic import fit_spanning_null, simulate

WORLDS = 200
NN_SEEDS = 5
SEED = 3000
MONTHS = tuple(sorted({m for n in range(1, 11) for m in (12 * n, 12 * n - 1)} - {11}))
MODELS = ("ols_p", "nn_fm", "et")


def statistic(
    zeros: pd.DataFrame, macro, decisions: pd.PeriodIndex, fixed: Mapping, workers: int
) -> dict[str, float]:
    cash = (zeros[12] / 12.0).shift(1)
    excess = excess_simple(holding_log_return(zeros, 120), cash)
    tasks = build_tasks(
        zeros[list(YIELD_MONTHS)],
        as_frame(rx12(zeros, 10)),
        macro,
        refit_years=range(decisions[0].year, decisions[-1].year + 1),
        window=(decisions[0], decisions[-1]),
        horizon=12,
        rules=REAL_TIME,
    )
    specs = ladder(NN_SEEDS)
    fc = run_forecasts(tasks, [specs[m] for m in MODELS], workers=workers, fixed=fixed)
    cer = {
        m: ev.cer(
            strategy_returns(
                signal_weights(fc.predictions[m][0], decisions), excess, COST_BP
            ).dropna()
        )
        for m in MODELS
    }
    return {"P4": cer["nn_fm"] - cer["ols_p"], "P5": cer["et"] - cer["ols_p"]}


def run_g3(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    decisions = window(*OOS_A)
    months = pd.period_range(TRAIN_START, OOS_A[1] + 1, freq="M")
    fixed = {m: prior["oos_a"]["params"][m] for m in ("nn_fm", "et")}
    zeros = study.zeros[list(MONTHS)].reindex(months)
    real = statistic(zeros, study.realtime_macro(), decisions, fixed, workers)
    final = study.vintage(FINAL_VINTAGE).transformed.reindex(months).to_numpy(dtype=float)
    cleaner = MacroCleaner().fit(final)
    columns = study.vintage(FINAL_VINTAGE).transformed.columns[cleaner.keep_]
    panel = pd.DataFrame(cleaner.transform(final), index=months, columns=columns)
    null = fit_spanning_null(zeros, panel)
    simulated = []
    for b in range(WORLDS):
        sim_zeros, sim_macro = simulate(null, SEED + b)
        simulated.append(
            statistic(sim_zeros, PanelMacro(sim_macro, lag=2), decisions, fixed, workers)
        )
        if (b + 1) % 10 == 0:
            print(f"G3 world {b + 1}/{WORLDS} done", file=sys.stderr, flush=True)
    p = {k: (1 + sum(s[k] >= real[k] for s in simulated)) / (WORLDS + 1) for k in ("P4", "P5")}
    return {
        "real": real,
        "p": p,
        "worlds": WORLDS,
        "nn_seeds": NN_SEEDS,
        "factor_max_eigenvalue": null.max_eigenvalue,
        "simulated": simulated,
    }
