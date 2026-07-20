import numpy as np
import pytest

from deep_hedge_price.surface_data import (
    generate_forward_surfaces,
    generate_numerical_forward_surfaces,
    joint_surface_loss,
    joint_surface_pareto,
)


@pytest.mark.parametrize("model", ["heston", "sabr", "rbergomi"])
def test_forward_surface_models_have_common_schema(model):
    dataset = generate_forward_surfaces(model, n_samples=6, seed=17)
    assert dataset.parameters.shape[0] == 6
    assert dataset.implied_volatility.shape == (6, 5, 13)
    assert dataset.variance_term.shape == (6, 5)
    assert np.all(dataset.implied_volatility > 0)
    assert dataset.teacher_method == "synthetic_proxy"
    assert not np.any(dataset.standard_error)
    rerun = generate_forward_surfaces(model, n_samples=6, seed=17)
    np.testing.assert_array_equal(dataset.implied_volatility, rerun.implied_volatility)


@pytest.mark.parametrize(
    ("model", "expected_method"),
    [
        ("heston", "heston_cos"),
        ("sabr", "hagan_sabr_to_bsm"),
        ("rbergomi", "rbergomi_mc_antithetic"),
    ],
)
def test_numerical_forward_surfaces_use_model_specific_teachers(model, expected_method):
    dataset = generate_numerical_forward_surfaces(
        model,
        n_samples=1,
        seed=23,
        log_moneyness=np.array([-0.1, 0.0, 0.1]),
        maturities=np.array([0.25]),
        rbergomi_paths=200,
    )
    assert dataset.teacher_method == expected_method
    assert dataset.implied_volatility.shape == (1, 1, 3)
    assert dataset.standard_error.shape == (1, 1, 3)
    assert np.all(np.isfinite(dataset.implied_volatility))
    if model == "rbergomi":
        assert np.all(dataset.standard_error > 0)
    else:
        assert not np.any(dataset.standard_error)


def test_joint_variance_loss_exposes_iv_only_counterexample():
    target_iv = np.full((2, 3), 0.2)
    predicted_iv = target_iv.copy()
    target_variance = np.array([0.04, 0.05])
    wrong_variance = np.array([0.08, 0.09])
    total, iv_loss, variance_loss = joint_surface_loss(
        predicted_iv,
        target_iv,
        wrong_variance,
        target_variance,
        lambda_var=10.0,
    )
    assert iv_loss == 0.0
    assert variance_loss > 0
    assert total == pytest.approx(10 * variance_loss)


def test_joint_loss_rejects_accidental_numpy_broadcasting():
    with pytest.raises(ValueError, match="variance arrays"):
        joint_surface_loss(
            np.full((2, 3), 0.2),
            np.full((2, 3), 0.2),
            np.full((2, 1), 0.04),
            np.full(2, 0.04),
            lambda_var=1.0,
        )


def test_surface_axes_must_be_strictly_increasing():
    with pytest.raises(ValueError, match="strictly increasing"):
        generate_forward_surfaces(
            "heston",
            n_samples=2,
            seed=1,
            maturities=np.array([0.5, 0.25]),
        )


def test_lambda_sweep_reports_non_dominated_iv_variance_frontier():
    target_iv = np.zeros(2)
    target_variance = np.zeros(2)
    all_points, frontier = joint_surface_pareto(
        {
            0.0: (np.full(2, 0.1), np.full(2, 0.4)),
            1.0: (np.full(2, 0.2), np.full(2, 0.2)),
            10.0: (np.full(2, 0.3), np.full(2, 0.1)),
            20.0: (np.full(2, 0.4), np.full(2, 0.5)),
        },
        target_iv,
        target_variance,
    )
    assert len(all_points) == 4
    assert {point.lambda_var for point in frontier} == {0.0, 1.0, 10.0}
