"""§31.2 original durations/local vol, independent Gaussian/Riccati/MC/PDE."""

import importlib
import math

import numpy as np
import pytest
from hullkit._short_rate_pde import discounted_path_values
from scipy.integrate import quad, solve_ivp
from scipy.linalg import solve_banded
from scipy.stats import ncx2


def model():
    return importlib.import_module("hullkit._short_rate_models")


@pytest.mark.parametrize(
    "a,b,s,r,T",
    [
        (0.1, 0.03, 0.01, 0.02, 5),
        (0.1, 0.1, 0.02, 0.1, 10),
        (0, 0.03, 0.01, -0.01, 4),
        (0.2, 0.04, 0, -0.005, 3),
        (1e-9, 0.03, 0.01, 0.02, 5),
    ],
)
def test_vasicek_bond_matches_independent_gaussian_kernel_integral_and_pde(a, b, s, r, T):
    row = model().vasicek_bond(r, a, b, s, T)

    def loading(u):
        return u if a == 0 else -math.expm1(-a * u) / a

    mean = r * loading(T) + b * (T - loading(T))
    variance = s * s * quad(lambda u: loading(u) ** 2, 0, T, epsabs=1e-14)[0]
    assert row["price"] == pytest.approx(math.exp(-mean + variance / 2), rel=1e-13)
    assert row["variance_integral"] == pytest.approx(variance, rel=1e-12, abs=1e-16)
    h = 1e-4
    dh = (
        model().vasicek_bond(r, a, b, s, T + h)["price"]
        - model().vasicek_bond(r, a, b, s, T - h)["price"]
    ) / (2 * h)
    residual = (
        -dh
        + a * (b - r) * (-row["B"] * row["price"])
        + 0.5 * s * s * row["B"] ** 2 * row["price"]
        - r * row["price"]
    )
    assert abs(residual) < 2e-10


@pytest.mark.parametrize(
    "a,b,s,r,T",
    [
        (0.1, 0.03, 0.07, 0.04, 4),
        (0.2, 0.01, 0.1, 0, 2),
        (0, 0.03, 0.1, 0.04, 2),
        (0.2, 0.04, 0, 0.04, 2),
        (0.1, 0.1, 0.02 / math.sqrt(0.1), 0.1, 10),
    ],
)
def test_cir_bond_matches_independent_riccati_ode_and_pde(a, b, s, r, T):
    row = model().cir_bond(r, a, b, s, T)
    solution = solve_ivp(
        lambda t, y: [1 - a * y[0] - 0.5 * s * s * y[0] ** 2, -a * b * y[0]],
        (0, T),
        [0, 0],
        rtol=2e-12,
        atol=2e-14,
    )
    B, logA = solution.y[:, -1]
    assert row["price"] == pytest.approx(math.exp(logA - B * r), rel=2e-12)
    assert row["B"] == pytest.approx(B, rel=2e-12)
    h = 1e-4
    dh = (
        model().cir_bond(r, a, b, s, T + h)["price"] - model().cir_bond(r, a, b, s, T - h)["price"]
    ) / (2 * h)
    residual = (
        -dh
        + a * (b - r) * (-row["B"] * row["price"])
        + 0.5 * s * s * r * row["B"] ** 2 * row["price"]
        - r * row["price"]
    )
    assert abs(residual) < 2e-10


def test_example_31_1_and_local_vol_matching_printed_numbers():
    row = model().vasicek_bond(0.04, 0.1, 0.05, 0.01, 4)
    assert row["B"] == pytest.approx(3.30, abs=0.005)
    assert 100 * 0.001 * row["B"] == pytest.approx(0.33, abs=0.005)
    assert 100 * 0.001 * 4 == pytest.approx(0.4)
    assert model().matching_cir_volatility(0.01, 0.04) == pytest.approx(0.05, abs=1e-14)
    for which in ["vasicek", "cir"]:
        price = model().vasicek_bond if which == "vasicek" else model().cir_bond
        r = 0.04
        s = 0.01 if which == "vasicek" else 0.05
        h = 1e-5
        sens = model().short_rate_bond_risk(which, r, 0.1, 0.05, s, [1, 2, 4], [0.03, 0.03, 1.03])

        def portfolio(rate, price=price, s=s):
            return sum(
                c * price(rate, 0.1, 0.05, s, t)["price"]
                for c, t in zip([0.03, 0.03, 1.03], [1, 2, 4], strict=True)
            )

        assert sens["duration"] == pytest.approx(
            -(portfolio(r + h) - portfolio(r - h)) / (2 * h * portfolio(r)), rel=1e-9
        )
        assert sens["convexity"] == pytest.approx(
            (portfolio(r + h) - 2 * portfolio(r) + portfolio(r - h)) / (h * h * portfolio(r)),
            rel=2e-6,
        )
        assert sens["relative_diffusion"] < 0


