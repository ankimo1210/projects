"""Deterministic gates for the volume-21 joint SPX/VIX teaching API."""

import numpy as np
import pytest
from hullkit import spx_vix


def test_four_factor_pdv_is_causal_positive_and_responds_to_leverage() -> None:
    parameters = spx_vix.PDVParameters(
        intercept=0.15,
        return_loadings=(-1.0, -0.5),
        variance_loadings=(0.2, 0.1),
    )
    negative = spx_vix.four_factor_pdv([-0.10, 0.0], parameters, initial_variance=0.04)
    positive = spx_vix.four_factor_pdv([0.10, 0.0], parameters, initial_variance=0.04)
    assert negative.factors.shape == (3, 4)
    np.testing.assert_allclose(negative.factors[0], positive.factors[0])
    assert negative.variance[1] > positive.variance[1]
    assert np.all(negative.variance > 0.0)


def test_affine_forward_variance_and_quintic_ou_are_positive_comparators() -> None:
    maturities = np.array([0.0, 0.5, 2.0])
    curve = spx_vix.affine_forward_variance(maturities, 0.04, [0.03, 0.02], [1.0, 5.0])
    assert curve[0] == pytest.approx(0.09)
    assert curve[-1] > 0.04
    assert np.all(np.diff(curve) < 0.0)
    np.testing.assert_allclose(spx_vix.rough_heston_fractional_kernel([0.1, 1.0], 0.5), 1.0)
    rough_kernel = spx_vix.rough_heston_fractional_kernel([0.1, 1.0], 0.1)
    assert rough_kernel[0] > rough_kernel[1]
    state = np.array([-1.0, 0.0, 2.0])
    variance = spx_vix.quintic_ou_variance(state, [1.0, 2.0, 0.0, 0.0, 0.0, 0.1])
    assert np.all(variance >= 0.0)
    with pytest.raises(ValueError, match="negative forward variance"):
        spx_vix.affine_forward_variance([1.0], 0.01, [-1.0], [0.0])


def _targets(offset: float = 0.0) -> spx_vix.JointMarketTargets:
    return spx_vix.JointMarketTargets(
        spx_iv=np.array([0.20, 0.22]) + offset,
        vix_futures=np.array([18.0, 19.0]) + offset,
        vix_options=np.array([1.5, 0.8]) + offset,
        variance_term=np.array([0.04, 0.05]) + offset,
    )


def test_joint_objective_keeps_all_four_quote_families_separate() -> None:
    exact = spx_vix.joint_spx_vix_objective(_targets(), _targets())
    assert exact.total == 0.0
    assert set(exact.components) == {"spx_iv", "vix_futures", "vix_options", "variance_term"}
    shifted = spx_vix.joint_spx_vix_objective(
        _targets(0.1),
        _targets(),
        scales={name: 0.1 for name in exact.components},
        weights={"spx_iv": 2.0, "vix_futures": 1.0, "vix_options": 1.0, "variance_term": 1.0},
    )
    assert shifted.components["spx_iv"] == pytest.approx(1.0)
    assert shifted.total == pytest.approx(5.0)


def test_nested_vix_teacher_takes_conditional_expectation_before_square_root() -> None:
    paths = np.array(
        [
            [[0.01, 0.09], [0.01, 0.09]],
            [[0.04, 0.04], [0.04, 0.04]],
        ]
    )
    result = spx_vix.nested_vix_teacher(paths, strike=20.0, discount_factor=0.95)
    np.testing.assert_allclose(result.vix, 100.0 * np.sqrt([0.05, 0.04]))
    assert result.future == pytest.approx(50.0 * (np.sqrt(0.05) + np.sqrt(0.04)))
    assert result.call_price == pytest.approx(0.95 * (100.0 * np.sqrt(0.05) - 20.0) / 2.0)
    assert result.standard_error > 0.0


def test_price_greek_speed_and_ood_diagnostics_are_explicit() -> None:
    greeks = spx_vix.finite_difference_greeks(lambda spot: spot * spot, 2.0, bump=1e-3)
    assert greeks["price"] == pytest.approx(4.0)
    assert greeks["delta"] == pytest.approx(4.0)
    assert greeks["gamma"] == pytest.approx(2.0, rel=1e-8)
    flags = spx_vix.out_of_domain_flags(
        [[0.5, 0.5], [1.1, 0.5], [0.5, -0.1]],
        [0.0, 0.0],
        [1.0, 1.0],
    )
    np.testing.assert_array_equal(flags, [False, True, True])
    comparison = spx_vix.compare_teacher_surrogate(
        [1.0, 2.0],
        [1.1, 1.9],
        teacher_seconds=2.0,
        surrogate_seconds=0.1,
        teacher_greeks=[[0.5], [0.6]],
        surrogate_greeks=[[0.4], [0.7]],
    )
    assert comparison.price_rmse == pytest.approx(0.1)
    assert comparison.greek_rmse == pytest.approx(0.1)
    assert comparison.speedup == pytest.approx(20.0)
    grid = np.array([[x, y] for x in np.linspace(-1.0, 1.0, 5) for y in np.linspace(0.0, 2.0, 5)])
    teacher = 1.0 + 2.0 * grid[:, 0] - grid[:, 1] + 0.5 * grid[:, 0] * grid[:, 1]
    surrogate = spx_vix.fit_polynomial_surrogate(grid, teacher)
    np.testing.assert_allclose(surrogate.predict(grid), teacher, atol=1e-8)
    np.testing.assert_array_equal(surrogate.ood([[0.0, 1.0], [2.0, 1.0]]), [False, True])
    assert spx_vix.CORE_MODEL_FAMILIES == (
        "four_factor_pdv",
        "affine_forward_variance",
        "rough_heston_kernel",
        "quintic_ou",
    )
    assert spx_vix.MODEL_OWNERS["rbergomi_heston_hawkes_paths"] == "rough_volatility"
    assert spx_vix.MODEL_OWNERS["neural_surrogate_training"] == "deep_hedge_price"
    assert spx_vix.RESEARCH_ONLY_MODELS == ("signature", "perturbed_optimal_transport")
