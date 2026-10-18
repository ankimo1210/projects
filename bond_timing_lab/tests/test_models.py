import numpy as np
import pytest
from bond_timing.models import EN_POINTS, en_grid, estimator, fit_predict, grid, ladder


def test_grid_is_a_sorted_cartesian_product():
    assert grid(b=(1, 2), a=(3,)) == ((("a", 3), ("b", 1)), (("a", 3), ("b", 2)))


def test_ladder_matches_the_design():
    specs = ladder()
    assert specs["nn_fm"].n_seeds == 20 and specs["nn_f"].n_seeds == 20
    assert len(specs["et"].grid) == 12 and len(specs["hgb"].grid) == 16
    assert len(specs["nn_fm"].grid) == 3 and len(specs["nn_f"].grid) == 3
    assert dict(specs["nn_fm"].grid[0])["hidden_layer_sizes"] == (32, 16)
    assert dict(specs["nn_f"].grid[0])["hidden_layer_sizes"] == (3,)
    assert {name: spec.inputs for name, spec in specs.items()} == {
        "ols_p": "P",
        "ols_pm": "PM",
        "cp": "F",
        "en": "FM",
        "et": "FM",
        "hgb": "FM",
        "nn_f": "F",
        "nn_fm": "FM",
    }
    assert ladder(5)["nn_fm"].n_seeds == 5


def test_en_grid_has_twenty_decreasing_alphas_per_l1_ratio():
    rng = np.random.default_rng(0)
    candidates = en_grid(rng.normal(size=(50, 4)), rng.normal(size=(50, 1)))
    assert len(candidates) == 3 * EN_POINTS
    alphas = [dict(c)["alpha"] for c in candidates[:EN_POINTS]]
    assert alphas == sorted(alphas, reverse=True)
    assert alphas[0] / alphas[-1] == pytest.approx(1000.0)


def test_ols_recovers_a_linear_rule():
    rng = np.random.default_rng(1)
    X, beta = rng.normal(size=(100, 3)), np.array([1.0, -2.0, 0.5])
    X_new = rng.normal(size=(5, 3))
    out = fit_predict("ols", (), 1, X, X @ beta + 1.0, X_new)
    np.testing.assert_allclose(out[:, 0], X_new @ beta + 1.0)


def test_models_predict_in_target_units_and_are_deterministic():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(120, 4))
    y = 1000.0 + X[:, 0] + rng.normal(0, 0.1, 120)
    params = (("max_depth", 2), ("max_features", 1.0), ("min_samples_leaf", 5))
    first = fit_predict("et", params, 1, X, y, X[:10])
    assert abs(first.mean() - 1000.0) < 2.0
    np.testing.assert_array_equal(first, fit_predict("et", params, 1, X, y, X[:10]))


def test_seed_average_differs_from_one_seed_and_repeats():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(80, 3))
    y = X[:, 0] + rng.normal(0, 0.1, 80)
    params = (("alpha", 1e-3), ("hidden_layer_sizes", (3,)))
    one = fit_predict("mlp", params, 1, X, y, X[:5])
    two = fit_predict("mlp", params, 2, X, y, X[:5])
    assert not np.allclose(one, two)
    np.testing.assert_array_equal(two, fit_predict("mlp", params, 2, X, y, X[:5]))


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError):
        estimator("svm", (), 0)
