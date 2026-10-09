"""Independent density/ordinary-Poisson checks for the synthetic cash call."""

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.stats import poisson

REFERENCE = (
    Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity/reference_methods.py"
)


@pytest.fixture
def reference():
    if not REFERENCE.is_file():
        return None
    spec = importlib.util.spec_from_file_location("short_maturity_independent_reference", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state(*, W=8.568429621061e-7, L=0.0, tau=1 / (365 * 1440), status="active"):
    return SimpleNamespace(
        carry_years=tau,
        variance=W,
        jump_mean_count=L,
        remaining_seconds=0.0 if status == "expiry" else tau * 365 * 86400,
        status=status,
    )


def parameters(**kwargs):
    fields = dict(rate=0.03, dividend=0.0, jump_mean=-0.05, jump_std=0.1)
    fields.update(kwargs)
    return SimpleNamespace(**fields)


@pytest.mark.parametrize(
    "L,want",
    [
        (0.0, [0.0369312678561, 0.5002092415187, 4.3098225498515]),
        (0.028 / 30, [0.0409347296796, 0.5177487839397, 4.3016755102457]),
    ],
)
def test_ordinary_count_reference_has_physical_atm_greeks(reference, L, want):
    assert reference is not None, "independent reference behavior is missing"
    result = reference.independent_mixture(100, 100, state(L=L), parameters())
    np.testing.assert_allclose(result["values"], want, rtol=2e-11, atol=2e-12)
    assert result["status"] == "ok"
    assert len(result["terms"]) == 9


@pytest.mark.parametrize("S,L", [(100, 0), (100, 0.028 / 30), (95, 0.028), (105, 0.028)])
def test_density_scores_agree_with_cdf_and_boundary_gamma(reference, S, L):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(L=L, W=0.00015873015873015873, tau=390 / (365 * 1440))
    cdf = reference.independent_mixture(S, 100, clock, parameters())
    density = reference.density_quad(S, 100, clock, parameters())
    np.testing.assert_allclose(density["values"], cdf["values"], rtol=2e-9, atol=2e-10)
    assert np.all(density["error_estimates"] >= 0)
    assert np.all(density["tail_bounds"] >= 0)
    assert abs(density["lr_gamma"] - density["values"][2]) <= (
        8 * density["lr_gamma_error_estimate"] + 2e-9
    )
    assert density["status"] == "ok"


def test_density_scores_resolve_one_minute_atm_gamma(reference):
    assert reference is not None, "independent reference behavior is missing"
    result = reference.density_quad(100, 100, state(L=0.028 / 30), parameters())
    assert result["values"][2] == pytest.approx(4.3016755102457, rel=2e-11)
    assert result["lr_gamma"] == pytest.approx(result["values"][2], abs=2e-9)
    assert result["error_estimates"][2] == 0.0


def test_tiny_positive_variance_has_smooth_atm_limit(reference):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=1e-20, tau=1e-12)
    p = parameters(rate=0, dividend=0)
    result = reference.independent_mixture(100, 100, clock, p)
    root = 1e-10
    want = [
        100 * math.erf(root / (2 * math.sqrt(2))),
        0.5 + root / (2 * math.sqrt(2 * math.pi)),
        1 / (100 * root * math.sqrt(2 * math.pi)),
    ]
    np.testing.assert_allclose(result["values"], want, rtol=2e-15)
    assert result["values"][0] > 0


def test_density_route_keeps_deep_itm_peak_when_lower_limit_is_far_negative(reference):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=1e-12, tau=1e-8)
    p = parameters(rate=0, dividend=0)
    result = reference.density_quad(105, 100, clock, p)
    assert result["values"][0] == pytest.approx(5.0, abs=2e-10)
    assert result["values"][1] == pytest.approx(1.0, abs=2e-8)
    assert result["values"][2] == 0.0
    # The LR2 integral is retained even when cancellation prevents precise Gamma.
    assert math.isfinite(result["lr_gamma"])
    assert result["lr_gamma_error_estimate"] >= 0


