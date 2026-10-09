"""Quote DML: physical derivatives, shared risk metric and reduced regression."""

import numpy as np
import pytest
import torch

from deep_hedge_price import _quote_dml as learner


def tiny_train():
    q0 = np.array([0.03, 0.032, 0.033, 0.0345, 0.036])
    q = q0 + np.linspace(-0.001, 0.001, 16)[:, None] * np.array([1.0, -1.0, 0.5, -0.5, 2.0])
    spot, maturity = np.linspace(90.0, 110.0, 16), np.linspace(0.5, 2.0, 16)
    a = 2 * np.eye(5)
    a[1, 0] = 0.3
    w = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    return {
        "x_quote": np.column_stack([q, spot, maturity]),
        "x_theta": np.column_stack([q0 + (q - q0) @ a.T, spot, maturity]),
        "price": 0.4 + 0.005 * (spot - 100) + (q - q0) @ w,
        "g_quote": np.tile(np.r_[0.005, w], (16, 1)),
        "g_theta": np.tile(np.r_[0.005, np.linalg.solve(a.T, w)], (16, 1)),
        "A": np.tile(a, (16, 1, 1)),
    }


@pytest.mark.parametrize("mode", learner.MODES)
def test_physical_spot_and_quote_derivatives_agree_with_revaluation(mode):
    train = tiny_train()
    fit = learner.fit_nn(train, mode=mode, seed=11, updates=2)
    key = "x_theta" if mode.startswith("theta") else "x_quote"
    x, a = train[key][:3], train["A"][:3]
    prediction = learner.predict_nn(fit, x, a)
    assert prediction["g_quote"].shape == (3, 6)
    plus, minus = x.copy(), x.copy()
    plus[:, 5] += 1e-3
    minus[:, 5] -= 1e-3
    finite_delta = (
        learner.predict_nn(fit, plus, a)["price"] - learner.predict_nn(fit, minus, a)["price"]
    ) / 0.002
    np.testing.assert_allclose(prediction["g_quote"][:, 0], finite_delta, atol=1e-8, rtol=1e-6)
    for bucket in range(5):
        shift = a[:, :, bucket] * 1e-6 if mode.startswith("theta") else np.eye(5)[bucket] * 1e-6
        plus, minus = x.copy(), x.copy()
        plus[:, :5] += shift
        minus[:, :5] -= shift
        finite_quote = (
            learner.predict_nn(fit, plus, a)["price"] - learner.predict_nn(fit, minus, a)["price"]
        ) / 2e-6
        # Richardson removes the O(h²) error for this deliberately narrow
        # training domain; both inputs remain physical quote/zero coordinates.
        plus, minus = x.copy(), x.copy()
        plus[:, :5] += shift / 2
        minus[:, :5] -= shift / 2
        half_width = (
            learner.predict_nn(fit, plus, a)["price"] - learner.predict_nn(fit, minus, a)["price"]
        ) / 1e-6
        finite_quote = (4 * half_width - finite_quote) / 3
        np.testing.assert_allclose(
            prediction["g_quote"][:, bucket + 1], finite_quote, atol=1e-8, rtol=1e-6
        )
    expected = (
        np.einsum("nij,ni->nj", a, prediction["g_native"][:, 1:])
        if mode.startswith("theta")
        else prediction["g_native"][:, 1:]
    )
    np.testing.assert_allclose(prediction["g_quote"][:, 1:], expected, atol=1e-10, rtol=1e-9)
    assert fit.stats["updates"] == 2 and not fit.stats["budget_failure"]


