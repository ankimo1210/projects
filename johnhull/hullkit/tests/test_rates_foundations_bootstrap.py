"""Hull Tables4.3/4.4 and independent linear/nonlinear calibration."""

import numpy as np
import pytest
from hullkit import _rates_foundations as r
from scipy.optimize import root

T = np.array([0.25, 0.5, 1, 1.5, 2])
P = np.array([99.6, 99, 97.8, 102.5, 105])
INST = [
    ([0.25], [100], 99.6),
    ([0.5], [100], 99),
    ([1], [100], 97.8),
    ([0.5, 1, 1.5], [2, 2, 102], 102.5),
    ([0.5, 1, 1.5, 2], [2.5, 2.5, 2.5, 102.5], 105),
]


def test_source_all_thirteen_values():
    curve = r.bootstrap_piecewise_zero(INST)
    assert 100 * curve[1] == pytest.approx([1.603, 2.010, 2.225, 2.284, 2.416], abs=0.0005)
    yields = [
        r.periodic_bond_yield(times, cash, price, frequency=m)
        for (times, cash, price), m in zip(INST, [4, 2, 1, 2, 2], strict=True)
    ]
    assert 100 * np.array(yields) == pytest.approx(
        [1.6064, 2.0202, 2.2495, 2.2949, 2.4238], abs=0.00005
    )
    assert np.exp(-1.5 * curve[1][3]) == pytest.approx(0.96631, abs=0.000005)
    assert 100 * np.interp(1.25, *curve) == pytest.approx(2.255, abs=0.0005)
    assert np.interp(2.5, [2.3, 2.7], [108, 109]) == pytest.approx(108.5)
    assert np.interp([0, 3], *curve) == pytest.approx([curve[1][0], curve[1][-1]])


def test_independent_discount_linear_solve():
    matrix = np.array(
        [
            [100, 0, 0, 0, 0],
            [0, 100, 0, 0, 0],
            [0, 0, 100, 0, 0],
            [0, 2, 2, 102, 0],
            [0, 2.5, 2.5, 2.5, 102.5],
        ]
    )
    df = np.linalg.solve(matrix, P)
    curve = r.bootstrap_piecewise_zero(INST)
    assert curve[1] == pytest.approx(-np.log(df) / T, abs=1e-11)


def test_independent_all_nodes_simultaneous_nonlinear_solve_for_coupon_gaps():
    # Explicit synthetic nonaligned coupons, not printed Hull inputs.
    knots = np.array([0.4, 1, 1.7])
    truth = np.array([0.02, 0.027, 0.033])
    schedules = [([0.4], [100]), ([0.5, 1], [3, 103]), ([0.7, 1.2, 1.7], [2, 2, 102])]
    prices = [
        np.dot(cf, np.exp(-np.interp(ts, knots, truth) * np.array(ts))) for ts, cf in schedules
    ]
    inst = [(ts, cf, p) for (ts, cf), p in zip(schedules, prices, strict=True)]
    curve = r.bootstrap_piecewise_zero(inst)

    def errors(z):
        return [
            np.dot(cf, np.exp(-np.interp(ts, knots, z) * np.array(ts))) - p for ts, cf, p in inst
        ]

    solve = root(errors, np.full(3, 0.025))
    assert solve.success
    assert curve[1] == pytest.approx(solve.x, abs=1e-10)
    assert curve[1] == pytest.approx(truth, abs=1e-10)