def test_positive_jump_tail_uses_exponentially_tilted_count(reference):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=0.02, L=0.5, tau=0.25)
    p = parameters(jump_mean=0.3, jump_std=0.4, dividend=0.02)
    short = reference.independent_mixture(110, 100, clock, p, nmax=2)
    long = reference.independent_mixture(110, 100, clock, p, nmax=24)
    tilted = 0.5 * math.exp(0.3 + 0.4**2 / 2)
    tail = math.exp(-0.02 * 0.25) * poisson.sf(2, tilted)
    np.testing.assert_allclose(
        short["tail_bounds"],
        [110 * tail, tail, tail / (110 * math.sqrt(2 * math.pi * (0.02 + 3 * 0.4**2)))],
        rtol=2e-14,
    )
    gap = long["values"] - short["values"]
    assert np.all(gap >= 0)
    assert np.all(gap <= short["tail_bounds"])


@pytest.mark.parametrize("order", [0.0, 1.0, 2.0, -1.0])
def test_compensated_sde_terminal_moments_follow_jump_mgf(reference, order):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=0.03, L=0.4, tau=0.75)
    p = parameters(rate=0.05, dividend=0.02, jump_mean=-0.12, jump_std=0.3)
    # Direct compound-Poisson normal MGF, independently expanded.
    kappa = math.exp(-0.12 + 0.3**2 / 2) - 1
    want = math.exp(
        order * 0.03 * 0.75
        + (order**2 - order) * 0.03 / 2
        + 0.4 * (math.exp(order * -0.12 + order**2 * 0.3**2 / 2) - 1 - order * kappa)
    )
    assert reference.terminal_moment(order, clock, p) == pytest.approx(want, rel=2e-14)


def test_compensated_first_moment_is_risk_neutral_forward(reference):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=0.1, L=0.7, tau=2.0)
    p = parameters(rate=0.04, dividend=0.015, jump_mean=0.2, jump_std=0.4)
    assert reference.terminal_moment(1, clock, p) == pytest.approx(math.exp(0.05), rel=2e-14)


@pytest.mark.parametrize("S", [95, 100, 105])
def test_reweighted_existing_merton_is_a_separate_price_comparator(reference, S):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(W=0.00015873015873015873, L=0.028, tau=390 / (365 * 1440))
    mixture = reference.independent_mixture(S, 100, clock, parameters())
    comparison = reference.merton_price_check(S, 100, clock, parameters())
    assert comparison["status"] == "ok"
    assert comparison["price"] == pytest.approx(mixture["values"][0], abs=2e-11)
    assert abs(comparison["difference"]) <= 2e-11


def test_three_spot_fd_widths_converge_to_physical_delta_gamma(reference):
    assert reference is not None, "independent reference behavior is missing"
    clock = state(L=0.028 / 30)
    want = reference.independent_mixture(100, 100, clock, parameters())["values"]
    rows = reference.spot_finite_differences(100, 100, clock, parameters())
    assert len(rows) == 3
    assert rows[0]["step"] > rows[1]["step"] > rows[2]["step"] > 0
    delta_errors = [abs(row["delta"] - want[1]) for row in rows]
    gamma_errors = [abs(row["gamma"] - want[2]) for row in rows]
    assert delta_errors[2] < delta_errors[0]
    assert gamma_errors[2] < gamma_errors[0]
    assert delta_errors[2] < 1e-5
    assert gamma_errors[2] < 5e-4


@pytest.mark.parametrize("S,want", [(95, [0, 0, 0]), (105, [5, 1, 0])])
@pytest.mark.parametrize("method", ["independent_mixture", "density_quad"])
def test_expiry_off_atm_has_classical_greeks(reference, method, S, want):
    assert reference is not None, "independent reference behavior is missing"
    expiry = state(W=0, L=0, tau=0, status="expiry")
    result = getattr(reference, method)(S, 100, expiry, parameters())
    np.testing.assert_array_equal(result["values"], want)
    np.testing.assert_array_equal(result["tail_bounds"], [0, 0, 0])
    assert result["status"] == "expiry"


