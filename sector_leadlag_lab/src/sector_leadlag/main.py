"""本番 A and 本番 B: H1, H2, H3 and the verdict (design §3).

``run_main_a`` reads period A only. ``run_main_b`` runs once, after main A is recorded, and
gives the verdict from the two (design §3.5).
"""

from __future__ import annotations

from dataclasses import asdict

from . import evaluate as ev
from .signal import cross_standardize
from .stages import (
    basket_series,
    build_signal,
    cash_summary,
    cut,
    etf_long_short,
    etf_returns,
    fit_summary,
    h1_baskets,
    h2_series,
)
from .strategy import CAPITAL
from .study import B1, B2, A, B, Study

SCENARIOS = {
    "base": (CAPITAL, 0.0),
    "cost_2bp": (CAPITAL, 2.0),
    "capital_3m": (3_000_000.0, 0.0),
    "capital_10m": (10_000_000.0, 0.0),
    "cost_5bp": (CAPITAL, 5.0),  # reported only (design §3.4)
}
ROBUSTNESS = ("cost_2bp", "capital_3m", "capital_10m")


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def run_main_a(study: Study, prior: dict, *, n_boot: int = ev.N_BOOT) -> dict:
    variant = prior["g0"]["selected"]
    signal = cut(build_signal(study, variant), A)
    sz = cross_standardize(signal)
    baskets = h1_baskets(study)
    basket = cut(basket_series(study, baskets.main).o2c, A)
    fit_b = ev.panel_fit(basket, sz)
    fit_e = ev.panel_fit(cut(etf_returns(study).o2c, A), sz)
    low, high = ev.ratio_interval(fit_b, fit_e, n_boot=n_boot)
    h2 = {}
    for name, (capital, cost_bp) in SCENARIOS.items():
        cash, spread = h2_series(study, signal, baskets.median, capital=capital, cost_bp=cost_bp)
        h2[name] = {
            "capital": capital,
            "cost_bp": cost_bp,
            "cash": {**cash_summary(cash), "p": ev.mean_test(cash.returns, n_boot=n_boot).p},
            "spread": {**ev.describe(spread), "p": ev.mean_test(spread, n_boot=n_boot).p},
        }
    base = h2["base"]
    robust = all(
        _sign(h2[name][part]["mean_ann"]) == _sign(base[part]["mean_ann"])
        for name in ROBUSTNESS
        for part in ("cash", "spread")
    )
    return {
        "variant": variant,
        "h1": {
            "basket": fit_summary(fit_b),
            "etf": fit_summary(fit_e),
            "ratio_ci": [low, high],
            "pass": fit_b.p < ev.ALPHA,
        },
        "h2": h2,
        "h2_pass": base["cash"]["p"] < ev.ALPHA and base["spread"]["p"] < ev.ALPHA,
        "robust": robust,
    }


def run_main_b(study: Study, prior: dict) -> dict:
    variant = prior["g0"]["selected"]
    signal = build_signal(study, variant)
    sz = cut(cross_standardize(signal), B)
    baskets = h1_baskets(study)
    etf = etf_returns(study)
    fit_b = ev.panel_fit(cut(basket_series(study, baskets.main).o2c, B), sz)
    fit_e = ev.panel_fit(cut(etf.o2c, B), sz)
    cash, spread = h2_series(study, cut(signal, B), baskets.median)
    ls = etf_long_short(cut(signal, (A[0], B[1])), study, etf.o2c)
    a = prior["main_a"]
    evidence = ev.Evidence(
        replicated=bool(prior["g0"]["pass"]),
        h1_p=a["h1"]["basket"]["p"],
        beta_b_period_b=fit_b.beta[0],
        h2_p_cash=a["h2"]["base"]["cash"]["p"],
        h2_p_spread=a["h2"]["base"]["spread"]["p"],
        robust=bool(a["robust"]),
        b_mean_cash=float(cash.returns.mean()),
        b_mean_spread=float(spread.mean()),
    )
    return {
        "variant": variant,
        "h1": {"basket": fit_summary(fit_b), "etf": fit_summary(fit_e)},
        "h2": {"cash": cash_summary(cash), "spread": ev.describe(spread)},
        "etf_long_short": {"b1": ev.describe(cut(ls, B1)), "b2": ev.describe(cut(ls, B2))},
        "h3": ev.h3_label(cut(ls, B2), cut(ls, A)),
        "evidence": asdict(evidence),
        "verdict": ev.verdict(evidence),
    }