def test_normalization_is_train_only_and_metric_uses_correct_physical_labels():
    train = tiny_train()
    quote = learner.fit_nn(train, mode="q_dml", seed=11, updates=2)
    theta = learner.fit_nn(train, mode="theta_quote_metric", seed=11, updates=2)
    internal = learner.fit_nn(train, mode="theta_dml", seed=11, updates=2)
    expected = np.sqrt(np.mean(train["g_quote"] ** 2, axis=0))
    np.testing.assert_allclose(quote.scale["risk_scale"], expected)
    np.testing.assert_allclose(theta.scale["risk_scale"], expected)
    np.testing.assert_allclose(
        internal.scale["risk_scale"], np.sqrt(np.mean(train["g_theta"] ** 2, axis=0))
    )
    exported = learner.export_nn(quote)
    features = train["x_quote"].copy()
    features[:, 5] = np.log(features[:, 5] / 100.0)
    features[:, 6] = np.log(features[:, 6])
    np.testing.assert_allclose(exported["feature_mean"], features.mean(axis=0))
    np.testing.assert_allclose(exported["feature_std"], features.std(axis=0))
    assert exported["price_mean"] == pytest.approx(train["price"].mean())
    assert exported["price_scale"] == pytest.approx(train["price"].std())
    out_of_domain = train["x_quote"].copy()
    out_of_domain[:, :5] += 1.0
    out_of_domain[:, 5:] *= 4.0
    learner.predict_nn(quote, out_of_domain, train["A"])
    for key in ["feature_mean", "feature_std", "price_mean", "price_scale", "risk_scale"]:
        np.testing.assert_allclose(learner.export_nn(quote)[key], exported[key])


def numpy_replay(exported, x, a):
    features = x.copy()
    features[:, 5] = np.log(x[:, 5] / 100.0)
    features[:, 6] = np.log(x[:, 6])
    h = (features - exported["feature_mean"]) / exported["feature_std"]
    activations = []
    for layer in range(2):
        h = np.tanh(h @ exported[f"layer{layer}_weight"].T + exported[f"layer{layer}_bias"])
        activations.append(h)
    price = (h @ exported["layer2_weight"].T + exported["layer2_bias"]).ravel()
    price = exported["price_mean"] + exported["price_scale"] * price
    jac = np.tile(exported["layer2_weight"], (len(x), 1))
    for layer in [1, 0]:
        jac = (jac * (1 - activations[layer] ** 2)) @ exported[f"layer{layer}_weight"]
    jac *= exported["price_scale"] / exported["feature_std"]
    jac[:, 5] /= x[:, 5]
    native = np.column_stack([jac[:, 5], jac[:, :5]])
    quoted = native.copy()
    if exported["mode"].startswith("theta"):
        quoted[:, 1:] = np.einsum("nij,ni->nj", a, native[:, 1:])
    return price, quoted


