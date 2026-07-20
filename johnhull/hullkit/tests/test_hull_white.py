"""Hard identities for the one-factor Hull–White financial teacher."""

import math

import numpy as np
import pytest
from hullkit import hull_white as hw
from hullkit import rates
from scipy.integrate import quad
from scipy.stats import norm

CURVE = (
    [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0],
    [0.012, 0.014, 0.017, 0.021, 0.024, 0.027, 0.029, 0.031],
)
PARAMS = hw.HullWhiteParams(mean_reversion=0.12, volatility=0.01)


def _receiver_spec(expiry, maturity, fixed_rate=0.028):
    payment_times = tuple(np.arange(expiry + 1.0, maturity + 0.1, 1.0))
    cashflows = [fixed_rate] * len(payment_times)
    cashflows[-1] += 1.0
    return hw.HullWhiteSwaption(expiry, payment_times, tuple(cashflows), "receiver")


def test_initial_curve_fit_and_shift():
    for maturity in CURVE[0]:
        assert hw.hw_discount_bond(0.0, maturity, 0.0, CURVE, PARAMS) == pytest.approx(
            rates.discount_factor(maturity, CURVE), abs=1e-14
        )
    assert hw.hw_phi(0.0, CURVE, PARAMS) == pytest.approx(
        rates.instantaneous_forward(0.0, CURVE), abs=1e-14
    )


def test_exact_transition_moments_and_seed_reproducibility():
    end = 4.0
    paths = hw.simulate_hw_paths([0.0, end], 0.0, PARAMS, n_paths=200_000, seed=7)
    repeated = hw.simulate_hw_paths([0.0, end], 0.0, PARAMS, n_paths=20, seed=7)
    assert np.array_equal(
        repeated,
        hw.simulate_hw_paths([0.0, end], 0.0, PARAMS, n_paths=20, seed=7),
    )
    variance = PARAMS.volatility**2 * (1.0 - math.exp(-2 * PARAMS.mean_reversion * end)) / (
        2 * PARAMS.mean_reversion
    )
    standard_error_mean = math.sqrt(variance / paths.shape[0])
    standard_error_variance = variance * math.sqrt(2.0 / (paths.shape[0] - 1))
    assert abs(float(paths[:, -1].mean())) < 4.0 * standard_error_mean
    assert abs(float(paths[:, -1].var(ddof=1)) - variance) < 4.0 * standard_error_variance


def test_zcb_option_put_call_parity_and_zero_vol_limit():
    expiry, maturity, strike = 2.0, 6.0, 0.88
    call = hw.hw_zcb_option(expiry, maturity, strike, CURVE, PARAMS, option_type="call")
    put = hw.hw_zcb_option(expiry, maturity, strike, CURVE, PARAMS, option_type="put")
    forward_intrinsic = rates.discount_factor(maturity, CURVE) - strike * rates.discount_factor(
        expiry, CURVE
    )
    assert call - put == pytest.approx(forward_intrinsic, abs=1e-13)

    deterministic = hw.HullWhiteParams(0.12, 0.0)
    expected = max(forward_intrinsic, 0.0)
    assert hw.hw_zcb_option(
        expiry, maturity, strike, CURVE, deterministic, option_type="call"
    ) == pytest.approx(expected, abs=1e-14)


@pytest.mark.parametrize("option_type", ["receiver", "payer"])
def test_jamshidian_matches_direct_forward_measure_quadrature(option_type):
    spec = _receiver_spec(1.5, 6.5)
    spec = hw.HullWhiteSwaption(
        spec.expiry, spec.payment_times, spec.fixed_cashflows, option_type
    )
    analytic = hw.hw_jamshidian_swaption(spec, CURVE, PARAMS)
    p_expiry = rates.discount_factor(spec.expiry, CURVE)
    variance_scale = PARAMS.volatility * math.sqrt(
        (1.0 - math.exp(-2.0 * PARAMS.mean_reversion * spec.expiry))
        / (2.0 * PARAMS.mean_reversion)
    )
    forwards = np.asarray(
        [rates.discount_factor(time, CURVE) / p_expiry for time in spec.payment_times]
    )
    vols = np.asarray(
        [
            hw.hw_b(spec.expiry, time, PARAMS.mean_reversion) * variance_scale
            for time in spec.payment_times
        ]
    )
    cashflows = np.asarray(spec.fixed_cashflows)

    def integrand(z):
        bonds = forwards * np.exp(-0.5 * vols**2 - vols * z)
        receiver = float(np.dot(cashflows, bonds) - 1.0)
        payoff = max(receiver if option_type == "receiver" else -receiver, 0.0)
        return payoff * norm.pdf(z)

    direct = p_expiry * quad(integrand, -9.0, 9.0, epsabs=1e-12)[0]
    assert analytic == pytest.approx(direct, abs=1e-9)


def test_synthetic_calibration_reprices_teacher_surface():
    specs = tuple(
        _receiver_spec(expiry, maturity)
        for expiry, maturity in ((1.0, 5.0), (2.0, 7.0), (3.0, 8.0), (4.0, 10.0))
    )
    teacher = np.asarray([hw.hw_jamshidian_swaption(spec, CURVE, PARAMS) for spec in specs])
    calibrated = hw.calibrate_hw1f(specs, teacher, CURVE, initial_guess=(0.06, 0.015))
    repriced = np.asarray([hw.hw_jamshidian_swaption(spec, CURVE, calibrated) for spec in specs])
    assert np.max(np.abs(repriced - teacher)) < 1e-9


def test_invalid_parameters_and_correlation_free_inputs_raise():
    with pytest.raises(ValueError, match="mean_reversion"):
        hw.HullWhiteParams(0.0, 0.01).validate()
    with pytest.raises(ValueError, match="ordered strictly after"):
        hw.HullWhiteSwaption(2.0, (1.0,), (1.0,)).validate()
