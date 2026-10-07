"""§32.2 original formulas, TN15, Gaussian/CIR independent payoff references."""

import importlib
import math

import numpy as np
import pytest
from hullkit._fitted_short_rate import gaussian_fitted_bond
from hullkit._short_rate_models import cir_bond, cir_transition, vasicek_bond
from hullkit._short_rate_pde import discounted_path_values
from scipy.integrate import quad
from scipy.stats import ncx2


def model():
    return importlib.import_module("hullkit._short_rate_bond_options")


@pytest.mark.parametrize("a", [0, 0.1])
@pytest.mark.parametrize("sigma", [0, 0.02])
@pytest.mark.parametrize("kind", ["call", "put"])
def test_gaussian_zcb_option_matches_independent_payment_measure_density(a, sigma, kind):
    expiry = 2.0
    maturity = 5.0
    r = 0.03
    b = 0.04
    K = 0.9
    pt = vasicek_bond(r, a, b, sigma, expiry)["price"]
    pu = vasicek_bond(r, a, b, sigma, maturity)["price"]
    row = model().gaussian_bond_option(expiry, maturity, a, sigma, pt, pu, K, kind=kind)
    interval = vasicek_bond(0, a, b, sigma, maturity - expiry)
    law = vasicek_bond(r, a, b, sigma, expiry)
    mean = law["mean_rate"] - law["cov_rate_integral"]
    variance = law["variance_rate"]
    sign = 1 if kind == "call" else -1

    def payoff(z):
        return max(
            sign
            * (math.exp(interval["logA"] - interval["B"] * (mean + math.sqrt(variance) * z)) - K),
            0,
        )

    if variance:
        threshold = (math.log(math.exp(interval["logA"]) / K) / interval["B"] - mean) / math.sqrt(
            variance
        )
        low, high = (-12, min(12, threshold)) if kind == "call" else (max(-12, threshold), 12)
        exact = (
            pt
            * quad(
                lambda z: payoff(z) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi),
                low,
                high,
                epsabs=1e-12,
            )[0]
            if high > low
            else 0
        )
    else:
        exact = pt * payoff(0)
    assert row["price"] == pytest.approx(exact, abs=1e-11)
    if a == 0:
        assert row["stddev"] == pytest.approx(
            sigma * (maturity - expiry) * math.sqrt(expiry), abs=1e-14
        )


def test_tn15_coupon_bond_put_decomposition_and_independent_gaussian_integral():
    m = model()
    a = 0.1
    b = 0.1
    sigma = 0.02
    r0 = 0.1
    expiry = 3
    K = 98
    times = np.array([3.5, 4, 4.5, 5])
    cash = np.array([5, 5, 5, 105])
    pt = vasicek_bond(r0, a, b, sigma, expiry)["price"]

    def at_exercise(rate, t):
        return vasicek_bond(rate, a, b, sigma, t - expiry)["price"]

    def zcb(t, strike, kind):
        pu = vasicek_bond(r0, a, b, sigma, t)["price"]
        return m.gaussian_bond_option(expiry, t, a, sigma, pt, pu, strike, kind=kind)["price"]

    row = m.jamshidian_coupon_option(expiry, times, cash, K, at_exercise, zcb, kind="put")
    assert row["critical_rate"] == pytest.approx(0.10952, abs=0.000005)
    assert row["cash_strikes"] == pytest.approx([4.734, 4.484, 4.248, 84.535], abs=0.0005)
    assert row["cash_strikes"].sum() == pytest.approx(98, abs=1e-11)
    law = vasicek_bond(r0, a, b, sigma, expiry)
    mean = law["mean_rate"] - law["cov_rate_integral"]
    sd = math.sqrt(law["variance_rate"])
    threshold = (row["critical_rate"] - mean) / sd
    exact = (
        pt
        * quad(
            lambda z: (
                max(
                    K
                    - sum(
                        c * at_exercise(mean + sd * z, t) for c, t in zip(cash, times, strict=True)
                    ),
                    0,
                )
                * math.exp(-z * z / 2)
                / math.sqrt(2 * math.pi)
            ),
            threshold,
            12,
            epsabs=1e-12,
        )[0]
    )
    assert row["price"] == pytest.approx(exact, abs=1e-11)
    assert row["price"] == pytest.approx(0.8751256363672947, abs=1e-10)
    assert abs(row["price"] - 0.8752) > 0.00005  # source rounded components; do not force total pin


