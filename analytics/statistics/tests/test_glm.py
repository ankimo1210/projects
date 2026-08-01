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


# Coefficients agree to ~1e-11 or better; standard errors only to ~5e-6.
# The gap is not a convergence artefact -- it survives evaluating both
# formulas at statsmodels' own coefficients. statsmodels reports the
# covariance built from the working weights of its final weighted least
# squares, and those weights were formed from the *previous* iterate's mu;
# recomputing them at the converged mu (what irls does) differs by O(tol).
# Verified: feeding statsmodels' own model.weights into this module's
# covariance formula reproduces its bse to 1.8e-16. Neither is wrong.
SE_RTOL = 1e-5


def test_logistic_irls_matches_statsmodels():
    X, y = logistic_data()
    got = glm.irls(X, y, family="binomial")
    ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    np.testing.assert_allclose(got.se, ref.bse, rtol=SE_RTOL)
    assert abs(got.deviance - ref.deviance) < 1e-7
    assert abs(got.loglik - ref.llf) < 1e-7


def test_poisson_irls_matches_statsmodels():
    X, y = poisson_data()
    got = glm.irls(X, y, family="poisson")
    ref = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    assert got.converged
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-8)
    np.testing.assert_allclose(got.se, ref.bse, rtol=SE_RTOL)
    assert abs(got.deviance - ref.deviance) < 1e-6


def test_standard_error_gap_is_the_weight_evaluation_point():
    """Pin the diagnosis, so a future regression is not misread as drift."""
    from scipy import special

    X, y = logistic_data()
    ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    # statsmodels' stored weights are not mu(1-mu) at the converged mu ...
    mu = special.expit(X @ ref.params)
    assert np.abs(np.asarray(ref.model.weights) - mu * (1 - mu)).max() > 1e-12
    # ... but feeding them through this module's covariance reproduces bse.
    w = np.asarray(ref.model.weights)
    se = np.sqrt(np.diag(np.linalg.pinv((X * w[:, None]).T @ X)))
    np.testing.assert_allclose(se, ref.bse, rtol=1e-12)


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


def test_perfect_separation_diverges_without_crashing():
    """When the MLE does not exist, say so -- do not raise LinAlgError.

    A perfectly separated logistic fit drives mu to the boundary, the
    working weight to zero and the working response to infinity. Without
    clipping, numpy's lstsq dies with "SVD did not converge", which reads
    as a bug in the caller's data rather than as the real answer: there is
    no maximum, the coefficient just runs away.
    """
    x = np.array([-3.0, -2.0, -1.0, 1.0, 2.0, 3.0])
    y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    X = np.column_stack([np.ones(6), x])
    slopes = [glm.irls(X, y, family="binomial", max_iter=k, tol=0.0).params[1] for k in (5, 20, 50)]
    assert all(np.isfinite(s) for s in slopes), slopes
    assert slopes[0] < slopes[1] < slopes[2], f"the slope should keep growing: {slopes}"
    assert slopes[-1] > 10.0, f"and grow a lot: {slopes[-1]}"


def test_dispersion_detects_overdispersion():
    """Negative-binomial data fitted as Poisson must show dispersion > 1."""
    rng = np.random.default_rng(4)
    n = 2000
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    mu = np.exp(X @ np.array([1.0, 0.5]))
    y = rng.negative_binomial(2.0, 2.0 / (2.0 + mu)).astype(float)
    got = glm.irls(X, y, family="poisson")
    assert glm.dispersion(got, y, X, "poisson") > 1.5
