"""Private RB-F08 supplied-normal Euler coupling and independent-level statistics.

The estimator uses ordinary multiplicative Euler, including negative states.
No function generates randomness or performs I/O. Sampling intervals target
the finest Euler expectation and do not remove its discretization bias.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import t

from ._numerical_mc import gbm_paths_from_normals


@dataclass(frozen=True)
class GBMCall:
    """European call inputs, with annualized rates/volatility and time in years."""

    spot: float
    strike: float
    rate: float
    sigma: float
    maturity: float
    yield_rate: float = 0.0

    def __post_init__(self):
        """Require finite coefficients, positive spot/strike/time and sigma >= 0."""
        values = (self.spot, self.strike, self.rate, self.sigma, self.maturity, self.yield_rate)
        if (
            not all(math.isfinite(value) for value in values)
            or min(self.spot, self.strike, self.maturity) <= 0
            or self.sigma < 0
        ):
            raise ValueError(
                "finite coefficients, positive spot/strike/time and sigma >= 0 required"
            )


def _integer(value, *, minimum, name):
    """Validate a count or grid index without accepting bool as an integer."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def coarse_normals(fine: np.ndarray) -> np.ndarray:
    """Sum adjacent fine normals divided by sqrt(2), preserving Brownian increments."""
    fine = np.asarray(fine, dtype=float)
    if (
        fine.ndim != 2
        or fine.shape[0] < 1
        or fine.shape[1] < 2
        or fine.shape[1] % 2
        or not np.all(np.isfinite(fine))
    ):
        raise ValueError("finite path-by-step normals with an even positive step count required")
    with np.errstate(over="raise", invalid="raise"):
        try:
            return fine.reshape(fine.shape[0], fine.shape[1] // 2, 2).sum(axis=2) / math.sqrt(2)
        except FloatingPointError as exc:
            raise ValueError("nonfinite coarse normal result") from exc


def gbm_level_samples(
    contract: GBMCall, normals: np.ndarray, *, level: int, base_steps: int = 4
) -> dict:
    """Replay an Euler fine/coarse pair and a separate paired exact-bias diagnostic.

    Rows are original paths; negative states never remove a row. Level zero
    samples the fine payoff alone. ``cost_counts`` covers the Euler estimator;
    ``diagnostic_cost_counts`` separately records the auxiliary exact terminal.
    Nonfinite paths or payoffs fail the whole invocation rather than filtering.
    """
    level = _integer(level, minimum=0, name="level")
    base_steps = _integer(base_steps, minimum=1, name="base_steps")
    steps = base_steps * 2**level
    z = np.asarray(normals, dtype=float)
    if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] != steps or not np.all(np.isfinite(z)):
        raise ValueError("at least two finite paths with base_steps * 2**level normals required")
    count = z.shape[0]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            discount = math.exp(-contract.rate * contract.maturity)
            fine = gbm_paths_from_normals(
                contract.spot,
                contract.rate,
                contract.sigma,
                contract.maturity,
                z,
                yield_rate=contract.yield_rate,
                scheme="euler",
            )
            fine_payoffs = discount * np.maximum(fine[:, -1] - contract.strike, 0)
            fine_negative = fine[:, 1:] < 0
            coarse_payoffs = None
            coarse_negative_states = 0
            negative_paths = np.any(fine_negative, axis=1)
            coarse_steps = 0
            if level > 0:
                coarse_steps = steps // 2
                coarse = gbm_paths_from_normals(
                    contract.spot,
                    contract.rate,
                    contract.sigma,
                    contract.maturity,
                    coarse_normals(z),
                    yield_rate=contract.yield_rate,
                    scheme="euler",
                )
                coarse_payoffs = discount * np.maximum(coarse[:, -1] - contract.strike, 0)
                coarse_negative = coarse[:, 1:] < 0
                coarse_negative_states = int(np.count_nonzero(coarse_negative))
                negative_paths |= np.any(coarse_negative, axis=1)
            exact = gbm_paths_from_normals(
                contract.spot,
                contract.rate,
                contract.sigma,
                contract.maturity,
                z.sum(axis=1, keepdims=True) / math.sqrt(steps),
                yield_rate=contract.yield_rate,
                scheme="exact",
            )
            exact_payoffs = discount * np.maximum(exact[:, -1] - contract.strike, 0)
            differences = fine_payoffs.copy() if level == 0 else fine_payoffs - coarse_payoffs
            bias = fine_payoffs - exact_payoffs
            arrays = (fine, fine_payoffs, differences, exact, exact_payoffs, bias)
            if level > 0:
                arrays += (coarse, coarse_payoffs)
            if not all(np.all(np.isfinite(array)) for array in arrays):
                raise ValueError("nonfinite path or payoff result")
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("nonfinite path or payoff result") from exc
    return {
        "fine_payoffs": fine_payoffs,
        "coarse_payoffs": coarse_payoffs,
        "differences": differences,
        "paired_exact_bias": bias,
        "fine_negative_states": int(np.count_nonzero(fine_negative)),
        "coarse_negative_states": coarse_negative_states,
        "negative_paths": int(np.count_nonzero(negative_paths)),
        "cost_counts": {
            "stock_updates": (steps + coarse_steps) * count,
            "normal_draws": steps * count,
            "payoff_evaluations": (1 + (level > 0)) * count,
            "coarse_aggregations": coarse_steps * count,
        },
        "diagnostic_cost_counts": {
            "stock_updates": count,
            "normal_draws": 0,
            "payoff_evaluations": count,
            "normal_sums": steps * count,
        },
    }


