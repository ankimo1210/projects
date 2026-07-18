"""Auditable polynomial and neural pricing-surrogate policies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .pricing_config import PricingModelConfig

GREEK_NAMES = ("delta", "gamma", "vega", "theta", "rho")


def dimensionless_features_numpy(inputs: np.ndarray) -> np.ndarray:
    """Theory-guided coordinates used by both fit and inference."""
    values = np.asarray(inputs, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 5:
        raise ValueError("pricing inputs must have shape (n, 5)")
    x, tau, rate, dividend, sigma = values.T
    sqrt_tau = np.sqrt(np.maximum(tau, 1e-12))
    total_vol = np.maximum(sigma * sqrt_tau, 1e-12)
    discounted_spot = x * np.exp(-dividend * tau)
    discounted_strike = np.exp(-rate * tau)
    d_1 = (np.log(np.maximum(x, 1e-12)) + (rate - dividend) * tau) / total_vol
    d_1 = d_1 + 0.5 * total_vol
    return np.column_stack(
        (
            d_1,
            d_1 - total_vol,
            total_vol,
            discounted_spot,
            discounted_strike,
        )
    )


def _polynomial_features(inputs: np.ndarray, degree: int) -> np.ndarray:
    x = np.asarray(inputs, dtype=np.float64)
    features = [np.ones((len(x), 1)), x]
    if degree >= 2:
        features.append(x**2)
        features.append(
            np.column_stack([x[:, i] * x[:, j] for i in range(5) for j in range(i + 1, 5)])
        )
    if degree >= 3:
        features.append(x**3)
    return np.column_stack(features)


@dataclass
class PolynomialRidge:
    """Normalized closed-form ridge baseline with a serializable state."""

    degree: int = 3
    alpha: float = 1e-8
    mean: np.ndarray | None = None
    scale: np.ndarray | None = None
    coefficients: np.ndarray | None = None

    def fit(self, inputs: np.ndarray, targets: np.ndarray):
        inputs = np.asarray(inputs, dtype=np.float64)
        targets = np.asarray(targets, dtype=np.float64).reshape(-1)
        if inputs.shape != (len(targets), 5):
            raise ValueError("polynomial inputs must have shape (n, 5)")
        self.mean = inputs.mean(axis=0)
        self.scale = np.maximum(inputs.std(axis=0), 1e-12)
        design = _polynomial_features((inputs - self.mean) / self.scale, self.degree)
        penalty = self.alpha * np.eye(design.shape[1])
        penalty[0, 0] = 0.0
        self.coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        if self.mean is None or self.scale is None or self.coefficients is None:
            raise RuntimeError("polynomial baseline is not fitted")
        design = _polynomial_features((np.asarray(inputs) - self.mean) / self.scale, self.degree)
        return design @ self.coefficients

    def save(self, path: str | Path) -> Path:
        if self.coefficients is None:
            raise RuntimeError("polynomial baseline is not fitted")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            output,
            degree=np.array(self.degree),
            alpha=np.array(self.alpha),
            mean=self.mean,
            scale=self.scale,
            coefficients=self.coefficients,
        )
        return output

    @classmethod
    def load(cls, path: str | Path):
        with np.load(path, allow_pickle=False) as data:
            return cls(
                degree=int(data["degree"]),
                alpha=float(data["alpha"]),
                mean=data["mean"],
                scale=data["scale"],
                coefficients=data["coefficients"],
            )


class PricingMLP(nn.Module):
    """Small MLP whose deterministic feature normalization is checkpointed."""

    def __init__(self, config: PricingModelConfig):
        super().__init__()
        self.config = config
        self.register_buffer("feature_mean", torch.zeros(5, dtype=torch.float64))
        self.register_buffer("feature_scale", torch.ones(5, dtype=torch.float64))
        activation: type[nn.Module] = nn.SiLU if config.activation == "silu" else nn.Tanh
        layers: list[nn.Module] = []
        width = 5
        for _ in range(config.hidden_layers):
            linear = nn.Linear(width, config.hidden_units, dtype=torch.float64)
            nn.init.kaiming_uniform_(linear.weight, nonlinearity="linear")
            layers.extend((linear, activation()))
            width = config.hidden_units
        self.trunk = nn.Sequential(*layers)
        self.price_head = nn.Linear(width, 1, dtype=torch.float64)
        if config.direct_greek_heads:
            # Delta is primarily a smooth function of d1.  Give that route its
            # own small, normalized learner instead of forcing it through the
            # price trunk or leaking the analytical normal CDF into inference.
            self.delta_head = nn.Sequential(
                nn.Linear(1, 64, dtype=torch.float64),
                nn.Tanh(),
                nn.Linear(64, 64, dtype=torch.float64),
                nn.Tanh(),
                nn.Linear(64, 1, dtype=torch.float64),
            )
            self.greek_head = nn.Linear(width, len(GREEK_NAMES) - 1, dtype=torch.float64)
        else:
            self.delta_head = None
            self.greek_head = None

    def set_normalization(self, mean, scale):
        mean = torch.as_tensor(mean, dtype=self.feature_mean.dtype, device=self.feature_mean.device)
        scale = torch.as_tensor(
            scale, dtype=self.feature_scale.dtype, device=self.feature_scale.device
        )
        if mean.shape != (5,) or scale.shape != (5,) or torch.any(scale <= 0):
            raise ValueError("feature normalization must contain five positive scales")
        self.feature_mean.copy_(mean)
        self.feature_scale.copy_(scale)

    @staticmethod
    def feature_map(inputs: torch.Tensor):
        x, tau, rate, dividend, sigma = inputs.unbind(dim=-1)
        sqrt_tau = torch.sqrt(torch.clamp(tau, min=1e-12))
        total_vol = torch.clamp(sigma * sqrt_tau, min=1e-12)
        discounted_spot = x * torch.exp(-dividend * tau)
        discounted_strike = torch.exp(-rate * tau)
        d_1 = (
            torch.log(torch.clamp(x, min=1e-12)) + (rate - dividend) * tau
        ) / total_vol + 0.5 * total_vol
        return torch.stack(
            (
                d_1,
                d_1 - total_vol,
                total_vol,
                discounted_spot,
                discounted_strike,
            ),
            dim=-1,
        )

    def components(self, inputs: torch.Tensor):
        mapped = self.feature_map(inputs)
        features = self.trunk((mapped - self.feature_mean) / self.feature_scale)
        raw_price = self.price_head(features).squeeze(-1)
        if self.config.output_mode == "time_value":
            x, tau, rate, dividend, _sigma = inputs.unbind(dim=-1)
            lower = torch.clamp(x * torch.exp(-dividend * tau) - torch.exp(-rate * tau), min=0.0)
            price = lower + F.softplus(raw_price, beta=4.0)
        else:
            price = raw_price
        if self.greek_head is None:
            direct = None
        else:
            raw_greeks = self.greek_head(features)
            discount = torch.exp(-inputs[:, 3] * inputs[:, 1])
            normalized_d1 = (mapped[:, :1] - self.feature_mean[:1]) / self.feature_scale[:1]
            raw_delta = self.delta_head(normalized_d1).squeeze(-1)
            direct = torch.stack(
                (
                    discount * torch.sigmoid(raw_delta),
                    F.softplus(raw_greeks[:, 0]),
                    F.softplus(raw_greeks[:, 1]),
                    raw_greeks[:, 2],
                    F.softplus(raw_greeks[:, 3]),
                ),
                dim=-1,
            )
        return price, direct

    def forward(self, inputs: torch.Tensor):
        return self.components(inputs)[0]

    @property
    def parameter_count(self):
        return sum(parameter.numel() for parameter in self.parameters())
