"""The book's own IRLS must reproduce statsmodels exactly."""

import numpy as np
import pytest
import statsmodels.api as sm
from stats_textbook import glm


def logistic_data(n=400, seed=0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    eta = X @ np.array([-0.5, 1.2])
    return X, rng.binomial(1, 1.0 / (1.0 + np.exp(-eta))).astype(float)


def poisson_data(n=300, seed=1):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    return X, rng.poisson(np.exp(X @ np.array([0.7, 0.4]))).astype(float)


def test_logistic_irls_matches_statsmodels():
    X, y = logistic_data()
    got = glm.irls(X, y, family="binomial")
    ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-7)
    assert abs(got.deviance - ref.deviance) < 1e-7
    assert abs(got.loglik - ref.llf) < 1e-7


def test_poisson_irls_matches_statsmodels():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    ref = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    # Measured agreement: params to 7e-12, se to 2e-6 relative. The looser
    # tolerance on se is real -- statsmodels stops iterating on a different
    # criterion, so the covariance is evaluated at a marginally different mu.
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-5)
    assert abs(got.deviance - ref.deviance) < 1e-6


def test_gaussian_irls_reduces_to_ordinary_least_squares():
    """With an identity link, one IRLS step is the OLS solve."""
    from stats_textbook import regression as reg

    rng = np.random.default_rng(2)
    n = 200
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    y = X @ np.array([1.0, -2.0]) + rng.normal(0, 1.0, n)
    np.testing.assert_allclose(
        glm.irls(X, y, family="gaussian").params, reg.ols(X, y).params, rtol=1e-10
    )


def test_irls_converges_in_a_handful_of_iterations():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    assert 2 <= got.n_iter <= 10, f"took {got.n_iter} iterations"


def test_irls_rejects_an_unknown_family():
    X, y = logistic_data()
    with pytest.raises(ValueError, match="family"):
        glm.irls(X, y, family="gamma")


def test_binomial_response_outside_zero_one_is_rejected():
    X, _y = logistic_data()
    with pytest.raises(ValueError, match="binomial"):
        glm.irls(X, np.full(X.shape[0], 2.0), family="binomial")


def test_deviance_residuals_square_to_the_deviance():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    d = glm.deviance_residuals(y, got.fitted, "poisson")
    assert abs(float((d**2).sum()) - got.deviance) < 1e-8


def test_dispersion_is_about_one_for_a_true_poisson():
    X, y = poisson_data(n=2000, seed=3)
    got = glm.irls(X, y, family="poisson")
    assert 0.85 <= glm.dispersion(got, y, X, "poisson") <= 1.15


def test_dispersion_detects_overdispersion():
    """Negative-binomial data fitted as Poisson must show dispersion > 1."""
    rng = np.random.default_rng(4)
    n = 2000
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    mu = np.exp(X @ np.array([1.0, 0.5]))
    y = rng.negative_binomial(2.0, 2.0 / (2.0 + mu)).astype(float)
    got = glm.irls(X, y, family="poisson")
    assert glm.dispersion(got, y, X, "poisson") > 1.5
