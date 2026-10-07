"""Hull Ex36.2 and independent CAPM beta with annualized sample volatility."""

import math

import numpy as np
import pytest
from hullkit import _real_options_foundations as r


def test_source_market_price_of_risk():
    assert r.capm_market_price(0.3, 0.05, 0.2) == pytest.approx(0.075)
    assert r.capm_market_price(0, 0.05, 0.2) == pytest.approx(0)


def test_independent_quarterly_covariance_and_ols_risk_premium():
    market = np.array([-3, -1, 1, 3.0])
    market = market / market.std(ddof=1) * 0.1
    residual = np.array([1, -1, -1, 1.0])
    residual = residual / residual.std(ddof=1) * 0.1
    sales = 0.3 * market + math.sqrt(1 - 0.3**2) * residual
    a = r.capm_risk_price_from_samples(sales, market, 0.05, periods_per_year=4)
    assert [a["correlation"], a["market_volatility"], a["lambda"]] == pytest.approx(
        [0.3, 0.2, 0.075], abs=1e-13
    )
    beta = np.linalg.lstsq(np.c_[np.ones(4), market], sales, rcond=None)[0][1]
    sales_volatility = sales.std(ddof=1) * math.sqrt(4)
    assert a["lambda"] == pytest.approx(beta * 0.05 / sales_volatility, abs=1e-13)
    with pytest.raises(ValueError, match="variance"):
        r.capm_risk_price_from_samples(sales, np.zeros(4), 0.05)
