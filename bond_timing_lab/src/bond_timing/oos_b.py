"""OOS-B: decisions from 2019-01, run once after OOS-A and G3, and the verdict (design §3.5-3.6)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from . import evaluate as ev
from .backtest import strategy_returns
from .stages import (
    COST_BP,
    PRIMARY,
    as_frame,
    forecast,
    primary_names,
    strategy_weights,
    summary,
    window,
)
from .study import OOS_B_START, Study


def build_evidence(
    oos_a: dict, g3: dict, oos_b: Mapping[str, Mapping[str, float]]
) -> dict[str, ev.Evidence]:
    tlt = oos_a["instruments"]["tlt"]
    out = {}
    for k in ("P1", "P2", "P3", "P4", "P5"):
        robust = tlt["robust"][k]
        common = {
            "p_vs_hold": tlt["tests"]["vs_hold"][k]["p_holm"],
            "robust_vs_hold": robust["vs_hold_4bp"] > 0 and robust["vs_hold_delay"] > 0,
            "oos_b_vs_hold": oos_b[k]["vs_hold"],
        }
        if k in ("P4", "P5"):
            out[k] = ev.Evidence(
                **common,
                p_vs_p1=tlt["tests"]["vs_p1"][k]["p_holm"],
                robust_vs_p1=robust["vs_p1_4bp"] > 0 and robust["vs_p1_delay"] > 0,
                oos_b_vs_p1=oos_b[k]["vs_p1"],
                g3_p=g3["p"][k],
            )
        else:
            out[k] = ev.Evidence(**common)
    return out


def run_oos_b(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(OOS_B_START, study.last_decision())
    fc = forecast(
        study,
        as_frame(study.outcomes.rx12[10]),
        list(PRIMARY.values()),
        decisions=decisions,
        horizon=12,
        macro=study.realtime_macro(),
        workers=workers,
    )
    cp = None
    if p1 == "cp":
        cp = forecast(
            study,
            as_frame(study.outcomes.rxbar),
            ["cp"],
            decisions=decisions,
            horizon=12,
            macro=None,
            workers=workers,
        )
    weights = strategy_weights(study, study.outcomes, decisions, fc, cp, "tlt")
    returns = {
        name: strategy_returns(w, study.outcomes.excess["tlt"], COST_BP)
        for name, w in weights.items()
    }
    cer = {name: ev.cer(r.dropna()) for name, r in returns.items()}
    diffs = {
        k: {"vs_hold": cer[v] - cer["hold"], "vs_p1": cer[v] - cer[p1]}
        for k, v in primary_names(p1).items()
    }
    evidence = build_evidence(prior["oos_a"], prior["g3"], diffs)
    return {
        "window": [str(decisions[0]), str(decisions[-1])],
        "p1": p1,
        "summary": {name: summary(returns[name], weights[name]) for name in weights},
        "diffs": diffs,
        "evidence": {k: asdict(e) for k, e in evidence.items()},
        "verdict": ev.verdict(evidence),
        "params": fc.params,
    }
