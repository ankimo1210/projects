"""Independent array replay: physical derivatives and coordinate orientation."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / "research" / "RB-F07" / "quote_dml"
MODES = ("q_price", "q_dml", "theta_price", "theta_dml", "theta_quote_metric")


def load_replay():
    path = HERE / "replay.py"
    assert path.exists(), "Independent quote-DML replay has not been implemented"
    spec = importlib.util.spec_from_file_location("quote_dml_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nn_export(mode):
    """Small complete export, with both rate and logarithmic-input exposures."""
    rng = np.random.default_rng(171)
    return {
        "kind": "nn",
        "mode": mode,
        "feature_mean": np.array([0.03, 0.032, 0.033, 0.0345, 0.036, 0.0, 0.0]),
        "feature_std": np.array([0.01, 0.009, 0.012, 0.008, 0.011, 0.1, 0.7]),
        "price_mean": 0.4,
        "price_scale": 0.3,
        "risk_scale": np.ones(6),
        "layer0_weight": rng.normal(0.0, 0.3, (3, 7)),
        "layer0_bias": np.array([0.1, -0.2, 0.05]),
        "layer1_weight": rng.normal(0.0, 0.4, (2, 3)),
        "layer1_bias": np.array([-0.1, 0.15]),
        "layer2_weight": np.array([[0.7, -0.4]]),
        "layer2_bias": np.array([0.2]),
    }


def inputs():
    x = np.array(
        [
            [0.028, 0.031, 0.034, 0.036, 0.038, 95.0, 0.7],
            [0.033, 0.035, 0.031, 0.033, 0.037, 108.0, 2.3],
        ]
    )
    a = np.array(
        [
            [1.2, 0.3, -0.2, 0.0, 0.0],
            [0.1, 0.9, 0.0, 0.2, 0.0],
            [0.2, -0.1, 1.1, 0.0, 0.1],
            [0.0, 0.4, 0.1, 1.3, 0.2],
            [-0.1, 0.0, 0.2, -0.3, 0.8],
        ]
    )
    return x, np.stack([a, a * 1.1])


@pytest.mark.parametrize("mode", MODES)
def test_nn_physical_native_derivatives_match_input_finite_differences(mode):
    """Catches omitted price/feature scales and the logarithmic spot chain rule."""
    replay = load_replay()
    exported, (x, a) = nn_export(mode), inputs()
    prediction = replay.nn_predict(exported, x, a)
    assert prediction["price"].shape == (2,)
    assert prediction["g_native"].shape == (2, 6)
    for risk, column in enumerate([5, 0, 1, 2, 3, 4]):
        bump = 1e-3 if column == 5 else 1e-6
        up, down = x.copy(), x.copy()
        up[:, column] += bump
        down[:, column] -= bump
        finite = (
            replay.nn_predict(exported, up, a)["price"]
            - replay.nn_predict(exported, down, a)["price"]
        ) / (2 * bump)
        np.testing.assert_allclose(prediction["g_native"][:, risk], finite, atol=1e-8, rtol=1e-6)
    if mode.startswith("q"):
        np.testing.assert_allclose(prediction["g_quote"], prediction["g_native"])


@pytest.mark.parametrize("mode", ["theta_price", "theta_dml", "theta_quote_metric"])
def test_theta_quote_risk_matches_recalibrated_coordinate_bumps(mode):
    """Non-symmetric A detects use of A rather than A transpose on gradients."""
    replay = load_replay()
    exported, (x, a) = nn_export(mode), inputs()
    prediction = replay.nn_predict(exported, x, a)
    for bucket in range(5):
        up, down = x.copy(), x.copy()
        up[:, :5] += 1e-6 * a[:, :, bucket]
        down[:, :5] -= 1e-6 * a[:, :, bucket]
        finite = (
            replay.nn_predict(exported, up, a)["price"]
            - replay.nn_predict(exported, down, a)["price"]
        ) / 2e-6
        np.testing.assert_allclose(
            prediction["g_quote"][:, bucket + 1], finite, atol=1e-8, rtol=1e-6
        )
    np.testing.assert_allclose(prediction["g_quote"][:, 0], prediction["g_native"][:, 0])


def test_nn_price_has_two_tanh_layers_and_linear_final_output():
    replay = load_replay()
    exported = nn_export("q_price")
    for layer in range(3):
        exported[f"layer{layer}_weight"][:] = 0.0
        exported[f"layer{layer}_bias"][:] = 0.0
    exported["layer0_bias"][0] = 0.5
    exported["layer1_weight"][0, 0] = 2.0
    exported["layer1_bias"][0] = -0.1
    exported["layer2_weight"][0, 0] = 3.0
    exported["layer2_bias"][0] = 2.0
    x, a = inputs()
    expected = 0.4 + 0.3 * (3 * np.tanh(2 * np.tanh(0.5) - 0.1) + 2)
    prediction = replay.nn_predict(exported, x, a)
    np.testing.assert_allclose(prediction["price"], expected, atol=1e-14)
    np.testing.assert_allclose(prediction["g_quote"], 0.0, atol=1e-14)


@pytest.mark.parametrize("column", [5, 6])
def test_nn_rejects_nonpositive_logarithmic_inputs(column):
    replay = load_replay()
    x, a = inputs()
    x[0, column] = 0.0
    with pytest.raises(ValueError):
        replay.nn_predict(nn_export("q_dml"), x, a)


def ridge_export(differential):
    powers = np.array(
        [(i, j, k) for i in range(4) for j in range(4) for k in range(4) if i + j + k <= 3]
    )
    return {
        "kind": "ridge",
        "differential": differential,
        "feature_mean": np.array([0.0, 0.045, 0.0]),
        "feature_std": np.array([0.2, 0.02, 0.5]),
        "price_mean": 0.4,
        "price_scale": 0.3,
        "risk_scale": np.ones(6),
        "powers": powers,
        "coefficients": np.random.default_rng(541).normal(0.0, 0.1, 20),
    }


def ridge_dataset():
    x, _ = inputs()
    aq = np.array([[0.2, -0.1, 0.7, 1.1, 0.4], [-0.1, 0.3, 0.5, 1.4, 0.2]])
    return {"x_quote": x, "integrated_rate": np.array([0.039, 0.06]), "a_quote": aq}


@pytest.mark.parametrize("differential", [False, True])
def test_ridge_physical_risk_matches_spot_and_quote_finite_differences(differential):
    """A quote perturbation must move integrated rate, not a polynomial input slot."""
    replay = load_replay()
    assert hasattr(replay, "ridge_predict"), "Reduced-regression replay not implemented"
    exported, data = ridge_export(differential), ridge_dataset()
    prediction = replay.ridge_predict(exported, data)
    for risk, column in enumerate([5, 0, 1, 2, 3, 4]):
        bump = 1e-3 if column == 5 else 1e-6
        up = {key: value.copy() for key, value in data.items()}
        down = {key: value.copy() for key, value in data.items()}
        up["x_quote"][:, column] += bump
        down["x_quote"][:, column] -= bump
        if column < 5:
            up["integrated_rate"] += bump * data["a_quote"][:, column]
            down["integrated_rate"] -= bump * data["a_quote"][:, column]
        finite = (
            replay.ridge_predict(exported, up)["price"]
            - replay.ridge_predict(exported, down)["price"]
        ) / (2 * bump)
        np.testing.assert_allclose(prediction["g_quote"][:, risk], finite, atol=1e-8, rtol=1e-6)


def test_ridge_keeps_cubic_cross_terms_and_physical_price_scaling():
    replay = load_replay()
    assert hasattr(replay, "ridge_predict"), "Reduced-regression replay not implemented"
    exported = ridge_export(True)
    exported["coefficients"][:] = 0.0
    terms = {(0, 0, 0): 0.2, (1, 1, 1): 1.7, (3, 0, 0): 0.8, (0, 2, 0): -0.5}
    for index, power in enumerate(exported["powers"]):
        exported["coefficients"][index] = terms.get(tuple(power), 0.0)
    spot = 100 * np.exp(0.2)
    data = {
        "x_quote": np.array([[0.03, 0.032, 0.033, 0.0345, 0.036, spot, np.exp(0.5)]]),
        "integrated_rate": np.array([0.065]),
        "a_quote": np.array([[0.2, -0.1, 0.7, 1.1, 0.4]]),
    }
    prediction = replay.ridge_predict(exported, data)
    # At standardized features (1,1,1), f=.2+1.7+.8-.5=2.2;
    # df/du0=1.7+3*.8=4.1; df/du1=1.7-2*.5=.7.
    assert prediction["price"][0] == pytest.approx(1.06, abs=1e-13)
    assert prediction["g_quote"][0, 0] == pytest.approx(0.3 * 4.1 / (0.2 * spot))
    np.testing.assert_allclose(prediction["g_quote"][0, 1:], 10.5 * data["a_quote"][0])


def test_ridge_derivatives_are_finite_at_zero_standardized_features():
    replay = load_replay()
    assert hasattr(replay, "ridge_predict"), "Reduced-regression replay not implemented"
    exported = ridge_export(False)
    exported["coefficients"][:] = 0.0
    for index, power in enumerate(exported["powers"]):
        if tuple(power) == (1, 0, 0):
            exported["coefficients"][index] = 2.0
        elif tuple(power) == (0, 1, 0):
            exported["coefficients"][index] = -0.5
    data = {
        "x_quote": np.array([[0.03, 0.032, 0.033, 0.0345, 0.036, 100.0, 1.0]]),
        "integrated_rate": np.array([0.045]),
        "a_quote": np.ones((1, 5)),
    }
    prediction = replay.ridge_predict(exported, data)
    assert prediction["price"][0] == pytest.approx(0.4)
    np.testing.assert_allclose(prediction["g_quote"], [[0.03, -7.5, -7.5, -7.5, -7.5, -7.5]])


def metric_fixture():
    """Two markets with eight contracts each; all expectations are hand computable."""
    identifiers = ["q_price_n512_s11", "q_dml_n512_s11", "theta_quote_metric_n512_s11"]
    scale = np.array([0.01, 1.0, 2.0, 1.0, 2.0, 3.0])
    x = np.tile(np.array([0.03, 0.032, 0.033, 0.0345, 0.036, 100.0, 1.0]), (16, 1))
    x[:4, 5] = 90.0
    x[12:, 5] = 110.0
    x[:8, 6] = 0.25
    x[8:12, 6] = 1.0
    x[12:, 6] = 2.0
    teacher = np.tile(np.array([0.01, 2.0, 0.0, -1.0, 0.0, 3.0]), (16, 1))
    arrays = {
        "model_ids": np.array(identifiers),
        "test_price": np.ones(16) * 0.4,
        "test_g_quote": teacher,
        "test_market_id": np.repeat([101, 102], 8),
        "test_x_quote": x,
        "reference_h": np.zeros((16, 6)),
        "reference_residual": np.tile([0.0, 0.01], (16, 1)),
        "shock_labels": np.array(["zero", "parallel_plus_1bp"]),
        "cost_rate_bp": np.array([0.0, 0.1, 0.5, 1.0]),
        "cost_stock_bp": np.array([0.0, 1.0, 5.0]),
    }
    normalized_errors = {
        identifiers[0]: [2.0, 4.0],
        identifiers[1]: [1.0, 2.0],
        identifiers[2]: [0.5, 3.0],
    }
    for identifier, levels in normalized_errors.items():
        prefix = f"pred__{identifier}__"
        arrays[prefix + "price"] = arrays["test_price"] + np.repeat([0.1, 0.2], 8)
        arrays[prefix + "g_quote"] = teacher + np.repeat(levels, 8)[:, None] * scale
        arrays[prefix + "h"] = np.tile(np.arange(6), (16, 1))
        arrays[prefix + "residual"] = np.tile([0.0, 0.03], (16, 1))
        arrays[prefix + "cost"] = np.repeat([1.0, 2.0], 8)[:, None, None] * np.arange(12).reshape(
            1, 4, 3
        )
        arrays[prefix + "risk_scale"] = scale.copy()
    protocol = {
        "contract": {"strike": 100.0},
        "sampling": {"contracts_per_market": 8},
        "bootstrap": {"repeats": 2000, "seed": 20261010, "confidence": 0.95},
    }
    return arrays, protocol


def test_metrics_recompute_physical_risk_hedges_residual_and_cost():
    replay = load_replay()
    assert hasattr(replay, "metrics"), "Array-derived research metrics not implemented"
    arrays, protocol = metric_fixture()
    result = replay.metrics(arrays, protocol)
    model = result["models"]["q_price_n512_s11"]
    assert model["price"]["mae"] == pytest.approx(0.15)
    assert model["price"]["rmse"] == pytest.approx(np.sqrt(0.025))
    assert model["price"]["p99"] == pytest.approx(0.2)
    assert model["price"]["max"] == pytest.approx(0.2)
    np.testing.assert_allclose(model["risk"]["rmse"], np.sqrt(10) * np.array([0.01, 1, 2, 1, 2, 3]))
    assert model["normalized_risk"]["rmse"] == pytest.approx(np.sqrt(10))
    assert model["zero_bucket_leakage"]["count"] == 32
    assert model["zero_bucket_leakage"]["rmse"] == pytest.approx(2 * np.sqrt(10))
    assert model["zero_bucket_leakage"]["by_component"][0]["count"] == 0
    assert model["zero_bucket_leakage"]["by_component"][0]["rmse"] is None
    assert model["zero_bucket_leakage"]["by_component"][2]["count"] == 16
    assert model["zero_bucket_leakage"]["by_component"][2]["max"] == pytest.approx(8.0)
    np.testing.assert_allclose(model["hedge_quantity_rmse"], np.arange(6))
    assert model["residual"]["rmse"] == pytest.approx(0.03 / np.sqrt(2))
    assert model["curvature_difference_rmse"] == pytest.approx(0.02 / np.sqrt(2))
    np.testing.assert_allclose(model["cost"]["mean"], 1.5 * np.arange(12).reshape(4, 3))
    np.testing.assert_allclose(model["cost"]["p99"], 2 * np.arange(12).reshape(4, 3))


def test_metrics_bootstrap_resamples_market_groups_and_paired_models():
    replay = load_replay()
    assert hasattr(replay, "metrics"), "Array-derived research metrics not implemented"
    arrays, protocol = metric_fixture()
    result = replay.metrics(arrays, protocol)
    h1 = result["hypotheses"]["H1"][0]
    h2 = result["hypotheses"]["H2"][0]
    assert h1["difference"] == pytest.approx(-np.sqrt(2.5))
    np.testing.assert_allclose(h1["ci95"], [-2.0, -1.0])
    assert h2["difference"] == pytest.approx(np.sqrt(2.5) - np.sqrt(4.625))
    np.testing.assert_allclose(h2["ci95"], [-1.0, 0.5])
    assert h1["training_seed"] == 11
    assert result["metadata"]["bootstrap"]["unit"] == "market"
    assert result["metadata"]["bootstrap"]["conditional_on_training_seed"] is True
    assert result["metadata"]["market_count"] == 2
    assert result == replay.metrics(arrays, protocol)


def test_metrics_fixed_maturity_and_moneyness_groups_are_not_refit():
    replay = load_replay()
    assert hasattr(replay, "metrics"), "Array-derived research metrics not implemented"
    arrays, protocol = metric_fixture()
    price = replay.metrics(arrays, protocol)["models"]["q_price_n512_s11"]
    assert price["price_by_maturity"]["short"]["count"] == 8
    assert price["price_by_maturity"]["medium"]["count"] == 4
    assert price["price_by_maturity"]["long"]["count"] == 4
    assert price["price_by_moneyness"]["otm"]["count"] == 4
    assert price["price_by_moneyness"]["atm"]["count"] == 8
    assert price["price_by_moneyness"]["itm"]["count"] == 4
    assert price["price_by_maturity"]["short"]["rmse"] == pytest.approx(0.1)
    assert price["price_by_maturity"]["long"]["rmse"] == pytest.approx(0.2)


def test_metrics_ignore_saved_flags_but_recompute_changed_predictions():
    replay = load_replay()
    assert hasattr(replay, "metrics"), "Array-derived research metrics not implemented"
    arrays, protocol = metric_fixture()
    baseline = replay.metrics(arrays, protocol)
    arrays["saved_pass"] = np.array(False)
    arrays["contract_coupons"] = np.ones((16, 5)) * 100.0
    assert replay.metrics(arrays, protocol) == baseline
    arrays["pred__q_price_n512_s11__price"][0] += 1.0
    changed = replay.metrics(arrays, protocol)
    assert changed["models"]["q_price_n512_s11"]["price"]["rmse"] > 0.15
    assert (
        changed["models"]["q_price_n512_s11"]["price"]
        != baseline["models"]["q_price_n512_s11"]["price"]
    )
    arrays["pred__q_price_n512_s11__g_quote"][0, 0] += 1.0
    assert replay.metrics(arrays, protocol)["hypotheses"]["H1"] != changed["hypotheses"]["H1"]


@pytest.mark.parametrize("damage", ["nonfinite", "cost_shape", "group_size", "scale"])
def test_metrics_reject_inconsistent_or_nonfinite_arrays(damage):
    replay = load_replay()
    assert hasattr(replay, "metrics"), "Array-derived research metrics not implemented"
    arrays, protocol = metric_fixture()
    if damage == "nonfinite":
        arrays["pred__q_price_n512_s11__price"][0] = np.nan
    elif damage == "cost_shape":
        arrays["pred__q_price_n512_s11__cost"] = np.zeros((16, 4, 2))
    elif damage == "group_size":
        arrays["test_market_id"][0] = 103
    else:
        arrays["pred__q_dml_n512_s11__risk_scale"][0] *= 2
    with pytest.raises(ValueError):
        replay.metrics(arrays, protocol)
