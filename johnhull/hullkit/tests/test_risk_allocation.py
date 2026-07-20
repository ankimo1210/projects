"""Tests for hullkit.risk_allocation: Euler marginal/component/incremental VaR and ES."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hullkit import risk, risk_allocation

# --- fixtures ----------------------------------------------------------

_CORR_5 = np.array(
    [
        [1.0, 0.4, 0.2, -0.1, 0.05],
        [0.4, 1.0, 0.3, 0.0, -0.2],
        [0.2, 0.3, 1.0, 0.25, 0.1],
        [-0.1, 0.0, 0.25, 1.0, 0.15],
        [0.05, -0.2, 0.1, 0.15, 1.0],
    ]
)


def _seeded_book(seed=7):
    rng = np.random.default_rng(seed)
    amounts = rng.uniform(-100.0, 100.0, size=5)
    vols = rng.uniform(0.01, 0.05, size=5)
    return amounts, vols, _CORR_5


# --- marginal_var_normal / component_var_normal ----------------------------


def test_component_var_normal_sums_to_normal_var():
    amounts, vols, corr = _seeded_book()
    alpha = 0.99
    components = risk_allocation.component_var_normal(amounts, vols, corr, alpha=alpha)
    sigma_p = risk.portfolio_sigma(amounts, vols, corr)
    expected = risk.normal_var(sigma_p, alpha)
    assert float(np.sum(components)) == pytest.approx(expected, abs=1e-12)


def test_marginal_var_normal_matches_finite_difference():
    amounts, vols, corr = _seeded_book()
    alpha = 0.99
    eps = 1e-6

    def var_of(a):
        sigma_p = risk.portfolio_sigma(a, vols, corr)
        return risk.normal_var(sigma_p, alpha)

    marginal = risk_allocation.marginal_var_normal(amounts, vols, corr, alpha=alpha)
    for i in range(len(amounts)):
        bumped_up = np.array(amounts, dtype=float)
        bumped_up[i] += eps
        bumped_down = np.array(amounts, dtype=float)
        bumped_down[i] -= eps
        fd = (var_of(bumped_up) - var_of(bumped_down)) / (2.0 * eps)
        assert marginal[i] == pytest.approx(fd, rel=1e-6)


def test_component_var_normal_equals_amounts_times_marginal():
    amounts, vols, corr = _seeded_book()
    marginal = risk_allocation.marginal_var_normal(amounts, vols, corr)
    component = risk_allocation.component_var_normal(amounts, vols, corr)
    assert component == pytest.approx(np.asarray(amounts) * marginal, abs=1e-12)


def test_marginal_var_normal_shape_mismatch_raises():
    amounts, vols, corr = _seeded_book()
    with pytest.raises(ValueError):
        risk_allocation.marginal_var_normal(amounts[:-1], vols, corr)
    with pytest.raises(ValueError):
        risk_allocation.marginal_var_normal(amounts, vols, corr[:-1, :-1])


def test_marginal_var_normal_empty_raises():
    with pytest.raises(ValueError):
        risk_allocation.marginal_var_normal([], [], [[]])


def test_component_var_normal_empty_raises():
    with pytest.raises(ValueError):
        risk_allocation.component_var_normal([], [], [[]])


# --- euler_es_components -----------------------------------------------


def test_euler_es_components_sums_to_historical_es():
    rng = np.random.default_rng(3)
    pnl_matrix = rng.standard_normal((400, 4)) * np.array([10.0, 5.0, 8.0, 3.0])
    alpha = 0.99
    components = risk_allocation.euler_es_components(pnl_matrix, alpha=alpha)
    total = pnl_matrix.sum(axis=1)
    _, es_total = risk.historical_var_es(total, alpha=alpha)
    assert float(np.sum(components)) == pytest.approx(es_total, abs=1e-12)


def test_euler_es_components_sums_to_historical_es_with_ties():
    # Duplicate the worst scenario row so the k=2 tail set spans a tie.
    rng = np.random.default_rng(11)
    base = rng.standard_normal((17, 4))
    worst_row = np.array([-50.0, -60.0, -40.0, -55.0])
    duplicated = np.tile(worst_row, (3, 1))
    pnl_matrix = np.vstack([base, duplicated])
    rng.shuffle(pnl_matrix)  # shuffles rows (axis=0) only
    alpha = 0.9  # n=20 -> k=2

    components = risk_allocation.euler_es_components(pnl_matrix, alpha=alpha)
    total = pnl_matrix.sum(axis=1)
    _, es_total = risk.historical_var_es(total, alpha=alpha)
    assert float(np.sum(components)) == pytest.approx(es_total, abs=1e-12)


def test_euler_es_components_empty_raises():
    with pytest.raises(ValueError):
        risk_allocation.euler_es_components(np.empty((0, 3)))
    with pytest.raises(ValueError):
        risk_allocation.euler_es_components(np.empty((3, 0)))


def test_euler_es_components_not_2d_raises():
    with pytest.raises(ValueError):
        risk_allocation.euler_es_components([1.0, 2.0, 3.0])


# --- incremental_var -----------------------------------------------------


def _diversification_book(seed=27, n_scen=5000):
    # roles: 0=dominant, 1=hedge (offsets dominant), 2,3=diversified baseline, 4=small uncorrelated
    rng = np.random.default_rng(seed)
    vols = np.array([60.0, 25.0, 20.0, 15.0, 3.0])
    corr = np.array(
        [
            [1.0, -0.35, 0.15, 0.05, 0.0],
            [-0.35, 1.0, 0.0, 0.0, 0.0],
            [0.15, 0.0, 1.0, 0.2, 0.0],
            [0.05, 0.0, 0.2, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        ]
    )
    cov = corr * np.outer(vols, vols)
    pnl_matrix = rng.multivariate_normal(mean=np.zeros(5), cov=cov, size=n_scen)
    return pnl_matrix


def test_incremental_var_small_uncorrelated_position_shows_diversification():
    pnl_matrix = _diversification_book()
    alpha = 0.99
    small_idx = 4
    inc_var = risk_allocation.incremental_var(pnl_matrix, small_idx, alpha=alpha)
    standalone_var, _ = risk.historical_var_es(pnl_matrix[:, small_idx], alpha=alpha)
    assert inc_var < standalone_var


def test_incremental_var_dominant_exceeds_hedged():
    pnl_matrix = _diversification_book()
    alpha = 0.99
    dominant_idx, hedge_idx = 0, 1
    inc_var_dominant = risk_allocation.incremental_var(pnl_matrix, dominant_idx, alpha=alpha)
    inc_var_hedge = risk_allocation.incremental_var(pnl_matrix, hedge_idx, alpha=alpha)
    assert inc_var_dominant > inc_var_hedge


def test_incremental_var_out_of_range_index_raises():
    pnl_matrix = _diversification_book(n_scen=100)
    with pytest.raises(ValueError):
        risk_allocation.incremental_var(pnl_matrix, 5)
    with pytest.raises(ValueError):
        risk_allocation.incremental_var(pnl_matrix, -1)


def test_incremental_var_empty_raises():
    with pytest.raises(ValueError):
        risk_allocation.incremental_var(np.empty((0, 3)), 0)


def test_incremental_var_not_2d_raises():
    with pytest.raises(ValueError):
        risk_allocation.incremental_var([1.0, 2.0, 3.0], 0)


# --- shared alpha validation ---------------------------------------------


def test_invalid_alpha_raises_across_api():
    amounts, vols, corr = _seeded_book()
    with pytest.raises(ValueError):
        risk_allocation.marginal_var_normal(amounts, vols, corr, alpha=0.0)
    with pytest.raises(ValueError):
        risk_allocation.component_var_normal(amounts, vols, corr, alpha=1.0)
    pnl_matrix = _diversification_book(n_scen=50)
    with pytest.raises(ValueError):
        risk_allocation.euler_es_components(pnl_matrix, alpha=1.5)
    with pytest.raises(ValueError):
        risk_allocation.incremental_var(pnl_matrix, 0, alpha=-0.1)


def test_non_finite_inputs_raise():
    amounts, vols, corr = _seeded_book()
    bad_amounts = np.array(amounts, dtype=float)
    bad_amounts[0] = math.nan
    with pytest.raises(ValueError):
        risk_allocation.marginal_var_normal(bad_amounts, vols, corr)

    pnl_matrix = _diversification_book(n_scen=50)
    bad_pnl = np.array(pnl_matrix, dtype=float)
    bad_pnl[0, 0] = math.inf
    with pytest.raises(ValueError):
        risk_allocation.euler_es_components(bad_pnl)
