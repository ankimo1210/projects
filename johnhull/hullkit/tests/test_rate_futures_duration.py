"""Hull Example6.6 duration hedge and independent price revaluation."""

import math

import pytest
from hullkit import _rate_futures as f
from scipy.optimize import brentq


def test_source_four_duration_hedge_values():
    quote = f.parse_32nds("93-02")
    contract = quote * 1000
    a = f.duration_futures_hedge(1e7, 6.8, contract, 9.2)
    assert [quote, contract, a["short_contracts"], a["rounded"]] == pytest.approx(
        [93.0625, 93062.5, 79.42, 79], abs=0.005
    )


def test_independent_full_revaluation_hedge_root_and_ctd_change():
    p, vf, dp, df = 1e7, 93062.5, 6.8, 9.2
    eps = 1e-5

    def residual(n):
        portfolio = p * (math.exp(-dp * eps) - math.exp(dp * eps))
        futures = vf * (math.exp(-df * eps) - math.exp(df * eps))
        return portfolio - n * futures

    numerical = brentq(residual, 0, 200)
    a = f.duration_futures_hedge(p, dp, vf, df)
    assert a["short_contracts"] == pytest.approx(numerical, rel=1e-8)
    assert f.duration_futures_hedge(p, dp, vf, 8)["short_contracts"] > a["short_contracts"]
    # A rate change in the portfolio bucket alone remains unhedged.
    assert abs(p * (math.exp(-dp * 0.001) - 1)) > 1000
