"""Conjugate Bayesian, MCMC diagnostic, and Gaussian-HMM primitives for B8."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import special, stats


def _vector(values: object, *, name: str, minimum: int = 1) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < minimum or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite one-dimensional array")
    return array


@dataclass(frozen=True)
class NormalMeanPosterior:
    mean: float
    variance: float
    prior_mean: float
    prior_variance: float
    observation_variance: float
    n_observations: int

    def predictive_interval(self, probability: float = 0.9) -> tuple[float, float]:
        if not 0.0 < probability < 1.0:
            raise ValueError("probability must lie strictly between zero and one")
        quantile = float(stats.norm.ppf(0.5 + probability / 2.0))
        scale = np.sqrt(self.observation_variance + self.variance)
        return self.mean - quantile * scale, self.mean + quantile * scale


def normal_mean_posterior(
    observations: object,
    *,
    observation_variance: float,
    prior_mean: float,
    prior_variance: float,
) -> NormalMeanPosterior:
    """Update a normal prior for a mean with known observation variance."""
    values = _vector(observations, name="observations")
    scalars = np.asarray([observation_variance, prior_mean, prior_variance], dtype=float)
    if not np.all(np.isfinite(scalars)) or observation_variance <= 0.0 or prior_variance <= 0.0:
        raise ValueError("variances must be positive and all scalar inputs finite")
    precision = 1.0 / prior_variance + values.size / observation_variance
    variance = 1.0 / precision
    mean = variance * (prior_mean / prior_variance + values.sum() / observation_variance)
    return NormalMeanPosterior(
        mean=float(mean),
        variance=float(variance),
        prior_mean=float(prior_mean),
        prior_variance=float(prior_variance),
        observation_variance=float(observation_variance),
        n_observations=values.size,
    )


@dataclass(frozen=True)
class BayesianLinearPosterior:
    mean: np.ndarray
    precision: np.ndarray
    shape: float
    scale: float
    n_observations: int


@dataclass(frozen=True)
class StudentTPredictive:
    mean: np.ndarray
    scale: np.ndarray
    degrees_of_freedom: float

    def interval(self, probability: float = 0.9) -> tuple[np.ndarray, np.ndarray]:
        if not 0.0 < probability < 1.0:
            raise ValueError("probability must lie strictly between zero and one")
        quantile = float(stats.t.ppf(0.5 + probability / 2.0, self.degrees_of_freedom))
        return self.mean - quantile * self.scale, self.mean + quantile * self.scale


def fit_bayesian_linear_regression(
    features: object,
    target: object,
    *,
    prior_precision: float = 1.0,
    prior_shape: float = 2.0,
    prior_scale: float = 1.0,
) -> BayesianLinearPosterior:
    """Fit a zero-centered Normal--Inverse-Gamma linear model."""
    x = np.asarray(features, dtype=float)
    y = _vector(target, name="target", minimum=2)
    if x.ndim != 2 or x.shape[0] != y.size or not np.all(np.isfinite(x)):
        raise ValueError("features must be a finite row-aligned matrix")
    if (
        not np.isfinite([prior_precision, prior_shape, prior_scale]).all()
        or min(prior_precision, prior_shape, prior_scale) <= 0.0
    ):
        raise ValueError("prior hyperparameters must be finite and strictly positive")
    precision = prior_precision * np.eye(x.shape[1]) + x.T @ x
    mean = np.linalg.solve(precision, x.T @ y)
    shape = prior_shape + 0.5 * y.size
    scale = prior_scale + 0.5 * (y @ y - mean @ precision @ mean)
    if scale <= 0.0:
        raise ValueError("posterior scale is not positive")
    return BayesianLinearPosterior(
        mean=mean,
        precision=precision,
        shape=float(shape),
        scale=float(scale),
        n_observations=y.size,
    )


def bayesian_linear_predictive(
    posterior: BayesianLinearPosterior, features: object
) -> StudentTPredictive:
    """Return the conjugate posterior predictive Student-t distribution."""
    if not isinstance(posterior, BayesianLinearPosterior):
        raise TypeError("posterior must be a BayesianLinearPosterior")
    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or x.shape[1] != posterior.mean.size or not np.all(np.isfinite(x)):
        raise ValueError("features has an incompatible shape or non-finite value")
    solved = np.linalg.solve(posterior.precision, x.T).T
    variance = posterior.scale / posterior.shape * (1.0 + np.sum(x * solved, axis=1))
    return StudentTPredictive(
        mean=x @ posterior.mean,
        scale=np.sqrt(variance),
        degrees_of_freedom=2.0 * posterior.shape,
    )


@dataclass(frozen=True)
class HierarchicalNormalPosterior:
    means: np.ndarray
    variances: np.ndarray
    shrinkage_weights: np.ndarray
    population_mean: float
    population_variance: float


def hierarchical_normal_posterior(
    estimates: object,
    standard_errors: object,
    *,
    population_mean: float,
    population_standard_deviation: float,
) -> HierarchicalNormalPosterior:
    """Compute known-hyperparameter normal-normal partial pooling."""
    values = _vector(estimates, name="estimates")
    errors = _vector(standard_errors, name="standard_errors")
    if values.size != errors.size or np.any(errors <= 0.0):
        raise ValueError("estimates and positive standard_errors must have equal length")
    if (
        not np.isfinite(population_mean)
        or not np.isfinite(population_standard_deviation)
        or population_standard_deviation <= 0.0
    ):
        raise ValueError(
            "population hyperparameters must be finite with positive standard deviation"
        )
    population_variance = population_standard_deviation**2
    sampling_variance = errors**2
    weight = population_variance / (population_variance + sampling_variance)
    means = weight * values + (1.0 - weight) * population_mean
    variances = 1.0 / (1.0 / population_variance + 1.0 / sampling_variance)
    return HierarchicalNormalPosterior(
        means=means,
        variances=variances,
        shrinkage_weights=weight,
        population_mean=float(population_mean),
        population_variance=float(population_variance),
    )


@dataclass(frozen=True)
class MCMCResult:
    samples: np.ndarray
    acceptance_rate: float
    effective_sample_size: np.ndarray


def effective_sample_size(samples: object) -> np.ndarray:
    """Estimate per-coordinate ESS using Geyer's initial positive sequence."""
    values = np.asarray(samples, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    if values.ndim != 2 or values.shape[0] < 8 or not np.all(np.isfinite(values)):
        raise ValueError(
            "samples must be a finite draws-by-parameter array with at least eight draws"
        )
    result = np.empty(values.shape[1])
    for column in range(values.shape[1]):
        centered = values[:, column] - values[:, column].mean()
        variance = float(centered @ centered / values.shape[0])
        if variance <= np.finfo(float).tiny:
            result[column] = float(values.shape[0])
            continue
        correlations = []
        for lag in range(1, values.shape[0] // 2):
            correlations.append(
                float(centered[lag:] @ centered[:-lag] / ((values.shape[0] - lag) * variance))
            )
        total = 0.0
        for index in range(0, len(correlations) - 1, 2):
            pair = correlations[index] + correlations[index + 1]
            if pair <= 0.0:
                break
            total += pair
        result[column] = min(float(values.shape[0]), values.shape[0] / max(1.0 + 2.0 * total, 1.0))
    return result


def metropolis_hastings(
    log_density: Callable[[np.ndarray], float],
    initial: object,
    n_samples: int,
    *,
    proposal_scale: object,
    rng: np.random.Generator,
    burn_in: int = 0,
) -> MCMCResult:
    """Run a Gaussian random-walk Metropolis sampler with explicit RNG."""
    if not callable(log_density):
        raise TypeError("log_density must be callable")
    current = _vector(initial, name="initial")
    scale = _vector(proposal_scale, name="proposal_scale")
    if scale.size != current.size or np.any(scale <= 0.0):
        raise ValueError("proposal_scale must be positive and match initial")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 8:
        raise ValueError("n_samples must be an integer of at least eight")
    if isinstance(burn_in, bool) or not isinstance(burn_in, int) or burn_in < 0:
        raise ValueError("burn_in must be a non-negative integer")
    current_log_density = float(log_density(current))
    if not np.isfinite(current_log_density):
        raise ValueError("initial state must have finite log density")
    draws = np.empty((n_samples, current.size))
    accepted = 0
    retained = 0
    for iteration in range(n_samples + burn_in):
        proposal = current + rng.normal(scale=scale, size=current.size)
        proposal_log_density = float(log_density(proposal))
        if (
            np.isfinite(proposal_log_density)
            and np.log(rng.random()) < proposal_log_density - current_log_density
        ):
            current = proposal
            current_log_density = proposal_log_density
            accepted += 1
        if iteration >= burn_in:
            draws[retained] = current
            retained += 1
    return MCMCResult(
        samples=draws,
        acceptance_rate=float(accepted / (n_samples + burn_in)),
        effective_sample_size=effective_sample_size(draws),
    )


def split_rhat(chains: object) -> np.ndarray:
    """Return classical split-Rhat; rank normalization is outside this helper."""
    values = np.asarray(chains, dtype=float)
    if values.ndim == 2:
        values = values[:, :, None]
    if (
        values.ndim != 3
        or values.shape[0] < 2
        or values.shape[1] < 16
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("chains must be finite chain-by-draw-by-parameter data")
    half = values.shape[1] // 2
    split = np.concatenate([values[:, :half], values[:, -half:]], axis=0)
    chain_means = split.mean(axis=1)
    within = split.var(axis=1, ddof=1).mean(axis=0)
    between = half * chain_means.var(axis=0, ddof=1)
    variance = (half - 1.0) / half * within + between / half
    return np.sqrt(variance / within)


@dataclass(frozen=True)
class GaussianHMM:
    initial_probabilities: np.ndarray
    transition_matrix: np.ndarray
    means: np.ndarray
    variances: np.ndarray
    log_likelihood_trace: np.ndarray
    converged: bool


def _hmm_data(observations: object, *, minimum: int = 10) -> np.ndarray:
    values = np.asarray(observations, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    if values.ndim != 2 or values.shape[0] < minimum or not np.all(np.isfinite(values)):
        raise ValueError("observations must be a finite time-by-feature array")
    return values


def _emission_log_density(model: GaussianHMM, observations: np.ndarray) -> np.ndarray:
    difference = observations[:, None, :] - model.means[None, :, :]
    return -0.5 * np.sum(
        np.log(2.0 * np.pi * model.variances)[None, :, :]
        + difference**2 / model.variances[None, :, :],
        axis=2,
    )


def _forward_backward(
    model: GaussianHMM, observations: np.ndarray
) -> tuple[float, np.ndarray, np.ndarray]:
    emission = _emission_log_density(model, observations)
    states = model.means.shape[0]
    alpha = np.empty_like(emission)
    alpha[0] = np.log(model.initial_probabilities) + emission[0]
    for time in range(1, observations.shape[0]):
        alpha[time] = emission[time] + special.logsumexp(
            alpha[time - 1][:, None] + np.log(model.transition_matrix), axis=0
        )
    log_likelihood = float(special.logsumexp(alpha[-1]))
    beta = np.zeros_like(alpha)
    for time in range(observations.shape[0] - 2, -1, -1):
        beta[time] = special.logsumexp(
            np.log(model.transition_matrix) + emission[time + 1][None, :] + beta[time + 1][None, :],
            axis=1,
        )
    gamma = np.exp(alpha + beta - log_likelihood)
    xi = np.empty((observations.shape[0] - 1, states, states))
    for time in range(observations.shape[0] - 1):
        log_xi = (
            alpha[time][:, None]
            + np.log(model.transition_matrix)
            + emission[time + 1][None, :]
            + beta[time + 1][None, :]
            - log_likelihood
        )
        xi[time] = np.exp(log_xi)
    return log_likelihood, gamma, xi


def fit_gaussian_hmm(
    observations: object,
    n_states: int,
    *,
    max_iterations: int = 200,
    tolerance: float = 1e-6,
    variance_floor: float = 1e-6,
) -> GaussianHMM:
    """Fit a diagonal-covariance Gaussian HMM by deterministic Baum--Welch EM."""
    data = _hmm_data(observations, minimum=20)
    if (
        isinstance(n_states, bool)
        or not isinstance(n_states, int)
        or not 2 <= n_states <= min(8, data.shape[0] // 5)
    ):
        raise ValueError("n_states must be an integer between two and min(8, n_observations // 5)")
    if (
        isinstance(max_iterations, bool)
        or not isinstance(max_iterations, int)
        or max_iterations < 2
    ):
        raise ValueError("max_iterations must be an integer of at least two")
    if not np.isfinite([tolerance, variance_floor]).all() or min(tolerance, variance_floor) <= 0.0:
        raise ValueError("tolerance and variance_floor must be finite and positive")
    if np.any(np.var(data, axis=0) <= np.finfo(float).tiny):
        raise ValueError("each HMM feature must have positive empirical variance")
    order = np.argsort(data[:, 0])
    groups = np.array_split(order, n_states)
    means = np.vstack([data[group].mean(axis=0) for group in groups])
    global_variance = np.maximum(np.var(data, axis=0, ddof=1), variance_floor)
    variances = np.vstack(
        [np.maximum(np.var(data[group], axis=0, ddof=1), 0.1 * global_variance) for group in groups]
    )
    transition = np.full((n_states, n_states), 0.05 / (n_states - 1))
    np.fill_diagonal(transition, 0.95)
    model = GaussianHMM(
        initial_probabilities=np.full(n_states, 1.0 / n_states),
        transition_matrix=transition,
        means=means,
        variances=variances,
        log_likelihood_trace=np.empty(0),
        converged=False,
    )
    trace: list[float] = []
    converged = False
    for _ in range(max_iterations):
        log_likelihood, gamma, xi = _forward_backward(model, data)
        trace.append(log_likelihood)
        weights = np.maximum(gamma.sum(axis=0), np.finfo(float).tiny)
        means = gamma.T @ data / weights[:, None]
        difference = data[:, None, :] - means[None, :, :]
        variances = np.maximum(
            np.sum(gamma[:, :, None] * difference**2, axis=0) / weights[:, None],
            variance_floor * global_variance,
        )
        transition_counts = xi.sum(axis=0) + 1e-8
        transition = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        initial = np.maximum(gamma[0], 1e-12)
        initial /= initial.sum()
        model = GaussianHMM(
            initial_probabilities=initial,
            transition_matrix=transition,
            means=means,
            variances=variances,
            log_likelihood_trace=np.asarray(trace),
            converged=False,
        )
        if len(trace) > 1 and trace[-1] - trace[-2] <= tolerance * (1.0 + abs(trace[-2])):
            converged = True
            break
    canonical = np.argsort(model.means[:, 0])
    model = GaussianHMM(
        initial_probabilities=model.initial_probabilities[canonical],
        transition_matrix=model.transition_matrix[np.ix_(canonical, canonical)],
        means=model.means[canonical],
        variances=model.variances[canonical],
        log_likelihood_trace=np.asarray(trace),
        converged=converged,
    )
    return model


def hmm_smoothed_probabilities(model: GaussianHMM, observations: object) -> np.ndarray:
    """Return retrospective state probabilities under a fitted HMM."""
    if not isinstance(model, GaussianHMM):
        raise TypeError("model must be a GaussianHMM")
    data = _hmm_data(observations)
    return _forward_backward(model, data)[1]


def hmm_filtered_probabilities(model: GaussianHMM, observations: object) -> np.ndarray:
    """Return online state probabilities using observations only through each row."""
    if not isinstance(model, GaussianHMM):
        raise TypeError("model must be a GaussianHMM")
    data = _hmm_data(observations)
    emission = _emission_log_density(model, data)
    probabilities = np.empty_like(emission)
    log_probability = np.log(model.initial_probabilities) + emission[0]
    log_probability -= special.logsumexp(log_probability)
    probabilities[0] = np.exp(log_probability)
    for time in range(1, data.shape[0]):
        log_probability = emission[time] + special.logsumexp(
            log_probability[:, None] + np.log(model.transition_matrix), axis=0
        )
        log_probability -= special.logsumexp(log_probability)
        probabilities[time] = np.exp(log_probability)
    return probabilities


def simulate_hmm_forecast(
    model: GaussianHMM,
    filtered_probability: object,
    horizon: int,
    n_samples: int,
    *,
    rng: np.random.Generator,
) -> np.ndarray:
    """Simulate future emissions from a filtered state distribution.

    The result shape is ``(n_samples, horizon, n_features)``.  Parameters are
    held fixed, so this is not a full Bayesian posterior predictive sample.
    """
    if not isinstance(model, GaussianHMM):
        raise TypeError("model must be a GaussianHMM")
    probability = _vector(filtered_probability, name="filtered_probability")
    if probability.size != model.means.shape[0] or np.any(probability < 0.0):
        raise ValueError("filtered_probability has an incompatible shape or negative value")
    if not np.isclose(probability.sum(), 1.0, atol=1e-10):
        raise ValueError("filtered_probability must sum to one")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1:
        raise ValueError("n_samples must be a positive integer")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    result = np.empty((n_samples, horizon, model.means.shape[1]))
    states = rng.choice(model.means.shape[0], size=n_samples, p=probability)
    for step in range(horizon):
        uniforms = rng.random(n_samples)
        cumulative = np.cumsum(model.transition_matrix[states], axis=1)
        states = np.sum(uniforms[:, None] > cumulative, axis=1)
        result[:, step] = rng.normal(
            loc=model.means[states], scale=np.sqrt(model.variances[states])
        )
    return result


def hmm_log_likelihood(model: GaussianHMM, observations: object) -> float:
    """Evaluate the sequential log predictive density of observations."""
    if not isinstance(model, GaussianHMM):
        raise TypeError("model must be a GaussianHMM")
    return _forward_backward(model, _hmm_data(observations))[0]


def viterbi_path(model: GaussianHMM, observations: object) -> np.ndarray:
    """Decode the highest joint-probability state path."""
    if not isinstance(model, GaussianHMM):
        raise TypeError("model must be a GaussianHMM")
    data = _hmm_data(observations)
    emission = _emission_log_density(model, data)
    score = np.empty_like(emission)
    backpointer = np.zeros_like(emission, dtype=int)
    score[0] = np.log(model.initial_probabilities) + emission[0]
    for time in range(1, data.shape[0]):
        candidates = score[time - 1][:, None] + np.log(model.transition_matrix)
        backpointer[time] = np.argmax(candidates, axis=0)
        score[time] = emission[time] + np.max(candidates, axis=0)
    path = np.empty(data.shape[0], dtype=int)
    path[-1] = int(np.argmax(score[-1]))
    for time in range(data.shape[0] - 2, -1, -1):
        path[time] = backpointer[time + 1, path[time + 1]]
    return path


@dataclass(frozen=True)
class HMMStateDiagnostics:
    occupancy: np.ndarray
    mean_duration: np.ndarray
    transition_matrix: np.ndarray


def hmm_state_diagnostics(model: GaussianHMM, observations: object) -> HMMStateDiagnostics:
    """Summarize decoded occupancy and durations without calling states truth."""
    path = viterbi_path(model, observations)
    states = model.means.shape[0]
    occupancy = np.bincount(path, minlength=states) / path.size
    durations: list[list[int]] = [[] for _ in range(states)]
    start = 0
    for index in range(1, path.size + 1):
        if index == path.size or path[index] != path[start]:
            durations[path[start]].append(index - start)
            start = index
    means = np.array([np.mean(item) if item else 0.0 for item in durations])
    return HMMStateDiagnostics(
        occupancy=occupancy, mean_duration=means, transition_matrix=model.transition_matrix.copy()
    )


def waic(log_likelihood_draws: object) -> tuple[float, float]:
    """Return WAIC and effective parameter count from draw-by-observation logs."""
    values = np.asarray(log_likelihood_draws, dtype=float)
    if (
        values.ndim != 2
        or values.shape[0] < 2
        or values.shape[1] < 1
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("log_likelihood_draws must be a finite draw-by-observation matrix")
    lppd = float(np.sum(special.logsumexp(values, axis=0) - np.log(values.shape[0])))
    effective_parameters = float(np.sum(np.var(values, axis=0, ddof=1)))
    return float(-2.0 * (lppd - effective_parameters)), effective_parameters


__all__ = [
    "BayesianLinearPosterior",
    "GaussianHMM",
    "HMMStateDiagnostics",
    "HierarchicalNormalPosterior",
    "MCMCResult",
    "NormalMeanPosterior",
    "StudentTPredictive",
    "bayesian_linear_predictive",
    "effective_sample_size",
    "fit_bayesian_linear_regression",
    "fit_gaussian_hmm",
    "hierarchical_normal_posterior",
    "hmm_filtered_probabilities",
    "hmm_log_likelihood",
    "hmm_smoothed_probabilities",
    "hmm_state_diagnostics",
    "metropolis_hastings",
    "normal_mean_posterior",
    "simulate_hmm_forecast",
    "split_rhat",
    "viterbi_path",
    "waic",
]
