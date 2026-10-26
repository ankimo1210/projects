"""DSINC American recursion: payoff transform, time quadrature, boundary roots and paper anchors."""

import math
from dataclasses import replace

import numpy as np
import pytest
from hullkit._dsinc_american import (
    american_put,
    local_boundary,
    payoff_transform,
    premium_with_boundary,
    scan_spacing,
)
from hullkit._dsinc_spectral import build_propagators, european_put
from hullkit._dsinc_types import (
    BOUNDARY_STATUS,
    PricingFailure,
    PutContract,
    SpectralConfig,
    VarianceModel,
)
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
SCAN = np.linspace(0.70, 0.95, 126)
S0 = SpectralConfig(
    n_time=100,
    n_var=160,
    log_var_bounds=(math.log(2e-4), math.log(2.0)),
    chi=0.5,
    panels=PANELS,
    points_per_panel=12,
)
SMALL = SpectralConfig(
    n_time=40,
    n_var=24,
    log_var_bounds=(math.log(0.005), math.log(0.3)),
    chi=0.5,
    panels=(0.0, 2.0, 5.0, 10.0, 20.0, 40.0),
    points_per_panel=4,
)
CONSTANT = SpectralConfig(
    n_time=2,
    n_var=4,
    log_var_bounds=(math.log(0.02), math.log(0.08)),
    chi=0.5,
    panels=PANELS,
    points_per_panel=12,
)
RD, RF, VAR = 0.05, 0.02, 0.04


def code(name):
    return BOUNDARY_STATUS[name]


def constant_propagators(cfg):
    zero = np.zeros(cfg.n_var)
    return build_propagators(
        CONTRACT, MODEL, cfg, coefficients=(zero, zero, zero, np.full(cfg.n_var, VAR))
    )


def j_term(x, tau, c):
    """E[(rd - rf e^X) 1{X <= c}] for X ~ N(x + (rd - rf - v/2) tau, v tau)."""
    m, s = x + (RD - RF - VAR / 2) * tau, math.sqrt(VAR * tau)
    return RD * norm.cdf((c - m) / s) - RF * math.exp(m + s * s / 2) * norm.cdf((c - m - s * s) / s)


def bsm_put(x, tau):
    s = math.sqrt(VAR * tau)
    d1 = (x + (RD - RF + VAR / 2) * tau) / s
    return math.exp(-RD * tau) * norm.cdf(s - d1) - math.exp(x - RF * tau) * norm.cdf(-d1)


class Shifted:
    """R_i(x) = g(x - shift_i): one residual profile moved by a node shift."""

    def __init__(self, g, shifts):
        self.g, self.shifts = g, np.asarray(shifts, float)

    def at(self, x):
        return self.g(np.asarray(x, float) - self.shifts)

    def on_grid(self, grid):
        return self.g(np.asarray(grid, float)[:, None] - self.shifts[None, :])


@pytest.fixture(scope="module")
def s0_propagators():
    return build_propagators(CONTRACT, MODEL, S0)


@pytest.fixture(scope="module")
def s0_result(s0_propagators):
    return american_put(CONTRACT, MODEL, np.r_[SPOTS, SCAN], S0, propagators=s0_propagators)


@pytest.mark.parametrize("omega", [0.5, 3.0, 17.0])
def test_payoff_transform_matches_quadrature(omega):
    s, c = 1j * omega - 0.5, -0.2

    def part(x, imag):
        value = (((RD - RF * math.exp(x)) if x <= c else 0.0) - RD) * np.exp(s * x)
        return value.imag if imag else value.real

    expected = sum(
        (1j if imag else 1.0) * quad(part, lo, hi, args=(imag,), limit=400)[0]
        for imag in (False, True)
        for lo, hi in ((-60.0, c), (c, 60.0))
    )
    got = payoff_transform(np.array([omega]), 0.5, np.array([c]), CONTRACT)
    assert got.shape == (1, 1) and abs(got[0, 0] - expected) <= 1e-8  # planning run: 1.5e-9


def test_flat_boundary_premium_matches_the_trapezoid_sum():
    cfg = replace(CONSTANT, n_time=100)
    got = premium_with_boundary(
        CONTRACT, constant_propagators(cfg), np.full((101, 4), -0.25), SPOTS
    )[:, 0]
    dt = 0.5 / 100
    weights = np.r_[
        np.full(99, dt), dt / 2
    ]  # t_1 .. t_N; t_0 lies outside the exercise region for these spots
    expected = [
        sum(
            w * math.exp(-RD * k * dt) * j_term(math.log(s), k * dt, -0.25)
            for k, w in zip(range(1, 101), weights, strict=True)
        )
        for s in SPOTS
    ]
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-6)  # planning run: 2.4e-7


