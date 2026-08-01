"""Random walks, Markov chains, and the Poisson process."""

import numpy as np
import pytest
from stats_textbook import processes as proc

# A two-state chain with a known stationary distribution: pi = (b, a)/(a+b)
# for P = [[1-a, a], [b, 1-b]].
TWO_STATE = np.array([[0.9, 0.1], [0.2, 0.8]])
# Deterministic 2-cycle: irreducible but periodic with period 2.
CYCLE = np.array([[0.0, 1.0], [1.0, 0.0]])
# Two closed classes: not irreducible.
REDUCIBLE = np.array([[1.0, 0.0], [0.0, 1.0]])


def test_random_walk_shape_starts_at_zero_and_is_deterministic():
    a = proc.random_walk(50, n_paths=7, seed=1)
    b = proc.random_walk(50, n_paths=7, seed=1)
    assert a.shape == (7, 51)
    assert (a[:, 0] == 0).all()
    np.testing.assert_array_equal(a, b)


def test_rademacher_walk_moves_by_exactly_one_each_step():
    paths = proc.random_walk(200, n_paths=3, step="rademacher", seed=2)
    assert set(np.unique(np.diff(paths, axis=1))) == {-1.0, 1.0}


def test_random_walk_rejects_unknown_step():
    with pytest.raises(ValueError, match="step"):
        proc.random_walk(10, step="levy")


def test_markov_chain_rejects_rows_that_are_not_distributions():
    with pytest.raises(ValueError, match="rows"):
        proc.MarkovChain(np.array([[0.5, 0.2], [0.3, 0.7]]))


def test_stationary_matches_the_closed_form():
    chain = proc.MarkovChain(TWO_STATE)
    pi = chain.stationary()
    np.testing.assert_allclose(pi, [2 / 3, 1 / 3], rtol=1e-10)
    # Stationarity is the defining property.
    np.testing.assert_allclose(pi @ TWO_STATE, pi, rtol=1e-10)


def test_distribution_after_converges_to_the_stationary_law():
    chain = proc.MarkovChain(TWO_STATE)
    p = chain.distribution_after(200, np.array([1.0, 0.0]))
    np.testing.assert_allclose(p, chain.stationary(), atol=1e-8)


def test_simulate_visits_states_in_stationary_proportion():
    chain = proc.MarkovChain(TWO_STATE)
    path = chain.simulate(50_000, x0=0, seed=4)
    assert path.shape == (50_001,)
    visited = np.bincount(path, minlength=2) / path.size
    np.testing.assert_allclose(visited, chain.stationary(), atol=0.02)


def test_irreducibility_and_period():
    assert proc.MarkovChain(TWO_STATE).is_irreducible()
    assert proc.MarkovChain(TWO_STATE).period() == 1
    assert proc.MarkovChain(CYCLE).is_irreducible()
    assert proc.MarkovChain(CYCLE).period() == 2
    assert not proc.MarkovChain(REDUCIBLE).is_irreducible()


def test_poisson_process_times_are_sorted_and_inside_the_window():
    t = proc.poisson_process(rate=5.0, t_max=10.0, seed=0)
    assert (np.diff(t) > 0).all()
    assert t[-1] <= 10.0


def test_poisson_counts_have_mean_and_variance_equal_to_rate_times_time():
    counts = proc.poisson_counts(rate=3.0, t_max=4.0, n_reps=20_000, seed=0)
    assert counts.shape == (20_000,)
    assert abs(counts.mean() - 12.0) < 0.15
    # The Poisson signature: variance equals the mean.
    assert abs(counts.var() - 12.0) < 0.4
