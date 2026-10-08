"""Calibrated digital teachers against independent bootstrap and density integrals."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_risk as risk

Q = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])
CASES = [(80, 0.05), (95, 0.25), (100, 1.5), (110, 4.5), (120, 5.0)]


@pytest.fixture(scope="module")
def teacher():
    def load():
        name = "hullkit._quote_dml_teachers"
        assert importlib.util.find_spec(name) is not None, (
            "calibrated quote digital teacher is missing"
        )
        return importlib.import_module(name)

    return load


@pytest.fixture(scope="module")
def reference():
    def load():
        path = (
            Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml/reference_methods.py"
        )
        assert path.exists(), "independent calibrated digital reference is missing"
        spec = importlib.util.spec_from_file_location("quote_dml_reference", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


@pytest.mark.parametrize("spot,maturity", CASES)
def test_price_and_total_risk_match_independent_density(teacher, reference, spot, maturity):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(Q)
    got = teacher.analytic(market, spot, maturity)
    expected = reference.digital_moments(Q, spot, maturity)
    assert got["price"] == pytest.approx(expected["price"], abs=1e-12, rel=1e-10)
    np.testing.assert_allclose(got["g_quote"], expected["g_quote"], atol=1e-10, rtol=1e-9)
    np.testing.assert_allclose(
        got["g_quote"][1:], market.dz_dq.T @ got["g_theta"][1:], atol=1e-10, rtol=1e-9
    )
    assert got["g_quote"][0] > 0


@pytest.mark.parametrize("q", [Q, Q - 0.04, Q + np.array([0.001, -0.001, 0.002, -0.002, 0.001])])
def test_market_and_inverse_calibration_use_correct_coordinates(teacher, reference, q):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(q)
    pillars, zeros = reference.bootstrap(q)
    np.testing.assert_allclose(market.calibration.times, pillars, atol=1e-14, rtol=1e-12)
    np.testing.assert_allclose(market.calibration.zeros, zeros, atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(
        market.calibration.jacobian @ market.dz_dq, np.eye(5), atol=1e-12, rtol=1e-10
    )


@pytest.mark.parametrize("maturity", [0.5, 1.0, 2.0, 3.0, 5.0])
def test_pillar_maturity_risk_matches_rebootstrap(teacher, reference, maturity):
    teacher, reference = teacher(), reference()
    got = teacher.analytic(teacher.prepare_market(Q), 100.0, maturity)
    for width in (1e-4, 1e-5, 1e-6):
        changes = np.eye(5) * width
        bumped = np.array(
            [
                (
                    reference.digital_price(Q + d, 100, maturity)
                    - reference.digital_price(Q - d, 100, maturity)
                )
                / (2 * width)
                for d in changes
            ]
        )
        np.testing.assert_allclose(got["g_quote"][1:], bumped, atol=1e-7, rtol=1e-6)


def test_fixed_cashflow_market_connection(teacher, reference):
    teacher, reference = teacher(), reference()
    market = teacher.prepare_market(Q)
    pv, gz = risk.cashflow_value(market.calibration, (1.5,), (-3_000_000,))

    def value(q):
        times, zeros = reference.bootstrap(q)
        return -3_000_000 * np.exp(-1.5 * np.interp(1.5, times, zeros))

    changes = np.eye(5) * 1e-5
    bumped = np.array([(value(Q + d) - value(Q - d)) / 2e-5 for d in changes])
    assert pv == pytest.approx(value(Q), abs=1e-6, rel=1e-10)
    np.testing.assert_allclose(
        risk.quote_sensitivity(market.calibration, gz).per_unit, bumped, atol=1e-4, rtol=1e-6
    )


def test_log_discount_and_quote_bp_preserve_physical_risk(teacher):
    teacher = teacher()
    market = teacher.prepare_market(Q)
    got = teacher.analytic(market, 100.0, 1.5)
    dz_dlogdf = np.diag(-1 / market.calibration.times)
    j_logdf = market.calibration.jacobian @ dz_dlogdf
    g_logdf = dz_dlogdf.T @ got["g_theta"][1:]
    np.testing.assert_allclose(
        np.linalg.solve(j_logdf.T, g_logdf), got["g_quote"][1:], atol=1e-10, rtol=1e-9
    )
    np.testing.assert_allclose(
        (market.dz_dq * 1e-4).T @ got["g_theta"][1:],
        got["g_quote"][1:] * 1e-4,
        atol=1e-14,
        rtol=1e-9,
    )


@pytest.mark.parametrize("kwargs", [{"spot": 0}, {"maturity": 0}, {"sigma": 0}, {"strike": 0}])
def test_mathematically_invalid_contract_rejected(teacher, kwargs):
    teacher = teacher()
    args = {"spot": 100.0, "maturity": 1.0, "sigma": 0.2, "strike": 100.0} | kwargs
    with pytest.raises(ValueError):
        teacher.analytic(teacher.prepare_market(Q), **args)


def test_invalid_quote_shape_rejected(teacher):
    teacher = teacher()
    with pytest.raises(ValueError):
        teacher.prepare_market(Q[:4])
