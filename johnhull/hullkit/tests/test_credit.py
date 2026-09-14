"""Tests for hullkit.credit against Hull 11e Ch.24/25 examples."""

import math

import pytest
from hullkit import credit
from scipy.stats import norm


def test_survival_and_default_constant_hazard():
    assert credit.survival_prob(2.0, 0.02) == pytest.approx(math.exp(-0.04), abs=1e-12)
    assert credit.default_prob(2.0, 0.02) == pytest.approx(1.0 - math.exp(-0.04), abs=1e-12)
    assert credit.survival_prob(0.0, 0.05) == pytest.approx(1.0)


def test_hazard_from_spread():
    assert credit.hazard_from_spread(0.012, 0.4) == pytest.approx(0.02, abs=1e-12)


def test_cds_spread_near_lambda_times_loss():
    s = credit.cds_spread(0.02, 0.4, 0.05, 5.0, freq=4)
    assert s == pytest.approx(0.012075, abs=5e-5)
    assert 0.0119 < s < 0.0121  # close to lambda(1-R)=0.012


def test_merton_example_24_3():
    v0, sig_v, q = credit.merton_default_prob(3.0, 0.80, 10.0, 0.05, 1.0)
    assert v0 == pytest.approx(12.3954, abs=2e-3)
    assert sig_v == pytest.approx(0.21230, abs=5e-4)
    assert q == pytest.approx(0.12697, abs=5e-4)  # Hull 12.7%


def test_merton_non_convergence_does_not_return_negative_asset_volatility():
    with pytest.raises(ValueError, match="did not converge"):
        credit.merton_default_prob(1.0, 0.01, 100.0, 0.05, 1.0)


def test_gaussian_copula_conditional_monotonic():
    q = 0.05
    a = 0.5
    pd_low_f = credit.gaussian_copula_conditional(q, a, -2.0)  # bad systemic state
    pd_high_f = credit.gaussian_copula_conditional(q, a, 2.0)  # good systemic state
    assert pd_low_f > q > pd_high_f
    assert credit.gaussian_copula_conditional(q, 0.0, 5.0) == pytest.approx(q, abs=1e-12)


def test_cds_spread_zero_periods_raises():
    # maturity=0.02, freq=4 -> round(0.02*4)=round(0.08)=0 -> should raise
    with pytest.raises(ValueError, match=r"maturity.*freq.*1 period"):
        credit.cds_spread(0.02, 0.4, 0.05, 0.1, freq=4)


def test_vasicek_credit_var():
    q, rho = 0.02, 0.1
    v999 = credit.vasicek_credit_var(q, rho, 0.999)
    assert v999 > q  # tail loss exceeds the mean PD
    # monotone in confidence and correlation
    assert credit.vasicek_credit_var(q, rho, 0.99) < v999
    assert credit.vasicek_credit_var(q, 0.3, 0.999) > v999
    # sanity vs closed form
    expected = norm.cdf((norm.ppf(q) + math.sqrt(rho) * norm.ppf(0.999)) / math.sqrt(1.0 - rho))
    assert v999 == pytest.approx(expected, abs=1e-12)


def test_vasicek_credit_var_hull_example_24_8():
    """Hull 11e GE Example 24.8: $100M retail book, PD 2%, R 60%, rho 0.1.

    The 99.9% worst-case default rate prints as 0.128 and the 1-year 99.9% credit
    VaR as $5.13M (100 x 0.128 x 0.4 = 5.12 with the rounded rate; the unrounded
    0.1282 gives 5.13).
    """
    worst_case_rate = credit.vasicek_credit_var(0.02, 0.1, 0.999)
    assert worst_case_rate == pytest.approx(0.128, abs=5e-4)
    credit_var_millions = 100.0 * worst_case_rate * (1.0 - 0.6)
    assert credit_var_millions == pytest.approx(5.13, abs=5e-3)
