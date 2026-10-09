"""Safe quote-DML routing preserves raw predictions and explicit failure reasons."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"
Q = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])


@pytest.fixture(scope="module")
def policy():
    def load():
        path = HERE / "policy.py"
        assert path.exists(), "quote-DML safe prediction policy is missing"
        spec = importlib.util.spec_from_file_location("quote_prediction_policy", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


@pytest.fixture
def protocol():
    return json.loads((HERE / "protocol.json").read_text())


def exported_nn(price=0.4, mode="q_price"):
    mean = np.r_[Q, 0.0, 0.0]
    first = np.zeros((1, 7))
    first[0, 0] = 1
    return {
        "kind": "nn",
        "mode": mode,
        "feature_mean": mean,
        "feature_std": np.ones(7),
        "price_mean": price,
        "price_scale": 1.0,
        "layer0_weight": first,
        "layer0_bias": np.zeros(1),
        "layer1_weight": np.ones((1, 1)),
        "layer1_bias": np.zeros(1),
        "layer2_weight": np.ones((1, 1)),
        "layer2_bias": np.zeros(1),
    }


def exported_ridge():
    powers = np.array(
        [(i, j, k) for i in range(4) for j in range(4) for k in range(4) if i + j + k <= 3]
    )
    coefficients = np.zeros(20)
    coefficients[np.flatnonzero(powers.sum(axis=1) == 0)[0]] = 0.4
    return {
        "kind": "ridge",
        "powers": powers,
        "coefficients": coefficients,
        "feature_mean": np.zeros(3),
        "feature_std": np.ones(3),
        "price_mean": 0.0,
        "price_scale": 1.0,
    }


@pytest.mark.parametrize("mode", ["q_price", "theta_quote_metric"])
def test_inside_domain_preserves_model_price_and_market_greek(policy, protocol, mode):
    policy = policy()
    export = exported_nn(mode=mode)
    got = policy.safe_prediction(export, Q, 100.0, 1.0, protocol)
    market = teacher.prepare_market(Q)
    coordinates = market.calibration.zeros if mode.startswith("theta") else Q
    expected = policy.replay.nn_predict(
        export, np.r_[coordinates, 100.0, 1.0][None], market.dz_dq[None]
    )
    assert got["status"] == "ok" and not got["fallback"]
    assert got["raw"]["price"] == pytest.approx(expected["price"][0], abs=1e-12)
    np.testing.assert_allclose(got["raw"]["g_quote"], expected["g_quote"][0], atol=1e-10)
    np.testing.assert_allclose(got["safe"]["g_quote"], got["raw"]["g_quote"], atol=1e-14)
    assert got["safe"]["price"] == got["raw"]["price"]
    # Passing domain/price bounds does not promise accurate model Greeks.
    assert not np.allclose(got["safe"]["g_quote"], teacher.analytic(market, 100, 1)["g_quote"])


def test_ridge_uses_same_safe_domain_rules(policy, protocol):
    policy = policy()
    got = policy.safe_prediction(exported_ridge(), Q, 100.0, 1.0, protocol)
    assert got["status"] == "ok" and not got["fallback"]
    assert got["safe"]["price"] == pytest.approx(0.4, abs=1e-14)
    np.testing.assert_allclose(got["safe"]["g_quote"], np.zeros(6), atol=1e-14)


def test_safe_and_raw_records_have_independent_storage(policy, protocol):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol)
    original = got["raw"]["g_quote"].copy()
    got["safe"]["price"] = 0.0
    got["safe"]["g_quote"][:] = 0.0
    assert got["raw"]["price"] == pytest.approx(0.4, abs=1e-14)
    np.testing.assert_allclose(got["raw"]["g_quote"], original, atol=1e-14)


@pytest.mark.parametrize(
    "q,spot,maturity,reason",
    [
        (Q + 0.01, 100.0, 1.0, "quote_ood"),
        (Q - 0.04, 100.0, 1.0, "quote_ood"),
        (Q, 70.0, 1.0, "spot_ood"),
        (Q, 130.0, 1.0, "spot_ood"),
        (Q, 100.0, 0.01, "maturity_ood"),
        (Q, 100.0, 6.0, "maturity_ood"),
    ],
)
def test_valid_ood_preserves_raw_and_falls_back_to_analytic(
    policy, protocol, q, spot, maturity, reason
):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), q, spot, maturity, protocol)
    exact = teacher.analytic(teacher.prepare_market(q), spot, maturity)
    assert got["status"] == "fallback" and got["fallback"]
    assert reason in got["reason"]
    assert got["raw"] is not None
    assert got["safe"]["price"] == pytest.approx(exact["price"], abs=1e-12, rel=1e-10)
    np.testing.assert_allclose(got["safe"]["g_quote"], exact["g_quote"], atol=1e-10, rtol=1e-9)
    assert got["raw"]["price"] != pytest.approx(got["safe"]["price"], abs=1e-6)


@pytest.mark.parametrize("context", [{"strike": 105.0}, {"sigma": 0.25}])
def test_supported_contract_change_uses_changed_analytic_contract(policy, protocol, context):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), Q, 100.0, 1.0, protocol, context=context)
    exact = teacher.analytic(teacher.prepare_market(Q), 100, 1, **context)
    assert got["status"] == "fallback" and got["fallback"]
    assert got["raw"] is not None
    assert got["safe"]["price"] == pytest.approx(exact["price"], abs=1e-12)
    np.testing.assert_allclose(got["safe"]["g_quote"], exact["g_quote"], atol=1e-10)


@pytest.mark.parametrize(
    "context",
    [
        {"pillar_times": [0.5, 1, 2, 3, 6]},
        {"quote_times": [[0.5], [0.5, 1], [1, 2], [1, 2, 3], [1, 2, 3, 4, 6]]},
        {"interpolation": "logdf_linear"},
    ],
)
def test_unsupported_curve_context_returns_no_prediction(policy, protocol, context):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), Q, 100.0, 1.0, protocol, context=context)
    assert got["status"] == "unsupported_context"
    assert got["raw"] is None and got["safe"] is None and not got["fallback"]


def test_identical_curve_context_is_supported(policy, protocol):
    policy = policy()
    context = {
        key: protocol["curve"][key] for key in ["pillar_times", "quote_times", "interpolation"]
    }
    assert (
        policy.safe_prediction(exported_nn(), Q, 100.0, 1.0, protocol, context=context)["status"]
        == "ok"
    )


@pytest.mark.parametrize("price", [-0.01, 2.0])
def test_price_bounds_trigger_fallback_without_clipping_raw(policy, protocol, price):
    policy = policy()
    got = policy.safe_prediction(exported_nn(price), Q, 100.0, 1.0, protocol)
    assert got["status"] == "fallback" and "price_bounds" in got["reason"]
    assert got["raw"]["price"] == pytest.approx(price, abs=1e-14)
    assert 0 < got["safe"]["price"] < 1


def test_bound_roundoff_is_tolerated_without_clipping(policy, protocol):
    policy = policy()
    got = policy.safe_prediction(exported_nn(-5e-13), Q, 100.0, 1.0, protocol)
    assert got["status"] == "ok" and not got["fallback"]
    assert got["safe"]["price"] == pytest.approx(-5e-13, abs=1e-15)


def test_training_box_boundaries_are_included(policy, protocol):
    policy = policy()
    for q, s, t in [(Q - 0.005, 80.0, 0.05), (Q + 0.005, 120.0, 5.0)]:
        got = policy.safe_prediction(exported_nn(), q, s, t, protocol)
        assert got["status"] == "ok" and not got["fallback"]


@pytest.mark.parametrize(
    "spot,maturity,context",
    [
        (0, 1, None),
        (100, 0, None),
        (np.inf, 1, None),
        (100, 1, {"strike": 0}),
        (100, 1, {"sigma": 0}),
    ],
)
def test_invalid_contract_math_fails_without_prediction(policy, protocol, spot, maturity, context):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), Q, spot, maturity, protocol, context=context)
    assert got["status"] == "failure" and not got["fallback"]
    assert got["raw"] is None and got["safe"] is None


def test_invalid_quote_shape_fails_without_prediction(policy, protocol):
    policy = policy()
    got = policy.safe_prediction(exported_nn(), Q[:4], 100, 1, protocol)
    assert got["status"] == "failure" and got["raw"] is None and got["safe"] is None


def test_calibration_failure_is_recorded_explicitly(policy, protocol, monkeypatch):
    policy = policy()

    def failed(q):
        raise RuntimeError("nonconvergence")

    monkeypatch.setattr(teacher, "prepare_market", failed)
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol)
    assert got["status"] == "failure" and "calibration" in got["reason"]
    assert got["raw"] is None and got["safe"] is None


def test_amplification_warning_uses_analytic_with_raw_preserved(policy, protocol):
    policy = policy()
    market = teacher.prepare_market(Q)
    calibration = replace(market.calibration, amplification=20.0, warnings=("amplification",))
    warning_market = replace(market, calibration=calibration)
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol, market=warning_market)
    assert got["status"] == "fallback" and "amplification" in got["reason"]
    assert got["raw"] is not None
    exact = teacher.analytic(market, 100, 1)
    np.testing.assert_allclose(got["safe"]["g_quote"], exact["g_quote"], atol=1e-10)


def test_rank_failure_returns_no_model_or_analytic_prediction(policy, protocol):
    policy = policy()
    market = teacher.prepare_market(Q)
    rank_market = replace(market, calibration=replace(market.calibration, rank=4))
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol, market=rank_market)
    assert got["status"] == "failure" and "rank" in got["reason"]
    assert got["raw"] is None and got["safe"] is None


def test_actual_jacobian_rank_failure_cannot_use_stale_rank_metadata(policy, protocol):
    policy = policy()
    market = teacher.prepare_market(Q)
    stale = replace(market, calibration=replace(market.calibration, jacobian=np.zeros((5, 5))))
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol, market=stale)
    assert got["status"] == "failure" and "rank" in got["reason"]
    assert got["raw"] is None and got["safe"] is None


@pytest.mark.parametrize("field", ["zeros", "dz_dq"])
def test_shared_market_numerics_must_correspond_to_the_declared_quotes(policy, protocol, field):
    policy = policy()
    market = teacher.prepare_market(Q)
    if field == "zeros":
        inconsistent = replace(
            market, calibration=replace(market.calibration, zeros=market.calibration.zeros + 0.001)
        )
    else:
        inconsistent = replace(market, dz_dq=market.dz_dq * 2)
    got = policy.safe_prediction(exported_nn(), Q, 100, 1, protocol, market=inconsistent)
    assert got["status"] == "failure" and "market" in got["reason"]
    assert got["raw"] is None and got["safe"] is None


def test_shared_market_avoids_recalibration_and_checks_quote_consistency(
    policy, protocol, monkeypatch
):
    policy = policy()
    market = teacher.prepare_market(Q)

    def unexpected(q):
        raise AssertionError("cached market should prevent recalibration")

    monkeypatch.setattr(teacher, "prepare_market", unexpected)
    got = policy.safe_prediction(exported_nn(), Q.copy(), 100, 1, protocol, market=market)
    assert got["status"] == "ok"
    inconsistent = policy.safe_prediction(exported_nn(), Q + 1e-4, 100, 1, protocol, market=market)
    assert inconsistent["status"] == "failure" and "market" in inconsistent["reason"]
    assert inconsistent["safe"] is None
