import numpy as np
from hullkit.vol_surface import (
    compare_surface_constraints,
    fit_ssvi_slice,
    project_convex_call_prices,
    ssvi_butterfly_margins,
    ssvi_is_butterfly_safe,
    ssvi_total_variance,
    variance_term_rmse,
)


def test_ssvi_fit_recovers_slice():
    k = np.linspace(-0.4, 0.4, 17)
    target = ssvi_total_variance(k, theta=0.05, rho=-0.55, phi=1.8)
    fitted = fit_ssvi_slice(k, target)
    rebuilt = ssvi_total_variance(k, fitted.theta, fitted.rho, fitted.phi)
    np.testing.assert_allclose(rebuilt, target, atol=1e-8)
    assert ssvi_is_butterfly_safe(fitted.theta, fitted.rho, fitted.phi)


def test_ssvi_positive_parameters_are_not_automatically_arbitrage_safe():
    margins = ssvi_butterfly_margins(theta=1.0, rho=0.9, phi=3.0)
    assert min(margins) < 0.0
    assert not ssvi_is_butterfly_safe(theta=1.0, rho=0.9, phi=3.0)


def test_convex_projection_repairs_monotonicity_and_convexity():
    strikes = np.array([80, 90, 100, 110, 120], dtype=float)
    broken = np.array([22.0, 15.0, 9.0, 10.0, 1.0])
    repaired = project_convex_call_prices(strikes, broken, lower_bound=0.0, upper_bound=100.0)
    assert np.all(np.diff(repaired) <= 1e-8)
    slopes = np.diff(repaired) / np.diff(strikes)
    assert np.all(np.diff(slopes) >= -1e-8)


def test_variance_consistency_is_separate_from_iv_fit():
    assert variance_term_rmse(np.array([0.04, 0.05]), np.array([0.04, 0.05])) == 0.0
    assert variance_term_rmse(np.array([0.04, 0.09]), np.array([0.04, 0.05])) > 0.0


def test_constraint_comparison_keeps_soft_and_hard_claims_separate():
    strikes = np.array([80, 90, 100, 110, 120], dtype=float)
    broken = np.array([22.0, 15.0, 9.0, 10.0, 1.0])
    comparison = compare_surface_constraints(
        strikes,
        broken,
        soft_weight=50.0,
        lower_bound=0.0,
        upper_bound=100.0,
    )
    diagnostics = comparison.to_dict()["diagnostics"]
    assert diagnostics["unconstrained"]["hard_checks_pass"] is False
    assert diagnostics["hard_constrained"]["hard_checks_pass"] is True
    assert set(diagnostics) == {"unconstrained", "soft_penalty", "hard_constrained"}


def test_soft_constraint_solver_handles_normalized_option_prices():
    strikes = np.linspace(0.82, 1.18, 9)
    broken = np.array([0.181, 0.143, 0.111, 0.086, 0.094, 0.049, 0.032, 0.019, 0.010])
    comparison = compare_surface_constraints(
        strikes,
        broken,
        soft_weight=100.0,
        lower_bound=np.maximum(1.0 - strikes, 0.0),
        upper_bound=1.0,
    )
    assert np.all(np.isfinite(comparison.soft_penalty))
    assert comparison.diagnostics["hard_constrained"]["hard_checks_pass"] is True
