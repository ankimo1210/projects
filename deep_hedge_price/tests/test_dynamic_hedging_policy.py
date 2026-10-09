"""Independent observables, cash, gradients and CPU-state tests for dynamic policy."""

import numpy as np
import pytest
import torch

from deep_hedge_price._dynamic_hedging_policy import (
    _PolicyNet,
    _torch_rollout,
    _weights,
    fit_policy,
    numpy_policy,
    observable_features,
)


def dataset():
    prices = np.array(
        [
            [[100.0, 6.0], [104.0, 8.0], [102.0, 5.0]],
            [[100.0, 6.0], [96.0, 4.0], [99.0, 5.0]],
            [[100.0, 6.0], [102.0, 7.0], [106.0, 9.0]],
            [[100.0, 6.0], [99.0, 5.0], [95.0, 3.0]],
        ]
    )
    return {
        "times": np.array([0.0, 0.5, 1.0]),
        "prices": prices,
        "memory_sum": np.column_stack([np.zeros(4), 6 * prices[:, 1, 0]]),
        "memory_count": np.array([0, 6]),
        "payoff": np.array([3.0, 1.0, 6.0, 0.0]),
        "premium": 7.0,
        "rate": 0.05,
        "cost_rates": np.array([0.001, 0.005]),
        "cashflows": np.tile(np.array([[0.0, 0.0], [0.4, 0.2], [0.3, 0.1]]), (4, 1, 1)),
    }


def test_observables_are_exactly_nine_declared_features():
    got = observable_features(
        np.array([100.0, 110.0]),
        0.5,
        np.array([600.0, 650.0]),
        6,
        np.array([6.0, 8.0]),
        np.array([[0.4, 0.5], [0.2, -0.1]]),
        [0.0005, 0.005],
    )
    expected = np.array(
        [
            [0.0, 0.5, 0.5, 0.5, 0.06, 0.4, 0.5, 0.0005, 0.005],
            [np.log(1.1), 0.5, 650 / 1200, 0.5, 0.08, 0.2, -0.1, 0.0005, 0.005],
        ]
    )
    assert got.shape == (2, 9)
    assert got == pytest.approx(expected)
    with pytest.raises(ValueError):
        observable_features(0.0, 0.0, 0.0, 0, 6.0, [0.0, 0.0], [0.0005, 0.005])


def test_numpy_export_matches_torch_bounded_actions_without_rng():
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(29)
        model = _PolicyNet()
    features = np.linspace(-0.8, 0.9, 45).reshape(5, 9)
    scaler = {"mean": np.linspace(-0.2, 0.3, 9), "std": np.linspace(0.5, 1.5, 9)}
    z = (features - scaler["mean"]) / scaler["std"]
    expected = model(torch.tensor(z, dtype=torch.float64)).detach().numpy()
    rng = np.random.get_state()
    got = numpy_policy(_weights(model), features, scaler, universe="U2")
    after = np.random.get_state()
    assert got == pytest.approx(expected, abs=1e-13)
    assert np.max(np.abs(got)) <= 2.0
    assert rng[0] == after[0] and np.array_equal(rng[1], after[1])
    one = numpy_policy(_weights(model), features, scaler, universe="U1")
    assert one[:, 0] == pytest.approx(expected[:, 0])
    assert one[:, 1] == pytest.approx(np.zeros(5))


def test_torch_cash_matches_independent_discounted_gain_and_core():
    data = dataset()
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(11)
        model = _PolicyNet()
    scaler = {"mean": np.zeros(9), "std": np.ones(9)}
    got = _torch_rollout(model, data, scaler, universe="U2")
    h = got["holdings"].detach().numpy()
    prices, times, cf, fees = (data["prices"], data["times"], data["cashflows"], data["cost_rates"])
    disc = np.exp(-data["rate"] * times)
    discounted_prices = prices * disc[None, :, None]
    gains = np.sum(h * np.diff(discounted_prices, axis=1), axis=(1, 2))
    dividends = np.sum(h * cf[:, 1:] * disc[None, 1:, None], axis=(1, 2))
    trades = np.concatenate([h[:, :1], np.diff(h, axis=1), -h[:, -1:]], axis=1)
    costs = np.sum(fees * prices * np.abs(trades), axis=2)
    expected = data["premium"] + gains + dividends - costs @ disc - data["payoff"] * disc[-1]
    assert got["discounted_pnl"].detach().numpy() == pytest.approx(expected, abs=2e-12)
    assert got["costs"].detach().numpy() == pytest.approx(costs, abs=1e-13)
    from hullkit._dynamic_hedging_core import cash_account

    core = cash_account(
        times,
        prices,
        h,
        data["payoff"],
        premium=data["premium"],
        rate=data["rate"],
        cashflows=cf,
        cost_rates=fees,
    )
    assert core["discounted_pnl"] == pytest.approx(expected, abs=2e-12)


def test_bptt_cash_gradient_matches_parameter_bump():
    data = dataset()
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(47)
        model = _PolicyNet()
    scaler = {"mean": np.zeros(9), "std": np.ones(9)}
    objective = _torch_rollout(model, data, scaler, universe="U2")["discounted_pnl"].square().mean()
    objective.backward()
    analytic = model.last.bias.grad[0].item()
    original = model.last.bias[0].item()
    values = []
    for shift in [-1e-5, 1e-5]:
        with torch.no_grad():
            model.last.bias[0] = original + shift
        values.append(
            _torch_rollout(model, data, scaler, universe="U2")["discounted_pnl"]
            .square()
            .mean()
            .item()
        )
    with torch.no_grad():
        model.last.bias[0] = original
    assert analytic == pytest.approx((values[1] - values[0]) / 2e-5, rel=2e-7, abs=2e-7)


