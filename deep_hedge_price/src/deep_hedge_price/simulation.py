"""Exact discrete-time GBM simulation."""

from __future__ import annotations

import math

import torch

from .config import MarketConfig


def resolve_device(requested: str) -> torch.device:
    """Resolve auto/cpu/cuda while providing a clear CUDA error."""
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return torch.device(requested)


def make_generator(device: torch.device, seed: int) -> torch.Generator:
    """Create a device-local deterministic random generator."""
    generator = torch.Generator(device=device.type)
    generator.manual_seed(seed)
    return generator


def simulate_gbm(
    config: MarketConfig,
    n_paths: int,
    *,
    device: str | torch.device = "cpu",
    seed: int | None = None,
    generator: torch.Generator | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Simulate exact GBM paths with shape ``[n_paths, n_steps + 1]``."""
    if n_paths <= 0:
        raise ValueError("n_paths must be positive")
    target_device = torch.device(device)
    if generator is not None and seed is not None:
        raise ValueError("provide either generator or seed, not both")
    rng = generator or make_generator(target_device, config.seed if seed is None else seed)
    if config.antithetic_sampling:
        half = (n_paths + 1) // 2
        base = torch.randn((half, config.n_steps), device=target_device, dtype=dtype, generator=rng)
        shocks = torch.cat((base, -base), dim=0)[:n_paths]
    else:
        shocks = torch.randn(
            (n_paths, config.n_steps), device=target_device, dtype=dtype, generator=rng
        )
    drift = (config.mu - 0.5 * config.volatility**2) * config.dt
    diffusion = config.volatility * math.sqrt(config.dt) * shocks
    log_increments = drift + diffusion
    log_paths = torch.cat(
        (
            torch.zeros((n_paths, 1), device=target_device, dtype=dtype),
            torch.cumsum(log_increments, dim=1),
        ),
        dim=1,
    )
    return config.s0 * torch.exp(log_paths)


def time_grid(config: MarketConfig, *, device: str | torch.device = "cpu") -> torch.Tensor:
    """Return hedge times from zero through maturity."""
    return torch.linspace(0.0, config.maturity_years, config.n_steps + 1, device=device)
