"""Independent limits, inverse-problem diagnostics, and solver accounting."""

import importlib

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import ndtr


def core():
    return importlib.import_module("hullkit._sabr_identifiability")


STRIKES = 100 * np.exp(np.array([-0.20, -0.10, -0.01, 0, 0.01, 0.10, 0.20]))
TRUTH = np.array([0.20, -0.30, 0.40])


def test_rectangular_linear_jacobian_exposes_third_null_direction():
    j = np.array([[1.0, 0.0, 1.0], [0.0, 1.0, 1.0]])
    result = core().jacobian_diagnostics(j)
    assert result["singular_values"] == pytest.approx([np.sqrt(3), 1, 0])
    assert result["rank"] == 2
    assert result["condition"] is None
    directions = result["right_vectors"]
    assert directions.shape == (3, 3)
    assert directions @ directions.T == pytest.approx(np.eye(3), abs=1e-14)
    assert abs(directions[-1] @ np.array([-1, -1, 1]) / np.sqrt(3)) == pytest.approx(1)
    assert j @ directions[-1] == pytest.approx([0, 0], abs=1e-14)


def test_svd_rank_threshold_and_full_rank_condition():
    result = core().jacobian_diagnostics(np.diag([4.0, 2.0, 1.0]))
    assert result["rank"] == 3
    assert result["condition"] == pytest.approx(4)
    tiny = core().jacobian_diagnostics(np.diag([4.0, 2.0, 1e-10]))
    assert tiny["rank"] == 2
    assert tiny["condition"] is None
    zero = core().jacobian_diagnostics(np.zeros((1, 3)))
    assert zero["rank"] == 0
    assert zero["singular_values"] == pytest.approx([0, 0, 0])


@pytest.mark.parametrize("rho", [-0.8, 0, 0.8])
def test_flat_sabr_limit_matches_independent_lognormal_payoff_integral(rho):
    strikes = 100 * np.exp(np.array([-0.25, -0.10, 0, 0.10, 0.25]))
    ivs = core().sabr_vols(100, 1, 1, [0.20, rho, 0], strikes)
    assert ivs == pytest.approx(np.full(5, 0.20), abs=1e-14)
    for strike, iv in zip(strikes, ivs, strict=True):
        d1 = np.log(100 / strike) / iv + iv / 2
        black = 100 * ndtr(d1) - strike * ndtr(d1 - iv)
        threshold = (np.log(strike / 100) + 0.02) / 0.20
        integral = quad(
            lambda z, k=strike: (
                (100 * np.exp(-0.02 + 0.20 * z) - k) * np.exp(-z * z / 2) / np.sqrt(2 * np.pi)
            ),
            threshold,
            12,
            epsabs=2e-11,
            epsrel=2e-12,
        )[0]
        assert black == pytest.approx(integral, abs=1e-10)


def test_scaled_central_jacobian_and_raw_coordinates():
    m = core()
    j = m.scaled_jacobian(100, 1, 0.5, TRUTH, STRIKES)
    independent = []
    for axis, scale in enumerate([0.20, 0.50, 0.50]):
        step = np.zeros(3)
        step[axis] = scale * 1e-4
        independent.append(
            (
                m.sabr_vols(100, 1, 0.5, TRUTH + step, STRIKES)
                - m.sabr_vols(100, 1, 0.5, TRUTH - step, STRIKES)
            )
            / (2e-4 * 0.0005)
        )
    assert j == pytest.approx(np.array(independent).T, rel=2e-6, abs=1e-6)
    doubled = m.scaled_jacobian(100, 1, 0.5, TRUTH, STRIKES, noise_scale=0.001)
    assert doubled == pytest.approx(j / 2)


def test_one_sided_upper_boundary_jacobian_agrees_with_inward_limit():
    m = core()
    theta = np.array([0.50, 0.95, 1.5])
    j = m.scaled_jacobian(100, 0.7, 0.5, theta, STRIKES)
    for axis, scale in enumerate([0.20, 0.50, 0.50]):
        step = np.zeros(3)
        step[axis] = scale * 1e-4
        v0 = m.sabr_vols(100, 0.7, 0.5, theta, STRIKES)
        v1 = m.sabr_vols(100, 0.7, 0.5, theta - step, STRIKES)
        v2 = m.sabr_vols(100, 0.7, 0.5, theta - 2 * step, STRIKES)
        independent = (3 * v0 - 4 * v1 + v2) / (2e-4 * 0.0005)
        assert j[:, axis] == pytest.approx(independent, rel=1e-5, abs=1e-5)


