import numpy as np
import pandas as pd
import pytest
from quant_textbook import make_regression_dataset, make_yield_change_panel


def test_regression_dataset_is_deterministic_and_has_requested_spectrum() -> None:
    first = make_regression_dataset(
        n_samples=100, n_features=5, condition_number=1e4, noise_std=0.0, seed=42
    )
    second = make_regression_dataset(
        n_samples=100, n_features=5, condition_number=1e4, noise_std=0.0, seed=42
    )
    np.testing.assert_array_equal(first.X, second.X)
    np.testing.assert_array_equal(first.y, second.y)
    assert np.linalg.cond(first.X) == pytest.approx(1e4, rel=1e-10)
    np.testing.assert_allclose(first.y, first.X @ first.coefficients)


def test_regression_generator_accepts_an_injected_generator() -> None:
    first_rng = np.random.default_rng(7)
    second_rng = np.random.default_rng(7)
    first = make_regression_dataset(seed=first_rng)
    second = make_regression_dataset(seed=second_rng)
    np.testing.assert_array_equal(first.X, second.X)
    np.testing.assert_array_equal(first.y, second.y)


def test_rank_deficient_regression_preserves_requested_nonzero_condition_number() -> None:
    dataset = make_regression_dataset(
        n_samples=100,
        n_features=5,
        condition_number=1e4,
        rank_deficient=True,
        noise_std=0.0,
        seed=8,
    )
    singular_values = np.linalg.svd(dataset.X, compute_uv=False)
    assert singular_values[0] / singular_values[-2] == pytest.approx(1e4, rel=1e-10)
    assert np.linalg.matrix_rank(dataset.X) == 4


def test_regression_dataset_exposes_an_explicit_intercept_design() -> None:
    dataset = make_regression_dataset(
        n_samples=50,
        n_features=3,
        intercept=1.25,
        noise_std=0.0,
        seed=11,
    )
    parameters = np.concatenate(([dataset.intercept], dataset.coefficients))
    np.testing.assert_allclose(dataset.design_with_intercept @ parameters, dataset.y)


def test_yield_panel_is_deterministic_and_loadings_are_lsc_orthonormal() -> None:
    first = make_yield_change_panel(n_observations=200, seed=22)
    second = make_yield_change_panel(n_observations=200, seed=22)
    pd.testing.assert_frame_equal(first.changes, second.changes)
    pd.testing.assert_frame_equal(first.factors, second.factors)
    pd.testing.assert_frame_equal(first.loadings, second.loadings)
    np.testing.assert_allclose(
        first.loadings.to_numpy().T @ first.loadings.to_numpy(), np.eye(3), atol=1e-14
    )
    assert list(first.factors.columns) == ["level", "slope", "curvature"]
    assert first.changes.columns.name == "maturity_years"


def test_optional_regime_shift_changes_factor_scale_and_mean() -> None:
    shift_at = 2000
    panel = make_yield_change_panel(
        n_observations=4000,
        regime_shift_at=shift_at,
        regime_volatility=2.5,
        regime_mean_shift=(0.0005, 0.0, 0.0),
        seed=9,
    )
    before = panel.factors.iloc[:shift_at]
    after = panel.factors.iloc[shift_at:]
    assert after["level"].mean() - before["level"].mean() > 0.0004
    assert after["slope"].std() > 2.0 * before["slope"].std()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_samples": 2, "n_features": 3}, "at least n_features"),
        ({"condition_number": 0.9}, "at least one"),
        ({"noise_std": -0.1}, "non-negative"),
    ],
)
def test_regression_dataset_rejects_invalid_inputs(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        make_regression_dataset(**kwargs)


def test_yield_panel_rejects_unsorted_maturities_and_bad_shift() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        make_yield_change_panel(maturities=(1.0, 3.0, 2.0))
    with pytest.raises(ValueError, match="before the final"):
        make_yield_change_panel(n_observations=10, regime_shift_at=10)