def block_moments(samples: np.ndarray) -> dict:
    """Return count, mean and centered sum of squares for a finite 1D block."""
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 1 or samples.size < 1 or not np.all(np.isfinite(samples)):
        raise ValueError("a nonempty finite one-dimensional sample block required")
    with np.errstate(over="raise", invalid="raise"):
        try:
            shifted = samples - samples[0]
            shifted_mean = float(shifted.mean())
            mean = float(samples[0]) + shifted_mean
            deviations = shifted - shifted_mean
            m2 = float(np.dot(deviations, deviations))
            if not all(math.isfinite(value) for value in (mean, m2)):
                raise ValueError("nonfinite moment result")
        except FloatingPointError as exc:
            raise ValueError("nonfinite moment result") from exc
    return {"count": int(samples.size), "mean": mean, "m2": m2}


def _moments(block, *, minimum=1):
    """Validate a centered-moment record used by merge and level summaries."""
    count = _integer(block["count"], minimum=minimum, name="moment count")
    mean, m2 = float(block["mean"]), float(block["m2"])
    if not all(math.isfinite(value) for value in (mean, m2)) or m2 < 0 or (count == 1 and m2 != 0):
        raise ValueError("finite mean and nonnegative finite m2 required")
    return count, mean, m2


def merge_moments(blocks: list[dict]) -> dict:
    """Merge centered moments without subtracting two large raw second moments.

    Blocks are disjoint parts of one sample. A singleton block is permitted;
    the final count must be >= 2 only when a sample variance is requested.
    The input records are not modified.
    """
    if not blocks:
        raise ValueError("at least one centered-moment block required")
    count, mean, m2 = _moments(blocks[0])
    try:
        for block in blocks[1:]:
            other_count, other_mean, other_m2 = _moments(block)
            total = count + other_count
            delta = other_mean - mean
            m2 = math.fsum((m2, other_m2, delta**2 * (count / total) * other_count))
            mean += delta * (other_count / total)
            count = total
            if not all(math.isfinite(value) for value in (mean, m2)):
                raise ValueError("nonfinite merged moment result")
    except OverflowError as exc:
        raise ValueError("nonfinite merged moment result") from exc
    return {"count": count, "mean": mean, "m2": m2}


def mlmc_summary(levels: list[dict], *, confidence: float = 0.95) -> dict:
    """Sum independent-level means with Satterthwaite approximate Student interval.

    Each count is the number of independent fine/coarse pairs, not twice that
    count. The interval covers the Euler expectation; bias is a separate input
    to the research layer. All-zero variance yields a degenerate point interval.
    """
    if not levels or not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("nonempty levels and confidence strictly between zero and one required")
    records = [_moments(block, minimum=2) for block in levels]
    components = [m2 / (count - 1) / count for count, _, m2 in records]
    try:
        price = math.fsum(mean for _, mean, _ in records)
        variance = math.fsum(components)
    except OverflowError as exc:
        raise ValueError("nonfinite MLMC summary result") from exc
    standard_error = math.sqrt(variance)
    degenerate = variance == 0
    df = None
    half_width = 0.0
    if not degenerate:
        df = 1 / math.fsum(
            (component / variance) ** 2 / (count - 1)
            for component, (count, _, _) in zip(components, records, strict=True)
        )
        half_width = float(t.ppf((1 + confidence) / 2, df)) * standard_error
    interval = (price - half_width, price + half_width)
    if not all(math.isfinite(value) for value in (price, variance, *interval)):
        raise ValueError("nonfinite MLMC summary result")
    return {
        "price": price,
        "variance": variance,
        "standard_error": standard_error,
        "confidence_level": confidence,
        "interval": interval,
        "df": df,
        "degenerate": degenerate,
        "level_counts": [count for count, _, _ in records],
    }


def allocate_paths(
    variances: np.ndarray,
    costs: np.ndarray,
    *,
    sampling_variance: float,
    minimum: int = 32,
    variance_floor: float = 1e-12,
) -> np.ndarray:
    """Ceil the fixed-pilot optimal independent-level allocation to integer counts.

    ``costs`` are strictly positive costs per fine/coarse pair. The floor is
    applied to all pilot variances; callers record its affected levels using
    the supplied variances and floor. Zero-variance levels retain ``minimum``
    paths even with a zero floor. The function does not run or adapt sampling.
    """
    variances = np.asarray(variances, dtype=float)
    costs = np.asarray(costs, dtype=float)
    minimum = _integer(minimum, minimum=1, name="minimum")
    if (
        variances.ndim != 1
        or variances.size < 1
        or costs.shape != variances.shape
        or not np.all(np.isfinite(variances))
        or not np.all(np.isfinite(costs))
        or np.any(variances < 0)
        or np.any(costs <= 0)
        or not math.isfinite(sampling_variance)
        or sampling_variance <= 0
        or not math.isfinite(variance_floor)
        or variance_floor < 0
        or minimum > np.iinfo(np.int64).max
    ):
        raise ValueError(
            "finite nonnegative variances, positive matching costs and budget required"
        )
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            effective = np.maximum(variances, variance_floor)
            root_variance, root_cost = np.sqrt(effective), np.sqrt(costs)
            required = (root_variance / root_cost) * np.sum(root_variance * root_cost)
            required = np.maximum(minimum, np.ceil(required / sampling_variance))
            if not np.all(np.isfinite(required)) or np.any(required >= 2**63):
                raise ValueError("allocation counts exceed finite int64 range")
            return required.astype(np.int64)
        except FloatingPointError as exc:
            raise ValueError("allocation counts exceed finite int64 range") from exc
