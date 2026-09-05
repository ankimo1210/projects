import numpy as np
import pytest

from quantcurve.curves import CurveBasis, ZeroCurve
from quantcurve.fitting import fit_curve
from quantcurve.pricing import PricingEngine, bond_cashflows, key_basis, risk_table, swap_schedule
from quantcurve.research import holdout_mask, maturity_groups


@pytest.mark.parametrize("kind", ["baseline", "advanced"])
def test_negative_curve_transform_consistency(kind):
    b = CurveBasis(kind)
    beta = np.full(b.size, -50.) if kind == "advanced" else np.array([-50., 0., 0.])
    c = ZeroCurve(b, beta)
    t = np.linspace(.001, 40, 501)
    np.testing.assert_allclose(c.zero(t), -.005, atol=1e-14)
    np.testing.assert_allclose(c.forward(t), -.005, atol=1e-14)
    np.testing.assert_allclose(-np.log(c.discount(t)) / t, c.zero(t), atol=1e-12)
    assert np.all(c.discount(t) > 1)
    assert c.discount([0])[0] == 1


def test_curve_continuity_and_forward_derivative(fitted):
    c = fitted.curve
    ts = np.r_[c.basis.knots[1:], 35.]
    h = 1e-6
    np.testing.assert_allclose(c.zero(ts - h), c.zero(ts + h), atol=2e-7)
    np.testing.assert_allclose(c.forward(ts - h), c.forward(ts + h), atol=2e-6)
    numerical = -(np.log(c.discount(ts + h)) - np.log(c.discount(ts - h))) / (2 * h)
    np.testing.assert_allclose(c.forward(ts), numerical, atol=2e-8, rtol=1e-6)
    np.testing.assert_allclose(c.forward([30, 35, 50]), c.forward([30])[0], atol=1e-12)


def test_large_and_tiny_times_stable(fitted):
    c = fitted.curve
    t = np.array([0, 1e-10, 1e-5, 1/12, 30, 100])
    assert np.isfinite(c.discount(t)).all()
    assert (c.discount(t) > 0).all()
    assert np.isfinite(c.forward(t)).all()
    with pytest.raises(ValueError):
        c.discount([-1])
    with pytest.raises(ValueError):
        c.zero([np.nan])


def test_stub_schedules_have_real_time_accruals():
    t, alpha = swap_schedule(1.25, 1)
    np.testing.assert_allclose(t, [1, 1.25])
    np.testing.assert_allclose(alpha, [1, .25])
    t, cf = bond_cashflows(1.25, 2, .04)
    np.testing.assert_allclose(t, [.5, 1, 1.25])
    np.testing.assert_allclose(cf, [2, 2, 101])
    _, cf_regular = bond_cashflows(1, 2, .04)
    np.testing.assert_allclose(cf_regular, [2, 102])


def test_independent_cashflow_prices(clean):
    f = clean[0].groupby("instrument_type", sort=True).head(1).copy().reset_index(drop=True)
    f["maturity_years"] = 1.0
    f["payment_frequency"] = 1
    f["coupon_rate"] = .025
    b = CurveBasis("baseline")
    c = ZeroCurve(b, [200, 0, 0])
    q = PricingEngine(f).quote(c)
    for i, row in f.iterrows():
        expected = 102.5 * np.exp(-.02) if row.instrument_type == "bond" else np.expm1(.02)
        assert q[i] == pytest.approx(expected, abs=1e-11)


def test_analytic_quote_jacobian_against_independent_fd(clean, fitted):
    e = PricingEngine(clean[0])
    b = fitted.curve.basis.matrix(e.times)
    beta = fitted.curve.beta
    _, jac = e.quotes_and_jacobian(beta, b)
    for j in (0, 4, 8, 14, len(beta) - 1):
        direction = np.eye(len(beta))[j] * .001
        plus = e.quote(ZeroCurve(fitted.curve.basis, beta + direction))
        minus = e.quote(ZeroCurve(fitted.curve.basis, beta - direction))
        np.testing.assert_allclose(jac[:, j], (plus - minus) / .002, rtol=2e-5, atol=5e-9)


def test_risk_finite_difference_and_key_partition(clean, fitted):
    risk = risk_table(clean[0], fitted.curve)
    assert len(risk) == len(clean[0])
    assert risk.fd_relative_error.max() < 1e-5
    assert risk.key_sum_relative_error.max() < 1e-5
    np.testing.assert_allclose(key_basis([0, 1, 2, 3, 5, 8, 10, 20, 30, 40]).sum(axis=1), 1., atol=1e-15)
    np.testing.assert_allclose(risk.dv01, risk.dv01_first_order, rtol=2e-6, atol=1e-7)


def test_receiver_fixed_risk_has_independent_closed_form(clean):
    f = clean[0][clean[0].instrument_type == "deposit"].head(1).copy()
    f["maturity_years"] = 2.
    f["normalized_quote"] = .03
    c = ZeroCurve(CurveBasis("baseline"), [200, 0, 0])
    actual = risk_table(f, c).dv01.iloc[0]
    expected = 1e6 * 1.06 * np.exp(-.02 * 2) * np.sinh(.0001 * 2)
    assert actual == pytest.approx(expected, rel=1e-11)


def test_outlier_downweight_is_effective_without_deletion(clean, fitted):
    f = clean[0].copy()
    i = f.index[(f.instrument_type == "ois_swap") & (f.maturity_years == 7)][0]
    f.loc[i, "normalized_quote"] += .03
    robust = fit_curve(f, smoothing=.001)
    ordinary = fit_curve(f, smoothing=.001, robust=False)
    t = np.linspace(.1, 30, 301)
    robust_error = np.linalg.norm(robust.curve.zero(t) - fitted.curve.zero(t))
    ordinary_error = np.linalg.norm(ordinary.curve.zero(t) - fitted.curve.zero(t))
    assert len(robust.quotes) == len(f)
    assert robust.robust_weights[i] < .01
    assert robust_error < ordinary_error * .2


def test_fit_is_reproducible(clean, fitted):
    second = fit_curve(clean[0], smoothing=.001)
    np.testing.assert_array_equal(second.curve.beta, fitted.curve.beta)
    np.testing.assert_array_equal(second.robust_weights, fitted.robust_weights)


def test_validation_groups_do_not_overlap(clean):
    f = clean[0]
    h = holdout_mask(f)
    g = maturity_groups(f)
    assert set(g[h]).isdisjoint(set(g[~h]))
    assert len(f[h]) > 0
    assert not h[0] and not h[-1]
