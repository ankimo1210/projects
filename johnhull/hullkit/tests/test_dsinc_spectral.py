"""Independent Fourier, CIR, and European controls for the DSINC engine."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import replace

import numpy as np
import pytest
from hullkit._dsinc_types import PutContract, SpectralConfig, VarianceModel
from hullkit.stochastic_volatility import heston_price
from scipy.integrate import quad
from scipy.interpolate import CubicSpline
from scipy.linalg import expm
from scipy.stats import norm


def _engine():
    assert importlib.util.find_spec("hullkit._dsinc_spectral") is not None, (
        "missing fixed-frequency engine"
    )
    return importlib.import_module("hullkit._dsinc_spectral")


def _config(**changes):
    base = SpectralConfig(
        50, 160, (np.log(0.0001), np.log(0.5)), 0.5, (0, 2, 5, 10, 20, 40, 80, 160), 12
    )
    return replace(base, **changes)


def _model(kind="three_halves"):
    return VarianceModel(kind, 20, 0.04, 4, -0.5, 0.04)


def test_constant_variance_fourier_mode():
    engine = _engine()
    z = np.linspace(-5, 0, 9)
    frequency = -3 - 0.5j
    matrix = engine._generator_matrix(
        z, np.full(9, 0.04), np.zeros(9), np.zeros(9), np.zeros(9), frequency, 0.03
    )
    actual = expm(0.7 * matrix) @ np.ones(9)
    expected = np.exp(0.7 * (1j * frequency * 0.03 - 0.5 * (frequency**2 + 1j * frequency) * 0.04))
    np.testing.assert_allclose(actual, expected, atol=1e-11, rtol=0)


def test_neumann_ghost_rows():
    engine = _engine()
    matrix = engine._generator_matrix(
        np.array([-1.0, 0.0, 1.0]),
        np.full(3, 0.04),
        np.ones(3),
        np.full(3, 0.7),
        np.zeros(3),
        0j,
        0.0,
    )
    np.testing.assert_allclose(matrix, [[-1, 1, 0], [0.15, -1, 0.85], [0, 1, -1]], atol=1e-15)


@pytest.mark.parametrize(
    "kind,a,b,covariance", [("heston", 1.5, -1.125, -0.15), ("three_halves", 0.06, -0.0018, -0.006)]
)
def test_common_generator_for_models(kind, a, b, covariance):
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    model = VarianceModel(kind, 2, 0.04, 0.3, -0.5, 0.04)
    z = np.log([0.02, 0.04, 0.08])
    h = np.log(2)
    matrix = engine.frequency_generator(contract, model, z, 2)
    expected = [
        0.5 * a * a / h**2 - (b + 2j * covariance) / (2 * h),
        -a * a / h**2 - 0.08 + 0.02j,
        0.5 * a * a / h**2 + (b + 2j * covariance) / (2 * h),
    ]
    np.testing.assert_allclose(matrix[1], expected, atol=1e-13)


def test_zero_frequency_preserves_one():
    engine = _engine()
    config = _config(n_var=80)
    matrix = engine.frequency_generator(
        PutContract(1, 0.5, 0.05, 0.02), _model(), engine.variance_grid(config), 0j
    )
    np.testing.assert_allclose(expm(0.005 * matrix) @ np.ones(80), 1, atol=2e-12)


def test_reciprocal_variance_cir_mean():
    engine = _engine()
    exact = np.exp(-0.4) / 0.04 + 45 * (1 - np.exp(-0.4))
    errors, widths = [], []
    for n in (160, 240, 320):
        z = np.linspace(np.log(0.0002), np.log(2), n)
        matrix = engine.frequency_generator(PutContract(1, 0.5, 0.05, 0.02), _model(), z, 0j)
        values = expm(0.5 * matrix.real) @ np.exp(-z)
        errors.append(abs(CubicSpline(z, values)(np.log(0.04)) - exact))
        widths.append(z[1] - z[0])
    order = np.polyfit(np.log(widths), np.log(errors), 1)[0]
    assert 1.5 <= order <= 2.5
    assert errors[-1] / exact < 1e-4


def test_positive_damping_residue_and_sign():
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    spots = np.array([0.9, 1.0, 1.1])
    log_spots = np.log(spots)
    config = _config(points_per_panel=24)
    omega, weights = engine.frequency_rule(config)
    k = -omega - 1j * config.chi
    g = np.exp((1j * k * 0.03 - 0.5 * (k * k + 1j * k) * 0.04) * 0.5)[:, None]
    actual = engine._put_at_nodes(contract, log_spots, omega, weights, config.chi, g)[:, 0]
    wanted = []
    for spot in spots:
        mean = np.log(spot) + (0.03 - 0.5 * 0.04) * 0.5
        sd = np.sqrt(0.04 * 0.5)
        wanted.append(
            np.exp(-0.05 * 0.5)
            * quad(
                lambda z, mean=mean, sd=sd: (1 - np.exp(mean + sd * z)) * norm.pdf(z),
                -12,
                -mean / sd,
                epsabs=1e-12,
            )[0]
        )
    np.testing.assert_allclose(actual, wanted, atol=1e-10)


def test_heston_european_against_existing_cf():
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    model = VarianceModel("heston", 2, 0.04, 0.2, -0.5, 0.04)
    spots = np.array([0.9, 1.0, 1.1])
    actual = engine.european_put(contract, model, spots, _config())
    wanted = [
        heston_price(s, 1, 0.05, 0.5, 0.04, 2, 0.04, 0.2, -0.5, dividend_yield=0.02, kind="put")
        for s in spots
    ]
    np.testing.assert_allclose(actual, wanted, atol=2e-5, rtol=0)


def test_offset_and_cubic_interpolation():
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    model = VarianceModel("heston", 2, 0.04, 0.2, -0.5, 0.04)
    config = _config(n_var=200)
    actual = engine.european_put(contract, model, np.array([1.0]), config)
    h = (config.log_var_bounds[1] - config.log_var_bounds[0]) / (config.n_var - 1)
    for shift in (-h / 2, h / 2):
        shifted = replace(config, log_var_bounds=tuple(v + shift for v in config.log_var_bounds))
        np.testing.assert_allclose(
            engine.european_put(contract, model, np.array([1.0]), shifted),
            actual,
            atol=5e-6,
            rtol=0,
        )


def test_invalid_damping_or_grid():
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    with pytest.raises(ValueError):
        engine.european_put(contract, _model(), np.array([1.0]), _config(log_var_bounds=(-2, 0)))
    with pytest.raises(ValueError):
        engine.frequency_generator(contract, _model(), np.array([-2.0, -1.0, -0.1]), 1)
    for config in ({"chi": 0}, {"chi": 1}, {"panels": (0, 2, 1)}, {"n_time": 0}):
        with pytest.raises(ValueError):
            _config(**config)


def test_european_maturity_and_invalid_spots():
    engine = _engine()
    contract = PutContract(1, 0, 0.05, 0.02)
    np.testing.assert_array_equal(
        engine.european_put(contract, _model(), np.array([1.25, 0.75, 1.0]), _config()),
        [0.0, 0.25, 0.0],
    )
    for spots in (np.array([]), np.array([0.0]), np.array([np.nan])):
        with pytest.raises(ValueError):
            engine.european_put(contract, _model(), spots, _config())


@pytest.mark.parametrize("changed", ["rate", "foreign", "expiry", "model", "grid"])
def test_propagator_contract_mismatch(changed):
    engine = _engine()
    contract = PutContract(1, 0.5, 0.05, 0.02)
    model = _model()
    config = _config(n_var=8, n_time=3, panels=(0, 5), points_per_panel=2)
    cached = engine.build_propagators(contract, model, config)
    if changed == "rate":
        contract = replace(contract, domestic_rate=0.06)
    elif changed == "foreign":
        contract = replace(contract, foreign_rate=0.01)
    elif changed == "expiry":
        contract = replace(contract, expiry=1)
    elif changed == "model":
        model = replace(model, rho=-0.4)
    else:
        config = replace(config, n_time=4)
    with pytest.raises(ValueError, match="cache"):
        engine.european_put(contract, model, np.array([1.0]), config, propagators=cached)
