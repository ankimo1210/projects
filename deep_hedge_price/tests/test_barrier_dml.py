"""Physical spot Delta, paired training protocol and isolated CPU execution."""

from __future__ import annotations

import importlib
import importlib.util

import numpy as np
import pytest
import torch


def learner():
    name = "deep_hedge_price._barrier_dml"
    assert importlib.util.find_spec(name) is not None, "private barrier DML learner is missing"
    return importlib.import_module(name)


def tiny_train():
    spot = np.linspace(85.0, 119.0, 16)
    maturity = np.geomspace(0.25, 2.0, 16)
    x = np.column_stack([spot, maturity])
    # A smooth synthetic price with negative Delta near H. The labels do not
    # use a financial teacher, keeping learner tests independent and cheap.
    price = 3.0 - 0.003 * (spot - 100) ** 2 + 0.2 * np.log(maturity)
    delta = -0.006 * (spot - 100)
    return x, price, delta


def numpy_replay(saved, x):
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    h = (features - saved["feature_mean"]) / saved["feature_std"]
    activations = []
    for layer in range(2):
        h = np.tanh(h @ saved[f"layer{layer}_weight"].T + saved[f"layer{layer}_bias"])
        activations.append(h)
    price = (
        saved["price_mean"]
        + saved["price_scale"] * (h @ saved["layer2_weight"].T + saved["layer2_bias"]).ravel()
    )
    derivative = np.tile(saved["layer2_weight"], (len(x), 1))
    for layer in (1, 0):
        derivative = (derivative * (1 - activations[layer] ** 2)) @ saved[f"layer{layer}_weight"]
    delta = derivative[:, 0] * saved["price_scale"] / saved["feature_std"][0]
    return price, delta


@pytest.mark.parametrize("dml", [False, True])
def test_physical_spot_delta_matches_fixed_maturity_price_bump(dml):
    module = learner()
    x, p, d = tiny_train()
    fit = module.train(x, p, d, seed=11, dml=dml, updates=2)
    price, delta = module.predict(fit, x)
    plus, minus = x.copy(), x.copy()
    plus[:, 0] += 0.001
    minus[:, 0] -= 0.001
    finite = (module.predict(fit, plus)[0] - module.predict(fit, minus)[0]) / 0.002
    np.testing.assert_allclose(delta, finite, atol=1e-9, rtol=1e-6)
    assert price.shape == delta.shape == (16,)
    assert fit.stats["updates"] == 2 and not fit.stats["budget_failure"]


def test_scales_use_training_labels_only_and_predictions_cannot_change_them():
    module = learner()
    x, p, d = tiny_train()
    scale = module.normalization(x, p, d)
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    np.testing.assert_allclose(scale["feature_mean"], features.mean(axis=0))
    np.testing.assert_allclose(scale["feature_std"], features.std(axis=0))
    assert scale["price_mean"] == pytest.approx(p.mean())
    assert scale["price_scale"] == pytest.approx(p.std())
    assert scale["delta_scale"] == pytest.approx(np.sqrt(np.mean(d * d)))
    fit = module.train(x, p, d, seed=11, dml=True, updates=2)
    saved = module.export(fit)
    module.predict(fit, np.array([[500.0, 20.0], [1.0, 0.01]]))
    after = module.export(fit)
    for key in ("feature_mean", "feature_std", "price_mean", "price_scale", "delta_scale"):
        np.testing.assert_allclose(after[key], saved[key])


def test_paired_modes_share_initial_price_weights_and_batch_seed_but_delta_loss_is_separate():
    module = learner()
    x, p, d = tiny_train()
    # Setup exhausts the cap, so both partial Fits retain their initial weights.
    price = module.train(x, p, d, seed=29, dml=False, updates=2, budget_s=1e-12)
    differential = module.train(x, p, d, seed=29, dml=True, updates=2, budget_s=1e-12)
    assert price.stats["initial_price_loss"] == pytest.approx(
        differential.stats["initial_price_loss"], abs=1e-12
    )
    assert price.stats["batch_seed"] == differential.stats["batch_seed"]
    for layer in range(3):
        np.testing.assert_allclose(
            module.export(price)[f"layer{layer}_weight"],
            module.export(differential)[f"layer{layer}_weight"],
        )
    predicted, delta = numpy_replay(module.export(differential), x)
    price_loss = np.mean(((predicted - p) / differential.scale["price_scale"]) ** 2)
    delta_loss = np.mean(((delta - d) / differential.scale["delta_scale"]) ** 2)
    assert differential.stats["initial_price_loss"] == pytest.approx(price_loss)
    assert differential.stats["initial_delta_loss"] == pytest.approx(delta_loss)
    assert differential.stats["initial_loss"] == pytest.approx(price_loss + delta_loss)
    assert price.stats["initial_delta_loss"] == 0.0


