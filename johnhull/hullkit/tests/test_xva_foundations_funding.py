"""Hull §9.2 funding arithmetic and separately specified cash/IM accounts."""

import math

import numpy as np
import pytest
from hullkit import _xva_foundations as x
from scipy.integrate import quad


def test_source_all_four_funding_quote_values():
    a = x.funding_quote_arithmetic(0.03, 0.029, 0.01, -0.002, 0.001, 0.02, 0.035)
    assert [
        a["swap_margin_bp"],
        a["average_funding_bp"],
        a["marginal_funding_bp"],
        100 * a["merged_rate"],
    ] == pytest.approx([10, 120, 30, 2.75])


@pytest.mark.parametrize("balance", [1e6, -1e6])
def test_independent_discounted_interest_cash_and_signed_incremental_im(balance):
    times = np.linspace(0, 5, 1001)
    df = np.exp(-0.03 * times)
    a = x.funding_cash_costs(
        times,
        np.full(1001, balance),
        np.full(1001, -500000),
        funding_spread=0.01,
        benefit_spread=0.005,
        im_spread=0.012,
        discounts=df,
    )
    integral = quad(lambda t: math.exp(-0.03 * t), 0, 5)[0]
    fca = max(balance, 0) * 0.01 * integral
    fba = max(-balance, 0) * 0.005 * integral
    mva = -500000 * 0.012 * integral
    assert [a["fca"], a["fba"], a["mva"], a["fva"]] == pytest.approx(
        [fca, fba, mva, fca - fba], rel=1e-8, abs=1e-8
    )
    assert a["mva"] < 0
