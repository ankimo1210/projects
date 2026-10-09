"""Private observable CPU policy for the fixed monthly K100/T1 Asian study.

Finance prices and cashflows are caller-owned constants. Gradients flow through
bounded actions, previous holdings and self-financing cash, including liquidation.
No generator state, latent variance, test scaler or future payoff enters features.
"""

from time import perf_counter

import numpy as np
import torch
from torch import nn


def observable_features(spot, time, memory_sum, memory_count, quote, old_holdings, spreads):
    """Return the nine declared physical features for K100/T1/12 fixings."""
    old = np.asarray(old_holdings, dtype=float)
    fee = np.asarray(spreads, dtype=float)
    if old.shape[-1:] != (2,) or fee.shape != (2,):
        raise ValueError("two previous holdings and two spreads required")
    s, t, a, n, q, hs, hq, fs, fq = np.broadcast_arrays(
        spot,
        time,
        memory_sum,
        memory_count,
        quote,
        old[..., 0],
        old[..., 1],
        fee[0],
        fee[1],
    )
    if np.any(s <= 0) or np.any((t < 0) | (t > 1)) or np.any((n < 0) | (n > 12)):
        raise ValueError("positive spot, time in [0,1], memory count in [0,12] required")
    return np.stack([np.log(s / 100), t, a / 1200, n / 12, q / 100, hs, hq, fs, fq], axis=-1)


def _universe(universe):
    if universe not in ("U1", "U2"):
        raise ValueError("universe must be U1 or U2")


def numpy_policy(weights, features, scaler, *, universe):
    """Replay exported 9→32→32→2 tanh CPU weights without RNG or Torch calls."""
    _universe(universe)
    x = (np.asarray(features, dtype=float) - scaler["mean"]) / scaler["std"]
    x = np.tanh(x @ weights["w1"] + weights["b1"])
    x = np.tanh(x @ weights["w2"] + weights["b2"])
    actions = 2 * np.tanh(x @ weights["w3"] + weights["b3"])
    if universe == "U1":
        actions[..., 1] = 0.0
    return actions


class _PolicyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.first = nn.Linear(9, 32, dtype=torch.float64, device="cpu")
        self.second = nn.Linear(32, 32, dtype=torch.float64, device="cpu")
        self.last = nn.Linear(32, 2, dtype=torch.float64, device="cpu")

    def forward(self, inputs):
        return 2 * torch.tanh(self.last(torch.tanh(self.second(torch.tanh(self.first(inputs))))))


def _weights(model):
    return {
        "w1": model.first.weight.detach().numpy().T.copy(),
        "b1": model.first.bias.detach().numpy().copy(),
        "w2": model.second.weight.detach().numpy().T.copy(),
        "b2": model.second.bias.detach().numpy().copy(),
        "w3": model.last.weight.detach().numpy().T.copy(),
        "b3": model.last.bias.detach().numpy().copy(),
    }


def _restore_weights(model, weights):
    with torch.no_grad():
        for layer, index in [(model.first, 1), (model.second, 2), (model.last, 3)]:
            layer.weight.copy_(torch.as_tensor(weights[f"w{index}"].T, dtype=torch.float64))
            layer.bias.copy_(torch.as_tensor(weights[f"b{index}"], dtype=torch.float64))


def _dataset(data):
    times = np.asarray(data["times"], dtype=float)
    prices = np.asarray(data["prices"], dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or times[0] != 0
        or times[-1] > 1
        or not np.isfinite(times).all()
        or np.any(np.diff(times) <= 0)
        or prices.ndim != 3
        or prices.shape[1:] != (len(times), 2)
        or len(prices) == 0
        or not np.isfinite(prices).all()
        or np.any(prices[..., 0] <= 0)
        or np.any(prices[..., 1] < 0)
    ):
        raise ValueError("finite two-asset paths on increasing time-zero grid required")
    n, m = len(prices), len(times) - 1
    memory = np.asarray(data["memory_sum"], dtype=float)
    counts = np.asarray(data["memory_count"], dtype=float)
    if memory.shape not in ((n, m), (n, m + 1)):
        raise ValueError("memory sum must match path/rebalance dates")
    if counts.shape not in ((m,), (m + 1,), (n, m), (n, m + 1)):
        raise ValueError("memory count must match rebalance dates")
    memory = memory[:, :m]
    counts = np.broadcast_to(counts[..., :m], (n, m))
    payoff = np.asarray(data["payoff"], dtype=float)
    cf = np.asarray(data.get("cashflows", np.zeros_like(prices)), dtype=float)
    fees = np.asarray(data["cost_rates"], dtype=float)
    premium, rate = float(data["premium"]), float(data["rate"])
    if (
        payoff.shape != (n,)
        or cf.shape != prices.shape
        or fees.shape != (2,)
        or np.any(fees < 0)
        or not all(np.isfinite(a).all() for a in [memory, counts, payoff, cf, fees])
        or not np.isfinite([premium, rate]).all()
    ):
        raise ValueError("finite matching payoff, CF, costs and cash conventions required")
    return {
        "times": times,
        "prices": prices,
        "memory_sum": memory,
        "memory_count": counts,
        "payoff": payoff,
        "cashflows": cf,
        "cost_rates": fees,
        "premium": premium,
        "rate": rate,
    }


