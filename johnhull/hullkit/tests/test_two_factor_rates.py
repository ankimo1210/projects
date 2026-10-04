"""§31.5 / full TN14: independent matrix exponentials, integrals and payoff MC."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.linalg import expm
from scipy.optimize import brentq
from scipy.special import ndtr

PARAMETERS = [
    (1, 0.1, 0.01, 0.0165, 0.6),
    (0.2, 0.7, 0.012, 0.02, -0.4),
    (0.3, 0.3, 0.012, 0.02, 0.5),
    (0.3, 0.30000001, 0.012, 0.02, 0.5),
    (0, 0, 0.012, 0.02, -1),
    (0.2, 0, 0.012, 0.02, 1),
    (0.2, 0.7, 0.012, 0, 0.3),
    (0.2, 0.7, 0, 0, 1),
]


def model():
    return importlib.import_module("hullkit._two_factor_rates")


def independent_joint(p, T):
    a, b, s1, s2, rho = p
    A = np.array([[-a, 1, 0], [0, -b, 0], [1, 0, 0.0]])
    Q = np.array([[s1 * s1, rho * s1 * s2, 0], [rho * s1 * s2, s2 * s2, 0], [0, 0, 0.0]])
    matrix = np.block([[A, Q], [np.zeros((3, 3)), -A.T]])
    result = expm(matrix * T)
    transition = result[:3, :3]
    cov = result[:3, 3:] @ transition.T
    return transition, (cov + cov.T) / 2


def normal_mean(f):
    return quad(
        lambda z: f(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi), -11, 11, epsabs=1e-11
    )[0]


@pytest.mark.parametrize("p", PARAMETERS)
def test_native_loadings_covariance_and_equilibrium_match_independent_block_exponential(p):
    T = 4.0
    r = -0.015
    u = -0.004
    m = model()
    result = m.two_factor_moments(r, u, *p, T)
    transition, cov = independent_joint(p, T)
    assert result["mean"] == pytest.approx(transition @ np.array([r, u, 0]), abs=2e-13)
    assert np.allclose(result["covariance"], cov, atol=2e-13, rtol=2e-12)
    price = m.equilibrium_bond(r, u, *p, T)
    assert price == pytest.approx(
        math.exp(-(transition @ np.array([r, u, 0]))[2] + 0.5 * cov[2, 2]), rel=2e-12
    )
    eig, V = np.linalg.eigh(cov)
    rng = np.random.default_rng(3152026)
    noise = rng.standard_normal((131072, 3)) @ (V * np.sqrt(np.maximum(eig, 0))).T
    samples = np.exp(-result["mean"][2] - noise[:, 2])
    se = samples.std(ddof=1) / math.sqrt(samples.size)
    assert abs(samples.mean() - price) <= 5 * se + 1e-13
    assert m.equilibrium_bond(r, u, *p, 0) == pytest.approx(1)


def test_equation_31_14_equal_a_b_zero_limits_and_hump_source_parameters():
    m = model()
    a = 0.2
    b = 0.7
    T = 4
    expected = math.exp(-a * T) / (a * (a - b)) - math.exp(-b * T) / (b * (a - b)) + 1 / (a * b)
    assert m.two_factor_loadings(a, b, T)["C"] == pytest.approx(expected, abs=1e-13)
    assert m.two_factor_loadings(0, 0, T)["C"] == pytest.approx(T * T / 2, abs=1e-13)
    equal = m.two_factor_loadings(0.3, 0.3, T)["C"]
    assert equal == pytest.approx((1 - math.exp(-0.3 * T) * (1 + 0.3 * T)) / 0.3**2, abs=1e-13)
    assert m.two_factor_loadings(0.3, 0.30000001, T)["C"] == pytest.approx(equal, rel=2e-8)
    vol = [m.forward_rate_volatility(*PARAMETERS[0], h) for h in [0, 0.5, 1, 2, 3, 5, 10]]
    assert vol == pytest.approx(
        [
            0.01,
            0.011077870705894563,
            0.012405654370778417,
            0.013384789054751245,
            0.012973742203410531,
            0.011036759048503184,
            0.006743896498789612,
        ],
        rel=1e-12,
    )
    # TN14 supplies parameters for a hump, not these computed printed price pins.
    assert vol[3] > vol[0] and vol[3] > vol[-1]


@pytest.mark.parametrize("rho", [-1, -0.4, 1])
def test_two_factor_equilibrium_pde_with_cross_derivative(rho):
    m = model()
    p = (0.2, 0.7, 0.012, 0.02, rho)
    r = 0.03
    u = 0.008
    T = 3
    h = 1e-4

    def value(rr, uu, t):
        return m.equilibrium_bond(rr, uu, *p, t)

    P = value(r, u, T)
    vt = -(value(r, u, T + h) - value(r, u, T - h)) / (2 * h)
    vr = (value(r + h, u, T) - value(r - h, u, T)) / (2 * h)
    vu = (value(r, u + h, T) - value(r, u - h, T)) / (2 * h)
    vrr = (value(r + h, u, T) - 2 * P + value(r - h, u, T)) / h**2
    vuu = (value(r, u + h, T) - 2 * P + value(r, u - h, T)) / h**2
    vru = (
        value(r + h, u + h, T)
        - value(r + h, u - h, T)
        - value(r - h, u + h, T)
        + value(r - h, u - h, T)
    ) / (4 * h * h)
    residual = (
        vt
        + (u - 0.2 * r) * vr
        - 0.7 * u * vu
        + 0.5 * 0.012**2 * vrr
        + 0.5 * 0.02**2 * vuu
        + rho * 0.012 * 0.02 * vru
        - r * P
    )
    assert abs(residual) < 3e-9


@pytest.mark.parametrize("p", PARAMETERS[:4])
@pytest.mark.parametrize("u0", [0, 0.01])
def test_curve_fit_matches_direct_theta_integral_and_initial_curve(p, u0):
    m = model()
    a, b, _s1, _s2, _rho = p

    def logdf(t):
        return -0.025 * t - 0.0015 * t * t - 0.004 * (-math.expm1(-0.4 * t)) / 0.4

    def forward(t):
        return 0.025 + 0.003 * t + 0.004 * math.exp(-0.4 * t)

    def derivative(t):
        return 0.003 - 0.0016 * math.exp(-0.4 * t)

    assert m.curve_fitted_bond(0, 3, forward(0), u0, *p, logdf, forward, u0=u0) == pytest.approx(
        math.exp(logdf(3)), rel=1e-12
    )
    t = 0.75
    T = 5
    r = -0.012
    u = 0.008

    def theta(s):
        return m.curve_fitted_theta(s, *p, forward, derivative, u0=u0)

    integral = quad(
        lambda s: m.two_factor_loadings(a, b, T - s)["B"] * theta(s), t, T, epsabs=1e-12
    )[0]
    _, cov = independent_joint(p, T - t)
    transition, _ = independent_joint(p, T - t)
    direct = math.exp(-(transition @ np.array([r, u, 0]))[2] - integral + 0.5 * cov[2, 2])
    fitted = m.curve_fitted_bond(t, T, r, u, *p, logdf, forward, u0=u0)
    assert fitted == pytest.approx(direct, rel=3e-12)


def test_tn14_theta_requires_initial_curve_maturity_derivative():
    m = model()
    p = (0.2, 0.7, 0.012, 0.02, -0.4)
    T = 5

    def forward(t):
        return 0.04

    def derivative(t):
        return 0

    def wrong(s):
        shift = m.two_factor_shift(s, *p)
        return 0.2 * (0.04 + shift["psi"]) - shift["psi_prime"]

    integral = quad(
        lambda s: m.two_factor_loadings(0.2, 0.7, T - s)["B"] * wrong(s), 0, T, epsabs=1e-12
    )[0]
    cov = independent_joint(p, T)[1]
    B = m.two_factor_loadings(0.2, 0.7, T)["B"]
    wrong_price = math.exp(-B * 0.04 - integral + 0.5 * cov[2, 2])
    assert wrong_price == pytest.approx(0.8233120472573889, rel=1e-12)
    assert wrong_price - math.exp(-0.04 * T) > 0.004
    theta = m.curve_fitted_theta(1, *p, forward, derivative)
    assert theta > 0.2 * 0.04


def printed_gamma_eta(p, t, T):
    a, b, s1, s2, rho = p

    def b_load(h):
        return -math.expm1(-a * h) / a

    def c_load(h):
        return math.exp(-a * h) / (a * (a - b)) - math.exp(-b * h) / (b * (a - b)) + 1 / (a * b)

    h = T - t
    B0 = b_load(t)
    C0 = c_load(t)
    g1 = math.exp(-(a + b) * T) * math.expm1((a + b) * t) / ((a + b) * (a - b)) - math.exp(
        -2 * a * T
    ) * math.expm1(2 * a * t) / (2 * a * (a - b))
    g2 = (
        g1
        + c_load(h)
        - c_load(T)
        + 0.5 * b_load(h) ** 2
        - 0.5 * b_load(T) ** 2
        + t / a
        - (math.exp(-a * h) - math.exp(-a * T)) / (a * a)
    ) / (a * b)
    g3 = -math.expm1(-(a + b) * t) / ((a - b) * (a + b)) + math.expm1(-2 * a * t) / (
        2 * a * (a - b)
    )
    g4 = (g3 - C0 - 0.5 * B0**2 + t / a + math.expm1(-a * t) / (a * a)) / (a * b)
    g5 = (0.5 * c_load(h) ** 2 - 0.5 * c_load(T) ** 2 + g2) / b
    g6 = (g4 - 0.5 * C0**2) / b
    eta = (
        s1 * s1 / (4 * a) * (-math.expm1(-2 * a * t)) * b_load(h) ** 2
        - rho * s1 * s2 * (B0 * C0 * b_load(h) + g4 - g2)
        - 0.5 * s2 * s2 * (C0 * C0 * b_load(h) + g6 - g5)
    )
    return np.array([g1, g2, g3, g4, g5, g6]), eta


@pytest.mark.parametrize("p", [PARAMETERS[0], PARAMETERS[1]])
def test_full_tn14_appendix_gamma_eta_matches_printed_algebra(p):
    for t, T in [(0.25, 2), (0.75, 5), (2, 8)]:
        expected, eta = printed_gamma_eta(p, t, T)
        row = model().tn14_gamma_eta(t, T, *p)
        assert row["gamma"] == pytest.approx(expected, abs=1e-10, rel=1e-11)
        assert row["eta"] == pytest.approx(eta, abs=3e-13)


@pytest.mark.parametrize("p", PARAMETERS)
def test_tn14_option_variance_and_price_match_independent_kernel_and_payoff_integral(p):
    m = model()
    a, b, s1, s2, rho = p
    expiry = 1.5
    maturity = 6
    load = m.two_factor_loadings(a, b, maturity - expiry)
    statecov = independent_joint(p, expiry)[1][:2, :2]
    coeff = np.array([load["B"], load["C"]])
    variance = float(coeff @ statecov @ coeff)

    def integrand(s):
        x = m.two_factor_loadings(a, b, maturity - s)
        y = m.two_factor_loadings(a, b, expiry - s)
        v1 = s1 * (x["B"] - y["B"])
        v2 = s2 * (x["C"] - y["C"])
        return v1 * v1 + v2 * v2 + 2 * rho * v1 * v2

    independent_variance = quad(integrand, 0, expiry, epsabs=1e-13)[0]
    df = math.exp(-0.04 * expiry)
    long_df = math.exp(-0.04 * maturity)
    F = 100 * long_df / df
    K = 85
    row = m.two_factor_zcb_option(expiry, maturity, *p, df, long_df, K, principal=100)
    assert row["variance"] == pytest.approx(variance, abs=3e-13)
    assert row["variance"] == pytest.approx(independent_variance, abs=3e-13)
    if variance:
        w = math.sqrt(variance)
        lower = (math.log(K / F) + variance / 2) / w
        exact = (
            df
            * quad(
                lambda z: (
                    max(F * math.exp(-variance / 2 + w * z) - K, 0)
                    * math.exp(-z * z / 2)
                    / math.sqrt(2 * math.pi)
                ),
                max(lower, -12),
                12,
                epsabs=1e-10,
            )[0]
            if lower < 12
            else 0
        )
    else:
        exact = df * max(F - K, 0)
    assert row["price"] == pytest.approx(exact, abs=1e-9)


def independent_coupon_call(coeff, cov, amounts, strike, discount):
    variance_u = cov[1, 1]
    su = math.sqrt(variance_u)
    conditional = cov[0, 0] - cov[0, 1] ** 2 / variance_u
    sd = math.sqrt(max(conditional, 0))
    diag = np.diag(coeff @ cov @ coeff.T)

    def payoff(z):
        u = su * z
        mean = cov[0, 1] / variance_u * u
        weights = amounts * np.exp(-coeff[:, 1] * u - 0.5 * diag)

        def basket(r):
            return float(weights @ np.exp(-coeff[:, 0] * r))

        boundary = brentq(lambda r: basket(r) - strike, -3, 3, xtol=1e-13)
        return float(
            weights
            @ (
                np.exp(-coeff[:, 0] * mean + 0.5 * coeff[:, 0] ** 2 * conditional)
                * ndtr((boundary - mean + coeff[:, 0] * conditional) / sd)
            )
            - strike * ndtr((boundary - mean) / sd)
        )

    return discount * normal_mean(payoff)


def test_tn14_coupon_moment_matching_is_distinct_from_exact_gaussian_payoff():
    m = model()
    p = (0.1, 1, 0.03, 0.08, -0.5)
    expiry = 2
    times = np.array([3, 4, 5, 7])
    cash = np.array([4, 4, 4, 104])
    discount = math.exp(-0.04 * expiry)
    dfs = np.exp(-0.04 * times)
    row = m.two_factor_coupon_approximation(expiry, times, cash, *p, discount, dfs, 100)
    cov = independent_joint(p, expiry)[1][:2, :2]
    coeff = np.array(
        [[m.two_factor_loadings(p[0], p[1], t - expiry)[k] for k in ["B", "C"]] for t in times]
    )
    amounts = cash * dfs / discount
    exact = independent_coupon_call(coeff, cov, amounts, 100, discount)
    assert exact == pytest.approx(9.88683278714467, abs=1e-9)
    assert row["price"] == pytest.approx(9.912082063880094, abs=1e-9)
    assert abs(row["price"] - exact) > 0.02
    rng = np.random.default_rng(3152026)
    states = rng.multivariate_normal([0, 0], cov, size=262144)
    bonds = dfs / discount * np.exp(-states @ coeff.T - 0.5 * np.diag(coeff @ cov @ coeff.T))
    basket = bonds @ cash
    for samples, target in [
        (basket, row["first_moment"]),
        (basket * basket, row["second_moment"]),
        (discount * np.maximum(basket - 100, 0), exact),
    ]:
        se = samples.std(ddof=1) / math.sqrt(samples.size)
        assert abs(samples.mean() - target) < 5 * se


def test_transformed_factor_covariance_and_singular_native_boundary():
    m = model()
    p = (0.2, 0.7, 0.012, 0.02, -0.4)
    row = m.tn14_transformed_factors(*p)
    transform = np.array([[1, 1 / (p[1] - p[0])], [0, 1]])
    cov = independent_joint(p, 2)[1][:2, :2]
    tcov = transform @ cov @ transform.T
    expected = row["sigma_y"] ** 2 * (-math.expm1(-2 * p[0] * 2)) / (2 * p[0])
    assert tcov[0, 0] == pytest.approx(expected, abs=1e-14)
    assert abs(row["correlation_y_u"]) <= 1
    zero = m.tn14_transformed_factors(0.2, 0.1, 0.1, 0.01, 1)
    assert zero["sigma_y"] == pytest.approx(0, abs=1e-14) and zero["correlation_y_u"] is None
    with pytest.raises(ValueError):
        m.tn14_transformed_factors(0.3, 0.3, 0.01, 0.02, 0.5)
