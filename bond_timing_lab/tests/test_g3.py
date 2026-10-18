import numpy as np
import pandas as pd
from bond_timing.data.fredmd import PanelMacro
from bond_timing.g3 import MONTHS, statistic


def test_g3_uses_nineteen_maturities():
    assert len(MONTHS) == 19 and {12, 108, 119, 120} <= set(MONTHS) and 11 not in MONTHS


def test_statistic_runs_on_a_small_world():
    index = pd.period_range("1971-08", "1983-12", freq="M")
    rng = np.random.default_rng(2)
    level = 0.06 + np.cumsum(rng.normal(0, 0.002, len(index)))
    zeros = pd.DataFrame(
        {m: level + 0.0001 * m + rng.normal(0, 1e-4, len(index)) for m in MONTHS}, index=index
    )
    panel = pd.DataFrame(
        rng.normal(size=(len(index), 10)), index=index, columns=[f"m{j}" for j in range(10)]
    )
    decisions = pd.period_range("1980-01", "1981-12", freq="M")
    nn = {"alpha": 0.001, "hidden_layer_sizes": [32, 16]}
    et = {"max_depth": 2, "max_features": 0.3, "min_samples_leaf": 5}
    fixed = {"nn_fm": {"1980-01": nn, "1981-01": nn}, "et": {"1980-01": et, "1981-01": et}}
    out = statistic(zeros, PanelMacro(panel), decisions, fixed, workers=1)
    assert set(out) == {"P4", "P5"} and all(np.isfinite(v) for v in out.values())
