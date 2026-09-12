"""Round-02 canonical pricing contract v2.0 (input/market_data/CONVENTIONS.md).

Independent checks: explicit schedule enumeration written from the contract text
(no call to ``schedule_times``), QuantLib 1.43 discount factors on continuous year
fractions (``FlatForward`` / ``DiscountCurve`` with ``Actual365Fixed``), and the
cases the contract requires: T shorter than one coupon period, on-grid, off-grid,
zero coupon, negative rates.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quantcurve.conventions import DEFAULT_STUB_RULE, ois_accruals, schedule_times
from quantcurve.curve import FunctionCurve
from quantcurve.instruments import build_instrument
from quantcurve.pricing import model_quote, pv_receiver
from quantcurve.risk import compute_risk

ql = pytest.importorskip("QuantLib")
REF = ql.Date(15, 1, 2026)


def v2_schedule(T: float, m: int) -> tuple[list[float], list[float]]:
    """Contract text: every k/m strictly before T, then T; alpha_i = t_i - t_{i-1}, t_0 = 0."""
    times, k = [], 1
    while k / m < T - 1e-12:
        times.append(k / m)
        k += 1
    times.append(T)
    acc = [times[0]] + [times[i] - times[i - 1] for i in range(1, len(times))]
    return times, acc


def test_default_rule_is_contract_v2():
    assert DEFAULT_STUB_RULE == "contract_v2"


@pytest.mark.parametrize(
    "T,m,times,acc",
    [
        (1.25, 1, [1.0, 1.25], [1.0, 0.25]),  # example from CONVENTIONS.md
        (0.2075, 2, [0.2075], [0.2075]),  # shorter than one coupon period
        (2.0, 1, [1.0, 2.0], [1.0, 1.0]),  # on-grid
        (2.8667, 2, [0.5, 1.0, 1.5, 2.0, 2.5, 2.8667], [0.5, 0.5, 0.5, 0.5, 0.5, 0.3667]),  # off-grid
        (1.0, 2, [0.5, 1.0], [0.5, 0.5]),
        (0.5, 1, [0.5], [0.5]),
    ],
)
def test_contract_schedule_examples(T, m, times, acc):
    t = schedule_times(T, m)
    a = ois_accruals(t, m)
    assert np.allclose(t, times) and np.allclose(a, acc)
    t2, a2 = v2_schedule(T, m)
    assert np.allclose(t, t2) and np.allclose(a, a2)


def test_no_rounding_of_T_times_m():
    # T*m = 2.999999 must still give three regular periods? No: 1.4999995*2 = 2.999999 < 3 -> [0.5, 1.0, 1.4999995]
    t = schedule_times(1.4999995, 2)
    assert np.allclose(t, [0.5, 1.0, 1.4999995])
    t = schedule_times(1.5000005, 2)
    assert np.allclose(t, [0.5, 1.0, 1.5, 1.5000005])


def _flat_curves():
    out = {}
    for r in (0.025, -0.01, 0.0):
        ql_curve = ql.FlatForward(REF, r, ql.Actual365Fixed(), ql.Continuous)
        out[r] = (ql_curve, FunctionCurve(lambda t, r=r: np.exp(-r * np.asarray(t, float))))
    return out


def test_quantlib_flat_forward_matches_function_curve_on_continuous_year_fractions():
    for r, (qc, fc) in _flat_curves().items():
        for t in (0.0833, 0.2075, 1.25, 2.8667, 17.05, 30.0):
            assert abs(qc.discount(t) - float(fc.discount(np.array([t]))[0])) < 1e-13
        if r < 0:
            assert qc.discount(5.0) > 1.0  # negative rates: D > 1 is valid under the contract


@pytest.mark.parametrize("r", [0.025, -0.01])
def test_bond_and_ois_prices_agree_with_independent_quantlib_discounting(r):
    qc, fc = _flat_curves()[r]
    for T, m, c in ((0.2075, 2, 0.03), (1.25, 1, 0.02), (2.8667, 2, 0.045), (10.0, 2, 0.0), (19.8617, 2, 0.015)):
        times, acc = v2_schedule(T, m)
        price_ind = sum(100.0 * c * a * qc.discount(t) for t, a in zip(times, acc)) + 100.0 * qc.discount(T)
        inst = build_instrument("b", "bond", T, 100.0, m, c)
        assert abs(model_quote(inst, fc) - price_ind) < 1e-9
        assert np.allclose(inst.amounts, [100.0 * c * a for a in acc])
        if c == 0.0:
            assert abs(model_quote(inst, fc) - 100.0 * qc.discount(T)) < 1e-12  # zero coupon
    for T in (0.0833, 0.2576, 1.303, 2.0, 2.8667, 7.1833, 30.0):
        m = 1 if T <= 2 else 2
        times, acc = v2_schedule(T, m)
        par_ind = (1.0 - qc.discount(T)) / sum(a * qc.discount(t) for t, a in zip(times, acc))
        inst = build_instrument("o", "ois_swap", T, 0.0, m)
        assert abs(model_quote(inst, fc) - par_ind) < 1e-13


def test_quantlib_discount_curve_daily_nodes_prices_offgrid_bond_like_function_curve():
    """Non-flat curve: a QuantLib DiscountCurve on daily nodes (log-linear) versus the analytic D(t)."""
    z = lambda t: 0.015 + 0.01 * (1 - np.exp(-np.asarray(t, float) / 3.0))
    D = lambda t: np.exp(-z(t) * np.asarray(t, float))
    dates = [REF + int(d) for d in range(0, 366 * 31, 1)]
    dfs = [float(D(d / 365.0)) if d > 0 else 1.0 for d in range(0, 366 * 31, 1)]
    qc = ql.DiscountCurve(dates, dfs, ql.Actual365Fixed())
    fc = FunctionCurve(D)
    T, m, c = 2.8667, 2, 0.045
    times, acc = v2_schedule(T, m)
    price_ql = sum(100.0 * c * a * qc.discount(t) for t, a in zip(times, acc)) + 100.0 * qc.discount(T)
    price_fc = model_quote(build_instrument("b", "bond", T, 100.0, m, c), fc)
    assert abs(price_ql - price_fc) < 1e-6  # daily log-linear interpolation error only


def test_receiver_pv_and_dv01_follow_contract_definitions():
    _, fc = _flat_curves()[0.025]
    # deposit PV = N((1+rT)D(T)-1) at par -> 0 ; bond PV = model price - trade price
    dep = build_instrument("d", "deposit", 0.5, (1 / float(fc.discount(np.array([0.5]))[0]) - 1) / 0.5)
    assert abs(pv_receiver(dep, fc)) < 1e-9
    inst = build_instrument("b", "bond", 2.8667, 100.0, 2, 0.045)
    risk = compute_risk([inst], fc)
    bumped_dn = FunctionCurve(lambda t: np.exp(-(0.025 - 1e-4) * np.asarray(t, float)))
    bumped_up = FunctionCurve(lambda t: np.exp(-(0.025 + 1e-4) * np.asarray(t, float)))
    dv01_ind = (model_quote(inst, bumped_dn) - model_quote(inst, bumped_up)) / 2.0
    assert abs(float(risk["dv01"].iloc[0]) - dv01_ind) < 1e-9
