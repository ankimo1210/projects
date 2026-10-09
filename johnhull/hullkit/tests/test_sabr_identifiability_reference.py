"""Independent approximating-map, analytic-boundary and optimizer references."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit.sabr import sabr_implied_vol

REFERENCE = Path(__file__).resolve().parents[2] / "research/RB-F06/reference_methods.py"
SCALE = np.array([0.20, 0.50, 0.50])


def reference():
    assert REFERENCE.is_file(), "RB-F06 independent reference methods are missing"
    spec = importlib.util.spec_from_file_location("rbf06_reference_test", REFERENCE)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def public_quotes(F, T, beta, theta, strikes):
    a, rho, nu = theta
    return np.array(
        [sabr_implied_vol(F, k, T, a * F ** (1 - beta), beta, rho, nu) for k in strikes]
    )


@pytest.mark.parametrize("rho", [-0.8, 0.0, 0.8])
def test_flat_lognormal_limit_removes_correlation(rho):
    ref = reference()
    strikes = 100 * np.exp(np.array([-0.25, -0.10, 0.0, 0.10, 0.25]))
    vols = ref.independent_hagan_vols(100.0, 1.0, 1.0, (0.2, rho, 0.0), strikes)
    assert np.allclose(vols, 0.2, rtol=0, atol=1e-12)


@pytest.mark.parametrize("strike", [75.0, 90.0, 100.0, 110.0, 125.0])
def test_flat_call_price_matches_independent_normal_density_integral(strike):
    ref = reference()
    black = ref.black_calls(100.0, 1.0, [strike], [0.2])[0]
    integrated = ref.flat_lognormal_quad(100.0, 1.0, strike, 0.2)
    assert black == pytest.approx(integrated, rel=0, abs=1e-10)
    if strike == 100.0:
        assert black == pytest.approx(7.965567455405804, abs=1e-12)


@pytest.mark.parametrize("beta", [0.0, 0.5, 1.0])
def test_nonzero_nu_transcription_matches_public_approximate_map(beta):
    ref = reference()
    theta = (0.2, -0.3, 0.4)
    strikes = 100 * np.exp(np.array([-0.20, -0.10, -0.01, 0, 0.01, 0.10, 0.20]))
    expected = public_quotes(100.0, 1.0, beta, theta, strikes)
    actual = ref.independent_hagan_vols(100.0, 1.0, beta, theta, strikes)
    assert np.allclose(actual, expected, rtol=1e-11, atol=2e-13)


def test_small_z_formula_has_smooth_nu_zero_limit():
    ref = reference()
    strikes = 100 * np.exp(np.array([-0.01, 0, 0.01]))
    at_zero = ref.independent_hagan_vols(100.0, 1.0, 0.5, (0.2, -0.3, 0.0), strikes)
    nearby = ref.independent_hagan_vols(100.0, 1.0, 0.5, (0.2, -0.3, 1e-9), strikes)
    assert np.allclose(nearby, at_zero, rtol=0, atol=1e-11)


def test_nu_zero_rho_zero_scaled_jacobian_is_rank_one():
    ref = reference()
    strikes = 100 * np.exp(np.array([-0.25, -0.10, 0, 0.10, 0.25]))
    jac = ref.independent_jacobian(100.0, 1.0, 1.0, (0.2, 0.0, 0.0), strikes)
    assert np.allclose(jac[:, 0], 400.0, rtol=0, atol=1e-9)
    assert np.allclose(jac[:, 1:], 0.0, rtol=0, atol=1e-13)
    assert np.linalg.matrix_rank(jac, tol=1e-8) == 1


@pytest.mark.parametrize("rho", [-0.3, 0.3])
def test_nu_zero_one_sided_derivative_is_analytic_even_off_atm(rho):
    ref = reference()
    beta, T, a = 0.5, 1.3, 0.2
    logs = np.array([-0.2, -0.01, 0, 0.01, 0.2])
    strikes = 100 * np.exp(-logs)
    m = a * np.exp((1 - beta) * logs / 2)
    denom = 1 + (1 - beta) ** 2 * logs**2 / 24 + (1 - beta) ** 4 * logs**4 / 1920
    correction = (1 - beta) ** 2 * m**2 / 24
    da = (m / a) * (1 + 3 * correction * T) / denom
    dnu = rho * (beta * m**2 * T / 4 - logs * (1 + correction * T) / 2) / denom
    expected = np.column_stack([da * 0.2, np.zeros_like(logs), dnu * 0.5]) / 0.0005
    actual = ref.independent_jacobian(100.0, T, beta, (a, rho, 0.0), strikes)
    assert np.allclose(actual, expected, rtol=2e-12, atol=1e-11)


def test_interior_five_point_jacobian_agrees_with_separate_two_point_difference():
    ref = reference()
    F, T, beta = 100.0, 1.0, 0.5
    theta = np.array([0.2, -0.3, 0.4])
    strikes = F * np.exp(np.array([-0.2, -0.01, 0, 0.01, 0.2]))
    columns = []
    for axis in range(3):
        bump = np.zeros(3)
        bump[axis] = SCALE[axis] * 3e-6
        columns.append(
            (
                public_quotes(F, T, beta, theta + bump, strikes)
                - public_quotes(F, T, beta, theta - bump, strikes)
            )
            / (2 * 3e-6 * 0.0005)
        )
    expected = np.column_stack(columns)
    actual = ref.independent_jacobian(F, T, beta, theta, strikes)
    assert np.allclose(actual, expected, rtol=3e-7, atol=2e-6)


def test_fixed_axis_fit_reoptimizes_nuisance_and_records_actual_q():
    ref = reference()
    strikes = 100 * np.exp(np.array([-0.2, -0.1, -0.01, 0, 0.01, 0.1, 0.2]))
    quotes = public_quotes(100.0, 1.0, 0.5, (0.2, -0.3, 0.4), strikes)
    fitted = ref.independent_fixed_fit(
        100.0, 1.0, 0.5, strikes, quotes, (0.27, -0.3, 0.75), fixed={1: -0.3}
    )
    assert fitted["success"], fitted["message"]
    assert fitted["theta"][1] == pytest.approx(-0.3, abs=1e-14)
    ivs = ref.independent_hagan_vols(100.0, 1.0, 0.5, fitted["theta"], strikes)
    assert fitted["q"] == pytest.approx(np.sum(((ivs - quotes) / 0.0005) ** 2), abs=1e-12)
    assert np.max(np.abs(ivs - quotes)) < 2e-8
    assert np.allclose(fitted["theta"], (0.2, -0.3, 0.4), atol=2e-6, rtol=0)
    assert 1 <= fitted["nfev"] <= 250 and fitted["seconds"] >= 0
    assert "status" in fitted


def test_all_fixed_axes_keep_noise_objective_without_optimizer():
    ref = reference()
    theta = (0.2, -0.3, 0.4)
    strikes = 100 * np.exp(np.array([-0.2, -0.1, -0.01, 0, 0.01, 0.1, 0.2]))
    quotes = public_quotes(100.0, 1.0, 0.5, theta, strikes)
    quotes += np.array([1, -2, 3, 0, -3, 2, -1]) * 0.0001
    fitted = ref.independent_fixed_fit(
        100.0, 1.0, 0.5, strikes, quotes, (0.3, 0.2, 0.8), fixed=dict(enumerate(theta))
    )
    assert fitted["success"]
    assert fitted["q"] == pytest.approx(1.12, abs=1e-9)
    assert fitted["nfev"] == 1


def test_independent_fit_retains_evaluation_budget_failure():
    ref = reference()
    strikes = np.array([85.0, 95.0, 100.0, 105.0, 115.0])
    quotes = public_quotes(100.0, 1.0, 0.5, (0.2, -0.3, 0.4), strikes)
    fitted = ref.independent_fixed_fit(
        100.0, 1.0, 0.5, strikes, quotes, (0.3, 0.2, 0.8), max_nfev=1
    )
    assert not fitted["success"]
    assert fitted["nfev"] == 1
    assert np.isfinite(fitted["q"])


def test_reference_evaluates_without_delegating_to_public_sabr(monkeypatch):
    import hullkit.sabr as sabr

    def forbidden(*args, **kwargs):
        raise AssertionError("reference delegated to production SABR")

    monkeypatch.setattr(sabr, "sabr_implied_vol", forbidden)
    ref = reference()
    assert ref.independent_hagan_vols(100.0, 1.0, 1.0, (0.2, 0, 0), [100])[0] == pytest.approx(0.2)
    assert ref.black_calls(100, 1, [100], [0.2])[0] == pytest.approx(7.965567455405804)
    assert ref.flat_lognormal_quad(100, 1, 100, 0.2) == pytest.approx(7.965567455405804)


def test_mathematically_undefined_reference_inputs_are_rejected():
    ref = reference()
    with pytest.raises(ValueError):
        ref.independent_hagan_vols(100, -1, 0.5, (0.2, 0, 0.4), [100])
    with pytest.raises(ValueError):
        ref.black_calls(100, 1, [0], [0.2])
    with pytest.raises(ValueError):
        ref.independent_jacobian(100, 1, 0.5, (0.2, 0, 0.4), [100], noise_scale=0)


def test_fixed_fit_does_not_mutate_the_callers_start_array():
    ref = reference()
    start = np.array([0.3, 0.2, 0.8])
    strikes = np.array([90.0, 100.0, 110.0])
    quotes = public_quotes(100.0, 1.0, 0.5, (0.2, -0.3, 0.4), strikes)
    ref.independent_fixed_fit(
        100.0,
        1.0,
        0.5,
        strikes,
        quotes,
        start,
        fixed={0: 0.2, 1: -0.3, 2: 0.4},
    )
    assert np.allclose(start, (0.3, 0.2, 0.8), rtol=0, atol=1e-14)
