"""§32.6 has instrument tenors, but no published market quote prices."""

import importlib
import math
from itertools import pairwise

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._short_rate_calibration")


def curve(t):
    return math.exp(-0.04 * t)


KNOTS = [0.0, 5.0, 7.0, 10.0]
SIGMAS = [0.009, 0.012, 0.015]


def independent_price(q, a, knots, sigmas):
    E = q["expiry"]

    def sigma(u):
        return sigmas[min(np.searchsorted(knots, u, side="right") - 1, len(sigmas) - 1)]

    variance = sum(
        quad(lambda u: sigma(u) ** 2 * math.exp(-2 * a * (E - u)), lo, min(hi, E), epsabs=1e-14)[0]
        for lo, hi in pairwise(knots)
        if lo < E
    )
    bs = np.array([quad(lambda u: math.exp(-a * u), 0, t - E)[0] for t in q["payment_times"]])
    forward_bonds = np.array([curve(t) / curve(E) for t in q["payment_times"]])
    cash = q["fixed_rate"] * np.asarray(q["accruals"])
    cash[-1] += 1
    sd = math.sqrt(variance)

    def bond(z):
        return float(cash @ (forward_bonds * np.exp(-bs * sd * z - 0.5 * variance * bs * bs)))

    root = brentq(lambda z: bond(z) - 1, -15, 15)
    sign = 1 if q["kind"] == "receiver" else -1
    bounds = (-12, root) if sign == 1 else (root, 12)
    return (
        q["notional"]
        * curve(E)
        * quad(lambda z: max(sign * (bond(z) - 1), 0) * norm.pdf(z), *bounds, epsabs=1e-12)[0]
    )


def quotes(a=0.1):
    rows = model().diagonal_basket([5, 6, 7, 8, 9], 10, math.expm1(0.04))
    for q in rows:
        q["price"] = independent_price(q, a, KNOTS, SIGMAS)
    return rows


def test_source_five_bermudan_calibration_instruments():
    rows = quotes()
    assert [(q["expiry"], q["payment_times"][-1] - q["expiry"]) for q in rows] == [
        (5, 5),
        (6, 4),
        (7, 3),
        (8, 2),
        (9, 1),
    ]
    for q in rows:
        actual = model().european_swaption(q, curve, 0.1, KNOTS, SIGMAS)
        assert actual["price"] == pytest.approx(q["price"], abs=2e-12)


@pytest.mark.parametrize("a", [0, 0.1])
def test_piecewise_variance_independent_kernel_integration_and_last_interval_extension(a):
    m = model()
    for E in [0, 2, 5, 6, 9, 12]:
        extended = [*KNOTS, 12.0] if E > 10 else KNOTS
        ss = [*SIGMAS, SIGMAS[-1]] if E > 10 else SIGMAS
        target = sum(
            quad(lambda u, s=s, E=E: s * s * math.exp(-2 * a * (E - u)), lo, min(hi, E))[0]
            for lo, hi, s in zip(extended[:-1], extended[1:], ss, strict=True)
            if lo < E
        )
        assert m.piecewise_rate_variance(E, a, KNOTS, SIGMAS) == pytest.approx(target, abs=1e-14)


@pytest.mark.parametrize("start", [[0.005, 0.005, 0.005], [0.02, 0.01, 0.006]])
def test_lm_fixed_a_recovers_synthetic_sigmas_and_independent_heldout(start):
    m = model()
    rows = quotes()
    result = m.calibrate_gaussian(rows, curve, KNOTS, start, 0.1)
    assert result["success"]
    assert result["sigmas"] == pytest.approx(SIGMAS, rel=2e-7)
    assert result["price_sse"] < 1e-20
    heldout = dict(rows[2], fixed_rate=0.05)
    assert m.european_swaption(heldout, curve, result["a"], KNOTS, result["sigmas"])[
        "price"
    ] == pytest.approx(independent_price(heldout, 0.1, KNOTS, SIGMAS), abs=2e-11)
    assert len(result["price_jacobian_singular_values"]) == 3
    assert result["price_jacobian_singular_values"][-1] > 0.001


def test_joint_a_fit_and_regularization_fit_smoothness_tradeoff():
    m = model()
    rows = quotes()
    for E, end in [(1, 4), (2, 8), (4, 10)]:
        q = m.diagonal_basket([E], end, 0.045)[0]
        q["price"] = independent_price(q, 0.1, KNOTS, SIGMAS)
        rows.append(q)
    result = m.calibrate_gaussian(rows, curve, KNOTS, [0.01, 0.011, 0.012], 0.07, fit_a=True)
    assert result["a"] == pytest.approx(0.1, abs=3e-7)
    assert result["sigmas"] == pytest.approx(SIGMAS, rel=3e-7)
    free = m.calibrate_gaussian(rows, curve, KNOTS, [0.01] * 3, 0.1)
    smooth = m.calibrate_gaussian(
        rows, curve, KNOTS, [0.01] * 3, 0.1, jump_weight=0.1, curvature_weight=0.1
    )
    assert smooth["price_sse"] > free["price_sse"]
    assert np.linalg.norm(np.diff(smooth["sigmas"])) < np.linalg.norm(np.diff(free["sigmas"]))

    # Combined penalties constrain their sum, not every individual term.
    def rough(sig):
        return np.sum(np.diff(sig) ** 2) + np.sum(np.diff(sig, n=2) ** 2)

    assert rough(smooth["sigmas"]) < rough(free["sigmas"])
    curved = [dict(q, price=independent_price(q, 0.1, KNOTS, [0.009, 0.016, 0.011])) for q in rows]
    free_c = m.calibrate_gaussian(curved, curve, KNOTS, [0.01] * 3, 0.1)
    smooth_c = m.calibrate_gaussian(curved, curve, KNOTS, [0.01] * 3, 0.1, curvature_weight=0.1)
    assert abs(np.diff(smooth_c["sigmas"], n=2)[0]) < abs(np.diff(free_c["sigmas"], n=2)[0])
    assert smooth_c["price_sse"] > free_c["price_sse"]


