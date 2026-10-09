"""Private CPU short-call price-only/Delta-DML learner and NumPy replay.

Plain rows are [spot, remaining_seconds, event_flag]. A single smooth network
returns an unconstrained total C/K; no intrinsic kink, clipping, expiry handling
or safe fallback is added here. There are no hullkit imports.
"""

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter

import numpy as np
import torch
from torch import nn


def _strike(strike):
    if not np.isfinite(strike) or strike <= 0:
        raise ValueError("strike must be finite and positive")
    return float(strike)


def _inputs(inputs):
    x = np.asarray(inputs, dtype=float)
    if x.ndim != 2 or x.shape[1] != 3 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("finite nonempty [spot,seconds,event] rows required")
    if np.any(x[:, :2] <= 0) or np.any((x[:, 2] != 0) & (x[:, 2] != 1)):
        raise ValueError("positive spot/seconds and event flags 0 or 1 required")
    return x


def normalization(inputs, prices, deltas, *, strike=100):
    """Fit log-feature and C/K scales using only supplied training rows."""
    strike = _strike(strike)
    x = _inputs(inputs)
    p, d = np.asarray(prices, dtype=float), np.asarray(deltas, dtype=float)
    if (
        p.shape != (len(x),)
        or d.shape != p.shape
        or not np.isfinite(p).all()
        or not np.isfinite(d).all()
    ):
        raise ValueError("finite price and delta labels must match training rows")
    features = np.column_stack([np.log(x[:, 0] / strike), np.log(x[:, 1]), x[:, 2]])
    deviation = features.std(axis=0)
    return {
        "mean": features.mean(axis=0),
        "std": np.where(deviation > 1e-12, deviation, 1.0),
        "price_mean": float(np.mean(p / strike)),
        "price_scale": max(float(np.std(p / strike)), 1e-12),
        "delta_scale": max(float(np.sqrt(np.mean(d * d))), 1e-12),
        "strike": strike,
    }


class _CallNet(nn.Module):
    def __init__(self, scale, strike):
        super().__init__()
        self.strike = strike
        for name in ["mean", "std", "price_mean", "price_scale"]:
            self.register_buffer(
                name, torch.as_tensor(scale[name], dtype=torch.float64, device="cpu").clone()
            )
        self.first = nn.Linear(3, 32, dtype=torch.float64, device="cpu")
        self.second = nn.Linear(32, 32, dtype=torch.float64, device="cpu")
        self.last = nn.Linear(32, 1, dtype=torch.float64, device="cpu")

    def forward(self, inputs):
        features = torch.stack(
            [torch.log(inputs[:, 0] / self.strike), torch.log(inputs[:, 1]), inputs[:, 2]],
            dim=1,
        )
        z = (features - self.mean) / self.std
        value = self.last(torch.tanh(self.second(torch.tanh(self.first(z))))).squeeze(-1)
        return self.strike * (self.price_mean + self.price_scale * value)


@dataclass
class Fit:
    """CPU model, train-only normalization and observed fit/budget outcomes."""

    model: nn.Module
    normalization: dict
    stats: dict


