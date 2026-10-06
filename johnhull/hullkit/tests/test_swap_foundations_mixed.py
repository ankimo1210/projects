"""Hull §7.10 construction inputs, with synthetic curves and independent decomposition."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s
from hullkit.rates import discount_factor

T = np.arange(0.5, 10.01, 0.5)
DC = (T, np.full(20, 0.03))
FC = (T, np.full(20, 0.04))
SPOT = 1.4


@pytest.mark.parametrize("dom_fixed", [0.03, None])
def test_source_constructed_cash_and_independent_auxiliary_fixed_decomposition(dom_fixed):
    direct = s.mixed_currency_value(T, 10e6, 7e6, DC, FC, SPOT, dom_fixed=dom_fixed, for_fixed=None)
    for aux in [0.04, 0.06]:
        tau = np.full(20, 0.5)
        dom_cash = s.currency_coupon_leg(10e6, T, DC, fixed_rate=dom_fixed)
        float_foreign = s.currency_coupon_leg(7e6, T, FC)
        fixed_foreign = 7e6 * aux * tau
        fixed_foreign[-1] += 7e6
        dd = np.array([discount_factor(float(t), DC) for t in T])
        fd = np.array([discount_factor(float(t), FC) for t in T])
        fixed_fixed = dom_cash @ dd - SPOT * (fixed_foreign @ fd)
        foreign_irs = SPOT * ((fixed_foreign - float_foreign) @ fd)
        assert direct["value"] == pytest.approx(fixed_fixed + foreign_irs, abs=1e-7)
        if dom_fixed is None:
            fixed_dom = 10e6 * 0.03 * tau
            fixed_dom[-1] += 10e6
            baseline = fixed_dom @ dd - SPOT * (fixed_foreign @ fd)
            domestic_irs = (dom_cash - fixed_dom) @ dd
            assert direct["value"] == pytest.approx(baseline + domestic_irs + foreign_irs, abs=1e-7)


def test_known_first_fixing_separate_from_future_forward():
    a = s.currency_coupon_leg(7e6, T, FC, first_fixing=0.05)
    future = s.currency_coupon_leg(7e6, T, FC)
    assert a[0] == pytest.approx(175000)
    assert a[1:] == pytest.approx(future[1:])
