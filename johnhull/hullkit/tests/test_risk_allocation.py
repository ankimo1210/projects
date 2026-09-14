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


def test_degenerate_portfolio_sigma_raises_instead_of_dividing_by_zero():
    vols = np.array([0.02, 0.02])
    perfect_hedge = np.array([[1.0, -1.0], [-1.0, 1.0]])
    flat_book = np.zeros(2)
    hedged_book = np.array([1.0, 1.0])
    assert risk.portfolio_sigma(flat_book, vols, np.eye(2)) == 0.0
    assert risk.portfolio_sigma(hedged_book, vols, perfect_hedge) == 0.0
    for amounts, corr in ((flat_book, np.eye(2)), (hedged_book, perfect_hedge)):
        with pytest.raises(ValueError, match="portfolio sigma must be finite and positive"):
            risk_allocation.marginal_var_normal(amounts, vols, corr)
        with pytest.raises(ValueError, match="portfolio sigma must be finite and positive"):
            risk_allocation.component_var_normal(amounts, vols, corr)

    # A non-PSD "correlation" gives a^T C a < 0, so sigma_P = sqrt(<0) is NaN;
    # the same guard rejects it through its isfinite half.
    not_psd = np.array([[1.0, 2.0], [2.0, 1.0]])
    with np.errstate(invalid="ignore"):
        assert math.isnan(risk.portfolio_sigma([1.0, -1.0], vols, not_psd))
        with pytest.raises(ValueError, match="portfolio sigma must be finite and positive"):
            risk_allocation.marginal_var_normal([1.0, -1.0], vols, not_psd)


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


def _tie_book(tie_first, tie_second):
    # n=20, alpha=0.9 -> k=2: the worst row (total -100) plus exactly one of two
    # distinct rows whose totals are both exactly -80.
    rng = np.random.default_rng(5)
    filler = rng.uniform(0.0, 1.0, size=(17, 3))
    worst = np.array([-60.0, -30.0, -10.0])
    return np.vstack(
        [filler[:5], tie_first, filler[5:9], worst, filler[9:14], tie_second, filler[14:]]
    )


def test_euler_es_components_stable_argsort_breaks_real_ties_by_row_order():
    tie_a = np.array([-50.0, -30.0, 0.0])
    tie_b = np.array([-20.0, -10.0, -50.0])
    worst = np.array([-60.0, -30.0, -10.0])
    a_first = _tie_book(tie_a, tie_b)
    b_first = _tie_book(tie_b, tie_a)
    for pnl_matrix in (a_first, b_first):
        totals = pnl_matrix.sum(axis=1)
        assert totals[5] == totals[16] == -80.0
        assert np.sort(totals)[1] == np.sort(totals)[2]  # the tie sits on the tail boundary

    components_a = risk_allocation.euler_es_components(a_first, alpha=0.9)
    components_b = risk_allocation.euler_es_components(b_first, alpha=0.9)
    # Stable argsort keeps the earlier row (index 5) of the tie in the tail set.
    np.testing.assert_array_equal(components_a, -(worst + tie_a) / 2.0)  # [55, 30, 5]
    np.testing.assert_array_equal(components_b, -(worst + tie_b) / 2.0)  # [40, 20, 30]
    # The allocation depends on the tie-break, the total ES does not.
    for pnl_matrix, components in ((a_first, components_a), (b_first, components_b)):
        _, es_total = risk.historical_var_es(pnl_matrix.sum(axis=1), alpha=0.9)
        assert float(np.sum(components)) == pytest.approx(es_total, abs=1e-12)
        assert es_total == pytest.approx(90.0, abs=1e-12)


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