@pytest.mark.parametrize(
    "a,b,s,r,T",
    [(0.2, 0.04, 0.05, 0.04, 1), (0.1, 0.005, 0.1, 0.0001, 0.25), (0.2, 0.01, 0.1, 0, 2)],
)
def test_cir_transition_matches_independent_density_moments_and_laplace(a, b, s, r, T):
    law = model().cir_transition_law(r, a, b, s, T)
    dist = ncx2(law["degrees"], law["noncentrality"])
    q = law["scale"]
    upper = dist.ppf(1 - 1e-12)
    mean = q * quad(lambda x: x * dist.pdf(x), 0, upper, epsabs=1e-9)[0]
    second = q * q * quad(lambda x: x * x * dist.pdf(x), 0, upper, epsabs=1e-8)[0]
    laplace = quad(lambda x: math.exp(-0.7 * q * x) * dist.pdf(x), 0, upper, epsabs=1e-11)[0]
    assert law["mean"] == pytest.approx(mean, abs=3e-12)
    assert law["variance"] == pytest.approx(second - mean * mean, abs=3e-12)
    assert model().cir_transition_laplace(0.7, r, a, b, s, T) == pytest.approx(laplace, abs=2e-11)
    sample = model().cir_transition(r, a, b, s, T, np.random.default_rng(3122026), size=65536)
    assert np.all(sample >= 0)
    assert abs(sample.mean() - mean) < 5 * sample.std(ddof=1) / math.sqrt(sample.size)


def test_zero_immigration_cir_absorption_atom_and_degenerate_cases():
    law = model().cir_transition_law(0.04, 0, 0.03, 0.1, 2)
    assert law["zero_atom"] == pytest.approx(math.exp(-4), rel=1e-12)
    rng = np.random.default_rng(3122026)
    sample = model().cir_transition(0.04, 0, 0.03, 0.1, 2, rng, size=131072)
    probability = np.mean(sample == 0)
    p = math.exp(-4)
    assert abs(probability - p) < 5 * math.sqrt(p * (1 - p) / sample.size)
    assert abs(sample.mean() - 0.04) < 5 * sample.std(ddof=1) / math.sqrt(sample.size)
    assert model().cir_transition(0, 0, 0.03, 0.1, 2, rng, size=3) == pytest.approx([0, 0, 0])
    assert model().cir_transition(0.03, 0.1, 0.05, 0, 2, rng, size=3) == pytest.approx(
        np.full(3, 0.05 + (0.03 - 0.05) * math.exp(-0.2))
    )
    assert model().cir_bond(0.04, 0.1, 0.05, 0.01, 0)["price"] == pytest.approx(1)


def test_cir_exact_endpoint_path_discount_matches_analytic_bond_with_time_error_budget():
    m = model()
    rng = np.random.default_rng(3122026)
    n = 32768
    steps = 128
    T = 2.0
    r0 = 0.04
    a = 0.1
    b = 0.03
    s = 0.07
    rates = np.empty((n, steps + 1))
    rates[:, 0] = r0
    for i in range(steps):
        rates[:, i + 1] = m.cir_transition(rates[:, i], a, b, s, T / steps, rng)
    samples = discounted_path_values(rates, np.linspace(0, T, steps + 1))
    se = samples.std(ddof=1) / math.sqrt(n)
    assert abs(samples.mean() - m.cir_bond(r0, a, b, s, T)["price"]) < 5 * se + 1e-5


