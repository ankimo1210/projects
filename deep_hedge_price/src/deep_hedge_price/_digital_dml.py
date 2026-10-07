"""Private CPU digital price-only/LRM-DML learner; no hullkit imports.

Consumes plain training arrays at the JSON/NPZ boundary. Only training labels
determine normalization. No validation/test labels enter optimization or select
weights. The learner is experimental, not a public pricing API.
"""

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import torch
from torch import nn


def _inputs(inputs):
    x = np.asarray(inputs, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2 or len(x) == 0 or not np.all(np.isfinite(x)):
        raise ValueError("finite nonempty [spot,maturity] rows required")
    if np.any(x <= 0):
        raise ValueError("positive spot and maturity required")
    return x


def normalization(inputs, prices, deltas):
    """Fit feature/price/delta scales solely to supplied training arrays."""
    x = _inputs(inputs)
    p, d = np.asarray(prices, dtype=float), np.asarray(deltas, dtype=float)
    if p.shape != (len(x),) or d.shape != p.shape:
        raise ValueError("label dimensions must match scenarios")
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(d)):
        raise ValueError("finite labels required")
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    std = features.std(axis=0)
    return {
        "mean": features.mean(axis=0),
        "std": np.where(std > 1e-12, std, 1),
        "price_scale": max(float(p.std()), 1e-12),
        "delta_scale": max(float(np.sqrt(np.mean(d * d))), 1e-12),
    }


class _DigitalNet(nn.Module):
    def __init__(self, scale, rate):
        super().__init__()
        self.register_buffer("mean", torch.as_tensor(scale["mean"], dtype=torch.float64))
        self.register_buffer("std", torch.as_tensor(scale["std"], dtype=torch.float64))
        self.rate = rate
        self.first = nn.Linear(2, 32, dtype=torch.float64)
        self.second = nn.Linear(32, 32, dtype=torch.float64)
        self.last = nn.Linear(32, 1, dtype=torch.float64)

    def forward(self, inputs):
        features = torch.stack([inputs[:, 0], torch.log(inputs[:, 1])], dim=1)
        z = (features - self.mean) / self.std
        value = self.last(torch.tanh(self.second(torch.tanh(self.first(z))))).squeeze(-1)
        return torch.exp(-self.rate * inputs[:, 1]) * torch.sigmoid(value)


@dataclass
class Fit:
    """A private fitted CPU model plus train-only scales and actual cost record."""

    model: nn.Module
    scale: dict
    stats: dict


def train(
    inputs,
    prices,
    deltas,
    *,
    seed,
    dml,
    budget_s=8.0,
    teacher_s=0.0,
    max_updates=None,
    rate=0.03,
):
    """Fit price-only or DML within a teacher-inclusive time cap on one CPU thread.

    Both variants use the same network, full training batch and Adam schedule.
    The cap is checked before each update; one final update/setup may overrun.
    A max_updates value is intended for deterministic small smoke tests only.
    """
    if not np.isfinite(budget_s) or not np.isfinite(teacher_s) or not 0 <= teacher_s < budget_s:
        raise ValueError("positive budget remaining after teacher generation required")
    if max_updates is not None and max_updates < 1:
        raise ValueError("positive update cap required")
    start = perf_counter()
    scale = normalization(inputs, prices, deltas)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            model = _DigitalNet(scale, rate)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
            x = torch.as_tensor(_inputs(inputs), dtype=torch.float64).requires_grad_(dml)
            p = torch.as_tensor(prices, dtype=torch.float64)
            d = torch.as_tensor(deltas, dtype=torch.float64)

            def objective():
                value = model(x)
                loss = torch.mean(((value - p) / scale["price_scale"]) ** 2)
                if dml:
                    gradient = torch.autograd.grad(value.sum(), x, create_graph=True)[0][:, 0]
                    loss = loss + torch.mean(((gradient - d) / scale["delta_scale"]) ** 2)
                return loss

            initial = float(objective().detach())
            updates = 0
            while perf_counter() - start + teacher_s < budget_s:
                if max_updates is not None and updates >= max_updates:
                    break
                optimizer.zero_grad(set_to_none=True)
                if x.grad is not None:
                    x.grad = None
                loss = objective()
                loss.backward()
                optimizer.step()
                updates += 1
            if updates == 0:
                raise RuntimeError("budget exhausted before any optimizer update")
            final = float(objective().detach())
    finally:
        torch.set_num_threads(old_threads)
    elapsed = perf_counter() - start
    return Fit(
        model,
        scale,
        {
            "updates": updates,
            "initial_loss": initial,
            "final_loss": final,
            "teacher_s": teacher_s,
            "training_s": elapsed,
            "teacher_and_training_s": teacher_s + elapsed,
            "budget_s": budget_s,
            "overrun_s": max(0.0, teacher_s + elapsed - budget_s),
            "seed": seed,
            "dml": bool(dml),
            "threads": 1,
        },
    )


def predict(fit, inputs):
    """Return model prices and autograd spot deltas in physical units."""
    x = torch.as_tensor(_inputs(inputs), dtype=torch.float64).requires_grad_(True)
    values = fit.model(x)
    delta = torch.autograd.grad(values.sum(), x)[0][:, 0]
    return values.detach().numpy(), delta.detach().numpy()