@pytest.mark.parametrize("dml", [False, True])
def test_export_replays_both_price_and_spot_delta_without_torch(dml):
    module = learner()
    x, p, d = tiny_train()
    fit = module.train(x, p, d, seed=47, dml=dml, updates=2)
    saved = module.export(fit)
    replay = numpy_replay(saved, x)
    original = module.predict(fit, x)
    for predicted, expected in zip(replay, original, strict=True):
        np.testing.assert_allclose(predicted, expected, atol=1e-12, rtol=1e-10)
    assert saved["layer0_weight"].shape == (32, 2)
    assert saved["layer1_weight"].shape == (32, 32)
    assert saved["layer2_weight"].shape == (1, 32)
    assert saved["stats"]["updates"] == 2 and saved["dml"] == dml
    saved["layer0_weight"][:] = 0.0
    saved["stats"]["updates"] = 0
    assert fit.stats["updates"] == 2
    np.testing.assert_allclose(module.predict(fit, x)[0], original[0])


def test_output_can_have_negative_delta_and_a_positive_barrier_left_limit():
    module = learner()
    x, p, d = tiny_train()
    fit = module.train(x, p, d, seed=11, dml=True, updates=2)
    # A hand-set network is a deterministic sign/architecture probe, not a
    # claim that two updates fit a financial contract accurately.
    with torch.no_grad():
        for parameter in fit.model.parameters():
            parameter.zero_()
        fit.model.layers[0].weight[0, 0] = 1.0
        fit.model.layers[1].weight[0, 0] = 1.0
        fit.model.layers[2].weight[0, 0] = -1.0
        fit.model.layers[2].bias[0] = 5.0
    price, delta = module.predict(fit, np.array([[119.999, 1.0], [120.0, 1.0]]))
    assert np.all(price > 1.0) and np.all(delta < 0.0)
    assert price[1] == pytest.approx(price[0], abs=0.001)
    # The learner supplies raw continuation values; the safe wrapper owns t0 KO.


def test_exhausted_budget_keeps_partial_fit_and_measured_failure_record():
    module = learner()
    x, p, d = tiny_train()
    fit = module.train(x, p, d, seed=11, dml=True, updates=2, budget_s=1e-12)
    assert fit.stats["updates"] == 0 and fit.stats["requested_updates"] == 2
    assert fit.stats["budget_failure"] and fit.stats["overrun_s"] > 0
    assert fit.stats["setup_s"] >= 0 and fit.stats["training_s"] >= 0
    assert fit.stats["elapsed_s"] >= fit.stats["setup_s"] + fit.stats["training_s"]
    assert np.isfinite(module.predict(fit, x)[0]).all()


@pytest.mark.parametrize("dml", [False, True])
def test_default_meta_device_and_accelerator_rng_are_isolated(monkeypatch, dml):
    module = learner()
    x, p, d = tiny_train()
    old_device = torch.get_default_device()
    rng = torch.get_rng_state().clone()
    old_threads = torch.get_num_threads()

    def forbidden(*args, **kwargs):
        raise AssertionError("learner must not seed an accelerator")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    try:
        torch.set_default_device("meta")
        fit = module.train(x, p, d, seed=29, dml=dml, updates=2)
        assert torch.get_default_device().type == "meta"
        assert all(
            parameter.device.type == "cpu" and parameter.dtype == torch.float64
            for parameter in fit.model.parameters()
        )
        assert np.isfinite(module.predict(fit, x)[0]).all()
        assert torch.get_default_device().type == "meta"
        assert torch.equal(torch.get_rng_state(), rng)
        assert torch.get_num_threads() == old_threads
    finally:
        torch.set_default_device(old_device)


def test_same_seed_repeats_predictions_without_changing_numpy_rng():
    module = learner()
    x, p, d = tiny_train()
    state = np.random.get_state()
    first = module.train(x, p, d, seed=47, dml=True, updates=2)
    second = module.train(x, p, d, seed=47, dml=True, updates=2)
    np.testing.assert_allclose(
        module.predict(first, x)[0], module.predict(second, x)[0], atol=1e-12, rtol=1e-10
    )
    after = np.random.get_state()
    np.testing.assert_array_equal(after[1], state[1])
    assert after[2:] == state[2:]


def test_constant_training_features_and_zero_labels_have_finite_scales():
    module = learner()
    x = np.tile([100.0, 1.0], (4, 1))
    fit = module.train(x, np.ones(4), np.zeros(4), seed=11, dml=True, updates=2)
    assert np.isfinite(fit.scale["feature_std"]).all() and np.all(fit.scale["feature_std"] > 0)
    assert fit.scale["price_scale"] > 0 and fit.scale["delta_scale"] > 0
    assert np.isfinite(module.predict(fit, x)[0]).all()


@pytest.mark.parametrize("bad", ["maturity", "labels", "updates", "budget"])
def test_mathematically_invalid_training_arrays_or_budgets_are_rejected(bad):
    module = learner()
    x, p, d = tiny_train()
    kwargs = {"seed": 11, "dml": True, "updates": 2}
    if bad == "maturity":
        x[0, 1] = 0.0
    elif bad == "labels":
        d = d[:-1]
    elif bad == "updates":
        kwargs["updates"] = 0
    else:
        kwargs["budget_s"] = 0.0
    with pytest.raises(ValueError):
        module.train(x, p, d, **kwargs)
