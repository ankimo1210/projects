"""Hull Example23.3 and eq23.17; matrix updates vs direct weighted outer products."""

import numpy as np
import pytest
from hullkit import _volatility_estimation as v


def test_example_23_3_full_covariance_update():
    initial = np.array([[0.01**2, 0.6 * 0.01 * 0.02], [0.6 * 0.01 * 0.02, 0.02**2]])
    updated = v.covariance_forecasts([[0.005, 0.025]], initial, decay=0.95)[1]
    assert updated == pytest.approx(np.array([[0.00009625, 0.00012025], [0.00012025, 0.00041125]]))
    assert np.sqrt(np.diag(updated)) == pytest.approx([0.00981, 0.02028], abs=0.000005)
    assert v.correlation_from_covariance(updated)[0, 1] == pytest.approx(0.6044, abs=0.00005)


def test_matrix_forecasts_match_finite_outer_product_weights_and_no_lookahead():
    returns = np.array([[0.01, -0.02], [-0.03, 0.01], [0.005, -0.002]])
    initial, decay = np.eye(2) * 0.0004, 0.94
    result = v.covariance_forecasts(returns, initial, decay=decay)
    for n in range(1, 4):
        direct = decay**n * initial
        for j in range(n):
            direct += (1 - decay) * decay ** (n - 1 - j) * np.outer(returns[j], returns[j])
        assert result[n] == pytest.approx(direct)
        assert v.covariance_diagnostics(result[n])["is_psd"]
    other = returns.copy()
    other[-1] = 5
    assert v.covariance_forecasts(other, initial)[:-1] == pytest.approx(result[:-1])


def test_garch_covariance_intercept_and_ewma_limit():
    returns = np.array([[0.005, 0.025], [-0.02, 0.01]])
    initial = np.array([[0.0001, 0.00012], [0.00012, 0.0004]])
    omega = np.array([[0.000002, -0.0000005], [-0.0000005, 0.000003]])
    result = v.covariance_forecasts(returns, initial, omega=omega, alpha=0.13, beta=0.86)
    direct = initial.copy()
    for n, move in enumerate(returns):
        direct = omega + 0.13 * np.outer(move, move) + 0.86 * direct
        assert result[n + 1] == pytest.approx(direct)
    ewma = v.covariance_forecasts(returns, initial, decay=0.95)
    limit = v.covariance_forecasts(returns, initial, omega=np.zeros((2, 2)), alpha=0.05, beta=0.95)
    assert limit == pytest.approx(ewma)


def test_source_pairwise_valid_but_globally_inconsistent_matrix():
    matrix = np.array([[1, 0, 0.9], [0, 1, 0.9], [0.9, 0.9, 1]])
    weights = np.array([1, 1, -1])
    assert weights @ matrix @ weights == pytest.approx(-0.6)
    report = v.covariance_diagnostics(matrix)
    assert not report["is_psd"]
    assert report["minimum_eigenvalue"] == pytest.approx(-0.272792206)
    with pytest.raises(ValueError):
        v.covariance_forecasts([[0.1, 0.2, 0.3]], matrix)


def test_singular_psd_is_valid_and_zero_variance_correlation_undefined():
    matrix = np.array([[0.01, 0.01, 0], [0.01, 0.01, 0], [0, 0, 0]])
    assert v.covariance_diagnostics(matrix)["is_psd"]
    corr = v.correlation_from_covariance(matrix)
    assert corr[:2, :2] == pytest.approx(np.ones((2, 2)))
    assert np.isnan(corr[2]).all()
    assert np.isnan(corr[:, 2]).all()