@pytest.mark.parametrize("method", ["independent_mixture", "density_quad"])
def test_expiry_atm_preserves_undefined_ordinary_greeks(reference, method):
    assert reference is not None, "independent reference behavior is missing"
    expiry = state(W=0, L=0, tau=0, status="expiry")
    result = getattr(reference, method)(100, 100, expiry, parameters())
    assert result["values"][0] == 0
    assert np.isnan(result["values"][1:]).all()
    assert result["status"] == "expiry_undefined_atm"
    assert result["reason"] == "ordinary_greeks_undefined_atm_expiry"


@pytest.mark.parametrize(
    "S,K,clock,p,nmax",
    [
        (-1, 100, state(), parameters(), 8),
        (100, math.inf, state(), parameters(), 8),
        (100, 100, state(W=-0.1), parameters(), 8),
        (100, 100, state(W=0), parameters(), 8),
        (100, 100, state(L=-0.1), parameters(), 8),
        (100, 100, state(tau=-0.1), parameters(), 8),
        (100, 100, state(tau=0), parameters(), 8),
        (100, 100, state(status="unknown"), parameters(), 8),
        (100, 100, state(W=1, L=0, tau=0, status="expiry"), parameters(), 8),
        (100, 100, state(), parameters(jump_std=-0.1), 8),
        (100, 100, state(), parameters(rate=math.nan), 8),
        (100, 100, state(), parameters(), -1),
        (100, 100, state(), parameters(), 2.5),
        (100, 100, state(), parameters(), True),
    ],
)
def test_reference_rejects_invalid_or_unsupported_clocks(reference, S, K, clock, p, nmax):
    assert reference is not None, "independent reference behavior is missing"
    with pytest.raises(ValueError):
        reference.independent_mixture(S, K, clock, p, nmax=nmax)


def test_density_quadrature_requires_positive_tolerances(reference):
    assert reference is not None, "independent reference behavior is missing"
    with pytest.raises(ValueError):
        reference.density_quad(100, 100, state(), parameters(), epsabs=0)
    with pytest.raises(ValueError):
        reference.density_quad(100, 100, state(), parameters(), epsrel=math.nan)


def test_density_reference_does_not_use_cdf_formula(reference, monkeypatch):
    def forbidden_cdf(_):
        pytest.fail("density reference called the CDF-price route")

    monkeypatch.setattr(reference, "_cdf", forbidden_cdf)
    result = reference.density_quad(100, 100, state(L=0.028 / 30), parameters())
    np.testing.assert_allclose(
        result["values"],
        [0.0409347296796, 0.5177487839397, 4.3016755102457],
        rtol=2e-10,
        atol=2e-12,
    )


def test_zero_count_conditional_delta_is_not_clipped_to_expected_call_bound(reference):
    clock = state(W=0.00015873015873015873, L=0.028, tau=390 / (365 * 1440))
    result = reference.independent_mixture(105, 100, clock, parameters())
    assert result["terms"][0]["values"][1] == pytest.approx(1.00119810524, rel=2e-11)
    assert result["terms"][0]["values"][1] > 1
    assert 0 < result["values"][1] < 1


def test_expiry_atm_spot_fd_does_not_label_symmetric_slope_as_ordinary_greek(reference):
    expiry = state(W=0, L=0, tau=0, status="expiry")
    rows = reference.spot_finite_differences(100, 100, expiry, parameters())
    assert len(rows) == 3
    for row in rows:
        assert math.isnan(row["delta"])
        assert math.isnan(row["gamma"])
        assert row["status"] == "expiry_undefined_atm"
        assert row["reason"] == "ordinary_greeks_undefined_atm_expiry"


@pytest.mark.parametrize("widths", [(1e-4, 1e-4, 1e-5), (0.01, 0), (0.1, 0.01, math.nan)])
def test_spot_fd_rejects_invalid_width_roster(reference, widths):
    with pytest.raises(ValueError):
        reference.spot_finite_differences(100, 100, state(), parameters(), relative_steps=widths)


def test_density_score_split_respects_final_delta_absolute_error_budget(reference):
    S = 100 * math.exp(0.05)
    result = reference.density_quad(S, 100, state(), parameters())
    assert result["error_estimates"][1] <= 1e-10
    assert result["values"][1] == pytest.approx(1.0, abs=2e-12)
    assert result["status"] == "ok"
