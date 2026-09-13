"""Tests for hullkit.credit_portfolio: Hull Examples 25.2/25.3, Table 25.8, copula identities."""

from itertools import pairwise

import numpy as np
import pytest
from hullkit import cds, credit
from hullkit import credit_portfolio as cp
from scipy.stats import binom, norm

EX_25_2 = dict(
    recovery=0.4, r=0.035, maturity=5.0, attach=0.03, detach=0.06, n_names=125, rho=0.15, freq=4
)


@pytest.fixture(scope="module")
def mezz():
    lam = cds.implied_hazard(0.0050, 0.4, 0.035, 5.0, freq=4)
    return lam, cp.cdo_tranche_valuation(lam, **EX_25_2)


def _node_index(nodes, value):
    return int(np.argmin(np.abs(nodes - value)))


def test_gauss_hermite_nodes_match_table_25_7():
    nodes, weights = cp.gauss_hermite_factor(60)
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    for value, weight in (
        (0.2020, 0.1579),
        (-0.2020, 0.1579),
        (-0.6060, 0.1342),
        (-1.0104, 0.0969),
    ):
        i = _node_index(nodes, value)
        assert nodes[i] == pytest.approx(value, abs=5e-5)
        assert weights[i] == pytest.approx(weight, abs=5e-5)


def test_conditional_default_prob_matches_credit_module():
    q, rho, f = 0.05, 0.3, -1.0
    assert cp.conditional_default_prob(q, rho, f) == pytest.approx(
        credit.gaussian_copula_conditional(q, np.sqrt(rho), f), abs=1e-12
    )


def test_binomial_pmf_is_stable_and_matches_scipy():
    pmf = cp.binomial_pmf(125, np.array([0.0, 0.02, 1.0]))
    assert pmf.shape == (3, 126)
    np.testing.assert_allclose(pmf.sum(axis=1), 1.0, atol=1e-12)
    np.testing.assert_allclose(pmf[1], binom.pmf(np.arange(126), 125, 0.02), atol=1e-14)
    assert pmf[0, 0] == pytest.approx(1.0, abs=1e-12)
    assert pmf[2, 125] == pytest.approx(1.0, abs=1e-12)


def test_heterogeneous_recursion_equals_binomial_when_homogeneous():
    p = np.full((3, 10), 0.07)
    p[1] = 0.3
    pmf = cp.heterogeneous_default_pmf(p)
    np.testing.assert_allclose(pmf[0], binom.pmf(np.arange(11), 10, 0.07), atol=1e-12)
    np.testing.assert_allclose(pmf[1], binom.pmf(np.arange(11), 10, 0.3), atol=1e-12)
    mixed = cp.heterogeneous_default_pmf(np.array([0.1, 0.5]))
    np.testing.assert_allclose(mixed, [0.45, 0.5, 0.05], atol=1e-12)


def test_example_25_2_hazard_and_conditional_columns(mezz):
    lam, val = mezz
    assert lam == pytest.approx(0.0083, abs=5e-5)
    cols = [_node_index(val.factor_nodes, v) for v in (0.2020, -0.2020, -0.6060, -1.0104)]
    np.testing.assert_allclose(
        val.expected_principal[cols, 19], [0.9953, 0.9687, 0.8636, 0.6134], atol=5e-5
    )
    np.testing.assert_allclose(
        val.expected_principal[cols, 20], [0.9936, 0.9600, 0.8364, 0.5648], atol=5e-5
    )
    np.testing.assert_allclose(
        val.annuity_by_factor[cols], [4.5624, 4.5345, 4.4080, 4.0361], atol=5e-5
    )
    np.testing.assert_allclose(
        val.accrual_by_factor[cols], [0.0007, 0.0043, 0.0178, 0.0478], atol=5e-5
    )
    np.testing.assert_allclose(
        val.protection_by_factor[cols], [0.0055, 0.0346, 0.1423, 0.3823], atol=5e-5
    )


def test_example_25_2_unconditional_legs_and_spread(mezz):
    _, val = mezz
    assert val.annuity == pytest.approx(4.2846, abs=5e-5)
    assert val.accrual == pytest.approx(0.0187, abs=5e-5)
    assert val.protection == pytest.approx(0.1496, abs=5e-5)
    assert val.spread * 1e4 == pytest.approx(348.0, abs=1.0)
    assert val.expected_principal[:, 0].min() == 1.0
    assert np.all(np.diff(val.expected_principal, axis=1) <= 1e-15)  # non-increasing in time
    order = np.argsort(val.factor_nodes)
    assert np.all(np.diff(val.expected_principal[order, -1]) >= -1e-15)  # non-decreasing in F


def test_capital_structure_loss_conservation(mezz):
    lam, _ = mezz
    bounds = [0.0, 0.03, 0.06, 0.09, 0.12, 0.22, 1.0]
    total = 0.0
    for lo, hi in pairwise(bounds):
        total += (hi - lo) * cp.cdo_tranche_valuation(
            lam, 0.4, 0.035, 5.0, lo, hi, 125, 0.15
        ).protection
    whole = cp.cdo_tranche_valuation(lam, 0.4, 0.035, 5.0, 0.0, 1.0, 125, 0.15).protection
    assert total == pytest.approx(whole, abs=1e-12)


