"""Seeding helpers for reproducible experiments."""

from __future__ import annotations

import random

import numpy as np
import torch


def set_seed(seed: int, deterministic: bool = False) -> None:
    """Seed python / numpy / torch (CPU and all CUDA devices).

    deterministic=True additionally requests deterministic kernels. This can
    slow training and some ops only warn — good enough for教育用途; bitwise
    reproducibility across different GPUs is still not guaranteed.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.benchmark = False


def make_generator(seed: int, device: str | torch.device = "cpu") -> torch.Generator:
    """Dedicated RNG stream (batch sampling / sampling-based generation).

    Using explicit generators keeps data order independent from model-side
    randomness (dropout etc.), which the gradient-accumulation equivalence
    test relies on.
    """
    g = torch.Generator(device=device)
    g.manual_seed(seed)
    return g