def test_zero_nu_zero_rho_has_exact_rank_one_not_cancellation_noise():
    m = core()
    for beta in (0.5, 1):
        for h in (1e-4, 3e-5, 1e-5):
            j = m.scaled_jacobian(100, 1, beta, [0.20, 0, 0], STRIKES, h=h)
            assert j[:, 1:] == pytest.approx(np.zeros((7, 2)), abs=1e-14)
            info = m.jacobian_diagnostics(j)
            assert info["rank"] == 1
            assert info["singular_values"][1:] == pytest.approx([0, 0], abs=1e-14)


@pytest.mark.parametrize("rho", [-0.8, 0.8])
def test_zero_nu_nonzero_rho_column_matches_analytic_hagan_derivative(rho):
    m = core()
    for beta in (0.5, 1):
        alpha = 0.20 * 100 ** (1 - beta)
        one_b = 1 - beta
        for strike, row in zip(
            STRIKES, m.scaled_jacobian(100, 1, beta, [0.20, rho, 0], STRIKES), strict=True
        ):
            log_fk = np.log(100 / strike)
            fk_pow = (100 * strike) ** (one_b / 2)
            denom = fk_pow * (1 + one_b**2 * log_fk**2 / 24 + one_b**4 * log_fk**4 / 1920)
            time0 = 1 + one_b**2 * alpha**2 / (24 * fk_pow**2)
            analytic = (
                (-rho * log_fk * time0 / 2 + rho * beta * alpha**2 / (4 * fk_pow**2))
                * fk_pow
                / denom
            )
            assert row[1] == pytest.approx(0, abs=1e-14)
            assert row[2] == pytest.approx(analytic * 0.50 / 0.0005, rel=1e-12, abs=1e-12)


def test_fixed_zero_nu_diagnostic_counts_only_evaluated_iv_vectors(monkeypatch):
    m = core()
    from hullkit import sabr

    quotes = m.sabr_vols(100, 1, 0.5, [0.20, 0, 0], STRIKES)
    original = sabr.sabr_implied_vol
    scalar_calls = []

    def counted(*args):
        scalar_calls.append(args)
        return original(*args)

    monkeypatch.setattr(sabr, "sabr_implied_vol", counted)
    result = m.fit_smile(100, 1, 0.5, STRIKES, quotes, [0.28, 0, 0], fixed={1: 0, 2: 0})
    assert result["success"]
    assert result["rank"] == 1
    assert result["boundary_flags"][2]
    assert result["diagnostic_calls"] == 3  # one final IV and two alpha-side evaluations
    assert result["scalar_iv_evaluations"] == len(scalar_calls)
    assert result["jacobian_scheme"][1:] == ["analytic_nu_zero", "analytic_nu_zero"]


def test_noiseless_recovery_preserves_solver_and_scaled_residual_diagnostics():
    m = core()
    quotes = m.sabr_vols(100, 1, 0.5, TRUTH, STRIKES)
    result = m.fit_smile(100, 1, 0.5, STRIKES, quotes, [0.28, 0.30, 0.80])
    assert result["success"]
    assert result["status"] > 0
    assert result["message"]
    assert result["theta"] == pytest.approx(TRUTH, abs=1e-7)
    assert result["alpha"] == pytest.approx(2, abs=1e-6)
    assert result["q"] == pytest.approx(0, abs=1e-14)
    assert result["scaled_residual"] == pytest.approx(result["raw_residual"] / 0.0005)
    assert result["q"] == pytest.approx(
        np.dot(result["scaled_residual"], result["scaled_residual"])
    )
    assert result["iv"] == pytest.approx(quotes, abs=1e-10)
    assert result["theta_jacobian"] == pytest.approx(
        result["scaled_jacobian"] * 0.0005 / [0.20, 0.50, 0.50]
    )
    assert result["raw_jacobian"] == pytest.approx(result["theta_jacobian"] / [10.0, 1.0, 1.0])
    assert result["rank"] == 3
    assert result["condition"] > 1
    assert result["start"] == pytest.approx([0.28, 0.30, 0.80])
    assert result["seconds"] >= 0
    assert result["optimality"] >= 0
    assert result["nfev"] > 1
    assert result["njev"] > 0
    assert result["active_mask"].shape == (3,)
    assert not result["boundary_flags"].any()


