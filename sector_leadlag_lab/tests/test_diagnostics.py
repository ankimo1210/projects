import numpy as np
import pandas as pd
import pytest
from sector_leadlag.diagnostics import placebo, run_diagnostics
from sector_leadlag.study import B1, A


def test_placebo_compares_the_real_change_with_pseudo_dates():
    days_a = pd.bdate_range(A[0], A[1])
    days_b = pd.bdate_range(B1[0], B1[1])
    a = pd.Series(np.tile([0.002, 0.0], len(days_a) // 2 + 1)[: len(days_a)], index=days_a)
    b = pd.Series(-0.01, index=days_b)
    out = placebo(pd.concat([a, b]), h=20, min_pre=100)
    assert out["post_days"] == 20
    assert out["actual_ann"] == pytest.approx(252 * (-0.01 - a.mean()))
    assert out["share_at_or_below"] == 0.0 and out["pseudo_min_ann"] > out["actual_ann"]
    assert out["pseudo_dates"] == len(days_a) - 20 - 100 + 1


def test_the_diagnostics_cover_design_section_9(decayed_world):
    out = run_diagnostics(decayed_world, {"g0": {"selected": "lagged"}})
    assert set(out["stale_opens"]) == {"o2c", "random_10", "random_20", "largest_gap_10"}
    assert set(out["other_signals"]) == {"pca_lambda0", "momentum", "k1", "variant_b"}
    assert (
        out["decomposition"]["etf"]["o2c"]["b1"] < 0 < out["decomposition"]["basket"]["o2c"]["b1"]
    )
    assert out["placebo"]["etf"]["share_at_or_below"] < 0.05
    assert out["reference_c"]["days"] > 0
    assert out["session_change"]["basket"]["after"]["p"] < 0.05
