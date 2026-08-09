"""Reproducible sampling experiments for convergence and coverage lessons."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np
from numpy.random import Generator
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
DistributionName = Literal["gaussian", "student_t", "pareto", "mixture"]


def _require_generator(rng: Generator) -> Generator:
    if not isinstance(rng, Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    return rng


def _positive_integer(value: int, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


@dataclass(frozen=True)
class DistributionSpec:
    """Parameters for one of the B2 sampling distributions.

    ``scale`` is a standard deviation for ``gaussian`` and each mixture
    component, and a multiplicative scale for ``student_t``.  ``minimum``
    is the Pareto lower endpoint.  The Gaussian mixture shares ``location``
    across components and multiplies the rare component's standard
    deviation by ``outlier_scale``.
    """

    name: DistributionName = "gaussian"
    location: float = 0.0
    scale: float = 1.0
    degrees_of_freedom: float = 3.0
    tail_index: float = 2.5
    minimum: float = 1.0
    mixture_probability: float = 0.02
    outlier_scale: float = 10.0

    def __post_init__(self) -> None:
        if self.name not in {"gaussian", "student_t", "pareto", "mixture"}:
            raise ValueError(f"unknown distribution: {self.name!r}")
        numeric = (
            self.location,
            self.scale,
            self.degrees_of_freedom,
            self.tail_index,
            self.minimum,
            self.mixture_probability,
            self.outlier_scale,
        )
        if not all(np.isfinite(value) for value in numeric):
            raise ValueError("distribution parameters must be finite")
        if self.scale <= 0.0:
            raise ValueError("scale must be strictly positive")
        if self.degrees_of_freedom <= 0.0:
            raise ValueError("degrees_of_freedom must be strictly positive")
        if self.tail_index <= 0.0:
            raise ValueError("tail_index must be strictly positive")
        if self.minimum <= 0.0:
            raise ValueError("minimum must be strictly positive")
        if not 0.0 <= self.mixture_probability <= 1.0:
            raise ValueError("mixture_probability must be between zero and one")
        if self.outlier_scale < 1.0:
            raise ValueError("outlier_scale must be at least one")

    @property
    def theoretical_mean(self) -> float:
        """Return the population mean, or ``nan`` when it does not exist."""

        if self.name in {"gaussian", "mixture"}:
            return float(self.location)
        if self.name == "student_t":
            return float(self.location) if self.degrees_of_freedom > 1.0 else float("nan")
        if self.tail_index <= 1.0:
            return float("nan")
        return float(self.minimum * self.tail_index / (self.tail_index - 1.0))

    @property
    def theoretical_variance(self) -> float:
        """Return population variance, or ``inf`` when the second moment fails."""

        if self.name == "gaussian":
            return float(self.scale**2)
        if self.name == "student_t":
            if self.degrees_of_freedom <= 2.0:
                return float("inf")
            return float(self.scale**2 * self.degrees_of_freedom / (self.degrees_of_freedom - 2.0))
        if self.name == "pareto":
            if self.tail_index <= 2.0:
                return float("inf")
            numerator = self.minimum**2 * self.tail_index
            denominator = (self.tail_index - 1.0) ** 2 * (self.tail_index - 2.0)
            return float(numerator / denominator)
        probability = self.mixture_probability
        return float(self.scale**2 * ((1.0 - probability) + probability * self.outlier_scale**2))


def _sample_shape(size: int | tuple[int, ...]) -> tuple[int, ...]:
    if isinstance(size, (int, np.integer)) and not isinstance(size, bool):
        return (_positive_integer(int(size), name="size"),)
    if not isinstance(size, tuple) or not size:
        raise TypeError("size must be a positive integer or a non-empty tuple of integers")
    return tuple(_positive_integer(item, name="size entry") for item in size)


def draw_distribution(
    specification: DistributionSpec,
    size: int | tuple[int, ...],
    *,
    rng: Generator,
) -> FloatArray:
    """Draw from a validated distribution without touching global RNG state."""

    if not isinstance(specification, DistributionSpec):
        raise TypeError("specification must be a DistributionSpec")
    shape = _sample_shape(size)
    generator = _require_generator(rng)
    if specification.name == "gaussian":
        values = generator.normal(specification.location, specification.scale, size=shape)
    elif specification.name == "student_t":
        values = specification.location + specification.scale * generator.standard_t(
            specification.degrees_of_freedom, size=shape
        )
    elif specification.name == "pareto":
        values = specification.minimum * (
            1.0 + generator.pareto(specification.tail_index, size=shape)
        )
    else:
        outlier = generator.random(shape) < specification.mixture_probability
        standard_deviation = np.where(
            outlier,
            specification.scale * specification.outlier_scale,
            specification.scale,
        )
        values = generator.normal(specification.location, standard_deviation)
    return np.asarray(values, dtype=float)


def running_sample_mean(samples: ArrayLike) -> FloatArray:
    """Return the sample mean after each finite one-dimensional draw."""

    values = np.asarray(samples, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("samples must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(values)):
        raise ValueError("samples must contain only finite values")
    return np.cumsum(values) / np.arange(1, values.size + 1)


@dataclass(frozen=True)
class SampleMeanExperiment:
    """Replicated sample means with rows corresponding to sample sizes."""

    sample_sizes: NDArray[np.int64]
    estimates: FloatArray
    theoretical_mean: float
    theoretical_variance: float
    distribution: DistributionSpec

    @property
    def median_absolute_error(self) -> FloatArray:
        if not np.isfinite(self.theoretical_mean):
            return np.full(self.sample_sizes.size, np.nan)
        return np.median(np.abs(self.estimates - self.theoretical_mean), axis=1)

    @property
    def root_mean_squared_error(self) -> FloatArray:
        if not np.isfinite(self.theoretical_mean):
            return np.full(self.sample_sizes.size, np.nan)
        return np.sqrt(np.mean((self.estimates - self.theoretical_mean) ** 2, axis=1))


def sample_mean_experiment(
    specification: DistributionSpec,
    sample_sizes: ArrayLike,
    n_replications: int,
    *,
    rng: Generator,
) -> SampleMeanExperiment:
    """Replicate sample means for several sizes with a single explicit stream."""

    raw_sizes = np.asarray(sample_sizes)
    if raw_sizes.ndim != 1 or raw_sizes.size == 0 or raw_sizes.dtype.kind not in {"i", "u"}:
        raise ValueError("sample_sizes must be a non-empty one-dimensional integer array")
    if np.any(raw_sizes < 1):
        raise ValueError("sample_sizes must be strictly positive")
    sizes = raw_sizes.astype(np.int64, copy=False)
    if np.unique(sizes).size != sizes.size:
        raise ValueError("sample_sizes must not contain duplicates")
    replications = _positive_integer(n_replications, name="n_replications")
    generator = _require_generator(rng)
    estimates = np.empty((sizes.size, replications), dtype=float)
    for index, sample_size in enumerate(sizes):
        draws = draw_distribution(
            specification,
            (replications, int(sample_size)),
            rng=generator,
        )
        estimates[index] = draws.mean(axis=1)
    return SampleMeanExperiment(
        sample_sizes=sizes.copy(),
        estimates=estimates,
        theoretical_mean=specification.theoretical_mean,
        theoretical_variance=specification.theoretical_variance,
        distribution=specification,
    )


@dataclass(frozen=True)
class CoverageDiagnostics:
    """Monte Carlo diagnostics for normal-approximation mean intervals."""

    coverage_probability: float
    monte_carlo_standard_error: float
    average_width: float
    confidence_level: float
    n_samples: int
    n_replications: int
    theoretical_mean: float
    interval_lower: FloatArray
    interval_upper: FloatArray


def normal_mean_coverage(
    specification: DistributionSpec,
    n_samples: int,
    n_replications: int,
    *,
    rng: Generator,
    confidence_level: float = 0.95,
    ddof: int = 1,
) -> CoverageDiagnostics:
    """Estimate coverage of a plug-in normal interval for a population mean."""

    sample_count = _positive_integer(n_samples, name="n_samples", minimum=2)
    replication_count = _positive_integer(n_replications, name="n_replications")
    if not np.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    if isinstance(ddof, bool) or not isinstance(ddof, (int, np.integer)):
        raise TypeError("ddof must be an integer")
    if not 0 <= ddof < sample_count:
        raise ValueError("ddof must be between zero and n_samples - 1")
    population_mean = specification.theoretical_mean
    if not np.isfinite(population_mean):
        raise ValueError("coverage is undefined because the population mean does not exist")

    draws = draw_distribution(
        specification,
        (replication_count, sample_count),
        rng=_require_generator(rng),
    )
    estimates = draws.mean(axis=1)
    standard_errors = draws.std(axis=1, ddof=int(ddof)) / np.sqrt(sample_count)
    critical_value = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)
    lower = estimates - critical_value * standard_errors
    upper = estimates + critical_value * standard_errors
    covered = (lower <= population_mean) & (population_mean <= upper)
    coverage = float(covered.mean())
    simulation_standard_error = float(np.sqrt(coverage * (1.0 - coverage) / replication_count))
    return CoverageDiagnostics(
        coverage_probability=coverage,
        monte_carlo_standard_error=simulation_standard_error,
        average_width=float(np.mean(upper - lower)),
        confidence_level=float(confidence_level),
        n_samples=sample_count,
        n_replications=replication_count,
        theoretical_mean=float(population_mean),
        interval_lower=np.asarray(lower, dtype=float),
        interval_upper=np.asarray(upper, dtype=float),
    )


def hoeffding_two_sided_bound(
    epsilon: float,
    n_samples: int,
    *,
    lower_bound: float,
    upper_bound: float,
) -> float:
    """Return Hoeffding's two-sided probability bound for a bounded mean."""

    count = _positive_integer(n_samples, name="n_samples")
    if not np.isfinite(epsilon) or epsilon <= 0.0:
        raise ValueError("epsilon must be finite and strictly positive")
    if not np.isfinite(lower_bound) or not np.isfinite(upper_bound):
        raise ValueError("bounds must be finite")
    if lower_bound >= upper_bound:
        raise ValueError("lower_bound must be smaller than upper_bound")
    probability = 2.0 * np.exp(-2.0 * count * epsilon**2 / (upper_bound - lower_bound) ** 2)
    return float(min(1.0, probability))
