"""Hull Tables22.9–11 rounded inputs; PCA independently checked by SVD."""

import numpy as np
import pytest
from hullkit import _market_risk as m
from scipy.stats import norm

# Source loadings rounded to 3dp; never silently orthogonalize published data.
LOADINGS = np.array(
    [
        [0.083, -0.242, 0.685, -0.682, -0.006, -0.025, -0.021, -0.004],
        [0.210, -0.465, 0.376, 0.574, -0.517, -0.031, 0.011, -0.008],
        [0.286, -0.467, 0.006, 0.185, 0.728, 0.347, 0.106, -0.074],
        [0.386, -0.315, -0.332, -0.145, 0.061, -0.604, -0.348, 0.361],
        [0.430, -0.099, -0.349, -0.265, -0.266, -0.008, 0.263, -0.688],
        [0.428, 0.119, -0.153, -0.172, -0.269, 0.515, 0.254, 0.589],
        [0.426, 0.394, 0.172, 0.099, 0.027, 0.244, -0.722, -0.205],
        [0.411, 0.478, 0.323, 0.204, 0.234, -0.434, 0.461, 0.036],
    ]
)
SD = np.array([11.54, 3.55, 1.78, 1.25, 0.91, 0.69, 0.62, 0.57])  # bp/day


def test_source_factor_variance_and_one_sd_rate_moves():
    result = m.pca_book(np.ones(8), LOADINGS, SD)
    assert result["market_variance"] == pytest.approx(152.5185)
    assert result["market_fraction"][:3] == pytest.approx([0.87315, 0.08263, 0.02077], abs=0.00001)
    assert sum(result["market_fraction"][:2]) == pytest.approx(0.956, abs=0.0005)
    assert LOADINGS[0, 0] * SD[0] == pytest.approx(0.96, abs=0.005)
    assert LOADINGS[1, 0] * SD[0] == pytest.approx(2.42, abs=0.005)
    assert LOADINGS.T @ LOADINGS == pytest.approx(np.eye(8), abs=0.002)


def test_source_book_with_printed_rounding_disagreement_preserved():
    # $m per bp on 2,3,5,7,10-year yields; remaining tenors have zero exposure.
    exposure = np.array([0, 10, 4, -8, -7, 2, 0, 0])
    result = m.pca_book(exposure, LOADINGS, SD, components=2)
    assert result["factor_exposures"][:2] == pytest.approx([-1.998, -3.067])
    assert result["risk"]["sigma"] == pytest.approx(25.49837, abs=0.000005)
    assert result["risk"]["var"] == pytest.approx(59.31808, abs=0.00001)
    # Source prints 25.45/59.2; original unrounded loadings are unavailable.
    assert abs(result["risk"]["var"] - 59.2) > 0.05
    scalar_variance = sum(
        (sum(exposure[i] * LOADINGS[i, j] for i in range(8)) * SD[j]) ** 2 for j in range(2)
    )
    assert result["risk"]["var"] == pytest.approx(norm.ppf(0.99) * np.sqrt(scalar_variance))


def test_eigen_fit_against_independent_svd_and_trace():
    raw = np.random.default_rng(229).normal(size=(600, 4)) @ np.array(
        [[2, 0, 0, 0], [0.2, 1, 0, 0], [0.3, 0.1, 0.5, 0], [0.1, 0.2, 0.3, 0.2]]
    )
    result = m.pca_fit(raw)
    centered = raw - raw.mean(axis=0)
    _, singular, right = np.linalg.svd(centered, full_matrices=False)
    assert result["factor_sd"] == pytest.approx(singular / np.sqrt(599))
    assert abs(result["loadings"]) == pytest.approx(abs(right.T), abs=1e-12)
    assert result["factor_sd"] @ result["factor_sd"] == pytest.approx(
        np.var(raw, axis=0, ddof=1).sum()
    )
    assert np.cov(result["scores"], rowvar=False) == pytest.approx(
        np.diag(result["factor_sd"] ** 2), abs=1e-12
    )
    assert result["scores"] @ result["loadings"].T + result["mean"] == pytest.approx(raw, abs=1e-12)


def test_basis_sign_invariance_and_rounded_loading_score_reconstruction():
    book = np.arange(8)
    base = m.pca_book(book, LOADINGS, SD, components=3)
    changed = LOADINGS.copy()
    changed[:, [0, 2, 5]] *= -1
    alternate = m.pca_book(book, changed, SD, components=3)
    assert alternate["risk"]["var"] == pytest.approx(base["risk"]["var"])
    scores = np.array([1, -2, 3, 4, 0, 1, 0.5, -0.2])
    moves = LOADINGS @ scores
    assert m.factor_scores(moves, LOADINGS) == pytest.approx(scores, abs=1e-12)


def test_small_market_factor_can_dominate_book_residual_risk():
    loading = np.eye(3)
    result = m.pca_book([0, 0, 1], loading, [10, 2, 0.2], components=2)
    assert sum(result["market_fraction"][:2]) > 0.999
    assert result["risk"]["sigma"] == 0
    assert result["full_variance"] == pytest.approx(0.04)
    assert result["residual_variance"] == pytest.approx(0.04)
    with pytest.raises(ValueError):
        m.pca_fit([[1, 2]])
