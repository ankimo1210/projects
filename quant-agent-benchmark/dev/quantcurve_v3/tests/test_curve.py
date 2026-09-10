from __future__ import annotations

import numpy as np
import pytest

from quantcurve.curve import BSplineForwardCurve, BumpedCurve, PiecewiseLinearZeroCurve, parallel_bump, tent_bump


@pytest.fixture
def spline():
    c = BSplineForwardCurve(np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25]), 30.0)
    rng = np.random.default_rng(3)
    return c.with_coeffs(0.02 + 0.006 * rng.standard_normal(c.n_basis))


def test_discount_at_zero_is_one(spline):
    assert spline.discount(np.array([0.0]))[0] == pytest.approx(1.0)


def test_forward_is_minus_dlogD(spline):
    t = np.array([0.3, 1.7, 9.9, 24.0, 29.5])
    h = 1e-5
    fd = -(spline.log_discount(t + h) - spline.log_discount(t - h)) / (2 * h)
    np.testing.assert_allclose(spline.forward(t), fd, atol=1e-7)


def test_negative_forwards_keep_discount_positive():
    c = BSplineForwardCurve(np.array([1, 5, 10, 20]), 30.0)
    c = c.with_coeffs(np.full(c.n_basis, -0.02))
    t = np.linspace(0, 40, 200)
    assert np.all(c.discount(t) > 0)
    assert np.all(c.zero(t) < 0)
    assert np.all(c.discount(t)[1:] > 1.0)


def test_flat_forward_extrapolation_beyond_domain(spline):
    f_end = spline.forward(np.array([30.0]))[0]
    np.testing.assert_allclose(spline.forward(np.array([31.0, 45.0])), f_end)
    # log D continues linearly with slope -f_end
    d = spline.log_discount(np.array([30.0, 32.0]))
    assert d[1] - d[0] == pytest.approx(-2.0 * f_end, rel=1e-9)


def test_penalty_zero_for_linear_forward(spline):
    tt = np.linspace(0, 30, 500)
    B = spline.design_forward(tt)
    beta = np.linalg.lstsq(B, 0.01 + 0.0005 * tt, rcond=None)[0]
    omega = spline.penalty_matrix()
    assert beta @ omega @ beta == pytest.approx(0.0, abs=1e-12)
    assert np.allclose(omega, omega.T)
    assert np.linalg.eigvalsh(omega).min() > -1e-10


def test_weighted_penalty_matches_unweighted_when_weight_is_one(spline):
    np.testing.assert_allclose(spline.penalty_matrix(lambda t: np.ones_like(t)), spline.penalty_matrix(), rtol=1e-10)


def test_design_integral_matches_quadrature(spline):
    t = np.array([0.4, 3.3, 12.5])
    A = spline.design_integral(t)
    for j, tj in enumerate(t):
        s = np.linspace(0, tj, 20001)
        num = np.trapezoid(spline.design_forward(s), s, axis=0)
        np.testing.assert_allclose(A[j], num, atol=1e-5)


def test_zero_rate_limit_at_zero(spline):
    assert spline.zero(np.array([0.0]))[0] == pytest.approx(spline.forward(np.array([0.0]))[0])


def test_grid_frame_columns(spline):
    df = spline.grid_frame(np.linspace(1 / 12, 30, 10))
    assert list(df.columns) == ["maturity_years", "zero_rate", "discount_factor", "forward_rate"]
    np.testing.assert_allclose(np.exp(-df["zero_rate"] * df["maturity_years"]), df["discount_factor"])


def test_piecewise_linear_curve():
    c = PiecewiseLinearZeroCurve(np.array([0.5, 1.0, 2.0]), np.array([0.01, 0.015, 0.02]))
    np.testing.assert_allclose(c.zero(np.array([0.25, 0.75, 3.0])), [0.01, 0.0125, 0.02])
    # forward on the (1,2) segment: z + t z' = 0.0175 + 1.5 * 0.005
    assert c.forward(np.array([1.5]))[0] == pytest.approx(0.025)
    assert c.forward(np.array([0.1]))[0] == pytest.approx(0.01)
    with pytest.raises(ValueError):
        PiecewiseLinearZeroCurve(np.array([1.0, 0.5]), np.array([0.01, 0.02]))


def test_tents_partition_of_unity_and_bump():
    centers = np.array([2.0, 5.0, 10.0, 30.0])
    tents = [tent_bump(centers, k) for k in range(4)]
    t = np.array([0.1, 2, 3.5, 5, 7.5, 10, 20, 30, 40])
    np.testing.assert_allclose(sum(f(t) for f in tents), 1.0)
    assert tents[1](np.array([3.5]))[0] == pytest.approx(0.5)
    base = PiecewiseLinearZeroCurve(np.array([1.0, 30.0]), np.array([0.02, 0.02]))
    b = BumpedCurve(base, parallel_bump(1e-4))
    np.testing.assert_allclose(b.zero(np.array([1.0, 10.0])), 0.0201)
    np.testing.assert_allclose(b.forward(np.array([5.0])), 0.0201, atol=1e-7)


def test_bad_knots_rejected():
    with pytest.raises(ValueError):
        BSplineForwardCurve(np.array([0.0, 1.0]), 30.0)
    with pytest.raises(ValueError):
        BSplineForwardCurve(np.array([2.0, 1.0]), 30.0)
