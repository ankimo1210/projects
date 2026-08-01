"""OLS as inference, matched against statsmodels."""

import numpy as np
import pytest
import statsmodels.api as sm
from stats_textbook import regression as reg


def make_data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
    y = X @ np.array([1.0, 2.0, -0.5]) + rng.normal(0, 1.5, n)
    return X, y


def test_ols_matches_statsmodels():
    X, y = make_data()
    got = reg.ols(X, y)
    ref = sm.OLS(y, X).fit()
    np.testing.assert_allclose(got.params, ref.params, rtol=1e-10)
    np.testing.assert_allclose(got.se, ref.bse, rtol=1e-10)
    np.testing.assert_allclose(got.tvalues, ref.tvalues, rtol=1e-10)
    np.testing.assert_allclose(got.pvalues, ref.pvalues, rtol=1e-8, atol=1e-12)
    assert got.df_resid == int(ref.df_resid)
    assert abs(got.r_squared - ref.rsquared) < 1e-12


def test_ols_recovers_the_true_coefficients():
    X, y = make_data(n=20_000, seed=1)
    got = reg.ols(X, y)
    np.testing.assert_allclose(got.params, [1.0, 2.0, -0.5], atol=0.05)


def test_fitted_and_residuals_decompose_y():
    X, y = make_data()
    got = reg.ols(X, y)
    np.testing.assert_allclose(got.fitted + got.resid, y, rtol=1e-12)
    # Residuals are orthogonal to every column of X -- the normal equations.
    np.testing.assert_allclose(X.T @ got.resid, np.zeros(X.shape[1]), atol=1e-9)


@pytest.mark.parametrize("kind", ["HC0", "HC1", "HC2", "HC3"])
def test_robust_standard_errors_match_statsmodels(kind):
    X, y = make_data()
    got = reg.robust_se(X, reg.ols(X, y).resid, kind=kind)
    ref = sm.OLS(y, X).fit(cov_type=kind).bse
    np.testing.assert_allclose(got, ref, rtol=1e-9)


def test_robust_se_rejects_an_unknown_kind():
    X, y = make_data()
    with pytest.raises(ValueError, match="kind"):
        reg.robust_se(X, reg.ols(X, y).resid, kind="HC4")


def test_robust_se_differs_from_ordinary_se_under_heteroskedasticity():
    rng = np.random.default_rng(2)
    n = 500
    x = rng.normal(size=n)
    X = np.column_stack([np.ones(n), x])
    y = 1.0 + 2.0 * x + rng.normal(0, 0.5 + np.abs(x), n)  # variance grows with |x|
    fit = reg.ols(X, y)
    hc3 = reg.robust_se(X, fit.resid, kind="HC3")
    # The ordinary SE is the one that is wrong here.
    assert abs(hc3[1] - fit.se[1]) / fit.se[1] > 0.05


def test_overall_f_test_matches_statsmodels():
    X, y = make_data()
    fit = reg.ols(X, y)
    f, p = reg.f_test_overall(fit, X, y)
    ref = sm.OLS(y, X).fit()
    assert abs(f - ref.fvalue) < 1e-8
    assert abs(p - ref.f_pvalue) < 1e-12


def test_vif_flags_collinearity_and_ignores_the_intercept():
    rng = np.random.default_rng(3)
    n = 400
    a = rng.normal(size=n)
    X = np.column_stack([np.ones(n), a, a + rng.normal(0, 0.05, n), rng.normal(size=n)])
    v = reg.vif(X)
    assert np.isnan(v[0]), "the intercept has no VIF"
    assert v[1] > 10 and v[2] > 10, "the near-duplicate pair must be flagged"
    assert v[3] < 2, "the independent column must not be"


def test_leverage_sums_to_the_number_of_parameters():
    X, _y = make_data()
    h = reg.leverage(X)
    assert abs(h.sum() - X.shape[1]) < 1e-9
    assert np.all((h >= 0) & (h <= 1))
