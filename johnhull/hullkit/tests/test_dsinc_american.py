"""EEP quadrature, guarded boundaries and independent constant-vol controls."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from hullkit._dsinc_spectral import Propagators, _input_hash, frequency_rule, variance_grid
from hullkit._dsinc_types import PricingFailure, PutContract, SpectralConfig, VarianceModel
from hullkit.trees import crr_price
from scipy.integrate import quad


def _american():
    return importlib.import_module("hullkit._dsinc_american")


def _config(**changes):
    return replace(
        SpectralConfig(
            100, 4, (np.log(0.02), np.log(0.08)), 0.5, (0, 2, 5, 10, 20, 40, 80, 160, 320, 640), 16
        ),
        **changes,
    )


def _constant_prop(contract, model, config):
    """Exact constant-variance Fourier propagation, independent of SDE builder."""
    omega, weights = frequency_rule(config)
    k = -omega - 1j * config.chi
    eigenvalue = (
        1j * k * (contract.domestic_rate - contract.foreign_rate) - 0.5 * (k * k + 1j * k) * 0.04
    )
    matrices = np.exp(eigenvalue * contract.expiry / config.n_time)[:, None, None] * np.eye(
        config.n_var
    )
    return Propagators(
        matrices,
        omega,
        weights,
        variance_grid(config),
        contract.expiry / config.n_time,
        _input_hash(contract, model, config),
        0.0,
        {"constant_variance_control": True},
    )


def test_time_quadrature_terminal_half_weight():
    am = _american()
    matrix = np.array([[[0.9, 0.1], [0.2, 0.8]]], dtype=complex)
    prop = Propagators(
        matrix, np.array([1.0]), np.array([1.0]), np.array([-4.0, -3.0]), 0.1, "fixture", 0.0, {}
    )
    first, second = np.array([[2.0, 3.0]]), np.array([[4.0, 5.0]])
    q1, d1 = am._advance_history(prop, np.zeros_like(first), 0.0, first, 0.05, 0.05)
    q2, d2 = am._advance_history(prop, q1, d1, second, 0.1, 0.05)
    discount = np.exp(-0.05 * 0.1)
    expected = discount * 0.1 * (matrix[0] @ second[0]) + discount**2 * 0.05 * (
        matrix[0] @ matrix[0] @ first[0]
    )
    np.testing.assert_allclose(q2[0], expected, atol=1e-15)
    assert d2 == pytest.approx(0.05 * (discount * 0.1 + discount**2 * 0.05))


def test_positive_strip_residue_in_eep():
    am = _american()
    c = PutContract(1, 0.5, 0.05, 0.02)
    omega, chi, boundary = np.array([0.2, 1.0, 3.0]), 0.5, -0.2
    actual = am.payoff_transform(omega, chi, np.array([boundary]), c)[:, 0]
    # Transform the integrable residue-subtracted source g(x)1{x<b}-rd.
    expected = []
    for w in omega:
        s = 1j * w - chi

        def integrand(x, s=s):
            source = -c.foreign_rate * np.exp(x) if x < boundary else -c.domestic_rate
            return np.exp(s * x) * source

        real = (
            quad(lambda x: integrand(x).real, -100, boundary, epsabs=1e-12)[0]
            + quad(lambda x: integrand(x).real, boundary, 100, epsabs=1e-12)[0]
        )
        imag = (
            quad(lambda x: integrand(x).imag, -100, boundary, epsabs=1e-12)[0]
            + quad(lambda x: integrand(x).imag, boundary, 100, epsabs=1e-12)[0]
        )
        expected.append(real + 1j * imag)
    np.testing.assert_allclose(actual, expected, atol=2e-12)


def test_boundary_endpoint_correction_only_at_root():
    am = _american()
    c, cfg = PutContract(1, 0.5, 0.05, 0.02), _config(n_time=2)
    model = VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04)
    prop = _constant_prop(c, model, cfg)
    g = np.ones((len(prop.omega), cfg.n_var), dtype=complex)
    q = np.zeros_like(g)
    x = np.array([-0.2])
    continuation = am._continuation_at_nodes(c, x, prop, cfg.chi, g, q, 0.003, tau=0.25)[0, 0]
    residual = am._boundary_residual(c, prop, cfg, g, q, 0.003, tau=0.25)(x, 0)[0]
    endpoint = prop.dt * (c.domestic_rate - c.foreign_rate * np.exp(x[0])) / 4
    assert residual == pytest.approx(1 - np.exp(x[0]) - continuation - endpoint)
    # At zero integral Q, D survives; it is not another discount or a floor.
    eu_only = am._continuation_at_nodes(c, x, prop, cfg.chi, g, q, 0.0, tau=0.25)[0, 0]
    assert continuation - eu_only == pytest.approx(0.003)


@pytest.mark.parametrize(
    ("function", "code"),
    [
        (lambda x: np.ones_like(x), "missing_sign_change"),
        (lambda x: np.full_like(x, np.nan), "nonfinite_residual"),
        (lambda x: x + 0.02345, "wrong_orientation"),
        (lambda x: -(x + 0.02) * (x + 0.05) * (x + 0.08), "multiple_roots"),
        (lambda x: np.zeros_like(x), "ambiguous_contact"),
        (lambda x: -((x + 0.05) ** 2), "ambiguous_contact"),
    ],
)
def test_root_guards(function, code):
    roots, diagnostic = _american().local_boundary(
        lambda x, node: function(x), np.array([0.0]), _config()
    )
    assert np.isnan(roots[0])
    assert diagnostic["statuses"] == [code]
    assert diagnostic["node_count"] == 1


def test_root_maxiter_and_whole_slice():
    am = _american()
    functions = [lambda x: -x - 0.02345, lambda x: x + 0.02, lambda x: np.ones_like(x)]
    roots, diagnostic = am.local_boundary(
        lambda x, j: functions[j](x), np.zeros(3), _config(root_maxiter=1)
    )
    assert np.all(np.isnan(roots))
    assert diagnostic["statuses"] == ["max_iterations", "wrong_orientation", "missing_sign_change"]
    assert diagnostic["node_count"] == 3


def test_success_records_narrow_bracket_and_residual():
    cfg = _config()
    roots, diagnostic = _american().local_boundary(lambda x, node: -x - 0.05, np.array([0.0]), cfg)
    record = diagnostic["nodes"][0]
    assert roots[0] == pytest.approx(-0.05, abs=cfg.root_x_tol)
    assert abs(record["residual"]) <= cfg.root_residual_tol
    assert record["bracket"][1] - record["bracket"][0] <= cfg.root_x_tol


def test_failure_records_whole_time_slice(monkeypatch):
    am = _american()
    calls = []

    def forced(residual, predictor, config):
        calls.append(1)
        return np.full(config.n_var, np.nan), {
            "statuses": ["missing_sign_change"] * config.n_var,
            "node_count": config.n_var,
        }

    monkeypatch.setattr(am, "local_boundary", forced)
    c, model, cfg = (
        PutContract(1, 0.5, 0.05, 0.02),
        VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04),
        _config(n_time=3),
    )
    with pytest.raises(PricingFailure) as failure:
        am.american_put(c, model, np.array([1.0]), cfg, propagators=_constant_prop(c, model, cfg))
    details = failure.value.details
    assert details["statuses"][2] == ["missing_sign_change"] * 4
    assert details["statuses"][0] == ["not_run"] * 4
    assert details["statuses"][1] == ["not_run"] * 4
    assert details["failed_boundary_propagated"] is False
    assert len(calls) == 1


def test_maturity_exact_payoff():
    result = _american().american_put(
        PutContract(1, 0, 0.05, 0.02),
        VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04),
        np.array([1.25, 0.75]),
        _config(),
    )
    np.testing.assert_array_equal(result.american, [0.0, 0.25])
    assert result.log_boundary.shape == (0, 0)
    assert result.times.size == result.log_variances.size == 0
    assert result.diagnostics["boundary_status"] == "not_applicable"


def test_constant_vol_american_and_exercise_homogeneity():
    am = _american()
    c, model, cfg = (
        PutContract(1, 1, 0.05, 0),
        VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04),
        _config(n_time=200),
    )
    spots = np.array([1.1, 0.7, 1.0, 0.9])
    prop = _constant_prop(c, model, cfg)
    prepared = am.prepare_american(c, model, cfg, propagators=prop)
    result = prepared.price(spots)
    wanted = np.array(
        [crr_price(s, 1, 0.05, 0.2, 1, 4000, kind="put", american=True) for s in spots]
    )
    np.testing.assert_allclose(result.american, wanted, atol=2e-5, rtol=0)
    assert result.american[1] == pytest.approx(0.3, abs=1e-15)
    assert np.all(result.american >= result.european - 2e-5)
    assert np.all(result.american <= 1 + 2e-5)
    assert result.diagnostics["max_root_residual"] <= 1e-8
    scaled = replace(c, strike=2)
    other = am.american_put(
        scaled, model, spots * 2, cfg, propagators=_constant_prop(scaled, model, cfg)
    )
    np.testing.assert_allclose(other.american, result.american * 2, atol=1e-14)
    np.testing.assert_array_equal(prepared.price(spots[::-1]).american, result.american[::-1])


def test_boundary_matches_independent_fd():
    # A short-maturity interior-domain control, separate from the failed S0 run.
    path = Path(__file__).resolve().parents[2] / "research/DSINC/reference_fd.py"
    spec = importlib.util.spec_from_file_location("dsinc_boundary_reference", path)
    ref = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ref
    spec.loader.exec_module(ref)
    contract = PutContract(1, 0.1, 0.05, 0.02)
    model = VarianceModel("three_halves", 20, 0.04, 4, -0.5, 0.04)
    config = _config(n_time=20, n_var=24, log_var_bounds=(np.log(0.01), np.log(0.16)))
    spots = np.array([0.9, 1.0, 1.1])
    spectral = _american().american_put(contract, model, spots, config)
    fd = ref.reference_put(
        contract,
        model,
        spots,
        ref.FDConfig(961, 101, 150, (-1.2, 1.2), (np.log(1e-5), np.log(8)), "american"),
    )
    np.testing.assert_allclose(spectral.american, fd.prices, atol=2e-5, rtol=0)
    comparison = ref.boundary_comparison(
        spectral.times, spectral.log_variances, spectral.log_boundary, fd
    )
    assert comparison["coverage"] >= 0.9
    assert comparison["accepted"]