def two_step_reference():
    """Boundaries and t0 prices for T = .5, N = 2 from explicit normal integrals."""
    dt = 0.25

    def residual(x, later):
        rhs = bsm_put(x, 2 * dt - later * dt) + dt / 4 * (RD - RF * math.exp(x))
        return 1.0 - math.exp(x) - rhs - later_terms(x, later)

    def later_terms(x, later):
        if later == 1:  # boundary at t_1: only t_2 (weight dt/2, boundary 0) follows
            return dt / 2 * math.exp(-RD * dt) * j_term(x, dt, 0.0)
        return dt * math.exp(-RD * dt) * j_term(x, dt, x1) + dt / 2 * math.exp(
            -2 * RD * dt
        ) * j_term(x, 2 * dt, 0.0)

    x1 = brentq(lambda x: residual(x, 1), -1.0, -1e-9, xtol=1e-14)
    x0 = brentq(lambda x: residual(x, 0), -1.0, -1e-9, xtol=1e-14)
    prices = [
        bsm_put(math.log(s), 2 * dt) + later_terms(math.log(s), 0) for s in SPOTS
    ]  # no t_0 endpoint term
    return (x0, x1), prices


def test_two_step_american_matches_explicit_sums():
    (x0, x1), prices = two_step_reference()  # planning run: x*_0 = -0.20568247, x*_1 = -0.16491088
    out = american_put(CONTRACT, MODEL, SPOTS, CONSTANT, propagators=constant_propagators(CONSTANT))
    np.testing.assert_allclose(
        out.log_boundary[:, 0], [x0, x1, 0.0], rtol=0, atol=2e-6
    )  # planning run: 7.1e-7
    np.testing.assert_allclose(out.american, prices, rtol=0, atol=2e-7)  # planning run: 4.1e-8


def test_single_crossing_root():
    out = local_boundary(Shifted(lambda u: -u, [-0.15, -0.05]), np.array([-0.1, -0.1]), S0)
    np.testing.assert_allclose(out.roots, [-0.15, -0.05], rtol=0, atol=1e-10)
    assert list(out.status) == [code("single")] * 2 and list(out.width) == [0.1, 0.1]


def test_missing_and_reversed_brackets_fail():
    flat = local_boundary(Shifted(lambda u: -1.0 + 0.0 * u, [0.0]), np.array([-0.1]), S0)
    reversed_ = local_boundary(Shifted(lambda u: u, [-0.15]), np.array([-0.1]), S0)
    assert flat.status[0] == code("missing_sign_change") and np.isnan(flat.roots[0])
    assert reversed_.status[0] == code("wrong_orientation") and np.isnan(reversed_.roots[0])


def test_multiple_crossings_choose_upper_or_lower():
    def g(
        u,
    ):  # crossings at x = -0.15 (+ to -), -0.12 (- to +), -0.09 (+ to -) for a shift of -0.12
        return -1e3 * (u + 0.03) * u * (u - 0.03)

    for crossing, root in (("upper", -0.09), ("lower", -0.15)):
        out = local_boundary(Shifted(g, [-0.12]), np.array([-0.1]), replace(S0, crossing=crossing))
        assert out.status[0] == code("multiple_crossings") and out.crossings[0] == 3
        assert out.roots[0] == pytest.approx(root, abs=1e-10)
        assert out.spread[0] == pytest.approx(0.06, abs=2 * scan_spacing(S0))


def test_zero_runs_are_ambiguous_but_a_single_zero_is_a_crossing():
    def flat(u):  # exact zeros on [-0.05, 0.05]
        return np.where(u < -0.05, 1.0, np.where(u > 0.05, -1.0, 0.0))

    assert local_boundary(Shifted(flat, [-0.1]), np.array([-0.1]), S0).status[0] == code(
        "ambiguous_contact"
    )
    delta = scan_spacing(S0)
    on_grid = local_boundary(
        Shifted(lambda u: -u, [-80 * delta]), np.array([-0.1]), S0
    )  # root exactly on a scan point
    assert on_grid.status[0] == code("single") and on_grid.roots[0] == pytest.approx(
        -80 * delta, abs=1e-10
    )


def test_nonfinite_and_maxiter_fail():
    def holed(u):
        return np.where(np.abs(u) < 0.01, np.nan, -u)

    def jump(u):  # a sign change with no zero: bisection never reaches |R| <= tol
        return np.where(u < 0.0, 1.0, -1.0)

    assert local_boundary(Shifted(holed, [-0.12]), np.array([-0.1]), S0).status[0] == code(
        "nonfinite"
    )
    maxiter = local_boundary(Shifted(jump, [-0.12]), np.array([-0.1]), S0)
    assert maxiter.status[0] == code("maxiter") and maxiter.iterations[0] == 60


