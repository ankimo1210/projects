"""Hull §29.4 four curve deltas, 55 gammas, full Hessian and PCA vegas."""

import importlib
import math

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._ir_hedging")


def test_hessian_and_directional_gamma_match_independent_quadratic_derivatives():
    A = np.array([[2.0, 0.7, -0.3], [0.7, 3.0, 0.5], [-0.3, 0.5, 4.0]])
    b = np.array([0.1, 0.2, -0.1])
    x = np.array([0.03, 0.04, 0.05])

    def value(z):
        return 0.5 * z @ A @ z + b @ z

    row = model().finite_difference_sensitivities(value, x, 1e-4)
    assert np.allclose(row["gradient"], A @ x + b, atol=1e-10)
    assert np.allclose(row["hessian"], A, atol=1e-8)
    report = model().rate_hedge_report(value, x, x, lambda q: q, np.eye(3)[:, :2], bump=1e-4)
    assert report["parallel_gamma"] == pytest.approx(float(np.ones(3) @ A @ np.ones(3)), abs=1e-8)
    assert report["parallel_gamma"] != pytest.approx(float(np.trace(A)))
    assert np.allclose(report["pca_gamma"], A[:2, :2], atol=1e-8)


def test_quote_rebuild_sensitivities_match_independent_deposit_discount_derivatives():
    T = np.arange(0.5, 5.001, 0.5)
    q = 0.035 + 0.009 * (1 - np.exp(-T / 2))
    cash = np.linspace(4, 8, len(T))

    def rebuild(quotes):
        return np.log1p(quotes * T) / T

    z = rebuild(q)

    def value(zeros):
        return float(np.sum(cash * np.exp(-zeros * T)))

    row = model().rate_hedge_report(value, z, q, rebuild, np.eye(10)[:, :2], bump=1e-5)
    assert row["unique_gamma_count"] == 55  # Hull p.703 printed 10*(10+1)/2
    assert row["quote_delta_cash"] == pytest.approx(
        -T * cash / (1 + q * T) ** 2 * 1e-5, rel=1e-8, abs=1e-10
    )
    assert row["bucket_delta_cash"] == pytest.approx(
        -T * cash * np.exp(-z * T) * 1e-5, rel=1e-8, abs=1e-10
    )
    assert np.allclose(
        row["quote_hessian"], np.diag(2 * T * T * cash / (1 + q * T) ** 3), atol=0.001, rtol=1e-6
    )


def test_pca_loadings_match_independent_svd_and_vega_projection():
    rng = np.random.default_rng(2942026)
    changes = rng.standard_normal((256, 8)) @ np.diag(np.linspace(0.1, 1, 8))
    rows = model().pca_loadings(changes, 2)
    demeaned = changes - changes.mean(axis=0)
    _, s, v = np.linalg.svd(demeaned, full_matrices=False)
    assert np.allclose(rows["eigenvalues"], s[:2] ** 2 / 255, atol=1e-12)
    assert np.allclose(abs(rows["loadings"].T @ v[:2].T), np.eye(2), atol=1e-10)
    vol = np.linspace(0.18, 0.25, 8)
    A = np.diag(np.arange(1, 9))
    b = np.linspace(-0.3, 0.7, 8)

    def value(vv):
        return 0.5 * vv @ A @ vv + b @ vv

    row = model().volatility_hedge_report(value, vol, rows["loadings"], bump=0.001)
    g = A @ vol + b
    assert row["parallel_vega_per_point"] == pytest.approx(g.sum() * 0.01, abs=1e-10)
    assert np.allclose(row["pca_vega_per_point"], g @ rows["loadings"] * 0.01, atol=1e-10)


def test_same_cap_and_swaption_portfolio_has_four_deltas_and_convergent_bump_error():
    from hullkit._cap_floor_market import cap_floor_price
    from hullkit._swaption_market import swaption_market_price

    T = np.arange(0.5, 5.001, 0.5)
    q = 0.035 + 0.009 * (1 - np.exp(-T / 2))
    vol = np.r_[np.linspace(0.18, 0.24, 7), 0.21]

    def rebuild(quotes):
        return np.log1p(quotes * T) / T

    z = rebuild(q)

    def value(zeros, v=vol):
        def df(t):
            return np.exp(-np.asarray(t) * np.interp(t, T, zeros))

        fix = np.arange(1.0, 4.001, 0.5)
        pay = fix + 0.5
        discount = df(pay)
        forward = (df(fix) / discount - 1) / 0.5
        cap = cap_floor_price(1e6, np.full(7, 0.5), discount, forward, 0.045, v[:-1], fix)
        swap_pay = np.arange(2.0, 5.001, 0.5)
        Ds = df(swap_pay)
        A = 0.5 * Ds.sum()
        F = (df(1.5) - Ds[-1]) / A
        return cap + swaption_market_price(1e6, A, F, 0.045, v[-1], 1.5)

    directions = np.column_stack([np.ones(10), np.linspace(-1, 1, 10)])
    directions = np.linalg.qr(directions)[0]
    rows = [
        model().rate_hedge_report(value, z, q, rebuild, directions, bump=h) for h in (1e-4, 5e-5)
    ]
    for row in rows:
        assert row["unique_gamma_count"] == 55
        assert np.isfinite(row["dv01_cash"]) and row["pca_delta_cash"].shape == (2,)
        assert np.allclose(row["hessian"], row["hessian"].T, atol=1e-6)
    first, second = [
        abs(row["quote_delta_cash"].sum() - row["quote_parallel_cash"]) for row in rows
    ]
    assert first > 1e-6 and second < 0.3 * first
    dv = [abs(row["bucket_delta_cash"].sum() - row["dv01_cash"]) for row in rows]
    assert dv[1] < 0.3 * dv[0]
    vegas = model().volatility_hedge_report(lambda v: value(z, v), vol, np.eye(8)[:, :2])
    assert np.isfinite(vegas["parallel_vega_per_point"])


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.finite_difference_sensitivities(lambda x: x.sum(), [0.03, 0.04], 0),
        lambda m: m.pca_loadings([[1.0, 2.0]], 2),
        lambda m: m.rate_hedge_report(
            lambda x: x.sum(), [0.03, 0.04], [0.03], lambda q: q, np.eye(2)
        ),
    ],
)
def test_undefined_sensitivity_inputs_rejected(call):
    with pytest.raises(ValueError):
        call(model())