def rb_pde(r0, mu, sigma, T, N):
    # Log-rate finite differences + Crank-Nicolson, independent of path quadrature.
    x = np.linspace(math.log(0.00001), math.log(2.0), N + 1)
    dx = x[1] - x[0]
    r = np.exp(x)
    nt = 1000
    dt = T / nt
    drift = mu - 0.5 * sigma * sigma
    low = 0.5 * sigma * sigma / dx**2 - drift / (2 * dx)
    up = 0.5 * sigma * sigma / dx**2 + drift / (2 * dx)
    diag = -sigma * sigma / dx**2 - r[1:-1]
    band = np.zeros((3, N - 1))
    band[0, 1:] = -dt * up / 2
    band[1] = 1 - dt * diag / 2
    band[2, :-1] = -dt * low / 2
    v = np.ones(N + 1)
    for j in range(nt):
        rhs = (1 + dt * diag / 2) * v[1:-1] + dt * low / 2 * v[:-2] + dt * up / 2 * v[2:]
        rhs[0] += dt * low / 2  # left boundary ~1
        rhs[-1] += dt * up / 2 * math.exp(-r[-1] * (j + 1) * dt)
        v[1:-1] = solve_banded((1, 1), band, rhs)
        v[0] = 1
        v[-1] = math.exp(-r[-1] * (j + 1) * dt)
    return float(np.interp(math.log(r0), x, v))


def test_rb_exact_gbm_endpoints_discount_mc_matches_independent_pde_and_refinement():
    m = model()
    r0 = 0.04
    mu = 0.05
    sigma = 0.15
    T = 3
    rng = np.random.default_rng(3122026)
    pairs = 8192
    steps = 256
    dt = T / steps
    dw = rng.standard_normal((pairs, steps)) * math.sqrt(dt)
    dw = np.vstack([dw, -dw])
    values = {}
    for count in [16, 64, 256]:
        inc = dw.reshape(2 * pairs, count, steps // count).sum(axis=2)
        grid = np.linspace(0, T, count + 1)
        paths = m.rb_paths(r0, mu, sigma, grid, inc)
        price = discounted_path_values(paths, grid)
        values[count] = (price[:pairs] + price[pairs:]) / 2
    se = values[256].std(ddof=1) / math.sqrt(pairs)
    coarse, fine = [rb_pde(r0, mu, sigma, T, n) for n in [600, 1200]]
    assert abs(fine - coarse) < 5e-5
    assert abs(values[256].mean() - fine) < 5 * se + 5e-5
    assert abs((values[64] - values[256]).mean()) < abs((values[16] - values[256]).mean()) * 0.1
    assert m.rb_deterministic_bond(r0, mu, T) == pytest.approx(
        math.exp(-r0 * math.expm1(mu * T) / mu), rel=1e-13
    )
    zero = m.rb_paths(0, mu, sigma, [0, 1], np.zeros((2, 1)))
    assert discounted_path_values(zero, [0, 1]) == pytest.approx([1, 1])


def test_feller_boundary_vasicek_negative_rates_and_reflection_bias():
    from scipy.special import ndtr

    m = model()
    a = 0.1
    b = 0.005
    r = 0.0001
    T = 0.25
    s = 0.1
    law = m.cir_transition_law(r, a, b, s, T)
    assert not law["feller"]
    assert law["zero_atom"] == pytest.approx(0)
    vas = m.vasicek_bond(r, a, b, 0.005, T)
    assert ndtr(-vas["mean_rate"] / math.sqrt(vas["variance_rate"])) > 0.1
    euler_mean = r + a * (b - r) * T
    sd = s * math.sqrt(r * T)
    negative_probability = ndtr(-euler_mean / sd)
    reflected_mean = sd * math.sqrt(2 / math.pi) * math.exp(
        -0.5 * (euler_mean / sd) ** 2
    ) + euler_mean * (1 - 2 * negative_probability)
    assert negative_probability > 0.1
    assert reflected_mean - law["mean"] > 1e-4
    assert m.cir_transition_law(0.04, 0.2, 0.04, 0.05, 1)["feller"]


def test_author_practice_bond_and_coupon_numbers_remain_distinct_from_body_pins():
    m = model()
    assert m.vasicek_bond(0.02, 0.1, 0.03, 0.01, 5)["price"] == pytest.approx(0.8966, abs=0.00005)
    row = m.short_rate_bond_risk(
        "vasicek", 0.01, 0.13, 0.012, 0.01, [0.5, 1, 1.5, 2], [1.5, 1.5, 1.5, 101.5]
    )
    assert row["price"] == pytest.approx(103.9083, abs=0.00005)
    assert row["duration"] == pytest.approx(1.7254, abs=0.00005)
    bumped = sum(
        c * m.vasicek_bond(0.0105, 0.13, 0.012, 0.01, t)["price"]
        for c, t in zip([1.5, 1.5, 1.5, 101.5], [0.5, 1, 1.5, 2], strict=True)
    )
    assert bumped == pytest.approx(103.8187, abs=0.00005)
