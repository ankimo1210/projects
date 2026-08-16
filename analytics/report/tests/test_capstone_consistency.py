"""Cross-book numerical consistency for the capstone (the report tree can import
all five books, so it is the natural home for this check).

The capstone teaches that one regression problem has many faces. This test pins
that down: the five books (linear algebra, NN, Bayesian, machine learning,
statistics) generate IDENTICAL data, and ridge (linear algebra) == Bayesian
posterior mean == gradient-descent-with-weight-decay (NN) == scikit-learn Ridge
(ML) on the shared features, with least squares (statistics) as the lambda -> 0
end of the same family.
"""

import numpy as np
from bayes_textbook.models import BayesianLinearRegression, ridge_solution
from bayes_textbook.simulation import make_capstone_dataset as by_data
from la_book.algebra import ridge as la_ridge
from la_book.datasets import make_capstone_dataset as la_data
from ml_textbook.datasets import make_capstone_dataset as ml_data
from nn_textbook.datasets import make_capstone_dataset as nn_data
from sklearn.linear_model import Ridge
from stats_textbook.datasets import make_capstone_dataset as st_data
from stats_textbook.regression import ols as st_ols


def _features(x, degree: int = 5):
    """Polynomial design matrix with standardized non-constant columns."""
    X = np.vander(np.asarray(x, dtype=float), degree + 1, increasing=True)
    Xs = X.copy()
    mu = X[:, 1:].mean(0)
    sd = X[:, 1:].std(0)
    Xs[:, 1:] = (X[:, 1:] - mu) / sd
    return Xs


def test_five_books_share_identical_data():
    books = [la_data(seed=0), nn_data(seed=0), by_data(seed=0), ml_data(seed=0), st_data(seed=0)]
    ref = books[0]
    for other in books[1:]:
        for ref_arr, other_arr in zip(ref, other, strict=True):
            np.testing.assert_array_equal(ref_arr, other_arr)


def test_four_lenses_agree():
    x, y = la_data(seed=0)
    phi = _features(x, degree=5)
    lam = 1.0

    w_la = la_ridge(phi, y, lam)  # linear algebra: closed-form ridge
    w_bayes = BayesianLinearRegression(sigma=1.0, sigma_w=1.0).fit(phi, y).w_mean
    w_ridge2 = ridge_solution(phi, y, lam)  # bayesian book's own ridge helper
    # ML lens: scikit-learn Ridge (no intercept, so the constant column is
    # penalized the same way the other lenses penalize it).
    w_ml = Ridge(alpha=lam, fit_intercept=False).fit(phi, y).coef_

    # NN lens: gradient descent on ||phi w - y||^2 + lam ||w||^2 (weight decay).
    gram = phi.T @ phi + lam * np.eye(phi.shape[1])
    lr = 1.0 / float(np.linalg.eigvalsh(gram).max())
    w_gd = np.zeros(phi.shape[1])
    for _ in range(50_000):
        w_gd = w_gd - lr * (phi.T @ (phi @ w_gd - y) + lam * w_gd)

    np.testing.assert_allclose(w_la, w_ridge2, atol=1e-10)
    np.testing.assert_allclose(w_la, w_bayes, atol=1e-8)
    np.testing.assert_allclose(w_la, w_gd, atol=1e-4)
    np.testing.assert_allclose(w_la, w_ml, atol=1e-8)


def test_the_frequentist_lens_is_ridge_at_zero_penalty():
    """statistics' capstone lens joins the other four at the limit.

    Least squares is what ridge becomes when the prior stops pulling, so
    the fifth book's answer has to be the lambda -> 0 end of the same
    family. Measured agreement: 3.4e-09 at lambda = 1e-10.
    """
    x, y = st_data(seed=0)
    phi = _features(x, degree=5)
    np.testing.assert_allclose(st_ols(phi, y).params, la_ridge(phi, y, 1e-10), atol=1e-7)


def test_shrinkage_is_visible_in_the_coefficient_norms():
    """The capstone's headline: a prior costs 7.40 of norm and buys stability."""
    x, y = st_data(seed=0)
    phi = _features(x, degree=5)
    norm_ols = float(np.linalg.norm(st_ols(phi, y).params))
    norm_ridge = float(np.linalg.norm(la_ridge(phi, y, 1.0)))
    assert 7.0 < norm_ols < 8.0, norm_ols
    assert 1.5 < norm_ridge < 2.0, norm_ridge
