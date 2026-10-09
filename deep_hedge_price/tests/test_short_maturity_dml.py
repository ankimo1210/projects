"""Private short-call learner: smooth prices, physical Greeks and paired budgets.

The smooth polynomial labels are a small numerical fixture, not a market model
or the research train/test grid. No Hull teacher or hullkit import is used.
"""

from copy import deepcopy

import numpy as np
import pytest
import torch

from deep_hedge_price import _short_maturity_dml as dml


def fixture():
    x = np.array(
        [[s, t, event] for s in [94, 100, 106] for t in [90, 900] for event in [0, 1]],
        dtype=float,
    )
    z = x[:, 0] - 100
    prices = 2 + 0.2 * z + 0.01 * z**2 + 0.03 * np.log(x[:, 1]) + 0.1 * x[:, 2]
    deltas = 0.2 + 0.02 * z
    return x, prices, deltas


def fit_small(*, differential=False, updates=3, **kwargs):
    x, prices, deltas = fixture()
    return dml.train(
        x,
        prices,
        deltas,
        seed=11,
        batch_seed=29,
        dml=differential,
        max_updates=updates,
        batch_size=5,
        budget_s=30,
        **kwargs,
    )


def test_train_only_normalization_in_dimensionless_price_units():
    x, prices, deltas = fixture()
    scale = dml.normalization(x, prices, deltas, strike=73)
    features = np.column_stack([np.log(x[:, 0] / 73), np.log(x[:, 1]), x[:, 2]])
    assert np.allclose(scale["mean"], features.mean(axis=0))
    assert np.allclose(scale["std"], features.std(axis=0))
    assert scale["price_mean"] == pytest.approx(np.mean(prices / 73))
    assert scale["price_scale"] == pytest.approx(np.std(prices / 73))
    assert scale["delta_scale"] == pytest.approx(np.sqrt(np.mean(deltas**2)))
    assert scale["strike"] == 73


def test_prediction_cannot_change_train_scales_or_input_arrays():
    fit = fit_small()
    scale_before = deepcopy(fit.normalization)
    x, _, _ = fixture()
    x_before = x.copy()
    dml.predict(fit, x)
    dml.predict(fit, np.array([[300, 100000, 1]], dtype=float))
    for name in scale_before:
        assert np.allclose(fit.normalization[name], scale_before[name])
    assert np.array_equal(x, x_before)


@pytest.mark.parametrize("differential", [False, True])
def test_training_reduces_own_objective_without_gamma_loss(differential):
    x, prices, deltas = fixture()
    fit = dml.train(
        x,
        prices,
        deltas,
        seed=11,
        batch_seed=29,
        dml=differential,
        max_updates=64,
        batch_size=12,
        budget_s=30,
    )
    assert fit.stats["updates"] == 64
    assert fit.stats["status"] == "completed"
    assert fit.stats["complete"]
    assert fit.stats["final_loss"] < fit.stats["initial_loss"]
    assert dml.predict(fit, x).shape == (len(x), 3)
    assert np.isfinite(dml.predict(fit, x)).all()
    assert fit.stats["gamma_loss"] is False
    assert next(fit.model.parameters()).dtype == torch.float64
    assert next(fit.model.parameters()).device.type == "cpu"


def test_initialization_roles_and_batches_are_paired_and_replayable():
    x, prices, deltas = fixture()
    kwargs = dict(seed=11, batch_seed=29, max_updates=4, batch_size=5, budget_s=30)
    plain = dml.train(x, prices, deltas, dml=False, **kwargs)
    twin = dml.train(x, prices, deltas, dml=True, **kwargs)
    replay = dml.train(x, prices, deltas, dml=False, **kwargs)
    assert np.array_equal(plain.stats["batch_indices"], twin.stats["batch_indices"])
    assert np.array_equal(plain.stats["batch_indices"], replay.stats["batch_indices"])
    assert np.allclose(dml.predict(plain, x), dml.predict(replay, x), atol=1e-11, rtol=1e-11)

    # Exhausted time cap exposes initial weights without an optimizer update.
    initial = dict(kwargs, budget_s=1, teacher_s=2)
    a = dml.train(x, prices, deltas, dml=False, **initial)
    b = dml.train(x, prices, deltas, dml=True, **initial)
    c = dml.train(x, prices, deltas, dml=False, **dict(initial, batch_seed=47))
    for key, value in dml.export_fit(a)["weights"].items():
        assert np.allclose(value, dml.export_fit(b)["weights"][key])
        assert np.allclose(value, dml.export_fit(c)["weights"][key])


