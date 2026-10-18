"""G1: worlds with no signal (W0) and with a planted macro signal (W2) (design §8, PREREG 16-17, 20).

Pass: in W0 no primary strategy is significant (H_A, Holm) in more than 2 of 20 worlds. W2 is
reported, not judged (PREREG §4): the detection counts of P1-P5, and those of an oracle and of a
perfect-feature regression at planted sizes of 1, 2, 3 and 6 times k.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace

import numpy as np
import pandas as pd

from . import evaluate as ev
from .backtest import signal_weights, strategy_returns
from .returns import Outcomes
from .stages import (
    COST_BP,
    as_frame,
    forecast,
    primary_names,
    primary_tests,
    strategy_weights,
    window,
)
from .study import FINAL_VINTAGE, OOS_A, TRAIN_START, Study, macro_pc1
from .synthetic import calibrate_k, plant, w0_world

REPS = 20
NN_SEEDS = 5
MAX_FALSE = 2
MODELS = ["ols_p", "ols_pm", "nn_fm", "et"]
SEEDS = {"W0": 1000, "W2": 2000}
POWER_MULTIPLES = (1.0, 2.0, 3.0, 6.0)
HOLM_BOUND = 5  # Holm multiplies the smallest of the five p-values by 5


def count_significant(
    runs: Sequence[Mapping], names: Sequence[str], key: str = "p_holm"
) -> dict[str, int]:
    return {name: sum(run[key][name] < ev.ALPHA for run in runs) for name in names}


def g1_passed(counts: Mapping[str, Mapping[str, int]]) -> bool:
    return all(count <= MAX_FALSE for count in counts["W0"].values())


def proxy_forecast(rx: pd.Series, z: pd.Series, decisions: pd.PeriodIndex) -> pd.Series:
    """OLS of the 12-month target on [1, z_s] over s + 12 <= t, refit each January: what a model
    could do if it saw the planted factor itself."""
    known = rx.dropna()
    out = pd.Series(np.nan, index=decisions)
    for year in range(decisions[0].year, decisions[-1].year + 1):
        t = pd.Period(f"{year}-01", "M")
        rows = known.index[(known.index >= TRAIN_START) & (known.index <= t - 12)]
        x = z.reindex(rows).to_numpy(dtype=float)
        ok = np.isfinite(x)
        X = np.column_stack([np.ones(ok.sum()), x[ok]])
        beta = np.linalg.lstsq(X, known.reindex(rows).to_numpy(dtype=float)[ok], rcond=None)[0]
        months = decisions[(decisions >= t) & (decisions <= t + 11)]
        out.loc[months] = beta[0] + beta[1] * z.reindex(months).to_numpy(dtype=float)
    return out


def power_table(
    source: Outcomes, index: pd.PeriodIndex, z: pd.Series, k: float, decisions: pd.PeriodIndex
) -> dict:
    """Detection counts of the oracle (hold when z_t > 0) and of the proxy in W2 worlds whose
    planted size is a multiple of k: raw p < 0.05, and 5p < 0.05 (the Holm bound)."""
    oracle = (z.reindex(decisions) > 0).astype(float)
    always = pd.Series(1.0, index=decisions)
    table = {}
    for multiple in POWER_MULTIPLES:
        tests: dict[str, list[ev.DiffTest]] = {"oracle": [], "proxy": []}
        for rep in range(REPS):
            seed = SEEDS["W2"] + rep
            world = plant(w0_world(source, index, seed), z, k * multiple)
            excess = world.excess["tlt"]
            hold = strategy_returns(always, excess, COST_BP)
            proxy = signal_weights(proxy_forecast(world.rx12[10], z, decisions), decisions)
            for name, weights in (("oracle", oracle), ("proxy", proxy)):
                returns = strategy_returns(weights, excess, COST_BP)
                tests[name].append(ev.diff_test(returns, hold, seed=ev.SEED + seed))
        table[f"{multiple:g}"] = {
            name: {
                "raw": sum(t.p_cer < ev.ALPHA for t in runs),
                "holm_bound": sum(HOLM_BOUND * t.p_cer < ev.ALPHA for t in runs),
                "mean_delta_cer": float(np.mean([t.delta_cer for t in runs])),
            }
            for name, runs in tests.items()
        }
    return table


def run_g1(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(*OOS_A)
    end = OOS_A[1] + 1
    source = replace(
        study.outcomes,
        excess=study.outcomes.excess.loc[:end],
        monthly_log_excess=study.outcomes.monthly_log_excess.loc[:end],
    )
    index = pd.period_range(TRAIN_START, end, freq="M")
    z = macro_pc1(study.vintage(FINAL_VINTAGE), TRAIN_START, OOS_A[1])
    k = calibrate_k(study.outcomes.excess["tlt"], z, decisions)
    macro = study.realtime_macro()
    worlds: dict[str, list[dict]] = {"W0": [], "W2": []}
    for family, base in SEEDS.items():
        for rep in range(REPS):
            seed = base + rep
            world = w0_world(source, index, seed)
            if family == "W2":
                world = plant(world, z, k)
            fc = forecast(
                study,
                as_frame(world.rx12[10]),
                MODELS,
                decisions=decisions,
                horizon=12,
                macro=macro,
                nn_seeds=NN_SEEDS,
                workers=workers,
            )
            cp = None
            if p1 == "cp":
                cp = forecast(
                    study,
                    as_frame(world.rxbar),
                    ["cp"],
                    decisions=decisions,
                    horizon=12,
                    macro=None,
                    workers=workers,
                )
            weights = strategy_weights(study, world, decisions, fc, cp, "tlt")
            returns = {
                name: strategy_returns(w, world.excess["tlt"], COST_BP)
                for name, w in weights.items()
            }
            tests = primary_tests(returns, p1, seed=ev.SEED + seed)["vs_hold"]
            worlds[family].append(
                {
                    "seed": seed,
                    "p_holm": {s: t["p_holm"] for s, t in tests.items()},
                    "p_raw": {s: t["p_cer"] for s, t in tests.items()},
                    "delta_cer": {s: t["delta_cer"] for s, t in tests.items()},
                }
            )
            print(f"G1 {family} world {rep + 1}/{REPS} done", file=sys.stderr, flush=True)
    names = list(primary_names(p1))
    counts = {family: count_significant(runs, names) for family, runs in worlds.items()}
    counts_raw = {
        family: count_significant(runs, names, key="p_raw") for family, runs in worlds.items()
    }
    return {
        "p1": p1,
        "k": k,
        "z_autocorr": float(z.dropna().autocorr(1)),
        "nn_seeds": NN_SEEDS,
        "counts": counts,
        "counts_raw": counts_raw,
        "pass": g1_passed(counts),
        "power": power_table(source, index, z, k, decisions),
        "worlds": worlds,
    }
