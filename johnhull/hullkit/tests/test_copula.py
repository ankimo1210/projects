"""Tests for hullkit.copula (one-factor Gaussian copula / portfolio loss).

Correlation leaves the marginal default probability unchanged but fattens the tail
of the pool-loss distribution — the heart of the 2008 CDO story.
"""

import numpy as np
from hullkit import copula


def test_correlation_leaves_marginal_default_unchanged():
    pd = 0.05
    for rho in (0.0, 0.3, 0.6):
        loss = copula.portfolio_loss_samples(
            pd, rho, n_names=100, n_sims=40_000, rng=np.random.default_rng(1)
        )
        assert abs(loss.mean() - pd) < 5e-3, rho


def test_correlation_fattens_the_tail():
    pd = 0.05
    lo = copula.portfolio_loss_samples(
        pd, 0.0, n_names=100, n_sims=40_000, rng=np.random.default_rng(1)
    )
    hi = copula.portfolio_loss_samples(
        pd, 0.5, n_names=100, n_sims=40_000, rng=np.random.default_rng(1)
    )
    assert hi.var() > 3 * lo.var()  # correlation greatly widens the loss distribution
    # independent pool variance matches the binomial value pd(1-pd)/n
    assert abs(lo.var() - pd * (1 - pd) / 100) < 1e-4


def test_conditional_default_increases_in_bad_factor():
    bad = copula.conditional_default_prob(0.05, 0.3, -2.0)
    good = copula.conditional_default_prob(0.05, 0.3, 2.0)
    assert bad > good
    assert 0.0 < good < bad < 1.0


def test_vasicek_cdf_is_monotonic_and_bounded():
    pd, rho = 0.05, 0.2
    c_lo = copula.vasicek_loss_cdf(0.01, pd, rho)
    c_hi = copula.vasicek_loss_cdf(0.30, pd, rho)
    assert 0.0 <= c_lo < c_hi <= 1.0
