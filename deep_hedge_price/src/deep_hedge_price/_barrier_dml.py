"""Private CPU price-only/DML learner for the discrete-barrier experiment.

Consumes physical [spot, maturity] and price/spot-Delta arrays. Only training
labels determine scales. The unconstrained linear price output can represent
negative Delta and a positive continuation limit as spot approaches H from
below. Contract validation, initial KO and fallback belong to the caller.
No financial teacher or hullkit implementation is imported here.
"""

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import torch
from torch import nn


def _inputs(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError("finite nonempty [spot,maturity] rows required")
    if np.any(x <= 0):
        raise ValueError("positive spot and maturity required")
    return x


def normalization(x, p, d):
    """Derive [S,log(T)] feature, price and physical Delta scales from train only."""
    x = _inputs(x)
    price, delta = np.asarray(p, dtype=float), np.asarray(d, dtype=float)
    if price.shape != (len(x),) or delta.shape != price.shape:
        raise ValueError("price and spot Delta labels must match scenario rows")
    if not np.isfinite(price).all() or not np.isfinite(delta).all():
        raise ValueError("finite price and spot Delta labels required")
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    return {
        "feature_mean": features.mean(axis=0),
        "feature_std": np.where(np.ptp(features, axis=0) > 0, features.std(axis=0), 1.0),
        "price_mean": float(price.mean()),
        "price_scale": max(float(price.std()), 1e-8),
        "delta_scale": max(float(np.sqrt(np.mean(delta * delta))), 1e-8),
    }


class _BarrierNet(nn.Module):
    def __init__(self, scale):
        super().__init__()
        self.register_buffer(
            "feature_mean", torch.tensor(scale["feature_mean"], dtype=torch.float64, device="cpu")
        )
        self.register_buffer(
            "feature_std", torch.tensor(scale["feature_std"], dtype=torch.float64, device="cpu")
        )
        self.price_mean, self.price_scale = scale["price_mean"], scale["price_scale"]
        self.layers = nn.ModuleList(
            [
                nn.Linear(2, 32, dtype=torch.float64, device="cpu"),
                nn.Linear(32, 32, dtype=torch.float64, device="cpu"),
                nn.Linear(32, 1, dtype=torch.float64, device="cpu"),
            ]
        )

    def forward(self, raw):
        features = torch.stack([raw[:, 0], torch.log(raw[:, 1])], dim=1)
        h = (features - self.feature_mean) / self.feature_std
        for layer in self.layers[:-1]:
            h = torch.tanh(layer(h))
        return self.price_mean + self.price_scale * self.layers[-1](h).squeeze(-1)


@dataclass
class Fit:
    """An inspectable private model, train scales and measured partial/full fit."""

    model: nn.Module
    scale: dict
    stats: dict


def train(x, p, d, *, seed, dml, updates=512, budget_s=120.0):
    """Train a paired 2→32→32→1 CPU float64 network with price/Delta loss.

    Both modes share initial weights, Adam lr=.003 and a seeded batch schedule
    of min(128,n) rows. DML adds the mean squared physical spot-Delta error
    divided by training Delta RMS, with weight one. Maturity derivatives are
    not trained as Greeks. The cap covers setup and fitting; an incomplete
    fit is returned with budget_failure rather than discarded or retried.
    CPU RNG, default device and thread state are isolated from the caller.
    """
    if int(updates) != updates or updates < 1 or not np.isfinite(budget_s) or budget_s <= 0:
        raise ValueError("positive integer update count and time budget required")
    start = perf_counter()
    x = _inputs(x)
    scale = normalization(x, p, d)
    dml = bool(dml)
    n = len(x)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        # Adam's internal step-state allocation must also inherit CPU even if
        # an embedding application has changed the default device to meta/GPU.
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            model = _BarrierNet(scale)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
            xx = torch.tensor(x, dtype=torch.float64, device="cpu")
            pp = torch.tensor(p, dtype=torch.float64, device="cpu")
            dd = torch.tensor(d, dtype=torch.float64, device="cpu")
            batch_rng = torch.Generator(device="cpu").manual_seed(seed + 104729)

            def objective(indices):
                raw = xx[indices].detach().requires_grad_(dml)
                value = model(raw)
                price_loss = (((value - pp[indices]) / scale["price_scale"]) ** 2).mean()
                delta_loss = value.new_zeros(())
                if dml:
                    derivative = torch.autograd.grad(value.sum(), raw, create_graph=True)[0][:, 0]
                    delta_loss = (((derivative - dd[indices]) / scale["delta_scale"]) ** 2).mean()
                return price_loss, delta_loss

            full = torch.arange(n, device="cpu")
            initial_price, initial_delta = (float(value.detach()) for value in objective(full))
            setup_s = perf_counter() - start
            training_start = perf_counter()
            completed = 0
            for _ in range(int(updates)):
                if perf_counter() - start >= budget_s:
                    break
                indices = torch.randperm(n, generator=batch_rng, device="cpu")[: min(128, n)]
                optimizer.zero_grad(set_to_none=True)
                price_loss, delta_loss = objective(indices)
                loss = price_loss + delta_loss
                if not torch.isfinite(loss):
                    raise ArithmeticError("nonfinite barrier DML training loss")
                loss.backward()
                optimizer.step()
                completed += 1
            final_price, final_delta = (float(value.detach()) for value in objective(full))
            training_s = perf_counter() - training_start
    finally:
        torch.set_num_threads(old_threads)
    elapsed = perf_counter() - start
    return Fit(
        model.eval(),
        scale,
        {
            "seed": int(seed),
            "dml": dml,
            "updates": completed,
            "requested_updates": int(updates),
            "batch_size": min(128, n),
            "batch_seed": int(seed + 104729),
            "threads": 1,
            "learning_rate": 0.003,
            "delta_weight": 1.0 if dml else 0.0,
            "setup_s": setup_s,
            "training_s": training_s,
            "elapsed_s": elapsed,
            "budget_s": float(budget_s),
            "overrun_s": max(0.0, elapsed - budget_s),
            "budget_failure": completed != updates or elapsed > budget_s,
            "initial_price_loss": initial_price,
            "initial_delta_loss": initial_delta,
            "initial_loss": initial_price + initial_delta,
            "final_price_loss": final_price,
            "final_delta_loss": final_delta,
            "final_loss": final_price + final_delta,
        },
    )


def predict(fit, x):
    """Return raw continuation price and physical spot Delta arrays on CPU."""
    raw = torch.tensor(_inputs(x), dtype=torch.float64, device="cpu", requires_grad=True)
    value = fit.model(raw)
    delta = torch.autograd.grad(value.sum(), raw)[0][:, 0]
    return value.detach().numpy(), delta.detach().numpy()


def export(fit):
    """Copy weights, train scales and fit statistics for independent NumPy replay."""
    result = {
        "kind": "barrier_nn",
        "dml": fit.stats["dml"],
        "stats": fit.stats.copy(),
        **{
            key: value.copy() if isinstance(value, np.ndarray) else value
            for key, value in fit.scale.items()
        },
    }
    for i, layer in enumerate(fit.model.layers):
        result[f"layer{i}_weight"] = layer.weight.detach().numpy().copy()
        result[f"layer{i}_bias"] = layer.bias.detach().numpy().copy()
    return result
