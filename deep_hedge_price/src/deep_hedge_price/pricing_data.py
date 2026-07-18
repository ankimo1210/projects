"""Leakage-audited, dimensionless Black--Scholes pricing datasets."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .black_scholes import (
    call_delta,
    call_gamma,
    call_price,
    call_rho,
    call_theta,
    call_vega,
)
from .pricing_artifacts import SPLITS, save_pricing_dataset
from .pricing_config import PricingConfig

FEATURE_NAMES = ("x", "tau", "r", "q", "sigma")
FORMULA_VERSION = "black_scholes_dimensionless_v1"


def latin_hypercube(n_rows: int, bounds: np.ndarray, *, seed: int) -> np.ndarray:
    """Generate a deterministic Latin hypercube without optional dependencies."""
    if n_rows <= 0:
        raise ValueError("n_rows must be positive")
    bounds = np.asarray(bounds, dtype=np.float64)
    if bounds.shape != (5, 2) or np.any(bounds[:, 0] >= bounds[:, 1]):
        raise ValueError("bounds must have shape (5, 2) with lower < upper")
    rng = np.random.default_rng(seed)
    unit = np.empty((n_rows, 5), dtype=np.float64)
    for column in range(5):
        unit[:, column] = (rng.permutation(n_rows) + rng.random(n_rows)) / n_rows
    return bounds[:, 0] + unit * (bounds[:, 1] - bounds[:, 0])


def _ood_shell(n_rows: int, bounds: np.ndarray, *, seed: int) -> np.ndarray:
    values = latin_hypercube(n_rows, bounds, seed=seed)
    rng = np.random.default_rng(seed + 1)
    widths = bounds[:, 1] - bounds[:, 0]
    for row in range(n_rows):
        column = row % bounds.shape[0]
        side = -1 if (row // bounds.shape[0]) % 2 == 0 else 1
        distance = (0.05 + 0.20 * rng.random()) * widths[column]
        values[row, column] = (
            bounds[column, 0] - distance if side < 0 else bounds[column, 1] + distance
        )
    # Preserve financially valid domains when pushing the lower shell.
    values[:, 0] = np.maximum(values[:, 0], 0.05)
    values[:, 1] = np.maximum(values[:, 1], 1e-6)
    values[:, 4] = np.maximum(values[:, 4], 1e-4)
    return values


def black_scholes_labels(inputs: np.ndarray) -> dict[str, np.ndarray]:
    """Evaluate normalized call price and analytic Greeks for ``K=1``."""
    inputs = np.asarray(inputs, dtype=np.float64)
    if inputs.ndim != 2 or inputs.shape[1] != 5:
        raise ValueError("inputs must have shape (n, 5)")
    x, tau, rate, dividend, sigma = inputs.T
    common = (x, 1.0, tau, rate, sigma, dividend)
    price = np.asarray(call_price(*common), dtype=np.float64)
    labels = {
        "inputs": inputs,
        "price": price,
        "delta": np.asarray(call_delta(*common), dtype=np.float64),
        "gamma": np.asarray(call_gamma(*common), dtype=np.float64),
        "vega": np.asarray(call_vega(*common), dtype=np.float64),
        "theta": np.asarray(call_theta(*common), dtype=np.float64),
        "rho": np.asarray(call_rho(*common), dtype=np.float64),
        "standard_error": np.zeros_like(price),
        "ci_lower": price.copy(),
        "ci_upper": price.copy(),
    }
    return labels


def generate_black_scholes_splits(config: PricingConfig) -> dict[str, dict[str, np.ndarray]]:
    """Generate independent train/validation/test and explicit OOD-shell splits."""
    config.validate()
    bounds = np.asarray([config.data.bounds[name] for name in FEATURE_NAMES], dtype=np.float64)
    sizes = {
        "train": config.data.train_size,
        "validation": config.data.validation_size,
        "test": config.data.test_size,
        "ood": config.data.ood_size,
    }
    result: dict[str, dict[str, np.ndarray]] = {}
    for offset, split in enumerate(SPLITS):
        seed = config.data.seed + 10_000 * offset
        rows = (
            _ood_shell(sizes[split], bounds, seed=seed)
            if split == "ood"
            else latin_hypercube(sizes[split], bounds, seed=seed)
        )
        result[split] = black_scholes_labels(rows)
    return result


def generate_black_scholes_dataset(
    config: PricingConfig,
    output_dir: str | Path,
    *,
    git_sha: str = "unknown",
) -> tuple[Path, Path]:
    """Generate and save a fully versioned analytic reference dataset."""
    splits = generate_black_scholes_splits(config)
    return save_pricing_dataset(
        splits,
        output_dir=Path(output_dir),
        model="black_scholes",
        teacher_method="analytic",
        parameterization="dimensionless_v1",
        seed=config.data.seed,
        generator_version=FORMULA_VERSION,
        git_sha=git_sha,
        metadata={
            "feature_names": list(FEATURE_NAMES),
            "bounds": {key: list(value) for key, value in config.data.bounds.items()},
            "sampling_design": config.data.sampling,
            "formula_version": FORMULA_VERSION,
            "config_fingerprint": config.fingerprint(),
        },
    )
