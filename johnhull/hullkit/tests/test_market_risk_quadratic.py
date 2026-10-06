"""Hull §22.5 and Technical Note 10; independent Gaussian integration."""

import numpy as np
import pytest
from hullkit import _market_risk as m
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import brentq
from scipy.stats import norm


def test_source_one_factor_raw_moments():
    b, c = 3.0, -0.4
    result = m.quadratic_moments([b], [[c]], [[1]])
    assert result["mean"] == pytest.approx(c)
    assert result["raw_second"] == pytest.approx(b * b + 3 * c * c)
    assert result["raw_third"] == pytest.approx(9 * b * b * c + 15 * c**3)
    x, w = hermgauss(12)
    pnl = b * np.sqrt(2) * x + c * 2 * x * x
    for key, power in [("mean", 1), ("raw_second", 2), ("raw_third", 3)]:
        assert result[key] == pytest.approx(w @ pnl**power / np.sqrt(np.pi), abs=1e-12)


def test_cross_gamma_moments_independent_two_dimensional_quadrature():
    a = np.array([2.0, -1.0])
    beta = np.array([[0.3, 0.4], [0.4, -0.2]])
    cov = np.array([[0.04, -0.015], [-0.015, 0.09]])
    shift = 0.7
    result = m.quadratic_moments(a, beta, cov, constant=shift)
    x, w = hermgauss(10)
    shocks = np.array([[u, v] for u in x for v in x]) * np.sqrt(2)
    shocks = shocks @ np.linalg.cholesky(cov).T
    weights = np.outer(w, w).ravel() / np.pi
    # Independent scalar polynomial includes both cross-gamma contributions.
    pnl = shift + 2 * shocks[:, 0] - shocks[:, 1] + 0.3 * shocks[:, 0] ** 2
    pnl += 0.8 * shocks[:, 0] * shocks[:, 1] - 0.2 * shocks[:, 1] ** 2
    mean = weights @ pnl
    var = weights @ (pnl - mean) ** 2
    skew = weights @ (pnl - mean) ** 3 / var**1.5
    assert result["mean"] == pytest.approx(mean)
    assert result["variance"] == pytest.approx(var)
    assert result["skewness"] == pytest.approx(skew)
    assert m.quadratic_pnl(shocks, a, beta, constant=shift) == pytest.approx(pnl)


def test_source_tn10_rounded_normal_and_skew_corrected_quantiles():
    # Official TN10 indexed text: mean=-.2, SD=2.2, skew=-.4; z=-2.33.
    normal = m.cornish_fisher_pnl_quantile(-0.2, 2.2, 0, 0.01, z=-2.33)
    corrected = m.cornish_fisher_pnl_quantile(-0.2, 2.2, -0.4, 0.01, z=-2.33)
    assert normal == pytest.approx(-5.326, abs=0.0005)
    assert corrected == pytest.approx(-5.976, abs=0.0005)
    exact_z = m.cornish_fisher_pnl_quantile(-0.2, 2.2, -0.4, 0.01)
    expected = -0.2 + 2.2 * (norm.ppf(0.01) - 0.4 * (norm.ppf(0.01) ** 2 - 1) / 6)
    assert exact_z == pytest.approx(expected)


@pytest.mark.parametrize("b,c", [(1.3, 0.25), (1.3, -0.25), (0.0, 0.4)])
def test_exact_quadratic_quantile_against_normal_root_probability(b, c):
    constant, probability = -0.3, 0.07

    def cdf(value):
        discriminant = b * b - 4 * c * (constant - value)
        if discriminant < 0:
            return 0.0 if c > 0 else 1.0
        roots = sorted(
            [(-b - np.sqrt(discriminant)) / (2 * c), (-b + np.sqrt(discriminant)) / (2 * c)]
        )
        interval = norm.cdf(roots[1]) - norm.cdf(roots[0])
        return interval if c > 0 else 1 - interval

    reference = brentq(lambda value: cdf(value) - probability, -50, 50, xtol=1e-11)
    assert m.quadratic_normal_quantile(b, c, probability, constant=constant) == pytest.approx(
        reference, abs=1e-10
    )


def test_skew_correction_is_an_approximation_and_normal_limit_is_exact():
    b, c = 2.0, 0.015
    moments = m.quadratic_moments([b], [[c]], [[1]])
    approx = m.cornish_fisher_pnl_quantile(
        moments["mean"], moments["sigma"], moments["skewness"], 0.01
    )
    exact = m.quadratic_normal_quantile(b, c, 0.01)
    assert approx == pytest.approx(exact, abs=0.004)
    assert m.quadratic_normal_quantile(-2, 0, 0.01) == pytest.approx(2 * norm.ppf(0.01))
    assert m.quadratic_normal_quantile(0, 0, 0.01, constant=3) == 3


def test_mixed_hessian_revaluation_has_cubic_error():
    spot = np.array([2.0, 3.0])
    # f(s,t)=s^2*t: exact analytic gradients and full Hessian.
    linear = np.array([2 * spot[0] ** 2 * spot[1], spot[0] ** 2 * spot[1]])
    beta = np.array([[spot[0] ** 2 * spot[1], spot[0] ** 2 * spot[1]], [spot[0] ** 2 * spot[1], 0]])
    direction = np.array([0.2, -0.1])
    errors = []
    for scale in [1, 0.5]:
        returns = scale * direction
        new = spot * (1 + returns)
        full = new[0] ** 2 * new[1] - spot[0] ** 2 * spot[1]
        errors.append(abs(full - m.quadratic_pnl(returns, linear, beta)))
    assert errors[0] / errors[1] == pytest.approx(8, rel=1e-9)


def test_deterministic_quadratic_and_mathematical_invalid_input():
    result = m.quadratic_moments([0], [[0]], [[0]], constant=2)
    assert result["variance"] == 0
    assert result["skewness"] == 0  # convention for a point mass
    with pytest.raises(ValueError):
        m.quadratic_moments([1, 2], [[0, 1], [0, 0]], np.eye(2))
    with pytest.raises(ValueError):
        m.cornish_fisher_pnl_quantile(0, -1, 0, 0.99)


@pytest.mark.parametrize("linear", [1, -1, 2, -2])
@pytest.mark.parametrize("quadratic", [1e-6, -1e-6, 1e-12, -1e-12])
def test_review_r2_small_gamma_finite_and_continuous_linear_limit(linear, quadratic):
    probability = 0.01
    # On the relevant monotone branch the other root lies >500000 SD away:
    # its probability is negligible. Direct mapped normal quantile is independent
    # of ncx2's large noncentrality computation and quadratic root subtraction.
    z = norm.ppf(probability)
    reference = abs(linear) * z + quadratic * z * z
    actual = m.quadratic_normal_quantile(linear, quadratic, probability)
    assert np.isfinite(actual)
    assert actual == pytest.approx(reference, abs=2e-11)
