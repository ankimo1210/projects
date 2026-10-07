"""Private Hull §32.4 moment-matched branching and node-discount rollback."""

import numpy as np


def match_trinomial_moments(offsets, mean, variance):
    """Solve mass/mean/second moment for three distinct successor offsets."""
    x = np.asarray(offsets, dtype=float)
    if x.shape != (3,) or np.unique(x).size != 3 or variance < 0:
        raise ValueError("three distinct offsets and nonnegative variance required")
    matrix = np.vstack([np.ones(3), x, x * x])
    p = np.linalg.solve(matrix, np.array([1.0, mean, variance + mean * mean]))
    if np.any(p < -1e-12) or np.any(p > 1 + 1e-12):
        raise ValueError("moments cannot be represented by nonnegative branch probabilities")
    p = np.maximum(p, 0)
    return p / p.sum()


def trinomial_branch(index, mean_reversion, delta, jmax):
    """Hull standard/upward/downward branch with Euler mean -a*j*dt.

    Labels are ascending. At +jmax successors are j-2,j-1,j; at -jmax they
    are j,j+1,j+2. Interior successors are j-1,j,j+1. Variance in grid
    units is 1/3 (grid step sigma*sqrt(3*dt)). This uses finite-period tree
    Euler drift, not the exact OU endpoint variance.
    """
    if mean_reversion < 0 or delta <= 0 or jmax < 1 or abs(index) > jmax:
        raise ValueError("valid node bound, nonnegative a and positive step required")
    start = index - 2 if index == jmax else index if index == -jmax else index - 1
    successors = np.arange(start, start + 3, dtype=int)
    probability = match_trinomial_moments(
        successors - index, -mean_reversion * index * delta, 1 / 3
    )
    return {"successors": successors, "probabilities": probability}


def discounted_rollback(
    level_rates, successors, probabilities, delta_times, terminal_payoffs, *, exercise_values=None
):
    """Cash-price rollback with exp(-R_node*dt), returning every value level.

    R is a continuous finite-period rate, not a constant discount imposed
    on all nodes. Successors are zero-based positions in the following
    array. Optional exercise_values has one vector per nonterminal level;
    the supplied terminal payoff already includes its final exercise/event
    convention. This kernel does not guess cash/quoted strike or accrual.
    """
    steps = len(level_rates)
    dt = np.asarray(delta_times, dtype=float)
    last = np.asarray(terminal_payoffs, dtype=float)
    if (
        len(successors) != steps
        or len(probabilities) != steps
        or dt.shape != (steps,)
        or np.any(dt <= 0)
        or last.ndim != 1
    ):
        raise ValueError("matching levels/positive time steps and terminal vector required")
    if exercise_values is not None and len(exercise_values) != steps:
        raise ValueError("one exercise vector per nonterminal level required")
    values = [None] * (steps + 1)
    values[-1] = last.copy()
    for i in range(steps - 1, -1, -1):
        rates = np.asarray(level_rates[i], dtype=float)
        nodes = np.asarray(successors[i], dtype=int)
        p = np.asarray(probabilities[i], dtype=float)
        if (
            rates.ndim != 1
            or nodes.ndim != 2
            or nodes.shape != p.shape
            or nodes.shape[0] != rates.size
            or np.any(nodes < 0)
            or np.any(nodes >= values[i + 1].size)
        ):
            raise ValueError(
                "branch indices/probabilities must match each node and successor level"
            )
        if np.any(p < 0) or not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-12):
            raise ValueError("nonnegative probabilities summing to one required")
        continuation = np.exp(-rates * dt[i]) * np.sum(p * values[i + 1][nodes], axis=1)
        if exercise_values is not None:
            exercise = np.asarray(exercise_values[i], dtype=float)
            if exercise.shape != rates.shape:
                raise ValueError("exercise values must match each node")
            continuation = np.maximum(continuation, exercise)
        values[i] = continuation
    return values