def test_fixed_a_black_caplet_price_hw_sigma_roundtrip_and_zero_vol():
    m = model()
    E, U = 5.0, 6.0
    F = math.expm1(0.04)
    black = 0.2
    result = m.implied_hw_caplet_sigma(E, U, 1, F, black, curve, 0.1)
    target = curve(U) * F * (2 * norm.cdf(0.5 * black * math.sqrt(E)) - 1)
    assert result["black_price"] == pytest.approx(target, abs=1e-14)
    assert result["hw_price"] == pytest.approx(target, abs=1e-12)
    # Independent integration of the expiry-measure lognormal zero bond.
    loading = quad(lambda u: math.exp(-0.1 * u), 0, U - E)[0]
    kernel = quad(lambda u: math.exp(-0.2 * (E - u)), 0, E)[0]
    bond_forward = curve(U) / curve(E)
    bond_strike = 1 / (1 + F)

    def quadrature_price(sigma):
        sd = sigma * loading * math.sqrt(kernel)
        if sd == 0:
            return curve(E) * (1 + F) * max(bond_strike - bond_forward, 0)
        boundary = (math.log(bond_strike / bond_forward) + 0.5 * sd * sd) / sd
        return (
            curve(E)
            * (1 + F)
            * quad(
                lambda z: (
                    max(bond_strike - bond_forward * math.exp(sd * z - 0.5 * sd * sd), 0)
                    * norm.pdf(z)
                ),
                -12,
                boundary,
                epsabs=1e-13,
            )[0]
        )

    independent_sigma = brentq(lambda s: quadrature_price(s) - target, 0.001, 0.1, xtol=1e-13)
    assert result["sigma"] == pytest.approx(independent_sigma, abs=1e-11)
    assert result["sigma"] != pytest.approx(black)
    assert m.implied_hw_caplet_sigma(E, U, 1, F, 0, curve, 0.1)["sigma"] == pytest.approx(0)


def test_bermudan_event_mesh_and_exercise_order_on_same_piecewise_sigma_tree():
    m = model()
    E = [5, 6, 7, 8, 9]
    pay = np.arange(6, 11)
    fixed = math.expm1(0.04)
    berm = m.bermudan_swaption(E, pay, np.ones(5), fixed, curve, 0.1, KNOTS, SIGMAS, max_step=0.25)
    euro = m.bermudan_swaption(
        [9], pay, np.ones(5), fixed, curve, 0.1, KNOTS, SIGMAS, max_step=0.25
    )
    wider = m.bermudan_swaption(
        [5, 7, 9], pay, np.ones(5), fixed, curve, 0.1, KNOTS, SIGMAS, max_step=0.25
    )
    assert euro["price"] <= wider["price"] <= berm["price"]
    assert berm["tree"]["max_curve_residual"] < 1e-12
    assert berm["tree"]["min_probability"] >= 0
    assert berm["exercise_times"] == pytest.approx(E)
    # Single exercise at 9 with only the last payment is a European 9x1.
    q = m.diagonal_basket([9], 10, fixed)[0]
    exact = independent_price(q, 0.1, KNOTS, SIGMAS)
    assert euro["price"] == pytest.approx(exact, abs=0.0005)
    finer = m.bermudan_swaption(
        [9], pay, np.ones(5), fixed, curve, 0.1, KNOTS, SIGMAS, max_step=0.125
    )
    assert abs(finer["price"] - exact) < abs(euro["price"] - exact)


def test_zero_sigma_deterministic_swaption_and_minimal_domain_checks():
    m = model()
    q = m.diagonal_basket([1], 3, 0.06)[0]
    bond = sum(0.06 * curve(t) / curve(1) for t in [2, 3]) + curve(3) / curve(1)
    assert m.european_swaption(q, curve, 0, [0, 3], [0])["price"] == pytest.approx(
        curve(1) * max(1 - bond, 0)
    )
    with pytest.raises(ValueError):
        m.piecewise_rate_variance(-1, 0.1, [0, 2], [0.01])
    with pytest.raises(ValueError):
        m.calibrate_gaussian([q], curve, KNOTS, [0.01] * 3, 0.1)
    with pytest.raises(ValueError):
        m.diagonal_basket([11], 10, 0.04)
