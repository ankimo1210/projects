"""Reproducible CPU/CUDA latency and calibration helpers."""

from __future__ import annotations

import importlib
import platform
import statistics
import time
from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar

from .pricing_data import black_scholes_labels

TEACHER_IMPORT_ERROR = (
    "hullkit is required for Heston/COS and Monte-Carlo teacher benchmarks; "
    "install the optional workspace package or run `uv sync --package hullkit` "
    "from the workspace root"
)


def benchmark_callable(
    function: Callable[[np.ndarray], object],
    inputs: np.ndarray,
    *,
    warmup=3,
    repeats=10,
    synchronize: Callable[[], None] | None = None,
    device: str = "cpu",
):
    """Return median and dispersion with explicit warm-up conditions."""
    if warmup < 0 or repeats <= 0:
        raise ValueError("warmup must be non-negative and repeats positive")
    if not device:
        raise ValueError("device must be non-empty")
    for _ in range(warmup):
        function(inputs)
        if synchronize:
            synchronize()
    timings = []
    for _ in range(repeats):
        if synchronize:
            synchronize()
        start = time.perf_counter_ns()
        function(inputs)
        if synchronize:
            synchronize()
        timings.append((time.perf_counter_ns() - start) / 1e6)
    median = statistics.median(timings)
    return {
        "batch_size": len(inputs),
        "warmup": warmup,
        "repeats": repeats,
        "device": device,
        "median_ms": median,
        "stdev_ms": statistics.pstdev(timings),
        "throughput_per_second": float(len(inputs) / (median / 1000.0)) if median else float("inf"),
        "hardware": {"platform": platform.platform(), "processor": platform.processor()},
    }


def _load_hullkit_teachers():
    """Load research teachers lazily so hullkit stays an optional integration."""
    try:
        module = importlib.import_module("hullkit.surrogate_data")
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(TEACHER_IMPORT_ERROR) from exc
    try:
        return module.heston_cos_price, module.mc_bsm_rows
    except AttributeError as exc:
        raise RuntimeError(
            "installed hullkit does not expose the required surrogate teacher API "
            "(heston_cos_price and mc_bsm_rows)"
        ) from exc


def _heston_cos_rows(inputs, heston_cos_price, *, n_terms):
    """Map common BS rows to a stable stochastic-volatility COS workload."""
    prices = []
    for x, tau, rate, dividend, sigma in np.asarray(inputs, dtype=np.float64):
        # Scaling spot by exp(-qT) preserves the terminal distribution when the
        # teacher API has a risk-free rate but no explicit dividend argument.
        dividend_adjusted_spot = x * np.exp(-dividend * tau)
        prices.append(
            heston_cos_price(
                dividend_adjusted_spot,
                1.0,
                rate,
                tau,
                v0=sigma**2,
                kappa=1.5,
                theta=sigma**2,
                xi=max(1e-3, 0.5 * sigma),
                rho=-0.6,
                N=n_terms,
            )
        )
    return np.asarray(prices, dtype=np.float64)


def benchmark_pricing_suite(
    inputs: np.ndarray,
    *,
    polynomial_function: Callable[[np.ndarray], object],
    neural_function: Callable[[np.ndarray], object],
    batch_sizes=(1, 32, 256),
    warmup=1,
    repeats=5,
    device="cpu",
    mc_seed=12_100,
    mc_paths=512,
    heston_cos_terms=128,
):
    """Benchmark analytic, numerical-teacher, polynomial, and MLP callables.

    All five methods receive exactly the same input slice and
    :func:`benchmark_callable` conditions at a given batch size.  The small,
    seeded MC workload is a latency comparison rather than a precision claim.
    """
    values = np.asarray(inputs, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 5 or not len(values):
        raise ValueError("inputs must have non-empty shape (n, 5)")
    sizes = tuple(dict.fromkeys(int(size) for size in batch_sizes))
    if not sizes or any(size <= 0 or size > len(values) for size in sizes):
        raise ValueError("batch_sizes must be positive and no larger than inputs")
    if mc_seed < 0 or mc_paths < 4 or heston_cos_terms <= 1:
        raise ValueError("invalid teacher benchmark configuration")

    heston_cos_price, mc_bsm_rows = _load_hullkit_teachers()

    def analytic_function(rows):
        return black_scholes_labels(rows)["price"]

    def heston_function(rows):
        return _heston_cos_rows(rows, heston_cos_price, n_terms=heston_cos_terms)

    def monte_carlo_function(rows):
        return mc_bsm_rows(
            rows,
            n_paths=mc_paths,
            seed=mc_seed,
            chunk_size=mc_paths,
        )["price"]

    callables: dict[str, Callable[[np.ndarray], object]] = {
        "analytic": analytic_function,
        "heston_cos": heston_function,
        "monte_carlo": monte_carlo_function,
        "polynomial": polynomial_function,
        "neural": neural_function,
    }
    rows_by_method: dict[str, list[dict[str, Any]]] = {name: [] for name in callables}
    for size in sizes:
        sample = values[:size]
        for name, function in callables.items():
            timing = benchmark_callable(
                function,
                sample,
                warmup=warmup,
                repeats=repeats,
                device=device,
            )
            timing["method"] = name
            rows_by_method[name].append(timing)

    return {
        "conditions": {
            "batch_sizes": list(sizes),
            "warmup": warmup,
            "repeats": repeats,
            "device": device,
            "common_input_slices": True,
        },
        **rows_by_method,
        "teacher_metadata": {
            "heston_cos": {
                "terms": heston_cos_terms,
                "kappa": 1.5,
                "xi": "0.5 * input_sigma (floored at 1e-3)",
                "rho": -0.6,
                "v0_and_theta": "input_sigma ** 2",
                "dividend_treatment": "spot * exp(-q * tau)",
            },
            "monte_carlo": {
                "method": "antithetic_control_variate",
                "seed": mc_seed,
                "paths_per_row": mc_paths,
                "purpose": "quick latency workload; not a precision claim",
            },
        },
    }


def calibration_recovery(
    price_function, rows: np.ndarray, true_prices: np.ndarray, *, bounds=(0.01, 1.5)
):
    """Recover volatility one quote at a time through the surrogate."""
    rows = np.asarray(rows, dtype=float)
    true_prices = np.asarray(true_prices, dtype=float)
    recovered = []
    repricing = []
    for row, target in zip(rows, true_prices, strict=True):

        def objective(sigma, source=row, target_price=target):
            candidate = source.copy()
            candidate[4] = sigma
            return float((price_function(candidate[None, :])[0] - target_price) ** 2)

        result = minimize_scalar(objective, bounds=bounds, method="bounded")
        recovered.append(float(result.x))
        repricing.append(float(np.sqrt(result.fun)))
    recovered_array = np.asarray(recovered)
    return {
        "n_quotes": len(rows),
        "volatility_mae": float(np.mean(np.abs(recovered_array - rows[:, 4]))),
        "repricing_mae": float(np.mean(repricing)),
        "recovered": recovered,
    }


def break_even_batch_size(analytic_rows, surrogate_rows):
    """Return the first measured batch where surrogate median latency is lower."""
    analytic = {row["batch_size"]: row["median_ms"] for row in analytic_rows}
    surrogate = {row["batch_size"]: row["median_ms"] for row in surrogate_rows}
    candidates = [
        size
        for size in sorted(analytic.keys() & surrogate.keys())
        if surrogate[size] < analytic[size]
    ]
    return candidates[0] if candidates else None
