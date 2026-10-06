"""Hull Table4.2: independent yield iteration and par-price root."""

import numpy as np
import pytest
from hullkit import _rates_foundations as r
from scipy.optimize import brentq

T = np.array([0.5, 1, 1.5, 2])
Z = np.array([0.05, 0.058, 0.064, 0.068])
CF = np.array([3, 3, 3, 103])


def test_source_all_five_values():
    a = r.bond_quote(T, CF, Z)
    assert a["price"] == pytest.approx(98.39, abs=0.005)
    assert a["yield"] == pytest.approx(0.0676, abs=0.00005)
    assert a["final_discount"] == pytest.approx(0.87284, abs=0.000005)
    assert a["coupon_annuity"] == pytest.approx(3.70027, abs=0.000005)
    assert a["par_annual_coupon"] == pytest.approx(6.87, abs=0.005)


def test_independent_newton_yield_and_par_price_root():
    a = r.bond_quote(T, CF, Z)
    y = 0.06
    for _ in range(12):
        pv = CF * np.exp(-y * T)
        y += (pv.sum() - a["price"]) / (T @ pv)
    assert a["yield"] == pytest.approx(y, abs=1e-11)

    def par_error(coupon):
        cash = np.full(4, coupon / 2)
        cash[-1] += 100
        return np.sum(cash * np.exp(-Z * T)) - 100

    root = brentq(par_error, 0, 20)
    assert a["par_annual_coupon"] == pytest.approx(root, abs=1e-11)
