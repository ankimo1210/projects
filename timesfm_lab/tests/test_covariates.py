"""The covariate ablation: same windows, same model, extra channels.

The result the bench reports is a null, so these tests exist mostly to rule out
the boring explanations for a null — covariates that never reach the model,
windows that silently differ between the two arms, misaligned channels.
"""

import numpy as np
import pandas as pd
import pytest
from timesfm_lab.covariates import (
    BUILDERS,
    SETTINGS,
    build_driver_windows,
    build_ett_windows,
    build_finance_windows,
    paired_arm_test,
)
from timesfm_lab.datasets import SPEC_BY_KEY

from timesfm_lab import finance

needs_ett = pytest.mark.skipif(
    not SPEC_BY_KEY["ett_h1"].path.exists(), reason="run scripts/fetch_data.sh first"
)
needs_finance = pytest.mark.skipif(
    not finance.CACHE.exists(), reason="run scripts/fetch_finance.py first"
)


def test_every_setting_has_a_builder():
    assert {s.key for s in SETTINGS} == set(BUILDERS)
    for s in SETTINGS:
        assert s.dataset in SPEC_BY_KEY


def _check(windows, spec, n_channels):
    assert windows
    for w in windows:
        assert w.past_covariates is not None
        assert w.past_covariates.shape == (n_channels, spec.context_length)
        assert np.isfinite(w.past_covariates).all()
        assert w.context.shape == (spec.context_length,)
        assert w.actual.shape == (spec.horizon,)


def test_the_driver_setting_hands_over_one_aligned_channel():
    spec = SPEC_BY_KEY["syn_nonlinear_driver"]
    _check(build_driver_windows(seed=0), spec, 1)


def test_the_driver_windows_match_the_plain_ones():
    """Both arms must score the *same* windows, or the comparison is not paired."""
    from timesfm_lab.datasets import build_windows

    plain = {
        (w.series_id, w.cutoff): w
        for w in build_windows(SPEC_BY_KEY["syn_nonlinear_driver"], seed=0)
    }
    for w in build_driver_windows(seed=0):
        ref = plain[(w.series_id, w.cutoff)]
        np.testing.assert_allclose(w.context, ref.context)
        np.testing.assert_allclose(w.actual, ref.actual)


def test_the_driver_is_the_signal_and_not_a_copy_of_the_target():
    ws = build_driver_windows(seed=0)
    cov = np.concatenate([w.past_covariates[0] for w in ws])
    ctx = np.concatenate([w.context for w in ws])
    assert not np.allclose(cov, ctx)
    assert abs(float(np.corrcoef(cov, ctx)[0, 1])) > 0.1  # related, not identical


def test_the_driver_seed_is_reproducible():
    a = build_driver_windows(seed=0)
    b = build_driver_windows(seed=0)
    for x, y in zip(a, b, strict=True):
        np.testing.assert_allclose(x.past_covariates, y.past_covariates)


@needs_ett
def test_ett_hands_over_the_six_load_channels():
    _check(build_ett_windows(seed=0), SPEC_BY_KEY["ett_h1"], 6)


@needs_finance
def test_finance_hands_over_log_volume_for_the_same_dates():
    _check(build_finance_windows(seed=0), SPEC_BY_KEY["fin_range_vol"], 1)


def _rows(n, uni, cov):
    out = []
    for i in range(n):
        base = {"setting": "s", "dataset": "d", "series_id": "a", "cutoff": i}
        out.append(base | {"arm": "univariate", "mase": uni[i]})
        out.append(base | {"arm": "with_covariates", "mase": cov[i]})
    return pd.DataFrame(out)


def test_paired_test_reports_the_direction_and_the_win_rate():
    df = _rows(8, uni=np.full(8, 1.0), cov=np.full(8, 0.5))
    got = paired_arm_test(df, "s")
    assert got["n"] == 8
    assert got["win_rate"] == 1.0
    assert got["delta_pct"] == pytest.approx(-50.0)
    assert got["p_value"] < 0.05


def test_paired_test_is_not_fooled_by_a_wash():
    rng = np.random.default_rng(0)
    uni = rng.normal(1.0, 0.2, 40)
    df = _rows(40, uni=uni, cov=uni + rng.normal(0, 0.01, 40))
    got = paired_arm_test(df, "s")
    assert got["p_value"] > 0.05
    assert abs(got["delta_pct"]) < 5


def test_paired_test_on_an_unknown_setting_is_empty_not_an_error():
    assert paired_arm_test(_rows(3, np.ones(3), np.ones(3)), "missing")["n"] == 0