def test_ho_lee_coupon_decomposition_and_payoff_identity_at_many_rates():
    m = model()
    E = 1.0
    a = 0
    s = 0.01
    times = np.array([2.0, 3.0, 4.0])
    cash = np.array([4.0, 4.0, 104.0])
    pt = math.exp(-0.04 * E)
    K = 100

    def logdf(t):
        return -0.04 * t

    def forward(t):
        return 0.04

    def bond(rate, t):
        return gaussian_fitted_bond(E, t, rate, a, s, logdf, forward)

    def price(t, strike, kind):
        return m.gaussian_bond_option(E, t, a, s, pt, math.exp(logdf(t)), strike, kind=kind)[
            "price"
        ]

    row = m.jamshidian_coupon_option(E, times, cash, K, bond, price, kind="put")
    strikes = row["bond_strikes"]
    for rate in np.linspace(-0.02, 0.12, 15):
        bonds = np.array([bond(rate, t) for t in times])
        assert max(K - cash @ bonds, 0) == pytest.approx(
            float(cash @ np.maximum(strikes - bonds, 0)), abs=1e-11
        )


@pytest.mark.parametrize(
    "a,b,s,r,E,U,K",
    [
        (0.1, 0.03, 0.07, 0.04, 2, 5, 0.85),
        (0.2, 0.01, 0.1, 0, 2, 5, 0.94),
        (0, 0.03, 0.1, 0.04, 2, 5, 0.9),
    ],
)
def test_cir_option_matches_independent_forward_density_integral_and_semigroup(a, b, s, r, E, U, K):
    m = model()
    row = m.cir_bond_option(r, a, b, s, E, U, K)
    pt = cir_bond(r, a, b, s, E)["price"]
    pu = cir_bond(r, a, b, s, U)["price"]
    interval = cir_bond(0, a, b, s, U - E)
    q, d, nc = row["forward_scale"], row["degrees"], row["noncentrality"]
    boundary = row["critical_rate"]
    A = math.exp(interval["logA"])
    B = interval["B"]
    if d:
        integral = quad(
            lambda x: max(A * math.exp(-B * q * x) - K, 0) * ncx2.pdf(x, d, nc),
            0,
            max(boundary, 0) / q,
            epsabs=1e-12,
        )[0]
    else:
        # Independent Poisson-mixture gamma expectation including absorbing-zero mass.
        from scipy.stats import chi2, poisson

        atom = math.exp(-nc / 2)
        integral = atom * max(A - K, 0)
        for n in range(1, int(poisson.ppf(1 - 1e-14, nc / 2)) + 2):
            integral += (
                poisson.pmf(n, nc / 2)
                * quad(
                    lambda x, n=n: max(A * math.exp(-B * q * x) - K, 0) * chi2.pdf(x, 2 * n),
                    0,
                    max(boundary, 0) / q,
                    epsabs=1e-12,
                )[0]
            )
    assert row["price"] == pytest.approx(pt * integral, abs=2e-10)
    denominator = 1 + 2 * B * q
    laplace = denominator ** (-d / 2) * math.exp(-nc * B * q / denominator)
    assert pt * A * laplace == pytest.approx(pu, abs=1e-12)
    put = m.cir_bond_option(r, a, b, s, E, U, K, kind="put")["price"]
    assert row["price"] - put == pytest.approx(pu - K * pt, abs=1e-13)


@pytest.mark.parametrize(
    "a,b,s,r,E,U,K", [(0.1, 0.03, 0.07, 0.04, 2, 5, 0.85), (0, 0.03, 0.1, 0.04, 2, 5, 0.9)]
)
def test_cir_price_matches_independent_raw_q_discounted_endpoint_path_mc(a, b, s, r, E, U, K):
    target = model().cir_bond_option(r, a, b, s, E, U, K)["price"]
    n = 32768
    steps = 128
    rng = np.random.default_rng(3222026)
    rates = np.empty((n, steps + 1))
    rates[:, 0] = r
    for i in range(steps):
        rates[:, i + 1] = cir_transition(rates[:, i], a, b, s, E / steps, rng)
    payoff = np.maximum(cir_bond(rates[:, -1], a, b, s, U - E)["price"] - K, 0)
    samples = discounted_path_values(rates, np.linspace(0, E, steps + 1), payoff)
    se = samples.std(ddof=1) / math.sqrt(n)
    assert abs(samples.mean() - target) < 5 * se + 1e-5


def test_zero_expiry_vol_strike_and_invalid_coupon_domain():
    m = model()
    assert m.gaussian_bond_option(0, 5, 0, 0.01, 1, 0.9, 0.8)["price"] == pytest.approx(0.1)
    assert m.cir_bond_option(0.03, 0.1, 0.04, 0, 2, 5, 0)["price"] == pytest.approx(
        cir_bond(0.03, 0.1, 0.04, 0, 5)["price"]
    )
    with pytest.raises(ValueError):
        m.jamshidian_coupon_option(1, [2], [0], 100, lambda r, t: 1, lambda t, k, kind: 1)
