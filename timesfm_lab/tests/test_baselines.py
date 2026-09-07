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


def test_har_recovers_a_persistent_level_better_than_a_random_walk():
    """HAR exists to exploit clustering; if it cannot, the finance section is void."""
    from timesfm_lab.baselines import har, naive
    from timesfm_lab.metrics import mae

    rng = np.random.default_rng(11)
    n, h = 600, 20
    # slow-moving latent level plus noise: exactly the shape HAR's lag averages target
    level = np.cumsum(rng.normal(0, 0.02, n + h))
    x = level + rng.normal(0, 0.3, n + h)
    ctx, actual = x[:n], x[n:]
    assert mae(actual, har(ctx, h, 5).point) < mae(actual, naive(ctx, h, 5).point)


def test_ewma_picks_a_smoother_lambda_on_a_noisier_series():
    from timesfm_lab.baselines import ewma

    rng = np.random.default_rng(12)
    n = 400
    level = np.cumsum(rng.normal(0, 0.05, n))
    quiet = ewma(level + rng.normal(0, 0.05, n), 10, 1)
    noisy = ewma(level + rng.normal(0, 2.0, n), 10, 1)
    # a noisier series must get a wider band, not a narrower one
    assert np.ptp(noisy.quantiles[0]) > np.ptp(quiet.quantiles[0])
