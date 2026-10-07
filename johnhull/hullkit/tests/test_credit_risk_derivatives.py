"""Hull §24.7: special-case pins, shared paths, lagged collateral and explicit factor coupling."""

import math

import numpy as np
import pytest
from hullkit import _credit_risk as c
from scipy.integrate import quad
from scipy.stats import norm


def test_source_example_24_4_four_collateral_branches_and_netting():
    values = np.array([50, 50, -50, -50])[:, None, None]
    lagged = np.array([45, 55, -45, -55])[:, None]
    result = c.path_credit_adjustments(values, [1], [0.02], recovery=0.4, lagged_values=lagged)
    assert result["positive"][:, 0] == pytest.approx([5, 0, 0, 5])
    trades = np.array([10, 30, -25])[None, None, :]
    net = c.path_credit_adjustments(trades, [1], [0.02])
    gross = c.path_credit_adjustments(trades, [1], [0.02], netting=False)
    assert net["ee"][0] == 15
    assert gross["ee"][0] == 40
    ranks = c.path_credit_adjustments(np.arange(10000)[:, None, None], [1], [0.02])
    assert ranks["pfe"][0] == 9750  # 250th worst of 10000 at 97.5%


def test_source_example_24_5_bond_ratio_and_hazard_approximation():
    result = c.single_payoff_credit_value(3, 0.015, 2, 0.4)
    assert result["bond_ratio_value"] == pytest.approx(2.9113366, abs=1e-7)
    assert result["hazard_value"] == pytest.approx(2.912213, abs=1e-6)
    assert result["bond_ratio_value"] == pytest.approx(2.91, abs=0.005)
    zero = c.single_payoff_credit_value(3, 0.015, 2, 0)
    assert zero["hazard_value"] == pytest.approx(zero["bond_ratio_value"])


def test_source_example_24_6_all_seven_values_and_independent_payoff_integral():
    result = c.forward_credit_value(1600, 1500, 0.2, 0.05, 2, [0.5, 1.5], [0.02, 0.03], 0.3)
    assert result["d1"][0] == pytest.approx(0.5271, abs=0.00005)
    assert result["d2"][0] == pytest.approx(0.3856, abs=0.00005)
    assert result["discounted_lgd_exposure"] == pytest.approx([92.67, 130.65], abs=0.005)
    assert result["cva"] == pytest.approx(5.77, abs=0.005)
    assert result["no_default_value"] == pytest.approx(90.48, abs=0.005)
    assert result["value"] == pytest.approx(84.71, abs=0.005)
    for time, exposure in zip([0.5, 1.5], result["discounted_lgd_exposure"], strict=True):
        sd = 0.2 * math.sqrt(time)
        cutoff = (math.log(1500 / 1600) + sd * sd / 2) / sd
        reference = (
            math.exp(-0.1)
            * 0.7
            * quad(
                lambda z, sd=sd: (1600 * math.exp(-sd * sd / 2 + sd * z) - 1500) * norm.pdf(z),
                cutoff,
                12,
            )[0]
        )
        assert exposure == pytest.approx(reference, rel=1e-10)


def test_shared_gbm_forward_paths_match_analytic_cva_with_six_standard_errors():
    def forward(spots, time):
        return spots[:, 0] - 1500 * np.exp(-0.05 * (2 - time))

    paths = c.gbm_book_paths(
        [1600 * np.exp(-0.1)],
        [0.2],
        [[1]],
        [0.5, 1.5],
        [forward],
        drifts=[0.05],
        samples=120000,
        seed=247,
    )
    result = c.path_credit_adjustments(
        paths["values"], [0.5, 1.5], [0.02, 0.03], recovery=0.3, rate=0.05
    )
    analytic = c.forward_credit_value(1600, 1500, 0.2, 0.05, 2, [0.5, 1.5], [0.02, 0.03], 0.3)
    assert result["cva"] == pytest.approx(analytic["cva"], abs=6 * result["cva_se"])
    assert paths["spots"].shape == (120000, 2, 1)


def test_zero_lag_zero_risk_and_cure_period_excess_posted_collateral():
    values = np.array([[[10], [30], [-25]], [[-10], [-30], [25]]])
    zero = c.path_credit_adjustments(values, [0, 1, 2], [0, 0.02, 0.03], collateral_lag=0)
    assert zero["cva"] == 0
    assert zero["positive"] == pytest.approx(np.zeros((2, 3)))
    lag = c.path_credit_adjustments(values, [0, 1, 2], [0, 0.02, 0.03], collateral_lag=1)
    assert lag["positive"] == pytest.approx(np.array([[10, 20, 0], [0, 0, 55]]))
    assert lag["negative"] == pytest.approx(np.array([[0, 0, 55], [10, 20, 0]]))


def test_incremental_netting_uses_same_paths_and_gross_is_additive():
    base = np.array([10, -10, 30])[:, None, None]
    added = np.array([-8, 20, -25])[:, None, None]
    total = np.concatenate([base, added], axis=2)
    before = c.path_credit_adjustments(base, [1], [0.02])
    after = c.path_credit_adjustments(total, [1], [0.02])
    incremental = c.incremental_credit_adjustment(base, added, [1], [0.02])
    assert incremental["cva"] == pytest.approx(after["cva"] - before["cva"])
    assert incremental["cva"] < 0  # new trade hedges existing positive exposure
    gross = c.path_credit_adjustments(total, [1], [0.02], netting=False)
    standalone = c.path_credit_adjustments(added, [1], [0.02])
    assert gross["cva"] == pytest.approx(before["cva"] + standalone["cva"])


def test_explicit_wrong_right_way_factor_weights_against_independent_quadrature():
    factors = np.random.default_rng(248).normal(size=120000)
    exposure = np.exp(0.5 * factors)[:, None, None]
    results = []
    for loading in [-0.5, 0, 0.5]:
        probabilities = c.conditional_event_weights([0.02], factors, loading)
        result = c.path_credit_adjustments(exposure, [1], probabilities, recovery=0.4)
        reference = (
            0.6
            * quad(
                lambda f, loading=loading: (
                    math.exp(0.5 * f)
                    * norm.cdf((norm.ppf(0.02) - loading * f) / math.sqrt(1 - loading**2))
                    * norm.pdf(f)
                ),
                -10,
                10,
            )[0]
        )
        assert result["cva"] == pytest.approx(reference, abs=6 * result["cva_se"])
        results.append(result["cva"])
    assert results[0] > results[1] > results[2]
