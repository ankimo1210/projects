"""Hull Table7.5 credit-spread comparative argument."""

import pytest
from hullkit import _swap_foundations as s


def test_source_all_thirteen_comparative_outputs():
    direct = s.comparative_irs(0.04, 0.052, -0.001, 0.006, 0.0435, 0.0435)
    assert [
        direct[k]
        for k in [
            "fixed_gap",
            "floating_gap",
            "joint_gain",
            "a_effective_spread",
            "b_effective_fixed",
            "a_gain",
            "b_gain",
        ]
    ] == pytest.approx([0.012, 0.007, 0.005, -0.0035, 0.0495, 0.0025, 0.0025])
    dealer = s.comparative_irs(0.04, 0.052, -0.001, 0.006, 0.0433, 0.0437)
    assert [
        dealer[k]
        for k in ["a_effective_spread", "b_effective_fixed", "dealer_gain", "a_gain", "b_gain"]
    ] == pytest.approx([-0.0033, 0.0497, 0.0004, 0.0023, 0.0023])
    assert s.comparative_irs(0.04, 0.052, -0.001, 0.016, 0.0433, 0.0437)[
        "b_effective_fixed"
    ] == pytest.approx(0.0597)


def test_independent_external_and_swap_cash_and_gain_conservation():
    a = s.comparative_irs(0.04, 0.052, -0.001, 0.006, 0.0433, 0.0437)
    for market in [0.01, 0.05]:
        a_cash = 0.04 + market - 0.0433
        b_cash = market + 0.006 + 0.0437 - market
        dealer_cash = 0.0437 - 0.0433
        assert a_cash == pytest.approx(market + a["a_effective_spread"])
        assert b_cash == pytest.approx(a["b_effective_fixed"])
        assert dealer_cash == pytest.approx(a["dealer_gain"])
    assert a["a_gain"] + a["b_gain"] + a["dealer_gain"] == pytest.approx(a["joint_gain"])