def test_failure_records_the_whole_time_slice():
    with pytest.raises(PricingFailure) as info:
        american_put(CONTRACT, MODEL, SPOTS, replace(SMALL, root_widths=(1e-4,)))
    details = info.value.details
    status = np.asarray(details["boundary_status"])
    assert info.value.code == "boundary_failure" and details["time_index"] == 39
    assert np.all(status[39] == code("missing_sign_change")) and np.all(
        status[:39] == code("not_run")
    )
    assert np.all(status[40] == code("terminal")) and np.all(
        np.isnan(np.asarray(details["log_boundary"])[:40])
    )
    assert details["last_completed_time_index"] == 40


def test_zero_expiry_returns_the_payoff_without_a_boundary():
    out = american_put(replace(CONTRACT, expiry=0.0), MODEL, SPOTS, SMALL)
    payoff = np.maximum(1.0 - SPOTS, 0.0)
    np.testing.assert_array_equal(out.american, payoff)
    np.testing.assert_array_equal(out.european, payoff)
    np.testing.assert_array_equal(out.early_exercise_premium, np.zeros(3))
    assert out.times.shape == (0,) and out.log_variances.shape == (0,)
    assert out.log_boundary.shape == out.boundary_status.shape == (0, 0)
    assert out.diagnostics["boundary_status"] == "not_applicable"


def test_spot_order_and_strike_homogeneity():
    base = american_put(CONTRACT, MODEL, SPOTS, SMALL)
    shuffled = american_put(CONTRACT, MODEL, np.array([1.1, 0.9, 1.0, 0.9]), SMALL)
    np.testing.assert_allclose(shuffled.american, base.american[[2, 0, 1, 0]], rtol=0, atol=1e-15)
    scaled = american_put(replace(CONTRACT, strike=100.0), MODEL, 100.0 * SPOTS, SMALL)
    np.testing.assert_allclose(scaled.american, base.american, rtol=0, atol=1e-15)
    deep = american_put(
        CONTRACT, MODEL, np.array([0.55, 0.6]), SMALL
    )  # below every node's t0 boundary (min -0.38)
    np.testing.assert_allclose(deep.american, [0.45, 0.4], rtol=0, atol=1e-14)


def test_prices_near_the_boundary_stay_within_the_bound_tolerance(s0_result):
    gap = s0_result.american[3:] - np.maximum(1.0 - SCAN, 0.0)
    assert (
        gap.min() >= -2e-5
    )  # planning run: -1.54e-5 at S/K = 0.832 (the v0 spline mixes exercised and continuation nodes)
    assert s0_result.diagnostics["bounds"]["american_minus_payoff_min"] == pytest.approx(
        gap.min(), abs=1e-15
    )
    assert np.all(np.diff(s0_result.american[3:]) < 0.0)


def test_bound_violations_are_reported_not_clipped():
    out = american_put(replace(CONTRACT, expiry=0.01), MODEL, SPOTS, replace(SMALL, n_time=1))
    assert (
        out.european[2] < -1e-3
    )  # cutoff 40 cannot resolve T = .01 (planning run: -1.09e-3); the raw value is kept
    assert out.diagnostics["bounds"]["european_lower_gap_min"] == pytest.approx(
        out.european[2], abs=1e-12
    )


def test_s0_reproduces_tables_3b_and_4(s0_result):
    np.testing.assert_allclose(
        s0_result.american[:3], [0.107601, 0.048662, 0.019499], rtol=0, atol=6e-6
    )
    np.testing.assert_allclose(
        s0_result.european[:3], [0.102557, 0.047224, 0.019105], rtol=0, atol=6e-6
    )
    np.testing.assert_allclose(
        s0_result.early_exercise_premium[:3], [0.005044, 0.001438, 0.000394], rtol=0, atol=6e-6
    )


def test_s0_boundary_status_and_residuals(s0_result):
    status = s0_result.boundary_status
    assert status.shape == (101, 160) and np.all(status[-1] == code("terminal"))
    assert not np.isin(status[:-1], [-1, 2, 3, 4, 5, 6]).any()
    rows, cols = np.nonzero(status == code("multiple_crossings"))
    assert (
        rows.size > 0 and np.exp(s0_result.log_variances[cols]).max() < 0.01
    )  # planning run: 58 cases, v <= 6.75e-4
    assert (
        np.all(s0_result.log_boundary[-1] == 0.0)
        and s0_result.diagnostics["max_root_residual"] <= 1e-8
    )
    assert s0_result.diagnostics["generator"]["scheme_nonmonotone"] is True


def test_american_and_european_paths_share_the_european_leg(s0_result, s0_propagators):
    alone = european_put(CONTRACT, MODEL, SPOTS, S0, propagators=s0_propagators)
    np.testing.assert_allclose(s0_result.european[:3], alone, rtol=0, atol=1e-13)