def _normalization(data):
    prices, times = data["prices"], data["times"]
    zero = np.zeros((len(prices), len(times) - 1, 2))
    features = observable_features(
        prices[:, :-1, 0],
        times[:-1],
        data["memory_sum"],
        data["memory_count"],
        prices[:, :-1, 1],
        zero,
        data["cost_rates"],
    ).reshape(-1, 9)
    deviation = features.std(axis=0)
    return {
        "mean": features.mean(axis=0),
        "std": np.where(deviation > 1e-12, deviation, 1.0),
        "source": "training_paths_only; previous holdings anchored at zero",
        "training_path_count": len(prices),
    }


def _torch_rollout(model, dataset, scaler, *, universe):
    """Roll all dates with old-holding BPTT and caller prices kept constant."""
    _universe(universe)
    data = _dataset(dataset)

    def to_tensor(x):
        return torch.as_tensor(x, dtype=torch.float64, device="cpu")

    prices, cf, fees = (to_tensor(data[key]) for key in ["prices", "cashflows", "cost_rates"])
    times = data["times"]
    n, m, _ = prices.shape
    mean, scale = to_tensor(scaler["mean"]), to_tensor(scaler["std"])
    constants = observable_features(
        data["prices"][:, :-1, 0],
        times[:-1],
        data["memory_sum"],
        data["memory_count"],
        data["prices"][:, :-1, 1],
        np.zeros((n, m - 1, 2)),
        data["cost_rates"],
    )
    constants = to_tensor(constants)
    old = torch.zeros((n, 2), dtype=torch.float64, device="cpu")
    cash = torch.full((n,), data["premium"], dtype=torch.float64, device="cpu")
    holdings, costs, cash_history = [], [], []
    for j in range(m - 1):
        if j:
            cash = cash * np.exp(data["rate"] * (times[j] - times[j - 1]))
        cash = cash + torch.sum(old * cf[:, j], dim=1)
        features = torch.cat([constants[:, j, :5], old, constants[:, j, 7:]], dim=1)
        action = model((features - mean) / scale)
        if universe == "U1":
            action = action * to_tensor([1.0, 0.0])
        trade = action - old
        cost = torch.sum(fees * prices[:, j] * torch.abs(trade), dim=1)
        cash = cash - torch.sum(trade * prices[:, j], dim=1) - cost
        holdings.append(action)
        costs.append(cost)
        cash_history.append(cash)
        old = action
    cash = cash * np.exp(data["rate"] * (times[-1] - times[-2]))
    cash = cash + torch.sum(old * cf[:, -1], dim=1)
    terminal_cost = torch.sum(fees * prices[:, -1] * torch.abs(old), dim=1)
    cash = cash + torch.sum(old * prices[:, -1], dim=1) - terminal_cost - to_tensor(data["payoff"])
    costs.append(terminal_cost)
    cash_history.append(cash)
    return {
        "holdings": torch.stack(holdings, dim=1),
        "costs": torch.stack(costs, dim=1),
        "cash": torch.stack(cash_history, dim=1),
        "pnl": cash,
        "discounted_pnl": cash * np.exp(-data["rate"] * times[-1]),
    }


