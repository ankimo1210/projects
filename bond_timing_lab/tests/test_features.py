import numpy as np
import pandas as pd
import pytest
from bond_timing.features import (
    INPUTS,
    YIELD_MONTHS,
    InputTransform,
    MacroCleaner,
    Pca,
    Standardizer,
    forwards,
    slope,
    trailing_sum,
)


def test_forwards_of_a_linear_curve():
    n = np.arange(1.0, 11.0)
    Y = np.vstack([0.02 + 0.001 * n, 0.03 + 0.002 * n])
    F = forwards(Y)
    np.testing.assert_allclose(F[:, 0], Y[:, 0])
    np.testing.assert_allclose(F[0, 1:], 0.02 + 0.001 * (2 * n[1:] - 1))


def test_standardizer_and_pca():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 5)) @ np.diag([5.0, 3.0, 1.0, 0.5, 0.1])
    np.testing.assert_allclose(Standardizer().fit(X).transform(X).std(axis=0), 1.0)
    pca = Pca(2).fit(X)
    assert pca.transform(X).shape == (200, 2)
    top = pca.components_[np.arange(2), np.abs(pca.components_).argmax(axis=1)]
    assert (top > 0).all()
    assert Standardizer().fit(np.ones((5, 2))).transform(np.ones((1, 2))).tolist() == [[0.0, 0.0]]


def test_macro_cleaner_drops_sparse_series_and_removes_outliers():
    rng = np.random.default_rng(1)
    M = rng.normal(size=(100, 10))
    M[:30, 0] = np.nan  # 30 % missing: dropped
    M[5, 1] = np.nan
    M[7, 2] = 1e6  # outlier: missing, then 0
    cleaner = MacroCleaner().fit(M)
    assert not cleaner.keep_[0] and cleaner.keep_[1:].all()
    Z = cleaner.transform(M)
    assert Z.shape == (100, 9)
    assert Z[5, 0] == 0.0 and Z[7, 1] == 0.0
    assert np.abs(Z.mean(axis=0)).max() < 0.05


def test_macro_cleaner_turns_missing_edge_values_into_zero():
    cleaner = MacroCleaner().fit(np.random.default_rng(2).normal(size=(80, 9)))
    edge = np.full((1, 9), np.nan)
    edge[0, 3] = 1.0
    out = cleaner.transform(edge)
    assert out.shape == (1, 9) and np.isfinite(out).all()
    assert (out[0, np.arange(9) != 3] == 0.0).all()


def test_input_transforms_have_the_design_widths():
    rng = np.random.default_rng(3)
    Y = 0.05 + np.cumsum(rng.normal(0, 0.001, size=(120, 10)), axis=0)
    M = rng.normal(size=(120, 12))
    widths = {
        name: InputTransform(spec).fit(Y, M).transform(Y[:3], M[:3]).shape[1]
        for name, spec in INPUTS.items()
    }
    assert widths == {"P": 3, "PM": 11, "F": 10, "FM": 22}
    with pytest.raises(ValueError):
        InputTransform(INPUTS["FM"]).fit(Y, None)


def test_slope_and_trend_signals():
    index = pd.period_range("2000-01", periods=14, freq="M")
    zeros = pd.DataFrame({m: 0.05 for m in YIELD_MONTHS}, index=index)
    assert (slope(zeros, pd.Series(0.06, index=index)) < 0).all()
    excess = pd.Series(np.r_[np.full(12, 0.01), [-0.5, 0.01]], index=index)
    trend = trailing_sum(excess)
    assert np.isnan(trend.iloc[10]) and trend.iloc[11] == pytest.approx(0.12)
    assert trend.iloc[12] < 0