@pytest.mark.parametrize("mode", learner.MODES)
def test_export_is_sufficient_for_numpy_price_and_greek_replay(mode):
    train = tiny_train()
    fit = learner.fit_nn(train, mode=mode, seed=47, updates=2)
    key = "x_theta" if mode.startswith("theta") else "x_quote"
    x, a = train[key], train["A"]
    exported = learner.export_nn(fit)
    price, greek = numpy_replay(exported, x, a)
    original = learner.predict_nn(fit, x, a)
    np.testing.assert_allclose(price, original["price"], atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(greek, original["g_quote"], atol=1e-10, rtol=1e-9)
    assert exported["layer0_weight"].shape == (64, 7)
    assert exported["layer1_weight"].shape == (64, 64)
    assert exported["layer2_weight"].shape == (1, 64)
    # Exported arrays are owned copies, so recording cannot mutate the live model.
    exported["layer0_weight"][:] = 0
    np.testing.assert_allclose(learner.predict_nn(fit, x, a)["price"], original["price"])


def test_seed_reproducibility_and_cpu_rng_and_threads_are_restored():
    train = tiny_train()
    rng = torch.get_rng_state().clone()
    numpy_rng = np.random.get_state()
    threads = torch.get_num_threads()
    first = learner.fit_nn(train, mode="q_dml", seed=29, updates=2)
    second = learner.fit_nn(train, mode="q_dml", seed=29, updates=2)
    assert torch.equal(torch.get_rng_state(), rng)
    assert torch.get_num_threads() == threads
    after_numpy = np.random.get_state()
    np.testing.assert_array_equal(numpy_rng[1], after_numpy[1])
    assert numpy_rng[2:] == after_numpy[2:]
    np.testing.assert_allclose(
        learner.predict_nn(first, train["x_quote"], train["A"])["price"],
        learner.predict_nn(second, train["x_quote"], train["A"])["price"],
        atol=1e-12,
        rtol=1e-10,
    )
    assert first.stats["setup_s"] >= 0 and first.stats["training_s"] >= 0


@pytest.mark.parametrize("mode", learner.MODES)
def test_reported_loss_uses_mean_of_six_physical_greeks_in_declared_metric(mode):
    train = tiny_train()
    # An exhausted setup budget leaves initialized weights untouched, allowing
    # the loss to be recomputed independently from exported NumPy weights.
    fit = learner.fit_nn(train, mode=mode, seed=11, updates=2, budget_s=1e-12)
    key = "x_theta" if mode.startswith("theta") else "x_quote"
    a = np.tile(np.eye(5), (16, 1, 1)) if mode == "theta_dml" else train["A"]
    value, greek = numpy_replay(learner.export_nn(fit), train[key], a)
    expected_price = np.mean(((value - train["price"]) / fit.scale["price_scale"]) ** 2)
    expected_risk = 0.0
    if mode not in ("q_price", "theta_price"):
        labels = train["g_theta" if mode == "theta_dml" else "g_quote"]
        expected_risk = np.mean(((greek - labels) / fit.scale["risk_scale"]) ** 2)
    assert fit.stats["initial_price_loss"] == pytest.approx(expected_price, abs=1e-12, rel=1e-10)
    assert fit.stats["initial_risk_loss"] == pytest.approx(expected_risk, abs=1e-12, rel=1e-10)
    assert fit.stats["initial_loss"] == pytest.approx(expected_price + expected_risk)


def test_exhausted_watchdog_is_failure_and_invalid_math_is_rejected():
    train = tiny_train()
    fit = learner.fit_nn(train, mode="q_dml", seed=11, updates=2, budget_s=1e-12)
    assert fit.stats["budget_failure"] and fit.stats["updates"] < 2
    with pytest.raises(ValueError, match="mode"):
        learner.fit_nn(train, mode="invented", seed=11, updates=2)
    bad = {**train, "x_quote": train["x_quote"].copy()}
    bad["x_quote"][0, 6] = 0
    with pytest.raises(ValueError, match="positive"):
        learner.fit_nn(bad, mode="q_price", seed=11, updates=2)


def polynomial_train():
    rng = np.random.default_rng(20261009)
    x = np.column_stack(
        [
            rng.uniform(0.02, 0.05, (128, 5)),
            rng.uniform(80.0, 120.0, 128),
            np.exp(rng.uniform(np.log(0.05), np.log(5.0), 128)),
        ]
    )
    aq = np.tile(np.array([0.2, 0.1, 0.8, 0.4, 0.05]), (128, 1))
    rate = np.sum(aq * x[:, :5], axis=1)
    u, r, t = np.log(x[:, 5] / 100.0), rate, np.log(x[:, 6])
    price = (
        0.45 + 0.12 * u - 0.7 * r + 0.03 * t + 0.04 * u * r * t + 0.008 * u**3 + 0.006 * r * t**2
    )
    delta = (0.12 + 0.04 * r * t + 0.024 * u**2) / x[:, 5]
    dr = -0.7 + 0.04 * u * t + 0.006 * t**2
    return {
        "x_quote": x,
        "integrated_rate": rate,
        "a_quote": aq,
        "price": price,
        "g_quote": np.column_stack([delta, dr[:, None] * aq]),
    }


@pytest.mark.parametrize("differential", [False, True])
def test_ridge_has_full_cubic_cross_terms_and_analytic_physical_greeks(differential):
    train = polynomial_train()
    fit = learner.fit_ridge(train, differential=differential)
    assert set(map(tuple, fit["powers"])) == {
        (i, j, k) for i in range(4) for j in range(4) for k in range(4) if i + j + k <= 3
    }
    predicted = learner.predict_ridge(fit, train)
    np.testing.assert_allclose(predicted["price"], train["price"], atol=1e-7, rtol=1e-6)
    np.testing.assert_allclose(predicted["g_quote"], train["g_quote"], atol=1e-7, rtol=1e-6)
    for bucket in range(6):
        plus = {key: value.copy() for key, value in train.items()}
        minus = {key: value.copy() for key, value in train.items()}
        width = 1e-3 if bucket == 0 else 1e-6
        if bucket == 0:
            plus["x_quote"][:, 5] += width
            minus["x_quote"][:, 5] -= width
        else:
            plus["x_quote"][:, bucket - 1] += width
            minus["x_quote"][:, bucket - 1] -= width
            plus["integrated_rate"] += train["a_quote"][:, bucket - 1] * width
            minus["integrated_rate"] -= train["a_quote"][:, bucket - 1] * width
        finite = (
            learner.predict_ridge(fit, plus)["price"] - learner.predict_ridge(fit, minus)["price"]
        ) / (2 * width)
        np.testing.assert_allclose(predicted["g_quote"][:, bucket], finite, atol=1e-8, rtol=1e-6)
    assert fit["kind"] == "ridge" and fit["differential"] == differential


def test_constant_features_and_zero_greek_labels_have_finite_train_scales():
    train = tiny_train()
    train["x_quote"][:, :5] = 0.03
    train["price"][:] = 0.5
    train["g_quote"][:] = 0
    fit = learner.fit_nn(train, mode="q_dml", seed=11, updates=2)
    assert np.all(fit.scale["feature_std"][:5] == 1.0)
    assert fit.scale["price_scale"] == 1e-8
    assert np.all(fit.scale["risk_scale"] == 1e-8)


def test_differential_ridge_minimizes_price_plus_mean_of_six_risk_errors():
    train = polynomial_train()
    phase = np.arange(len(train["price"]))
    train["price"] += 0.003 * np.sin(phase)
    train["g_quote"] += np.cos(phase[:, None]) * np.array([0.0002, 0.03, 0.05, 0.08, 0.02, 0.07])
    fit = learner.fit_ridge(train, differential=True)

    def objective(candidate):
        pred = learner.predict_ridge(candidate, train)
        price_loss = np.mean(((pred["price"] - train["price"]) / candidate["price_scale"]) ** 2)
        risk_loss = np.mean(((pred["g_quote"] - train["g_quote"]) / candidate["risk_scale"]) ** 2)
        penalty = 1e-8 * np.sum(candidate["coefficients"][1:] ** 2)
        return price_loss + risk_loss + penalty

    # Incorrect stacking (sum instead of mean, or price scaling of Greeks)
    # changes this optimum when the two sets of noisy labels cannot both fit.
    for column in range(20):
        plus = {**fit, "coefficients": fit["coefficients"].copy()}
        minus = {**fit, "coefficients": fit["coefficients"].copy()}
        plus["coefficients"][column] += 1e-6
        minus["coefficients"][column] -= 1e-6
        derivative = (objective(plus) - objective(minus)) / 2e-6
        assert derivative == pytest.approx(0.0, abs=1e-7)


def test_cpu_fit_ignores_global_default_device_and_restores_cpu_rng():
    train = tiny_train()
    old_device = torch.get_default_device()
    before_rng = torch.get_rng_state().clone()
    try:
        torch.set_default_device("meta")
        fit = learner.fit_nn(train, mode="q_dml", seed=11, updates=2)
        assert all(parameter.device.type == "cpu" for parameter in fit.model.parameters())
        assert all(buffer.device.type == "cpu" for buffer in fit.model.buffers())
        predicted = learner.predict_nn(fit, train["x_quote"], train["A"])
        assert np.all(np.isfinite(predicted["price"]))
        assert torch.get_default_device().type == "meta"
        assert torch.equal(torch.get_rng_state(), before_rng)
    finally:
        torch.set_default_device(old_device)


def test_cpu_fit_does_not_detect_or_seed_accelerators(monkeypatch):
    train = tiny_train()
    before_rng = torch.get_rng_state().clone()

    def forbidden(*args, **kwargs):
        pytest.fail("CPU learner must not inspect or seed accelerators")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    monkeypatch.setattr(torch.cuda, "device_count", forbidden)
    fit = learner.fit_nn(train, mode="q_dml", seed=11, updates=2)
    assert fit.stats["updates"] == 2
    assert torch.equal(torch.get_rng_state(), before_rng)