def train(
    inputs,
    prices,
    deltas,
    *,
    seed,
    batch_seed,
    dml,
    max_updates=512,
    batch_size=128,
    learning_rate=0.003,
    budget_s=120,
    teacher_s=0,
    strike=100,
):
    """Train the paired update-capped experiment, retaining incomplete fits.

    The wall cap includes this function's setup/evaluation and teacher_s.
    It is checked before updates, so an update or final evaluation can overrun.
    batch_indices contains attempted batches; updates counts completed optimizer
    steps. No gamma labels or validation/test arguments enter optimization.
    """
    start = perf_counter()
    strike = _strike(strike)
    x = _inputs(inputs)
    scale = normalization(x, prices, deltas, strike=strike)
    if (
        max_updates < 1
        or int(max_updates) != max_updates
        or batch_size < 1
        or int(batch_size) != batch_size
    ):
        raise ValueError("positive integer update and batch caps required")
    if (
        not np.isfinite([learning_rate, budget_s, teacher_s]).all()
        or learning_rate <= 0
        or budget_s < 0
        or teacher_s < 0
    ):
        raise ValueError("positive learning rate and nonnegative finite time costs required")
    max_updates, batch_size = int(max_updates), int(batch_size)
    p = torch.as_tensor(np.asarray(prices, dtype=float), dtype=torch.float64, device="cpu")
    d = torch.as_tensor(np.asarray(deltas, dtype=float), dtype=torch.float64, device="cpu")
    full_x = torch.as_tensor(x, dtype=torch.float64, device="cpu")
    old_threads = torch.get_num_threads()
    updates, batches = 0, []
    initial_loss = final_loss = None
    status, reason = "time_cap", "time cap before first update"
    torch.set_num_threads(1)
    try:
        with torch.device("cpu"), torch.enable_grad(), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            model = _CallNet(scale, strike)
            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
            batch_rng = np.random.default_rng(batch_seed)

            def objective(rows=None):
                batch = full_x if rows is None else full_x[rows]
                batch = batch.detach().requires_grad_(bool(dml))
                target_price = p if rows is None else p[rows]
                target_delta = d if rows is None else d[rows]
                value = model(batch)
                loss = torch.mean(((value - target_price) / (strike * scale["price_scale"])) ** 2)
                if dml:
                    delta = torch.autograd.grad(value.sum(), batch, create_graph=True)[0][:, 0]
                    loss = loss + torch.mean(((delta - target_delta) / scale["delta_scale"]) ** 2)
                return loss

            if perf_counter() - start + teacher_s < budget_s:
                observed = float(objective().detach())
                if np.isfinite(observed):
                    initial_loss = observed
                    while updates < max_updates:
                        if perf_counter() - start + teacher_s >= budget_s:
                            status, reason = "time_cap", "time cap before next update"
                            break
                        rows = batch_rng.integers(0, len(x), size=batch_size, dtype=np.int32)
                        batches.append(rows)
                        optimizer.zero_grad(set_to_none=True)
                        loss = objective(rows)
                        if not torch.isfinite(loss):
                            status, reason = "nonfinite_loss", "nonfinite training objective"
                            break
                        loss.backward()
                        if any(
                            parameter.grad is not None and not torch.isfinite(parameter.grad).all()
                            for parameter in model.parameters()
                        ):
                            status, reason = "nonfinite_gradient", "nonfinite parameter gradient"
                            break
                        try:
                            optimizer.step()
                        except RuntimeError as exc:
                            status, reason = "optimizer_error", str(exc)
                            break
                        updates += 1
                        if any(
                            not torch.isfinite(parameter).all() for parameter in model.parameters()
                        ):
                            status, reason = (
                                "nonfinite_parameters",
                                "nonfinite weights after optimizer step",
                            )
                            break
                    else:
                        status, reason = "completed", None
                    observed = float(objective().detach())
                    if np.isfinite(observed):
                        final_loss = observed
                    elif status == "completed":
                        status, reason = "nonfinite_loss", "nonfinite final training objective"
                else:
                    status, reason = "nonfinite_loss", "nonfinite initial training objective"
    finally:
        torch.set_num_threads(old_threads)
    elapsed = perf_counter() - start
    return Fit(
        model,
        scale,
        {
            "status": status,
            "complete": status == "completed",
            "reason": reason,
            "updates": updates,
            "requested_updates": max_updates,
            "batch_indices": np.stack(batches)
            if batches
            else np.empty((0, batch_size), dtype=np.int32),
            "batch_attempts": len(batches),
            "batch_size": batch_size,
            "initial_loss": initial_loss,
            "final_loss": final_loss,
            "learning_rate": float(learning_rate),
            "teacher_s": float(teacher_s),
            "training_s": elapsed,
            "teacher_and_training_s": elapsed + teacher_s,
            "budget_s": float(budget_s),
            "overrun_s": max(0.0, elapsed + teacher_s - budget_s),
            "cost_scope": "function validation/setup/fit/evaluation/thread restore plus teacher_s; excludes module import",
            "seed": int(seed),
            "batch_seed": int(batch_seed),
            "dml": bool(dml),
            "gamma_loss": False,
            "threads": 1,
            "strike": strike,
        },
    )


