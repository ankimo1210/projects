"""G1: the US returns rotated against Japan, so that no lead-lag is left, and the power of H1.

Each world rotates the US returns by a fixed random number of US trading days (at least 60) and
rebuilds the whole signal, C_full included, from the rotated returns (design §8). The power
check adds 0.5 x beta_ETF x sz of the rotated signal to the basket returns and counts how often
the H1 test finds it.
"""

from __future__ import annotations

from . import evaluate as ev
from .signal import cross_standardize
from .stages import SCALE, basket_series, build_signal, cut, h1_baskets
from .study import A, Study
from .synthetic import SHIFTS, circular_shift, plant, shift_amounts

MAX_SIGNIFICANT = 2
POWER_SHARE = 0.5


def run_g1(study: Study, prior: dict, *, count: int = SHIFTS) -> dict:
    variant = prior["g0"]["selected"]
    beta = POWER_SHARE * prior["g0"]["variants"][variant]["fit_a"]["beta_1e4"] * SCALE
    us_ret = study.us_returns()
    o2c = cut(basket_series(study, h1_baskets(study).main).o2c, A)
    worlds = []
    for k in shift_amounts(len(us_ret), count):
        signal = build_signal(study, variant, us_ret=circular_shift(us_ret, k))
        sz = cut(cross_standardize(signal), A)
        null = ev.panel_fit(o2c, sz)
        planted = ev.panel_fit(plant(o2c, sz, beta), sz)
        worlds.append(
            {
                "shift": k,
                "beta_1e4": null.beta[0] / SCALE,
                "p": null.p,
                "planted_beta_1e4": planted.beta[0] / SCALE,
                "planted_p": planted.p,
            }
        )
    significant = sum(world["p"] < ev.ALPHA for world in worlds)
    return {
        "variant": variant,
        "count": count,
        "significant": significant,
        "detected": sum(world["planted_p"] < ev.ALPHA for world in worlds),
        "planted_beta_1e4": beta / SCALE,
        "pass": significant <= MAX_SIGNIFICANT,
        "worlds": worlds,
    }