def test_moderate_quote_noise_is_fitted_with_bounded_parameter_recovery():
    m = core()
    noise = np.array([-0.0002, 0.0001, -0.0004, 0.0002, 0.0003, -0.0001, 0.0002])
    quotes = m.sabr_vols(100, 1, 0.5, TRUTH, STRIKES) + noise
    result = m.fit_smile(100, 1, 0.5, STRIKES, quotes, [0.12, -0.60, 0.08])
    assert result["success"]
    assert result["theta"][0] == pytest.approx(0.20, abs=0.002)
    assert result["theta"][1] == pytest.approx(-0.30, abs=0.04)
    assert result["theta"][2] == pytest.approx(0.40, abs=0.05)
    assert result["q"] <= np.sum((noise / 0.0005) ** 2) + 1e-10


def test_fixed_axis_nuisance_refitting_improves_over_literal_slice():
    m = core()
    quotes = m.sabr_vols(100, 1, 0.5, TRUTH, STRIKES)
    fixed_nu = 0.20
    slice_theta = np.array([0.20, -0.30, fixed_nu])
    slice_q = np.sum(((m.sabr_vols(100, 1, 0.5, slice_theta, STRIKES) - quotes) / 0.0005) ** 2)
    result = m.fit_smile(100, 1, 0.5, STRIKES, quotes, TRUTH, fixed={2: fixed_nu})
    assert result["success"]
    assert result["theta"][2] == fixed_nu
    assert result["q"] < slice_q - 1
    assert result["start"] == pytest.approx(TRUTH)
    assert result["effective_start"] == pytest.approx(slice_theta)
    assert result["fixed"] == {2: fixed_nu}
    assert result["scaled_jacobian"].shape == (7, 3)
    assert result["right_vectors"].shape == (3, 3)


def test_two_quotes_are_allowed_and_retain_full_null_direction():
    m = core()
    strikes = np.array([90.0, 110.0])
    quotes = m.sabr_vols(100, 1, 0.5, TRUTH, strikes)
    result = m.fit_smile(100, 1, 0.5, strikes, quotes, [0.28, 0.30, 0.80])
    assert result["success"]
    assert result["q"] < 1e-12
    assert result["rank"] == 2
    assert result["condition"] is None
    assert result["singular_values"][2] == 0
    assert result["scaled_jacobian"] @ result["right_vectors"][-1] == pytest.approx(
        [0, 0], abs=1e-10
    )


def test_budget_failure_is_retained_with_actual_price_evaluation_accounting(monkeypatch):
    m = core()
    from hullkit import sabr

    quotes = m.sabr_vols(100, 1, 0.5, TRUTH, STRIKES)
    original = sabr.sabr_implied_vol
    scalar_calls = []

    def counted(*args):
        scalar_calls.append(args)
        return original(*args)

    monkeypatch.setattr(sabr, "sabr_implied_vol", counted)
    result = m.fit_smile(100, 1, 0.5, STRIKES, quotes, [0.28, 0.30, 0.80], max_nfev=1)
    assert not result["success"]
    assert result["status"] == 0
    assert result["nfev"] == 1
    assert result["residual_calls"] > result["nfev"]
    assert result["diagnostic_calls"] > 0
    assert len(scalar_calls) == result["scalar_iv_evaluations"]
    assert len(scalar_calls) == len(STRIKES) * (
        result["residual_calls"] + result["diagnostic_calls"]
    )
    assert np.isfinite(result["q"])
    assert np.isfinite(result["theta"]).all()


@pytest.mark.parametrize("bad", ["forward", "maturity", "strike", "quotes", "noise", "start"])
def test_mathematically_invalid_fit_inputs_are_rejected(bad):
    m = core()
    forward, maturity, strikes = 100.0, 1.0, STRIKES.copy()
    quotes = np.full(7, 0.20)
    start, noise = TRUTH.copy(), 0.0005
    if bad == "forward":
        forward = 0
    elif bad == "maturity":
        maturity = -1
    elif bad == "strike":
        strikes[0] = 0
    elif bad == "quotes":
        quotes[0] = -1
    elif bad == "noise":
        noise = 0
    elif bad == "start":
        start[0] = 0.8
    with pytest.raises(ValueError):
        m.fit_smile(forward, maturity, 0.5, strikes, quotes, start, noise_scale=noise)