def predict(fit, inputs):
    """Return [C, physical Delta, physical Gamma] from the same scalar model."""
    x = torch.as_tensor(_inputs(inputs), dtype=torch.float64, device="cpu").requires_grad_(True)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with torch.device("cpu"), torch.enable_grad():
            value = fit.model(x)
            delta = torch.autograd.grad(value.sum(), x, create_graph=True)[0][:, 0]
            gamma = torch.autograd.grad(delta.sum(), x)[0][:, 0]
            return torch.stack([value, delta, gamma], dim=1).detach().numpy()
    finally:
        torch.set_num_threads(old_threads)


def export_fit(fit):
    """Copy plain NumPy weights/scales/stats; no tensors or optimizer state."""
    return {
        "weights": {
            name: value.detach().cpu().numpy().copy()
            for name, value in fit.model.named_parameters()
        },
        "normalization": deepcopy(fit.normalization),
        "stats": deepcopy(fit.stats),
    }


def numpy_predict(weights, normalization, inputs, *, strike=100):
    """RNG/optimizer-free tanh replay, including feature scales and spot chain."""
    strike = _strike(strike)
    x = _inputs(inputs)
    if not np.isclose(strike, normalization["strike"], atol=0, rtol=1e-12):
        raise ValueError("strike must match saved training normalization")
    mean, std = np.asarray(normalization["mean"]), np.asarray(normalization["std"])
    if (
        mean.shape != (3,)
        or std.shape != (3,)
        or not np.isfinite(mean).all()
        or not np.isfinite(std).all()
        or np.any(std <= 0)
    ):
        raise ValueError("saved log-feature normalization must be finite and positive")
    expected_shapes = {
        "first.weight": (32, 3),
        "first.bias": (32,),
        "second.weight": (32, 32),
        "second.bias": (32,),
        "last.weight": (1, 32),
        "last.bias": (1,),
    }
    arrays = {name: np.asarray(weights[name], dtype=float) for name in expected_shapes}
    if any(
        arrays[name].shape != shape or not np.isfinite(arrays[name]).all()
        for name, shape in expected_shapes.items()
    ):
        raise ValueError("saved weights must be finite 3/32/32/1 arrays")
    features = np.column_stack([np.log(x[:, 0] / strike), np.log(x[:, 1]), x[:, 2]])
    z = (features - mean) / std
    first = np.tanh(z @ arrays["first.weight"].T + arrays["first.bias"])
    first_slope = arrays["first.weight"][:, 0] / std[0]
    first_x = (1 - first * first) * first_slope
    first_xx = -2 * first * (1 - first * first) * first_slope**2
    second = np.tanh(first @ arrays["second.weight"].T + arrays["second.bias"])
    inner_x = first_x @ arrays["second.weight"].T
    inner_xx = first_xx @ arrays["second.weight"].T
    second_x = (1 - second * second) * inner_x
    second_xx = (1 - second * second) * (inner_xx - 2 * second * inner_x**2)
    raw = (second @ arrays["last.weight"].T + arrays["last.bias"])[:, 0]
    multiplier = strike * normalization["price_scale"]
    value = strike * normalization["price_mean"] + multiplier * raw
    value_x = multiplier * (second_x @ arrays["last.weight"].T)[:, 0]
    value_xx = multiplier * (second_xx @ arrays["last.weight"].T)[:, 0]
    return np.column_stack([value, value_x / x[:, 0], (value_xx - value_x) / x[:, 0] / x[:, 0]])