def test_example_25_3_third_to_default():
    val = cp.kth_to_default_valuation(3, 10, 0.02, 0.4, 0.05, 5.0, rho=0.3, freq=1)
    i = _node_index(val.factor_nodes, -1.0104)
    np.testing.assert_allclose(
        val.cumulative_prob[i, 1:], [0.0047, 0.0335, 0.0928, 0.1757, 0.2717], atol=5e-5
    )
    assert val.payoff_by_factor[i] == pytest.approx(0.1379, abs=5e-5)
    assert val.annuity_by_factor[i] == pytest.approx(3.8443, abs=5e-5)
    assert val.accrual_by_factor[i] == pytest.approx(0.1149, abs=5e-5)
    assert val.payoff == pytest.approx(0.0629, abs=5e-5)
    assert val.annuity == pytest.approx(4.0580, abs=5e-5)
    assert val.accrual == pytest.approx(0.0524, abs=5e-5)
    assert val.spread * 1e4 == pytest.approx(153.0, abs=1.0)
    spreads = [cp.kth_to_default_spread(k, 10, 0.02, 0.4, 0.05, 5.0, 0.3) for k in range(1, 6)]
    assert np.all(np.diff(spreads) < 0.0)


def test_table_25_8_compound_and_base_correlations():
    lam = cds.implied_hazard(0.0023, 0.4, 0.03, 5.0, freq=4)
    assert lam == pytest.approx(0.00382, abs=5e-6)
    quotes = [0.1034, 41.59e-4, 11.95e-4, 5.60e-4, 2.00e-4]
    bounds = [0.0, 0.03, 0.06, 0.09, 0.12, 0.22]
    result = cp.base_correlations(quotes, bounds, lam, 0.4, 0.03, 5.0, 125)
    np.testing.assert_allclose(result.compound * 100, [17.7, 7.8, 14.0, 18.2, 23.3], atol=0.15)
    np.testing.assert_allclose(result.base * 100, [17.7, 28.4, 36.5, 43.2, 60.5], atol=0.15)
    # implied correlations reprice the market quotes
    equity = cp.cdo_tranche_valuation(lam, 0.4, 0.03, 5.0, 0.0, 0.03, 125, result.compound[0])
    assert equity.upfront(0.05) == pytest.approx(0.1034, abs=1e-6)
    for lo, hi, rho, quote in zip(
        bounds[1:-1], bounds[2:], result.compound[1:], quotes[1:], strict=True
    ):
        assert cp.cdo_tranche_spread(lam, 0.4, 0.03, 5.0, lo, hi, 125, rho) == pytest.approx(
            quote, abs=1e-8
        )
    curve = cp.expected_loss_curve(bounds[1:], result.base, lam, 0.4, 0.03, 5.0, 125)
    np.testing.assert_allclose(curve, result.cumulative_expected_loss, atol=1e-8)
    # Hull: the 0–X% expected loss increases with X at a decreasing rate (slopes over ΔX fall)
    slopes = np.diff(curve) / np.diff(bounds[1:])
    assert np.all(np.diff(curve) > 0.0) and np.all(np.diff(slopes) < 0.0)


def test_double_t_limits_to_gaussian_and_threshold_is_consistent():
    q, rho = 0.04, 0.15
    assert cp.double_t_threshold(q, rho, nu=1e6) == pytest.approx(norm.ppf(q), abs=1e-4)
    nodes, weights = cp.double_t_factor_quadrature(4.0, 200)
    x_star = cp.double_t_threshold(q, rho, 4.0)
    unconditional = float(weights @ cp.double_t_conditional_prob(q, rho, nodes, 4.0))
    assert unconditional == pytest.approx(q, abs=1e-6)  # E_F[Q(t|F)] = Q(t)
    assert abs(x_star - norm.ppf(q)) > 1e-3
    args = (0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    gaussian = cp.cdo_tranche_spread(*args)
    limit = cp.cdo_tranche_spread(*args, copula="double_t", nu=1e6)
    assert abs(limit - gaussian) * 1e4 < 0.5
    fat = cp.cdo_tranche_spread(*args, copula="double_t", nu=4.0)
    assert abs(fat - gaussian) > 1e-4


def test_heterogeneous_hazards_reduce_to_homogeneous_valuation():
    hom = cp.cdo_tranche_valuation(0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    het = cp.cdo_tranche_valuation(np.full(125, 0.0083), 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    assert het.spread == pytest.approx(hom.spread, abs=1e-12)
    skewed = cp.cdo_tranche_valuation(
        np.linspace(0.002, 0.0146, 125), 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15
    )
    assert abs(skewed.spread - hom.spread) > 1e-4


def test_validation_errors():
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.06, 0.03, 125, 0.15)
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.03, 0.06, 125, 1.0)
    with pytest.raises(ValueError):
        cp.kth_to_default_valuation(0, 10, 0.02, 0.4, 0.05, 5.0, 0.3)
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.03, 0.06, 125, 0.15, copula="clayton")
    with pytest.raises(ValueError):
        cp.double_t_threshold(0.05, 0.2, nu=2.0)
    with pytest.raises(ValueError):
        cp.base_correlations([0.1, 0.01], [0.01, 0.03, 0.06], 0.01, 0.4, 0.03, 5.0, 125)
