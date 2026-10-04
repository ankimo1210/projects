"""Hull §29.2 printed values, independent pricing/strip and payment-measure MC."""

import importlib
import math
from datetime import date

import numpy as np
import pytest
from scipy.integrate import quad


def model():
    return importlib.import_module("hullkit._cap_floor_market")


def integral(p, F, K, sig, T, kind="call", normal=False, shift=0.0):
    sign = 1 if kind == "call" else -1
    w = sig * math.sqrt(T)
    if w == 0:
        return p * max(sign * (F - K), 0)
    if normal:
        boundary = (K - F) / w

        def underlying(z):
            return F + w * z
    else:
        boundary = (math.log((K + shift) / (F + shift)) + w * w / 2) / w

        def underlying(z):
            return (F + shift) * math.exp(-w * w / 2 + w * z) - shift

    lo, hi = (max(-12, boundary), 12) if sign == 1 else (-12, min(12, boundary))
    if hi <= lo:
        return 0.0
    return (
        p
        * quad(
            lambda z: (
                max(sign * (underlying(z) - K), 0) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
            ),
            lo,
            hi,
            epsabs=1e-13,
            epsrel=1e-11,
        )[0]
    )


def test_example_293_printed_discount_d_values_and_price():
    m = model()
    p = math.exp(-0.065 * 1.25)
    assert p == pytest.approx(0.9220, abs=0.00005)
    d1, d2 = m.black_rate_d(0.07, 0.08, 0.2, 1.0)
    assert d1 == pytest.approx(-0.5677, abs=0.00005)
    assert d2 == pytest.approx(-0.7677, abs=0.00005)
    value = m.caplet_price(1e7, 0.25, p, 0.07, 0.08, 0.2, 1.0)
    assert value / 1e6 == pytest.approx(0.00519, abs=0.000005)
    assert value == pytest.approx(1e7 * 0.25 * integral(p, 0.07, 0.08, 0.2, 1.0), abs=1e-8)
    assert m.caplet_payment(1e7, 0.25, 0.04, 0.03) == pytest.approx(25000.0)
    assert m.caplet_payment(1e7, 0.25, 0.015, 0.02, "floor") == pytest.approx(12500.0)


@pytest.mark.parametrize("kind", ["cap", "floor"])
def test_zcb_portfolio_identity_at_fixing(kind):
    m = model()
    R = np.linspace(-0.1, 0.25, 31)
    K = 0.08
    alpha = 0.25
    N = 1e7
    cash = m.caplet_payment(N, alpha, R, K, kind) / (1 + R * alpha)
    assert np.allclose(m.caplet_bond_payoff(N, alpha, R, K, kind), cash, atol=1e-8, rtol=1e-12)


def test_printed_backward_schedule_and_actual_day_count():
    m = model()
    assert np.allclose(
        m.backward_cap_schedule(1.22, 2.8, 0.25),
        [[1.22, 1.55], [1.55, 1.8], [1.8, 2.05], [2.05, 2.3], [2.3, 2.55], [2.55, 2.8]],
        atol=1e-12,
    )
    alpha = m.actual_year_fraction(date(2026, 5, 1), date(2026, 8, 1), 360)
    assert alpha == pytest.approx(0.2556, abs=0.00005)
    F = m.simple_forward_from_discounts(0.99, 0.982, alpha)
    assert 1 + alpha * F == pytest.approx(0.99 / 0.982)
    base = m.caplet_price(1e6, 92 / 360, 0.95, 0.03, 0.035, 0.2, 1)
    other = m.caplet_price(1e6, 92 / 365, 0.95, 0.03 * 365 / 360, 0.035 * 365 / 360, 0.2, 1)
    assert base == pytest.approx(other, abs=1e-9)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("family", ["normal", "shifted"])
def test_negative_rates_against_independent_normal_or_shifted_integral(kind, family):
    m = model()
    F = -0.005
    K = -0.002
    p = 0.96
    T = 2.0
    sig = 0.008 if family == "normal" else 0.3
    shift = 0 if family == "normal" else 0.03
    value = m.rate_option_price(p, F, K, sig, T, kind, model=family, shift=shift)
    expected = integral(p, F, K, sig, T, kind, normal=family == "normal", shift=shift)
    assert value == pytest.approx(expected, abs=1e-12, rel=1e-10)
    c = m.rate_option_price(p, F, K, sig, T, "call", model=family, shift=shift)
    q = m.rate_option_price(p, F, K, sig, T, "put", model=family, shift=shift)
    assert c - q == pytest.approx(p * (F - K), abs=1e-12)


