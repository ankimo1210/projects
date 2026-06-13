"""Tests for la_book.decompositions and datasets."""

import numpy as np
import pytest
from la_book import datasets
from la_book import decompositions as dec


def test_lu_reconstructs():
    rng = np.random.default_rng(0)
    A = rng.standard_normal((5, 5))
    P, L, U = dec.lu(A)
    np.testing.assert_allclose(P @ L @ U, A, atol=1e-12)
    # L unit lower triangular, U upper triangular.
    np.testing.assert_allclose(np.tril(L), L, atol=1e-12)
    np.testing.assert_allclose(np.triu(U), U, atol=1e-12)


def test_qr_reconstructs_orthonormal():
    rng = np.random.default_rng(1)
    A = rng.standard_normal((6, 3))
    Q, R = dec.qr(A)
    np.testing.assert_allclose(Q @ R, A, atol=1e-12)
    np.testing.assert_allclose(Q.T @ Q, np.eye(3), atol=1e-12)


def test_cholesky_reconstructs():
    rng = np.random.default_rng(2)
    M = rng.standard_normal((4, 4))
    A = M @ M.T + 4 * np.eye(4)
    L = dec.cholesky(A)
    np.testing.assert_allclose(L @ L.T, A, atol=1e-10)


def test_svd_lowrank_rank_and_optimal_error():
    rng = np.random.default_rng(3)
    A = rng.standard_normal((10, 8))
    k = 3
    Ak = dec.svd_lowrank(A, k)
    assert np.linalg.matrix_rank(Ak, tol=1e-10) == k
    # Eckart-Young: Frobenius error equals sqrt of the tail singular values squared.
    s = np.linalg.svd(A, compute_uv=False)
    expected = np.sqrt((s[k:] ** 2).sum())
    assert np.linalg.norm(A - Ak, "fro") == pytest.approx(expected, rel=1e-10)


def test_lowrank_errors_decrease():
    img = datasets.make_test_image(64)
    errs = dec.lowrank_errors(img, ks=[1, 5, 10, 20])
    assert np.all(np.diff(errs) < 0)


def test_compression_ratio():
    assert dec.compression_ratio((100, 100), 10) == pytest.approx(10 * 201 / 10000)


def test_pca_matches_sklearn_up_to_sign():
    from sklearn.decomposition import PCA

    X = datasets.make_correlated_cloud(n=200, seed=0)
    ours = dec.pca_fit(X)
    ref = PCA(n_components=2).fit(X)
    np.testing.assert_allclose(ours.explained_variance, ref.explained_variance_, rtol=1e-10)
    for i in range(2):
        dot = abs(ours.components[i] @ ref.components_[i])
        assert dot == pytest.approx(1.0, abs=1e-10)


def test_pca_components_orthonormal_variance_sorted():
    X = datasets.make_correlated_cloud(n=300, seed=1)
    res = dec.pca_fit(X)
    np.testing.assert_allclose(res.components @ res.components.T, np.eye(2), atol=1e-10)
    assert res.explained_variance[0] >= res.explained_variance[1]
    assert res.explained_variance_ratio.sum() == pytest.approx(1.0)
    # Scores are the centered data expressed in the principal basis.
    np.testing.assert_allclose(res.scores, (X - res.mean) @ res.components.T, atol=1e-12)


def test_whiten_gives_identity_covariance():
    X = datasets.make_correlated_cloud(n=500, seed=2)
    Z, _ = dec.whiten(X)
    cov = Z.T @ Z / (len(Z) - 1)
    np.testing.assert_allclose(cov, np.eye(2), atol=1e-6)


def test_datasets_are_reproducible():
    a = datasets.make_asset_returns(n_days=50, seed=7)
    b = datasets.make_asset_returns(n_days=50, seed=7)
    np.testing.assert_allclose(a.to_numpy(), b.to_numpy())
    mats, curves = datasets.make_yield_curves(n_days=30)
    assert curves.shape == (30, len(mats))
    adj, labels = datasets.make_two_cluster_graph(n_per=8)
    assert adj.shape == (16, 16)
    assert labels.sum() == 8
    np.testing.assert_allclose(adj, adj.T)


def test_load_yield_curves_default_and_csv(tmp_path):
    from la_book.datasets import load_yield_curves

    mats, df = load_yield_curves()  # default = synthetic
    assert df.shape[1] == len(mats)
    # round-trip a user CSV through the hook
    csv = tmp_path / "yc.csv"
    df.head(5).to_csv(csv, index=False)
    mats2, df2 = load_yield_curves(path=csv)
    assert df2.shape == (5, df.shape[1])
    np.testing.assert_allclose(mats2, mats)
