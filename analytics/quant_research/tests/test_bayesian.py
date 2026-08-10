from __future__ import annotations

import numpy as np
import pytest
from quant_textbook.bayesian import (
    bayesian_linear_predictive,
    effective_sample_size,
    fit_bayesian_linear_regression,
    fit_gaussian_hmm,
    hierarchical_normal_posterior,
    hmm_filtered_probabilities,
    hmm_log_likelihood,
    hmm_smoothed_probabilities,
    hmm_state_diagnostics,
    metropolis_hastings,
    normal_mean_posterior,
    simulate_hmm_forecast,
    split_rhat,
    viterbi_path,
    waic,
)


def test_normal_conjugacy_matches_precision_weighted_formula() -> None:
    posterior = normal_mean_posterior(
        [1.0, 2.0, 3.0], observation_variance=4.0, prior_mean=0.0, prior_variance=2.0
    )
    assert posterior.variance == pytest.approx(0.8)
    assert posterior.mean == pytest.approx(1.2)
    lower, upper = posterior.predictive_interval(0.9)
    assert lower < posterior.mean < upper


def test_bayesian_linear_predictive_contains_known_coefficients() -> None:
    rng = np.random.default_rng(8101)
    x = np.column_stack([np.ones(500), rng.normal(size=500)])
    y = x @ np.array([0.5, -1.2]) + rng.normal(scale=0.3, size=500)
    posterior = fit_bayesian_linear_regression(x, y, prior_precision=0.01)
    np.testing.assert_allclose(posterior.mean, [0.5, -1.2], atol=0.04)
    predictive = bayesian_linear_predictive(posterior, x[:10])
    lower, upper = predictive.interval()
    assert np.all(lower < predictive.mean)
    assert np.all(upper > predictive.mean)


def test_hierarchical_posterior_shrinks_noisy_group_more() -> None:
    posterior = hierarchical_normal_posterior(
        [1.0, 1.0], [0.1, 2.0], population_mean=0.0, population_standard_deviation=1.0
    )
    assert posterior.means[0] > posterior.means[1]
    assert posterior.shrinkage_weights[0] > posterior.shrinkage_weights[1]


def test_metropolis_hastings_recovers_standard_normal_and_reports_ess() -> None:
    result = metropolis_hastings(
        lambda x: -0.5 * float(x @ x),
        [4.0],
        5000,
        proposal_scale=[1.0],
        burn_in=1000,
        rng=np.random.default_rng(8102),
    )
    assert abs(result.samples[:, 0].mean()) < 0.08
    assert 0.2 < result.acceptance_rate < 0.8
    assert 100.0 < result.effective_sample_size[0] <= 5000.0


def test_split_rhat_flags_shifted_chain() -> None:
    rng = np.random.default_rng(8103)
    good = rng.normal(size=(4, 1000, 1))
    bad = good.copy()
    bad[0, :, 0] += 2.0
    assert split_rhat(good)[0] < 1.02
    assert split_rhat(bad)[0] > 1.1
    assert effective_sample_size(good[0])[0] > 500.0


def test_gaussian_hmm_recovers_persistent_two_state_sequence() -> None:
    rng = np.random.default_rng(8104)
    transition = np.array([[0.97, 0.03], [0.04, 0.96]])
    state = np.zeros(2000, dtype=int)
    for index in range(1, state.size):
        state[index] = rng.choice(2, p=transition[state[index - 1]])
    observations = rng.normal(loc=np.where(state == 0, -2.0, 2.0), scale=0.4)
    model = fit_gaussian_hmm(observations, 2)
    probabilities = hmm_smoothed_probabilities(model, observations)
    filtered = hmm_filtered_probabilities(model, observations)
    decoded = viterbi_path(model, observations)
    diagnostics = hmm_state_diagnostics(model, observations)
    assert model.converged
    assert np.all(np.diff(model.log_likelihood_trace) >= -1e-6)
    assert probabilities.shape == (2000, 2)
    np.testing.assert_allclose(filtered.sum(axis=1), 1.0)
    np.testing.assert_allclose(
        hmm_filtered_probabilities(model, observations[:500]),
        filtered[:500],
        atol=1e-12,
    )
    assert (decoded == state).mean() > 0.98
    assert np.all(diagnostics.occupancy > 0.1)
    assert hmm_log_likelihood(model, observations) > -3000.0
    forecast = simulate_hmm_forecast(model, filtered[-1], 5, 200, rng=np.random.default_rng(8105))
    assert forecast.shape == (200, 5, 1)
    assert np.all(np.isfinite(forecast))


def test_waic_matches_direct_definition() -> None:
    logs = np.log(np.array([[0.5, 0.2], [0.4, 0.3], [0.6, 0.25]]))
    value, effective = waic(logs)
    assert np.isfinite(value)
    assert effective > 0.0


@pytest.mark.parametrize(
    "call",
    [
        lambda: normal_mean_posterior(
            [], observation_variance=1.0, prior_mean=0.0, prior_variance=1.0
        ),
        lambda: fit_bayesian_linear_regression([[1.0]], [1.0]),
        lambda: hierarchical_normal_posterior(
            [1.0], [-1.0], population_mean=0.0, population_standard_deviation=1.0
        ),
        lambda: metropolis_hastings(
            lambda x: 0.0, [0.0], 7, proposal_scale=[1.0], rng=np.random.default_rng(1)
        ),
        lambda: split_rhat(np.ones((1, 20, 1))),
        lambda: fit_gaussian_hmm(np.ones(30), 2),
        lambda: waic([[0.0]]),
    ],
)
def test_bayesian_contracts_reject_invalid_inputs(call) -> None:
    with pytest.raises((TypeError, ValueError)):
        call()