@pytest.mark.parametrize("strike", [73, 100])
def test_numpy_replay_matches_torch_second_derivatives_and_three_spot_bumps(strike):
    fit = fit_small(differential=True, strike=strike)
    x, _, _ = fixture()
    expected = dml.predict(fit, x)
    saved = dml.export_fit(fit)
    actual = dml.numpy_predict(saved["weights"], saved["normalization"], x, strike=strike)
    assert actual.shape == (len(x), 3)
    assert np.allclose(actual, expected, atol=1e-11, rtol=1e-10)
    for h in [0.08, 0.04, 0.02]:
        plus, minus = x.copy(), x.copy()
        plus[:, 0] += h
        minus[:, 0] -= h
        up = dml.numpy_predict(saved["weights"], saved["normalization"], plus, strike=strike)
        down = dml.numpy_predict(saved["weights"], saved["normalization"], minus, strike=strike)
        delta = (up[:, 0] - down[:, 0]) / (2 * h)
        gamma = (up[:, 0] - 2 * actual[:, 0] + down[:, 0]) / h**2
        assert np.allclose(actual[:, 1], delta, atol=1e-6, rtol=1e-4)
        assert np.allclose(actual[:, 2], gamma, atol=1e-7, rtol=1e-3)


def test_numpy_replay_is_rng_free_and_export_does_not_alias_model(monkeypatch):
    fit = fit_small()
    saved = dml.export_fit(fit)
    x, _, _ = fixture()
    expected = dml.predict(fit, x)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved replay must not sample or optimize")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(torch, "manual_seed", forbidden)
    monkeypatch.setattr(torch.optim.Adam, "step", forbidden)
    assert np.allclose(
        dml.numpy_predict(saved["weights"], saved["normalization"], x),
        expected,
        atol=1e-11,
        rtol=1e-10,
    )
    saved["weights"]["first.weight"][:] = 123
    saved["normalization"]["mean"][:] = 456
    assert np.allclose(dml.predict(fit, x), expected, atol=1e-11, rtol=1e-10)


def test_total_price_output_has_no_intrinsic_kink_or_clip():
    fit = fit_small()
    with torch.no_grad():
        for parameter in fit.model.parameters():
            parameter.zero_()
        fit.model.last.bias.fill_(-100)
    x = np.array([[99.9, 90, 0], [100, 90, 0], [100.1, 90, 0]], dtype=float)
    result = dml.predict(fit, x)
    assert np.all(result[:, 0] < 0)
    assert np.allclose(result[:, 1:], 0, atol=1e-14)
    saved = dml.export_fit(fit)
    assert np.allclose(
        dml.numpy_predict(saved["weights"], saved["normalization"], x),
        result,
        atol=1e-11,
        rtol=1e-10,
    )


def test_cpu_rng_and_thread_count_restore_after_success_and_optimizer_failure(monkeypatch):
    x, prices, deltas = fixture()
    old_threads = torch.get_num_threads()
    old_rng = torch.get_rng_state().clone()
    success = fit_small()
    assert success.stats["threads"] == 1
    assert torch.get_num_threads() == old_threads
    assert torch.equal(torch.get_rng_state(), old_rng)

    def failing_step(self, *args, **kwargs):
        assert torch.get_num_threads() == 1
        raise RuntimeError("synthetic optimizer failure")

    monkeypatch.setattr(torch.optim.Adam, "step", failing_step)
    failure = dml.train(
        x,
        prices,
        deltas,
        seed=11,
        batch_seed=29,
        dml=True,
        max_updates=3,
        batch_size=5,
        budget_s=30,
    )
    assert failure.stats["status"] == "optimizer_error"
    assert not failure.stats["complete"]
    assert failure.stats["updates"] == 0
    assert "synthetic optimizer failure" in failure.stats["reason"]
    assert torch.get_num_threads() == old_threads
    assert torch.equal(torch.get_rng_state(), old_rng)


def test_time_cap_retains_zero_updates_and_teacher_cost():
    fit = fit_small(teacher_s=40)
    assert fit.stats["updates"] == 0
    assert fit.stats["status"] == "time_cap"
    assert not fit.stats["complete"]
    assert fit.stats["batch_indices"].shape == (0, 5)
    assert fit.stats["teacher_and_training_s"] == pytest.approx(40 + fit.stats["training_s"])
    assert fit.stats["overrun_s"] == pytest.approx(
        max(0, fit.stats["teacher_and_training_s"] - fit.stats["budget_s"])
    )


