import numpy as np
import pytest

from deep_hedge_price.volatility_data import (
    TrainWindowPCA,
    TrainWindowStandardizer,
    WalkForwardSplit,
    assert_horizon_disjoint,
    build_volatility_targets,
    purged_walk_forward_splits,
    realized_variance_targets,
)


def test_purged_splits_remove_horizon_overlap():
    splits = purged_walk_forward_splits(160, min_train=60, test_size=20, horizon=5, embargo=2)
    assert len(splits) >= 3
    for split in splits:
        assert split.train.max() + 5 + 2 < split.test.min()
        assert_horizon_disjoint(split)


def test_overlap_audit_rejects_leakage():
    split = WalkForwardSplit(train=np.arange(20), test=np.arange(22, 30), horizon=5, embargo=0)
    with pytest.raises(ValueError, match="horizons overlap"):
        assert_horizon_disjoint(split)


def test_scaler_only_uses_train_window_and_targets_have_nan_tail():
    features = np.column_stack([np.arange(20), np.arange(20) ** 2])
    scaler = TrainWindowStandardizer.fit(features, np.arange(10))
    np.testing.assert_allclose(scaler.transform(features[:10]).mean(axis=0), 0, atol=1e-12)
    returns = np.linspace(-0.02, 0.02, 20)
    targets = realized_variance_targets(returns, (1, 5))
    assert np.isnan(targets[1][-1:]).all()
    assert np.isnan(targets[5][-5:]).all()
    assert targets[5][0] == pytest.approx(np.log(np.sum(returns[1:6] ** 2)))


def test_scaler_rejects_negative_or_out_of_sample_train_indices():
    features = np.column_stack([np.arange(10), np.arange(10) ** 2])
    with pytest.raises(ValueError, match="in bounds"):
        TrainWindowStandardizer.fit(features, np.array([-1, 0, 1]))
    with pytest.raises(ValueError, match="in bounds"):
        TrainWindowStandardizer.fit(features, np.array([0, 1, 10]))


def test_pca_is_fit_on_train_window_only():
    rng = np.random.default_rng(4)
    features = rng.normal(size=(20, 3))
    train = np.arange(12)
    fitted = TrainWindowPCA.fit(features, train, n_components=2)
    changed_test = features.copy()
    changed_test[12:] += 1_000.0
    refitted = TrainWindowPCA.fit(changed_test, train, n_components=2)
    np.testing.assert_allclose(fitted.mean, refitted.mean)
    np.testing.assert_allclose(np.abs(fitted.components), np.abs(refitted.components))
    assert fitted.transform(features).shape == (20, 2)


def test_rv_and_surface_latent_targets_are_separate_and_future_aligned():
    returns = np.linspace(-0.02, 0.02, 30)
    latents = np.column_stack([np.arange(30), -np.arange(30)])
    targets = build_volatility_targets(returns, latents, (1, 5, 21))

    assert set(targets.log_realized_variance) == {1, 5, 21}
    np.testing.assert_allclose(
        targets.future_realized_variance[5][0],
        np.sum(returns[1:6] ** 2),
    )
    np.testing.assert_array_equal(targets.surface_latent[5][0], latents[5])
    assert np.isnan(targets.surface_latent[21][-21:]).all()
    assert np.isnan(targets.future_realized_variance[21][-21:]).all()