def fit_policy(dataset, *, universe, seed, updates, batch_size, learning_rate, cap_seconds):
    """Fit training-only net-P&L MSE and retain every attempted batch/failure.

    CPU RNG and thread count are restored. The time cap includes validation,
    setup and final diagnostic replay; it is checked before each optimizer
    update, so one update and final evaluation may overrun. Last finite weights
    remain available with an explicit incomplete status when any attempt fails.
    """
    start = perf_counter()
    _universe(universe)
    data = _dataset(dataset)
    if (
        updates < 1
        or int(updates) != updates
        or batch_size < 1
        or int(batch_size) != batch_size
        or not np.isfinite([learning_rate, cap_seconds]).all()
        or learning_rate <= 0
        or cap_seconds < 0
    ):
        raise ValueError("positive update/batch/rate and nonnegative finite cap required")
    updates, batch_size = int(updates), int(batch_size)
    scaler = _normalization(data)
    old_threads = torch.get_num_threads()
    losses, batches, attempt_events = [], [], []
    done, status, reason = 0, "time_cap", "time cap before first update"
    initial_loss = final_loss = None
    torch.set_num_threads(1)
    try:
        with torch.device("cpu"), torch.enable_grad(), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            model = _PolicyNet()
            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
            batch_rng = np.random.default_rng(np.random.SeedSequence([seed, 1937]))
            last_finite = _weights(model)
            if perf_counter() - start < cap_seconds:
                initial_loss = float(
                    _torch_rollout(model, data, scaler, universe=universe)["discounted_pnl"]
                    .square()
                    .mean()
                    .detach()
                )
                if not np.isfinite(initial_loss):
                    status, reason = "nonfinite_loss", "nonfinite initial training objective"
                else:
                    for _ in range(updates):
                        if perf_counter() - start >= cap_seconds:
                            status, reason = "time_cap", "time cap before next update"
                            break
                        rows = batch_rng.integers(
                            0, len(data["prices"]), size=batch_size, dtype=np.int32
                        )
                        batches.append(rows)
                        batch = {
                            key: value[rows]
                            if isinstance(value, np.ndarray)
                            and key
                            in ("prices", "memory_sum", "memory_count", "payoff", "cashflows")
                            else value
                            for key, value in data.items()
                        }
                        optimizer.zero_grad(set_to_none=True)
                        loss = (
                            _torch_rollout(model, batch, scaler, universe=universe)[
                                "discounted_pnl"
                            ]
                            .square()
                            .mean()
                        )
                        losses.append(float(loss.detach()))
                        event = {"attempt": len(batches), "status": "pending"}
                        attempt_events.append(event)
                        if not torch.isfinite(loss):
                            status, reason = "nonfinite_loss", "nonfinite batch objective"
                            event["status"] = status
                            break
                        loss.backward()
                        if any(
                            p.grad is not None and not torch.isfinite(p.grad).all()
                            for p in model.parameters()
                        ):
                            status, reason = "nonfinite_gradient", "nonfinite gradient"
                            event["status"] = status
                            break
                        try:
                            optimizer.step()
                        except RuntimeError as exc:
                            status, reason = "optimizer_error", str(exc)
                            event["status"] = status
                            break
                        done += 1
                        if any(not torch.isfinite(p).all() for p in model.parameters()):
                            status, reason = (
                                "nonfinite_parameters",
                                "nonfinite weights after update",
                            )
                            event["status"] = status
                            break
                        last_finite = _weights(model)
                        event["status"] = "completed"
                    else:
                        status, reason = "completed", None
            _restore_weights(model, last_finite)
            with torch.no_grad():
                result = _torch_rollout(model, data, scaler, universe=universe)
                final_loss = float(result["discounted_pnl"].square().mean())
                train_holdings = result["holdings"].numpy().copy()
                train_pnl = result["discounted_pnl"].numpy().copy()
            if not np.isfinite(final_loss) and status == "completed":
                status, reason = "nonfinite_loss", "nonfinite final training objective"
    finally:
        torch.set_num_threads(old_threads)
    elapsed = perf_counter() - start
    if status == "completed" and elapsed > cap_seconds:
        status, reason = (
            "time_cap",
            "completed updates but final diagnostics/restore exceeded time cap",
        )
    return {
        "weights": last_finite,
        "scaler": scaler,
        "status": status,
        "complete": status == "completed",
        "reason": reason,
        "updates": done,
        "requested_updates": updates,
        "updates_complete": done == updates,
        "attempt_count": len(batches),
        "attempt_events": attempt_events,
        "batch_indices": np.stack(batches)
        if batches
        else np.empty((0, batch_size), dtype=np.int32),
        "losses": np.asarray(losses),
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "train_holdings": train_holdings,
        "train_discounted_pnl": train_pnl,
        "original_path_count": len(data["prices"]),
        "universe": universe,
        "seed": int(seed),
        "batch_seed_components": [int(seed), 1937],
        "batch_size": batch_size,
        "learning_rate": float(learning_rate),
        "cap_seconds": float(cap_seconds),
        "elapsed_seconds": elapsed,
        "overrun_seconds": max(0.0, elapsed - cap_seconds),
        "cost_scope": "validation/setup/train/final diagnostics/CPU thread restore; excludes import",
        "threads": 1,
        "dtype": "float64",
        "device": "cpu",
    }