def test_time_cap_after_one_update_keeps_actual_overrun(monkeypatch):
    clock = {"seconds": 0.0}
    original = torch.optim.Adam.step

    def controlled_step(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        clock["seconds"] += 2.0
        return result

    monkeypatch.setattr(dml, "perf_counter", lambda: clock["seconds"])
    monkeypatch.setattr(torch.optim.Adam, "step", controlled_step)
    x, prices, deltas = fixture()
    fit = dml.train(
        x,
        prices,
        deltas,
        seed=11,
        batch_seed=29,
        dml=False,
        max_updates=3,
        batch_size=5,
        budget_s=1,
        teacher_s=0.2,
    )
    assert fit.stats["updates"] == 1
    assert fit.stats["status"] == "time_cap"
    assert not fit.stats["complete"]
    assert fit.stats["training_s"] == pytest.approx(2)
    assert fit.stats["overrun_s"] == pytest.approx(1.2)


def test_nonfinite_loss_is_recorded_as_failed_fit(monkeypatch):
    def nan_forward(self, inputs):
        return inputs[:, 0] * torch.tensor(float("nan"))

    monkeypatch.setattr(dml._CallNet, "forward", nan_forward)
    fit = fit_small(differential=True)
    assert fit.stats["status"] == "nonfinite_loss"
    assert not fit.stats["complete"]
    assert fit.stats["updates"] == 0
    assert fit.stats["initial_loss"] is None


@pytest.mark.parametrize("column,value", [(0, 0), (1, 0), (1, -1), (2, 0.5)])
def test_mathematically_invalid_inputs_rejected(column, value):
    x, prices, deltas = fixture()
    x[0, column] = value
    with pytest.raises(ValueError):
        dml.train(x, prices, deltas, seed=11, batch_seed=29, dml=False)


def test_constant_train_features_and_labels_have_finite_scales():
    x = np.array([[100, 60, 0], [100, 60, 0]], dtype=float)
    scale = dml.normalization(x, np.array([1, 1.0]), np.array([0, 0.0]))
    assert np.all(scale["std"] > 0)
    assert scale["price_scale"] > 0 and scale["delta_scale"] > 0


def test_cpu_model_ignores_an_ambient_non_cpu_default_device():
    with torch.device("meta"):
        fit = fit_small(teacher_s=40)
        assert next(fit.model.parameters()).device.type == "cpu"
        x, _, _ = fixture()
        assert np.isfinite(dml.predict(fit, x)).all()


def test_cpu_training_never_seeds_accelerator_generators(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("CPU learner must not seed accelerator generators")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    monkeypatch.setattr(torch.mps, "manual_seed", forbidden)
    monkeypatch.setattr(torch.xpu, "manual_seed_all", forbidden)
    before = torch.get_rng_state().clone()
    fit = fit_small(differential=True, updates=2)
    assert fit.stats["complete"]
    assert fit.stats["updates"] == 2
    assert torch.equal(torch.get_rng_state(), before)


@pytest.mark.parametrize("differential", [False, True])
def test_optimizer_execution_uses_cpu_and_restores_ambient_meta_device(differential, monkeypatch):
    original_step = torch.optim.Adam.step
    states = []

    def tracked_step(self, *args, **kwargs):
        result = original_step(self, *args, **kwargs)
        states.append(
            [
                value.device.type
                for state in self.state.values()
                for value in state.values()
                if isinstance(value, torch.Tensor)
            ]
        )
        return result

    monkeypatch.setattr(torch.optim.Adam, "step", tracked_step)
    with torch.device("meta"):
        fit = fit_small(differential=differential, updates=2)
        assert torch.empty(0).device.type == "meta"
    assert fit.stats["complete"]
    assert fit.stats["updates"] == 2
    assert len(states) == 2
    assert all(row and set(row) == {"cpu"} for row in states)
    assert all(parameter.device.type == "cpu" for parameter in fit.model.parameters())


def test_predict_enables_greeks_and_restores_ambient_no_grad():
    fit = fit_small(differential=True)
    x, _, _ = fixture()
    expected = dml.predict(fit, x)
    with torch.no_grad():
        actual = dml.predict(fit, x)
        assert not torch.is_grad_enabled()
    assert np.allclose(actual, expected, atol=1e-11, rtol=1e-10)
    assert torch.is_grad_enabled()


@pytest.mark.parametrize("differential", [False, True])
def test_training_enables_grad_and_restores_caller_no_grad(differential):
    with torch.no_grad():
        fit = fit_small(differential=differential, updates=2)
        assert not torch.is_grad_enabled()
    assert fit.stats["complete"]
    assert fit.stats["updates"] == 2
    assert torch.is_grad_enabled()