def test_about_one_percent_normal_vol_and_zero_shift_limit():
    m = model()
    black = m.rate_option_price(1, 0.03, 0.03, 0.33, 1)
    normal_vol = black * math.sqrt(2 * math.pi)
    assert normal_vol == pytest.approx(0.00986, abs=0.000005)
    assert m.rate_option_price(1, 0.03, 0.03, normal_vol, 1, model="normal") == pytest.approx(
        black, abs=1e-13
    )
    assert m.rate_option_price(
        0.95, 0.03, 0.025, 0.2, 1, model="shifted", shift=0
    ) == pytest.approx(m.rate_option_price(0.95, 0.03, 0.025, 0.2, 1), abs=1e-13)


def strip_inputs():
    t = np.array([0.5, 1, 1.5, 2, 2.5])
    p = np.exp(-0.04 * (t + 0.5))
    alpha = np.full(5, 0.5)
    F = np.array([0.031, 0.034, 0.036, 0.039, 0.042])
    vol = np.array([0.18, 0.21, 0.24, 0.23, 0.20])
    K = 0.037
    N = 1e6
    prices = np.cumsum(
        [
            N * a * integral(df, f, K, s, T)
            for a, df, f, s, T in zip(alpha, p, F, vol, t, strict=True)
        ]
    )
    return N, alpha, p, F, K, t, vol, prices


def test_strip_spot_vol_reprices_all_caps_and_zero_cost_collar():
    m = model()
    N, a, p, F, K, t, vol, prices = strip_inputs()
    recovered = m.strip_cap_volatilities(N, a, p, F, K, t, prices)
    assert np.allclose(recovered, vol, atol=1e-10)
    cap = m.cap_floor_price(N, a, p, F, K, recovered, t)
    floor = m.cap_floor_price(N, a, p, F, K, recovered, t, "floor")
    assert cap == pytest.approx(prices[-1], abs=1e-7)
    assert cap - floor == pytest.approx(np.sum(N * a * p * (F - K)), abs=1e-7)
    strike = m.zero_cost_collar_floor_strike(N, a, p, F, K, recovered, t)
    independently = sum(
        N * x * integral(df, f, strike, s, T, "put")
        for x, df, f, s, T in zip(a, p, F, vol, t, strict=True)
    )
    assert independently == pytest.approx(cap, abs=1e-7)
    bad = prices.copy()
    bad[1] = bad[0] - 1
    with pytest.raises(ValueError):
        m.strip_cap_volatilities(N, a, p, F, K, t, bad)


def test_payment_numeraire_mean_and_shifted_caplet_match_exact_q_mc():
    m = model()
    r = 0.04
    eta = 0.012
    T = 1.0
    U = 1.5
    alpha = U - T
    N = 1e6
    K = 0.045
    Pfix = math.exp(-r * T + eta * eta * T**3 / 6)
    Ppay = math.exp(-r * U + eta * eta * U**3 / 6)
    F = m.simple_forward_from_discounts(Pfix, Ppay, alpha)
    n = 262144
    z = np.random.default_rng(2026100431).standard_normal((n, 2))
    rate = r + eta * math.sqrt(T) * z[:, 0]
    J = r * T + eta * (T**1.5 * z[:, 0] / 2 + math.sqrt(T**3 / 12) * z[:, 1])
    B = np.exp(-rate * alpha + eta * eta * alpha**3 / 6)
    R = (1 / B - 1) / alpha
    D = np.exp(-J)
    weight = D * B / Ppay
    for x, truth in [(weight, 1.0), (weight * R, F)]:
        assert abs(x.mean() - truth) <= 5 * x.std(ddof=1) / math.sqrt(n)
    payoff = D * B * N * alpha * np.maximum(R - K, 0)
    price = m.caplet_price(N, alpha, Ppay, F, K, eta * alpha, T, model="shifted", shift=1 / alpha)
    assert abs(payoff.mean() - price) <= 5 * payoff.std(ddof=1) / math.sqrt(n)


