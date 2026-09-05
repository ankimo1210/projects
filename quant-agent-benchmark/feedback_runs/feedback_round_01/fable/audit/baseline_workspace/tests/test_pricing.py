from __future__ import annotations

import numpy as np
import pytest

from quantcurve.curve import BSplineForwardCurve, PiecewiseLinearZeroCurve
from quantcurve.instruments import build_instrument, cash_flows
from quantcurve.pricing import SplineResidualEngine, analytic_dv01, dollar_duration, model_quote, pv_receiver, rate_residual


def flat(z: float) -> PiecewiseLinearZeroCurve:
    return PiecewiseLinearZeroCurve(np.array([1.0, 40.0]), np.array([z, z]))


def test_deposit_quote_and_pv_at_par():
    c = flat(0.02)
    T = 0.5
    r = (np.exp(0.02 * T) - 1) / T
    inst = build_instrument("d", "deposit", T, r)
    assert model_quote(inst, c) == pytest.approx(r)
    assert pv_receiver(inst, c) == pytest.approx(0.0, abs=1e-9)
    assert rate_residual(inst, c) == pytest.approx(0.0, abs=1e-14)


def test_ois_par_on_flat_curve_and_pv_sign():
    c = flat(0.03)
    inst = build_instrument("s", "ois_swap", 5.0, 0.0, frequency=2)
    D = np.exp(-0.03 * inst.times)
    par = (1 - D[-1]) / np.sum(0.5 * D)
    assert model_quote(inst, c) == pytest.approx(par)
    at_par = build_instrument("s", "ois_swap", 5.0, par, frequency=2)
    assert pv_receiver(at_par, c) == pytest.approx(0.0, abs=1e-9)
    higher = build_instrument("s", "ois_swap", 5.0, par + 0.001, frequency=2)
    assert pv_receiver(higher, c) > 0  # receiving a higher fixed rate is worth more


def test_bond_price_and_cash_flows():
    c = flat(0.02)
    inst = build_instrument("b", "bond", 2.0, 100.0, frequency=2, coupon_rate=0.04)
    times, amounts = cash_flows(inst)
    np.testing.assert_allclose(times, [0.5, 1.0, 1.5, 2.0])
    np.testing.assert_allclose(amounts, [2, 2, 2, 102])
    expected = np.sum(amounts * np.exp(-0.02 * times))
    assert model_quote(inst, c) == pytest.approx(expected)
    assert pv_receiver(inst, c) == pytest.approx(expected)
    assert dollar_duration(inst, c) == pytest.approx(np.sum(times * amounts * np.exp(-0.02 * times)))


def test_bond_rate_residual_sign():
    c = flat(0.02)
    inst = build_instrument("b", "bond", 5.0, 100.0, frequency=2, coupon_rate=0.02)
    fair = model_quote(inst, c)
    rich = build_instrument("b", "bond", 5.0, fair + 1.0, frequency=2, coupon_rate=0.02)
    assert rate_residual(rich, c) < 0  # market above model -> market yield below model


def test_engine_matches_generic_pricing_and_jacobian():
    curve = BSplineForwardCurve(np.array([0.5, 1, 2, 5, 10, 20]), 30.0)
    rng = np.random.default_rng(0)
    curve = curve.with_coeffs(0.02 + 0.004 * rng.standard_normal(curve.n_basis))
    insts = [
        build_instrument("d1", "deposit", 0.25, 0.014),
        build_instrument("s1", "ois_swap", 1.5, 0.0161, 1),
        build_instrument("s2", "ois_swap", 7.0, 0.0234, 2),
        build_instrument("s3", "ois_swap", 30.0, 0.0207, 2),
        build_instrument("b1", "bond", 6.11, 106.9, 2, 0.0355),
        build_instrument("b2", "bond", 29.5, 92.0, 2, 0.017),
    ]
    eng = SplineResidualEngine(curve, insts)
    r = eng.residuals(curve.coeffs)
    np.testing.assert_allclose(r, [rate_residual(i, curve) for i in insts], atol=1e-14)
    q = eng.model_quotes(curve.coeffs)
    np.testing.assert_allclose(q, [model_quote(i, curve) for i in insts], rtol=1e-12)
    J = eng.jacobian(curve.coeffs)
    Jfd = np.zeros_like(J)
    for k in range(curve.n_basis):
        e = np.zeros(curve.n_basis)
        e[k] = 1e-6
        Jfd[:, k] = (eng.residuals(curve.coeffs + e) - eng.residuals(curve.coeffs - e)) / 2e-6
    assert np.max(np.abs(J - Jfd)) < 1e-7 * max(1.0, np.max(np.abs(J)))


def test_analytic_dv01_matches_finite_difference():
    curve = BSplineForwardCurve(np.array([1, 5, 10, 20]), 30.0)
    curve = curve.with_coeffs(np.full(curve.n_basis, 0.025))
    for inst in (
        build_instrument("d", "deposit", 0.5, 0.02),
        build_instrument("s", "ois_swap", 10.0, 0.024, 2),
        build_instrument("b", "bond", 12.3, 101.0, 2, 0.03),
    ):
        up = pv_receiver(inst, curve.bumped(lambda t: np.full_like(t, 1e-4)))
        down = pv_receiver(inst, curve.bumped(lambda t: np.full_like(t, -1e-4)))
        fd = (down - up) / 2
        assert fd == pytest.approx(analytic_dv01(inst, curve), rel=1e-5)
        assert fd > 0


def test_build_instrument_validation():
    with pytest.raises(ValueError):
        build_instrument("x", "bond", 5.0, 100.0, 2, None)
    with pytest.raises(ValueError):
        build_instrument("x", "ois_swap", -1.0, 0.02, 1)
    with pytest.raises(ValueError):
        build_instrument("x", "future", 1.0, 0.02)
