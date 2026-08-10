"""Resampling and multiple-testing primitives for B3.

The bootstrap implemented here is explicitly i.i.d.; it must not be silently
applied to serially dependent returns.  Randomized permutation p-values use a
plus-one correction, so an approximate p-value is never reported as zero.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.random import Generator
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
Statistic = Callable[[FloatArray], float]
TwoSampleStatistic = Callable[[FloatArray, FloatArray], float]
ParametricSampler = Callable[[Generator, int], ArrayLike]


def _require_generator(rng: Generator) -> Generator:
    if not isinstance(rng, Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    return rng


def _samples(values: ArrayLike, *, name: str, minimum: int = 2) -> FloatArray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or result.size < minimum:
        raise ValueError(f"{name} must be a one-dimensional array with at least {minimum} entries")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def _positive_integer(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be strictly positive")
    return int(value)


def _confidence_level(value: float) -> float:
    level = float(value)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    return level


def _evaluate_statistic(
    statistic: Statistic,
    samples: FloatArray,
    *,
    name: str = "statistic",
) -> float:
    if not callable(statistic):
        raise TypeError(f"{name} must be callable")
    result = np.asarray(statistic(samples), dtype=float)
    if result.ndim != 0 or not np.isfinite(result):
        raise ValueError(f"{name} must return one finite scalar")
    return float(result)


@dataclass(frozen=True)
class BootstrapResult:
    """Scalar statistic and its i.i.d. bootstrap sampling distribution."""

    estimate: float
    bootstrap_bias: float
    bootstrap_standard_error: float
    confidence_interval: tuple[float, float]
    confidence_level: float
    replicates: FloatArray
    n_resamples: int
    method: Literal["nonparametric", "parametric"]
    sampling_assumption: str
    interval_method: Literal["percentile"] = "percentile"


def _bootstrap_result(
    estimate: float,
    replicates: FloatArray,
    *,
    confidence_level: float,
    method: Literal["nonparametric", "parametric"],
) -> BootstrapResult:
    lower_probability = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(
        replicates,
        [lower_probability, 1.0 - lower_probability],
    )
    return BootstrapResult(
        estimate=estimate,
        bootstrap_bias=float(replicates.mean() - estimate),
        bootstrap_standard_error=float(replicates.std(ddof=1)),
        confidence_interval=(float(lower), float(upper)),
        confidence_level=confidence_level,
        replicates=replicates,
        n_resamples=replicates.size,
        method=method,
        sampling_assumption=(
            "i.i.d. observations resampled with replacement"
            if method == "nonparametric"
            else "sampler reproduces the fitted data-generating mechanism"
        ),
    )


def bootstrap_statistic(
    samples: ArrayLike,
    statistic: Statistic,
    n_resamples: int,
    *,
    rng: Generator,
    confidence_level: float = 0.95,
) -> BootstrapResult:
    """Compute an i.i.d. nonparametric percentile bootstrap.

    Each resample draws individual observations with replacement.  The caller
    is responsible for exchangeability; use of this function on an ordered
    dependent series does not produce a valid time-series bootstrap.
    """

    values = _samples(samples, name="samples")
    generator = _require_generator(rng)
    count = _positive_integer(n_resamples, name="n_resamples")
    if count < 2:
        raise ValueError("n_resamples must be at least two to estimate uncertainty")
    level = _confidence_level(confidence_level)
    estimate = _evaluate_statistic(statistic, values)
    replicates = np.empty(count, dtype=float)
    for index in range(count):
        indices = generator.integers(0, values.size, size=values.size)
        replicates[index] = _evaluate_statistic(statistic, values[indices])
    return _bootstrap_result(
        estimate,
        replicates,
        confidence_level=level,
        method="nonparametric",
    )


def parametric_bootstrap_statistic(
    samples: ArrayLike,
    sampler: ParametricSampler,
    statistic: Statistic,
    n_resamples: int,
    *,
    rng: Generator,
    confidence_level: float = 0.95,
) -> BootstrapResult:
    """Bootstrap a scalar statistic from an explicit fitted-model sampler.

    ``sampler(rng, n_samples)`` must draw one finite sample from the fitted
    model.  Passing the generator through the API prevents hidden global RNG
    state and makes the fitted sampling mechanism visible at the call site.
    """

    values = _samples(samples, name="samples")
    if not callable(sampler):
        raise TypeError("sampler must be callable")
    generator = _require_generator(rng)
    count = _positive_integer(n_resamples, name="n_resamples")
    if count < 2:
        raise ValueError("n_resamples must be at least two to estimate uncertainty")
    level = _confidence_level(confidence_level)
    estimate = _evaluate_statistic(statistic, values)
    replicates = np.empty(count, dtype=float)
    for index in range(count):
        simulated = _samples(
            sampler(generator, values.size),
            name="sampler output",
            minimum=values.size,
        )
        if simulated.size != values.size:
            raise ValueError("sampler must return exactly n_samples entries")
        replicates[index] = _evaluate_statistic(statistic, simulated)
    return _bootstrap_result(
        estimate,
        replicates,
        confidence_level=level,
        method="parametric",
    )


@dataclass(frozen=True)
class PermutationTestResult:
    """Randomized two-sample permutation test with plus-one correction."""

    observed_statistic: float
    p_value: float
    null_distribution: FloatArray
    alternative: Literal["two-sided", "less", "greater"]
    n_resamples: int
    correction: str = "plus-one"
    exchangeability_assumption: str = "observations are exchangeable under the null"


def permutation_test_two_sample(
    first: ArrayLike,
    second: ArrayLike,
    statistic: TwoSampleStatistic,
    n_resamples: int,
    *,
    rng: Generator,
    alternative: Literal["two-sided", "less", "greater"] = "two-sided",
) -> PermutationTestResult:
    """Randomly reassign two independent samples under exchangeability."""

    first_sample = _samples(first, name="first")
    second_sample = _samples(second, name="second")
    if not callable(statistic):
        raise TypeError("statistic must be callable")
    if alternative not in {"two-sided", "less", "greater"}:
        raise ValueError("alternative must be 'two-sided', 'less', or 'greater'")
    count = _positive_integer(n_resamples, name="n_resamples")
    generator = _require_generator(rng)

    def evaluate(left: FloatArray, right: FloatArray) -> float:
        result = np.asarray(statistic(left, right), dtype=float)
        if result.ndim != 0 or not np.isfinite(result):
            raise ValueError("statistic must return one finite scalar")
        return float(result)

    observed = evaluate(first_sample, second_sample)
    pooled = np.concatenate((first_sample, second_sample))
    null_distribution = np.empty(count, dtype=float)
    first_size = first_sample.size
    for index in range(count):
        permutation = generator.permutation(pooled.size)
        null_distribution[index] = evaluate(
            pooled[permutation[:first_size]],
            pooled[permutation[first_size:]],
        )
    tolerance = 100.0 * np.finfo(float).eps * max(1.0, abs(observed))
    greater_count = int(np.count_nonzero(null_distribution >= observed - tolerance))
    less_count = int(np.count_nonzero(null_distribution <= observed + tolerance))
    greater_p = (greater_count + 1.0) / (count + 1.0)
    less_p = (less_count + 1.0) / (count + 1.0)
    if alternative == "greater":
        p_value = greater_p
    elif alternative == "less":
        p_value = less_p
    else:
        p_value = min(1.0, 2.0 * min(greater_p, less_p))
    return PermutationTestResult(
        observed_statistic=observed,
        p_value=float(p_value),
        null_distribution=null_distribution,
        alternative=alternative,
        n_resamples=count,
    )


@dataclass(frozen=True)
class MultipleTestingResult:
    """Adjusted p-values and decisions in the original hypothesis order."""

    raw_p_values: FloatArray
    adjusted_p_values: FloatArray
    rejected: NDArray[np.bool_]
    alpha: float
    method: Literal["bonferroni", "benjamini-hochberg"]
    family_size: int
    number_rejected: int
    critical_raw_p_value: float
    dependence_assumption: str


def _p_values_and_alpha(p_values: ArrayLike, alpha: float) -> tuple[FloatArray, float]:
    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("p_values must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(values)) or np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("p_values must be finite and between zero and one")
    level = float(alpha)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("alpha must be strictly between zero and one")
    return values, level


def _multiple_testing_result(
    raw: FloatArray,
    adjusted: FloatArray,
    alpha: float,
    method: Literal["bonferroni", "benjamini-hochberg"],
) -> MultipleTestingResult:
    rejected = adjusted <= alpha
    critical = float(np.max(raw[rejected])) if np.any(rejected) else float("nan")
    return MultipleTestingResult(
        raw_p_values=raw.copy(),
        adjusted_p_values=adjusted,
        rejected=rejected,
        alpha=alpha,
        method=method,
        family_size=raw.size,
        number_rejected=int(np.count_nonzero(rejected)),
        critical_raw_p_value=critical,
        dependence_assumption=(
            "none beyond valid marginal p-values for Bonferroni FWER control"
            if method == "bonferroni"
            else "independent or positive-regression-dependent valid p-values"
        ),
    )


def bonferroni_adjust(p_values: ArrayLike, *, alpha: float = 0.05) -> MultipleTestingResult:
    """Control family-wise error with Bonferroni adjusted p-values."""

    values, level = _p_values_and_alpha(p_values, alpha)
    adjusted = np.minimum(1.0, values * values.size)
    return _multiple_testing_result(values, adjusted, level, "bonferroni")


def benjamini_hochberg(
    p_values: ArrayLike,
    *,
    alpha: float = 0.05,
) -> MultipleTestingResult:
    """Apply the Benjamini-Hochberg step-up FDR procedure."""

    values, level = _p_values_and_alpha(p_values, alpha)
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    ranks = np.arange(1, values.size + 1, dtype=float)
    ordered_adjusted = np.minimum.accumulate((ordered * values.size / ranks)[::-1])[::-1]
    ordered_adjusted = np.minimum(ordered_adjusted, 1.0)
    adjusted = np.empty_like(ordered_adjusted)
    adjusted[order] = ordered_adjusted
    return _multiple_testing_result(values, adjusted, level, "benjamini-hochberg")