@pytest.mark.parametrize("known", [False, True])
def test_daily_backward_rfr_with_observed_factor_exact_quad_and_discounted_q_mc(known):
    m = model()
    nobs = 65 if not known else 39
    alpha = np.full(nobs, 0.25 / 65)
    obs = (0.5 + np.arange(nobs) * alpha[0]) if not known else np.arange(nobs) * alpha[0]
    total = 0.25
    factor = 1.0 if not known else 1.001
    r = 0.03
    eta = 0.01
    N = 1e6
    stat = m.gaussian_backward_rfr_statistics(obs, alpha, r, eta, total, factor)
    F = stat["forward_rate"]
    K = F
    price = m.gaussian_backward_rfr_price(N, K, stat)
    C = np.minimum.outer(obs, obs)
    va = eta**2 * float(alpha @ C @ alpha)
    cov = va + eta**2 * obs[0] ** 2 * alpha.sum() / 2
    vj = eta**2 * (obs[0] ** 3 / 3 + float(alpha @ C @ alpha) + obs[0] ** 2 * alpha.sum())
    mj = r * (obs[0] + alpha.sum())
    ma = r * alpha.sum()
    sd = math.sqrt(va)
    kg = 1 + total * K
    root = (math.log(kg / factor) - ma) / sd
    reference = quad(
        lambda z: (
            N
            * math.exp(-mj - cov / sd * z + 0.5 * (vj - cov * cov / va))
            * max(factor * math.exp(ma + sd * z) - kg, 0)
            * math.exp(-z * z / 2)
            / math.sqrt(2 * math.pi)
        ),
        max(root, -12),
        12,
        epsabs=1e-9,
    )[0]
    assert price == pytest.approx(reference, abs=1e-8, rel=1e-10)
    n = 65536
    rng = np.random.default_rng(2026100440 + known)
    W = np.cumsum(rng.standard_normal((n, nobs)) * np.sqrt(np.diff(np.r_[0.0, obs])), axis=1)
    A = r * alpha.sum() + eta * (W @ alpha)
    J = (
        r * obs[0]
        + eta * (obs[0] / 2 * W[:, 0] + math.sqrt(obs[0] ** 3 / 12) * rng.standard_normal(n))
        + A
    )
    values = np.exp(-J) * N * np.maximum(factor * np.exp(A) - kg, 0)
    assert abs(values.mean() - price) <= 5 * values.std(ddof=1) / math.sqrt(n)
    assert m.rfr_forward_from_ois(
        factor, stat["fixing_discount"], stat["discount"], total
    ) == pytest.approx(F, abs=1e-12)
    midpoint = m.rfr_midpoint_caplet_price(N, total, stat["discount"], F, K, eta / abs(F), obs)
    assert midpoint == pytest.approx(
        N * total * integral(stat["discount"], F, K, eta / abs(F), float(np.mean(obs))), abs=1e-8
    )
    # Hull's midpoint is an approximation with model-dependent bias, not this exact daily model.
    assert abs(midpoint - price) > 1.0


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.caplet_price(1e6, 0.25, 0.95, 0.03, 0.04, 0.2, -1),
        lambda m: m.caplet_bond_payoff(1e6, 0.25, -4, 0.03),
        lambda m: m.backward_cap_schedule(2, 1, 0.25),
        lambda m: m.compound_observed_rate([-0.2], [10]),
    ],
)
def test_mathematically_undefined_inputs_rejected(call):
    with pytest.raises(ValueError):
        call(model())


def test_flat_cap_quotes_strip_back_to_declared_spot_volatilities():
    N, a, p, F, K, t, vol, _ = strip_inputs()
    quoted = [
        0.18000000000000058,
        0.20274058218590343,
        0.22104923707585233,
        0.2242815872753157,
        0.21750912224091026,
    ]
    actual = model().flat_cap_vols_to_spot(N, a, p, F, K, t, quoted)
    assert np.allclose(actual, vol, atol=1e-10, rtol=1e-10)
