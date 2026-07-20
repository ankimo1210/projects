from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import torch
from torch import nn


class ExponentialMovingAverage:
    """Port of the pinned torch_ema dependency used by TLOB@f1c0af4.

    The repository constructs torch_ema.ExponentialMovingAverage with its
    default use_num_updates=True, so the effective decay at update n is
    min(decay, (1 + n) / (10 + n)) and only approaches the configured decay
    after roughly 9,000 updates.
    """

    def __init__(
        self, model: nn.Module, decay: float = 0.999, *, use_num_updates: bool = True
    ) -> None:
        if not 0 < decay < 1:
            raise ValueError("EMA decay must be in (0,1)")
        self.decay = decay
        self.num_updates: int | None = 0 if use_num_updates else None
        self.parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
        self.shadow = [parameter.detach().clone() for parameter in self.parameters]

    @torch.no_grad()
    def update(self) -> None:
        decay = self.decay
        if self.num_updates is not None:
            self.num_updates += 1
            decay = min(decay, (1 + self.num_updates) / (10 + self.num_updates))
        for shadow, parameter in zip(self.shadow, self.parameters, strict=True):
            shadow.mul_(decay).add_(parameter.detach(), alpha=1.0 - decay)

    @contextmanager
    def average_parameters(self) -> Iterator[None]:
        stored = [parameter.detach().clone() for parameter in self.parameters]
        try:
            with torch.no_grad():
                for parameter, shadow in zip(self.parameters, self.shadow, strict=True):
                    parameter.copy_(shadow)
            yield
        finally:
            with torch.no_grad():
                for parameter, original in zip(self.parameters, stored, strict=True):
                    parameter.copy_(original)


@dataclass
class TLOBRepositoryLifecycle:
    model: nn.Module
    learning_rate: float
    ema_decay: float = 0.999
    ema_use_num_updates: bool = True

    def __post_init__(self) -> None:
        self.loss_function = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate, eps=1e-8)
        self.ema = ExponentialMovingAverage(
            self.model, decay=self.ema_decay, use_num_updates=self.ema_use_num_updates
        )
        self.minimum_validation_loss = float("inf")

    def train_one_step(self, features: torch.Tensor, targets: torch.Tensor) -> float:
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        logits = self.model(features)
        loss = self.loss_function(logits, targets)
        # In the pinned Lightning module ema.update() is called in training_step,
        # before automatic backward/optimizer stepping. Preserve that ordering.
        self.ema.update()
        loss.backward()
        self.optimizer.step()
        return float(loss.detach())

    @torch.no_grad()
    def validation_one_step(self, features: torch.Tensor, targets: torch.Tensor) -> float:
        self.model.eval()
        with self.ema.average_parameters():
            logits = self.model(features)
            loss = self.loss_function(logits, targets)
        return float(loss)

    def apply_validation_loss_rule(self, validation_loss: float) -> dict[str, float | bool]:
        previous = self.minimum_validation_loss
        improved = validation_loss < previous
        if improved:
            if validation_loss - previous > -0.002:
                self.optimizer.param_groups[0]["lr"] /= 2
            self.minimum_validation_loss = validation_loss
        else:
            self.optimizer.param_groups[0]["lr"] /= 2
        return {
            "improved": improved,
            "minimum_validation_loss": self.minimum_validation_loss,
            "learning_rate": self.optimizer.param_groups[0]["lr"],
        }
