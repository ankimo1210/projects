"""Hull Ch3 appendix CAPM numerical pins and independent factor laws."""

import numpy as np
import pytest
from hullkit import _futures_hedging as h


def test_source_capm_expected_returns():
    assert h.capm_expected_return(0.05, 0.13, [0, 0.75]) == pytest.approx([0.05, 0.11])


def test_independent_regression_and_two_state_portfolio_expectation():
    market = np.array([-0.1, 0, 0.1, 0.2])
    asset = 0.02 + 0.75 * market
    estimated = h.regression_beta(asset, market)
    ols = np.linalg.lstsq(np.c_[np.ones(4), market], asset, rcond=None)[0][1]
    assert estimated == pytest.approx(ols)
    beta = h.portfolio_beta([0.4, 0.6], [0.75, 1.5])
    portfolio = 0.4 * asset + 0.6 * (0.03 + 1.5 * market)
    assert beta == pytest.approx(np.cov(portfolio, market, ddof=1)[0, 1] / np.var(market, ddof=1))
    states = np.array([-0.07, 0.23])
    probs = np.array([0.25, 0.75])
    expected_market = np.dot(probs, states)
    cash_returns = 0.05 + beta * (states - 0.05)
    assert h.capm_expected_return(0.05, expected_market, beta) == pytest.approx(
        probs @ cash_returns
    )
