"""DSINC fixed-frequency propagation and European prices (3/2 and Heston controls)."""

import math
from dataclasses import replace

import numpy as np
import pytest
from hullkit import bsm
from hullkit._dsinc_spectral import (
    _assemble_generator,
    build_propagators,
    coefficient_arrays,
    european_put,
    frequency_generator,
    frequency_rule,
    generator_diagnostics,
    interpolate_at_variance,
    variance_grid,
)
from hullkit._dsinc_types import PutContract, SpectralConfig, VarianceModel
from hullkit.stochastic_volatility import heston_price
from scipy.interpolate import CubicSpline
from scipy.linalg import expm

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
THREE_HALVES = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
HESTON = VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
HESTON_BOUNDS = (math.log(0.002), math.log(0.4))


def config(n_var=160, bounds=(math.log(2e-4), math.log(2.0)), **changes):
    base = dict(
        n_time=100, n_var=n_var, log_var_bounds=bounds, chi=0.5, panels=PANELS, points_per_panel=12
    )
    return SpectralConfig(**(base | changes))


def constant_variance(cfg, variance=0.04):
    zero = np.zeros(cfg.n_var)
    return build_propagators(
        CONTRACT, THREE_HALVES, cfg, coefficients=(zero, zero, zero, np.full(cfg.n_var, variance))
    )


@pytest.fixture(scope="module")
def heston_base():
    return european_put(CONTRACT, HESTON, SPOTS, config(bounds=HESTON_BOUNDS))


def test_frequency_rule_is_panelwise_gauss_legendre():
    omega, weights = frequency_rule(config())
    assert omega.shape == weights.shape == (108,) and np.all(np.diff(omega) > 0)
    assert weights.sum() == pytest.approx(640.0, rel=1e-13)
    omega, weights = frequency_rule(config(panels=(0.0, 2.0, 5.0), points_per_panel=4))
    assert np.sum(weights * omega**7) == pytest.approx(5.0**8 / 8, rel=1e-12)