def test_fit_retains_attempts_and_restores_rng_dtype_and_threads():
    data = dataset()
    np_before = np.random.get_state()
    torch_before = torch.random.get_rng_state().clone()
    dtype, threads = torch.get_default_dtype(), torch.get_num_threads()
    got = fit_policy(
        data,
        universe="U1",
        seed=11,
        updates=3,
        batch_size=4,
        learning_rate=0.003,
        cap_seconds=60.0,
    )
    assert got["status"] == "completed"
    assert got["updates"] == 3 and got["attempt_count"] == 3
    assert got["original_path_count"] == 4
    assert got["batch_indices"].shape == (3, 4)
    assert len(got["losses"]) == 3
    assert got["train_holdings"][:, :, 1] == pytest.approx(np.zeros((4, 2)))
    assert torch.equal(torch_before, torch.random.get_rng_state())
    assert torch.get_default_dtype() == dtype and torch.get_num_threads() == threads
    np_after = np.random.get_state()
    assert np_before[0] == np_after[0] and np.array_equal(np_before[1], np_after[1])
    assert got["scaler"]["mean"][:5] == pytest.approx(
        observable_features(
            data["prices"][:, :-1, 0],
            data["times"][:-1],
            data["memory_sum"],
            data["memory_count"],
            data["prices"][:, :-1, 1],
            np.zeros((4, 2, 2)),
            data["cost_rates"],
        )
        .reshape(-1, 9)
        .mean(axis=0)[:5]
    )


def test_zero_time_cap_is_preserved_as_incomplete_attempt():
    got = fit_policy(
        dataset(),
        universe="U2",
        seed=29,
        updates=2,
        batch_size=4,
        learning_rate=0.003,
        cap_seconds=0.0,
    )
    assert got["status"] == "time_cap"
    assert not got["complete"] and got["updates"] == 0
    assert got["attempt_count"] == 0
    assert got["batch_indices"].shape == (0, 4)
    assert all(np.isfinite(a).all() for a in got["weights"].values())
    assert got["overrun_seconds"] >= 0.0


def test_exported_numpy_policy_replays_all_observable_dates_and_cash():
    data = dataset()
    result = fit_policy(
        data,
        universe="U2",
        seed=47,
        updates=2,
        batch_size=4,
        learning_rate=0.003,
        cap_seconds=60.0,
    )
    old = np.zeros((4, 2))
    all_holdings = []
    for j, time in enumerate(data["times"][:-1]):
        features = observable_features(
            data["prices"][:, j, 0],
            time,
            data["memory_sum"][:, j],
            data["memory_count"][j],
            data["prices"][:, j, 1],
            old,
            data["cost_rates"],
        )
        old = numpy_policy(result["weights"], features, result["scaler"], universe="U2")
        all_holdings.append(old.copy())
    holdings = np.stack(all_holdings, axis=1)
    assert holdings == pytest.approx(result["train_holdings"], abs=3e-13)
    from hullkit._dynamic_hedging_core import cash_account

    cash = cash_account(
        data["times"],
        data["prices"],
        holdings,
        data["payoff"],
        premium=data["premium"],
        rate=data["rate"],
        cashflows=data["cashflows"],
        cost_rates=data["cost_rates"],
    )
    assert cash["discounted_pnl"] == pytest.approx(result["train_discounted_pnl"], abs=3e-12)


def test_nonfinite_objective_retains_all_paths_and_incomplete_status():
    data = dataset()
    data["payoff"] = np.full(4, 1e200)
    result = fit_policy(
        data,
        universe="U2",
        seed=11,
        updates=2,
        batch_size=4,
        learning_rate=0.003,
        cap_seconds=60.0,
    )
    assert not result["complete"] and result["status"] == "nonfinite_loss"
    assert result["original_path_count"] == 4 and result["updates"] == 0
    assert result["train_discounted_pnl"].shape == (4,)
    assert result["attempt_count"] == 0
    assert np.isinf(result["initial_loss"])


def test_malformed_math_data_is_rejected_without_path_filtering():
    data = dataset()
    data["prices"][2, 1, 0] = np.nan
    with pytest.raises(ValueError, match="finite two-asset"):
        fit_policy(
            data,
            universe="U1",
            seed=11,
            updates=1,
            batch_size=4,
            learning_rate=0.003,
            cap_seconds=60.0,
        )


def test_final_diagnostic_cap_overrun_is_not_complete(monkeypatch):
    from deep_hedge_price import _dynamic_hedging_policy as policy

    clock = iter([0.0, 0.1, 0.2, 2.0])
    monkeypatch.setattr(policy, "perf_counter", lambda: next(clock))
    result = fit_policy(
        dataset(),
        universe="U2",
        seed=11,
        updates=1,
        batch_size=4,
        learning_rate=0.003,
        cap_seconds=1.0,
    )
    assert not result["complete"]
    assert result["status"] == "time_cap"
    assert result["updates"] == 1 and result["updates_complete"]
    assert result["overrun_seconds"] == pytest.approx(1.0)
