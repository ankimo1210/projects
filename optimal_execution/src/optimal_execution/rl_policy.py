"""Actor-critic policy network and evaluation wrapper.

A small shared-body MLP with a categorical policy head over the bounded
15-action grid (market multiplier x limit directive — see environment.py)
and a value head. Everything runs on CPU; CUDA is used only if available
and never required.

The *residual* variant is not a different network: it is the same policy
acting in an environment whose ``baseline`` is the Almgren–Chriss schedule,
so action m=1.0 reproduces the classical baseline exactly and the network
learns bounded deviations around it. The safety layer stays authoritative
in both variants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .environment import N_ACTIONS, OBS_DIM, ExecutionEnv


def default_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _ortho_init(layer: nn.Linear, gain: float) -> nn.Linear:
    nn.init.orthogonal_(layer.weight, gain)
    nn.init.constant_(layer.bias, 0.0)
    return layer


class ActorCritic(nn.Module):
    def __init__(self, hidden: int = 64, obs_dim: int = OBS_DIM, n_actions: int = N_ACTIONS):
        super().__init__()
        self.body = nn.Sequential(
            _ortho_init(nn.Linear(obs_dim, hidden), np.sqrt(2)),
            nn.Tanh(),
            _ortho_init(nn.Linear(hidden, hidden), np.sqrt(2)),
            nn.Tanh(),
        )
        self.pi = _ortho_init(nn.Linear(hidden, n_actions), 0.01)
        self.v = _ortho_init(nn.Linear(hidden, 1), 1.0)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        z = self.body(obs)
        return self.pi(z), self.v(z).squeeze(-1)

    def distribution(self, obs: torch.Tensor) -> torch.distributions.Categorical:
        logits, _ = self.forward(obs)
        return torch.distributions.Categorical(logits=logits)

    @torch.no_grad()
    def act(self, obs: np.ndarray, deterministic: bool = False) -> tuple[int, float, float]:
        t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)
        logits, value = self.forward(t)
        dist = torch.distributions.Categorical(logits=logits)
        action = torch.argmax(logits, dim=-1) if deterministic else dist.sample()
        return int(action.item()), float(dist.log_prob(action).item()), float(value.item())


def save_checkpoint(model: ActorCritic, path: Path, meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "meta": meta}, path)


def load_checkpoint(path: Path) -> tuple[ActorCritic, dict[str, Any]]:
    blob = torch.load(path, map_location="cpu", weights_only=False)
    meta = blob["meta"]
    model = ActorCritic(hidden=int(meta.get("hidden", 64)))
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, meta


class RLPolicy:
    """Strategy-protocol wrapper: deterministic (or sampled) policy actions."""

    def __init__(self, model: ActorCritic, deterministic: bool = True):
        self.model = model
        self.deterministic = deterministic

    @staticmethod
    def from_checkpoint(path: str | Path, deterministic: bool = True) -> RLPolicy:
        model, _ = load_checkpoint(Path(path))
        return RLPolicy(model, deterministic)

    def reset(self) -> None:  # stateless
        return

    def __call__(self, obs: np.ndarray, env: ExecutionEnv) -> int:
        action, _, _ = self.model.act(obs, deterministic=self.deterministic)
        return action