def test_log_variance_coefficients_follow_ito():
    v = np.geomspace(1e-3, 2.0, 7)
    cases = (
        (THREE_HALVES, 20.0 * v * (0.04 - v), 4.0 * v**1.5),
        (HESTON, 2.0 * (0.04 - v), 0.2 * np.sqrt(v)),
    )
    for model, drift, diffusion in cases:  # dv = drift dt + diffusion dW, zeta = log v
        a, b, sqrt_v_a = coefficient_arrays(model, v)
        np.testing.assert_allclose(a, diffusion / v, rtol=1e-14)
        np.testing.assert_allclose(b, drift / v - diffusion**2 / (2 * v**2), rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(sqrt_v_a, np.sqrt(v) * a, rtol=1e-14)


def test_both_models_share_one_generator_path():
    z = variance_grid(config(n_var=12))
    for model in (THREE_HALVES, HESTON):
        k = -3.0 - 0.5j
        direct = _assemble_generator(
            z, *coefficient_arrays(model, np.exp(z)), np.exp(z), k, 0.05, 0.02, model.rho
        )
        np.testing.assert_array_equal(frequency_generator(CONTRACT, model, z, k), direct)


def test_constant_variance_generator_is_the_bsm_exponent():
    z, zero, v = variance_grid(config(n_var=6)), np.zeros(6), np.full(6, 0.04)
    for omega in (0.5, 7.0, 300.0):
        k = -omega - 0.5j
        exponent = (
            1j * k * (0.05 - 0.02 - 0.04 / 2) - 0.5 * k * k * 0.04
        )  # log E exp(ik dX) / dt for the BSM log-spot
        m = expm(0.005 * _assemble_generator(z, zero, zero, zero, v, k, 0.05, 0.02, -0.5))
        np.testing.assert_allclose(m, np.exp(0.005 * exponent) * np.eye(6), rtol=0, atol=1e-11)


def test_zero_frequency_preserves_constants():
    for model, cfg in ((THREE_HALVES, config()), (HESTON, config(bounds=HESTON_BOUNDS))):
        z = variance_grid(cfg)
        m = expm(0.005 * frequency_generator(CONTRACT, model, z, 0.0))
        np.testing.assert_allclose(m @ np.ones(z.size), 1.0, rtol=0, atol=1e-12)


def test_neumann_ghost_rows_are_second_order():
    errors = []
    for n in (41, 81):
        z = variance_grid(config(n_var=n, bounds=(math.log(0.01), math.log(0.5))))
        w = math.pi / (z[-1] - z[0])
        f, fp, fpp = (
            np.cos(w * (z - z[0])),
            -w * np.sin(w * (z - z[0])),
            -(w**2) * np.cos(w * (z - z[0])),
        )
        a, b, _ = coefficient_arrays(THREE_HALVES, np.exp(z))
        applied = frequency_generator(CONTRACT, THREE_HALVES, z, 0.0).real @ f
        errors.append(np.max(np.abs(applied - (0.5 * a**2 * fpp + b * fp))))
    assert 1.8 < math.log2(errors[0] / errors[1]) < 2.2  # planning run: 1.997


def test_reciprocal_variance_mean_matches_cir():
    tau = 0.5
    exact = math.exp(-0.8 * tau) / 0.04 + 45.0 * (
        1.0 - math.exp(-0.8 * tau)
    )  # u = 1/v is CIR: du = (36 - 0.8u)dt - 4 sqrt(u) dW
    errors, steps = [], []
    for n in (160, 240, 320):
        z = variance_grid(config(n_var=n))
        u = expm(tau * frequency_generator(CONTRACT, THREE_HALVES, z, 0.0).real) @ np.exp(-z)
        errors.append(abs(CubicSpline(z, u)(math.log(0.04)) - exact) / exact)
        steps.append(z[1] - z[0])
    orders = [
        math.log(errors[i] / errors[i + 1]) / math.log(steps[i] / steps[i + 1]) for i in range(2)
    ]
    assert errors[-1] <= 1e-4 and all(
        1.5 <= p <= 2.5 for p in orders
    )  # planning run: 6.57e-5, 2.91e-5, 1.63e-5


def test_heston_european_matches_the_existing_cf_pricer(heston_base):
    reference = [
        heston_price(s, 1.0, 0.05, 0.5, 0.04, 2.0, 0.04, 0.2, -0.5, dividend_yield=0.02, kind="put")
        for s in SPOTS
    ]
    np.testing.assert_allclose(heston_base, reference, rtol=0, atol=2e-5)  # planning run: <= 2.1e-7
    flipped = european_put(CONTRACT, replace(HESTON, rho=0.5), SPOTS, config(bounds=HESTON_BOUNDS))
    assert (
        np.max(np.abs(flipped - reference)) > 1e-4
    )  # a mixed-term sign error cannot pass (planning run: 3.9e-3)


@pytest.mark.parametrize("chi, tol", [(0.5, 1e-7), (0.25, 5e-6), (0.75, 5e-6)])
def test_constant_variance_european_matches_bsm(chi, tol):
    cfg = config(n_var=8, chi=chi)
    got = european_put(CONTRACT, THREE_HALVES, SPOTS, cfg, propagators=constant_variance(cfg))
    reference = [bsm.put_price(s, 1.0, 0.05, 0.2, 0.5, q=0.02) for s in SPOTS]
    np.testing.assert_allclose(
        got, reference, rtol=0, atol=tol
    )  # planning run: 4e-8 (chi=.5), 2e-6 (.25, .75)


def test_variance_interpolation_is_not_a_knot_and_refuses_extrapolation():
    z = np.linspace(-3.0, -1.0, 21)
    values = np.vstack([np.sin(3.0 * z), np.exp(z)])
    got = interpolate_at_variance(values, z, math.exp(-1.73))
    np.testing.assert_allclose(
        got, CubicSpline(z, values, axis=1, bc_type="not-a-knot")(-1.73), rtol=0, atol=1e-15
    )
    np.testing.assert_allclose(
        interpolate_at_variance(values, z, math.exp(z[0])), values[:, 0], rtol=0, atol=1e-12
    )
    for outside in (math.exp(z[0] - 1e-9), math.exp(z[-1] + 1e-9)):
        with pytest.raises(ValueError, match="outside"):
            interpolate_at_variance(values, z, outside)


def test_heston_european_is_insensitive_to_a_half_cell_offset(heston_base):
    h = (HESTON_BOUNDS[1] - HESTON_BOUNDS[0]) / 159
    moved = european_put(
        CONTRACT, HESTON, SPOTS, config(bounds=(HESTON_BOUNDS[0] + h / 2, HESTON_BOUNDS[1] + h / 2))
    )
    assert np.max(np.abs(moved - heston_base)) <= 1e-7  # planning run: 7.3e-9


@pytest.mark.parametrize(
    "spots, bounds",
    [
        (SPOTS, (math.log(0.05), math.log(2.0))),
        (np.array([0.9, -1.0]), None),
        (np.array([[1.0]]), None),
        (np.array([math.nan]), None),
    ],
)
def test_european_rejects_bad_inputs(spots, bounds):
    cfg = config(n_var=8) if bounds is None else config(n_var=8, bounds=bounds)
    with pytest.raises(ValueError):
        european_put(CONTRACT, THREE_HALVES, spots, cfg)


def test_propagators_are_bound_to_their_inputs():
    cfg = config(n_var=8)
    prop = build_propagators(CONTRACT, THREE_HALVES, cfg)
    european_put(CONTRACT, THREE_HALVES, SPOTS, cfg, propagators=prop)
    european_put(
        replace(CONTRACT, strike=100.0), THREE_HALVES, 100.0 * SPOTS, cfg, propagators=prop
    )  # strike is not bound
    mismatches = [
        (replace(CONTRACT, domestic_rate=0.06), THREE_HALVES, cfg),
        (replace(CONTRACT, foreign_rate=0.01), THREE_HALVES, cfg),
        (replace(CONTRACT, expiry=1.0), THREE_HALVES, cfg),
        (CONTRACT, replace(THREE_HALVES, xi=3.9), cfg),
        (CONTRACT, THREE_HALVES, replace(cfg, chi=0.25)),
    ]
    for contract, model, other in mismatches:
        with pytest.raises(ValueError, match="propagators"):
            european_put(contract, model, SPOTS, other, propagators=prop)


def test_s0_generator_diagnostics_record_the_nonmonotone_scheme():
    d = generator_diagnostics(CONTRACT, THREE_HALVES, config())
    assert d["scheme_nonmonotone"] is True and d["zero_frequency_min_entry"] == pytest.approx(
        -0.0316, abs=5e-4
    )
    assert d["zero_frequency_row_sum_error"] <= 1e-12
    assert 14.0 < d["peclet_max"] < 15.0 and d["peclet_above_one"] == 45


def test_s0_european_matches_table_3b():
    got = european_put(CONTRACT, THREE_HALVES, SPOTS, config())
    np.testing.assert_allclose(
        got, [0.102557, 0.047224, 0.019105], rtol=0, atol=6e-6
    )  # planning run: <= 3.4e-7


def test_zero_expiry_european_is_the_payoff():
    got = european_put(replace(CONTRACT, expiry=0.0), THREE_HALVES, SPOTS, config(n_var=8))
    np.testing.assert_array_equal(got, np.maximum(1.0 - SPOTS, 0.0))


def test_propagator_parts_below_1e_200_are_stored_as_exact_zeros():
    cfg = config(n_var=120, panels=(0.0, 2.0), points_per_panel=1)  # one frequency, omega = 1
    prop = build_propagators(CONTRACT, THREE_HALVES, cfg)
    k = -prop.omega[0] - 1j * cfg.chi
    raw = expm(prop.dt * frequency_generator(CONTRACT, THREE_HALVES, variance_grid(cfg), k))
    tiny_real, tiny_imag = np.abs(raw.real) < 1e-200, np.abs(raw.imag) < 1e-200
    # the far off-diagonal tails of expm(dt A_k) are nonzero but below 1e-200: the flush has work
    assert np.count_nonzero(raw.real[tiny_real]) + np.count_nonzero(raw.imag[tiny_imag]) > 0
    flushed = raw.copy()
    flushed.real[tiny_real], flushed.imag[tiny_imag] = 0.0, 0.0
    np.testing.assert_array_equal(prop.matrices[0], flushed)
