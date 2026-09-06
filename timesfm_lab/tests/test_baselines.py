import numpy as np
import pytest
from timesfm_lab.baselines import BASELINES, QUANTILE_LEVELS, seasonal_naive


@pytest.mark.parametrize("name", sorted(BASELINES))
def test_every_baseline_returns_the_contract_shapes(name):
    rng = np.random.default_rng(0)
    n, m, h = 400, 24, 48
    t = np.arange(n)
    x = 10 + 0.01 * t + 3 * np.sin(2 * np.pi * t / m) + rng.normal(0, 0.2, n)
    fc = BASELINES[name](x, h, m)
    assert fc.point.shape == (h,)
    assert fc.quantiles.shape == (h, len(QUANTILE_LEVELS))
    assert np.isfinite(fc.point).all()
    assert np.isfinite(fc.quantiles).all()


@pytest.mark.parametrize("name", sorted(BASELINES))
def test_quantile_fans_never_cross(name):
    rng = np.random.default_rng(3)
    x = np.abs(np.cumsum(rng.normal(size=600))) + 1.0
    fc = BASELINES[name](x, 30, 7)
    assert (np.diff(fc.quantiles, axis=1) >= -1e-9).all()


def test_seasonal_naive_repeats_the_last_season_exactly():
    x = np.arange(100, dtype=float)
    fc = seasonal_naive(x, 10, 24)
    np.testing.assert_allclose(fc.point, x[76:86])


def test_seasonal_naive_fan_widens_only_at_season_boundaries():
    rng = np.random.default_rng(5)
    m = 12
    x = np.tile(np.arange(m, dtype=float), 40) + rng.normal(0, 1.0, m * 40)
    fc = seasonal_naive(x, 3 * m, m)
    width = fc.quantiles[:, 8] - fc.quantiles[:, 0]
    # flat inside a season, strictly wider once a full season has elapsed
    assert np.allclose(width[:m], width[0], rtol=0.05)
    assert width[m] > width[0]
    assert width[2 * m] > width[m]


def test_baselines_degrade_gracefully_on_a_near_constant_series():
    x = np.full(300, 4.0)
    x[-1] = 4.0001
    for name, fn in BASELINES.items():
        fc = fn(x, 12, 24)
        assert np.isfinite(fc.point).all(), name
        assert np.isfinite(fc.quantiles).all(), name
