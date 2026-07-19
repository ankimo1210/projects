"""Black/Heston/SV-jump carbon option baselines and sensitivities."""

import numpy as np
import pytest
from hullkit import carbon


def test_black76_zero_vol_and_put_call_parity():
    call = carbon.black76_price(100.0, 90.0, 0.03, 0.0, 2.0)
    assert call == pytest.approx(np.exp(-0.06) * 10.0)
    call = carbon.black76_price(100.0, 95.0, 0.03, 0.30, 2.0)
    put = carbon.black76_price(100.0, 95.0, 0.03, 0.30, 2.0, kind="put")
    assert call - put == pytest.approx(np.exp(-0.06) * 5.0, abs=1e-12)


def test_gbm_mc_agrees_with_black76_within_sampling_error():
    dynamics = carbon.CarbonDynamics(v0=0.09, theta=0.09, vol_of_vol=0.0)
    estimate = carbon.carbon_option_mc(
        100.0,
        100.0,
        0.02,
        1.0,
        model="gbm",
        dynamics=dynamics,
        n_steps=8,
        n_paths=40_000,
        seed=7,
    )
    analytic = carbon.black76_price(100.0, 100.0, 0.02, 0.30, 1.0)
    assert abs(estimate.price - analytic) < 4.0 * estimate.standard_error


def test_heston_and_sv_jump_are_reproducible_synthetic_challengers():
    dynamics = carbon.CarbonDynamics(jump_intensity=0.5)
    heston = carbon.simulate_terminal_futures(
        80.0, 1.0, model="heston", dynamics=dynamics, n_steps=20, n_paths=2_000, seed=3
    )
    jump = carbon.simulate_terminal_futures(
        80.0, 1.0, model="sv_jump", dynamics=dynamics, n_steps=20, n_paths=2_000, seed=3
    )
    again = carbon.simulate_terminal_futures(
        80.0, 1.0, model="sv_jump", dynamics=dynamics, n_steps=20, n_paths=2_000, seed=3
    )
    np.testing.assert_array_equal(jump, again)
    assert np.all(heston > 0.0) and np.all(jump > 0.0)
    assert not np.array_equal(heston, jump)


def test_risk_premia_are_reported_as_separate_one_at_a_time_effects():
    sensitivity = carbon.risk_premium_sensitivity(
        100.0,
        100.0,
        0.0,
        1.0,
        n_steps=16,
        n_paths=8_000,
        seed=11,
    )
    assert sensitivity.return_effect > 0.0
    assert np.isfinite(sensitivity.variance_effect)
    assert np.isfinite(sensitivity.jump_effect)
    assert sensitivity.return_shifted != sensitivity.variance_shifted


def test_invalid_post_premium_parameters_raise():
    with pytest.raises(ValueError, match="theta"):
        carbon.simulate_terminal_futures(
            100.0,
            1.0,
            dynamics=carbon.CarbonDynamics(theta=0.01),
            risk_premia=carbon.CarbonRiskPremia(variance_premium=-0.02),
        )
