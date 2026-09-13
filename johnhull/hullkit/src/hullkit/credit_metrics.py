"""CreditMetrics: rating transitions and credit VaR (Hull 11e, §24.9).

Hull Table 24.4 (S&P 1981–2019 one-year transition matrix, WR reallocated) is
transcribed as a textbook fixture. Rating changes are sampled with a one-factor
Gaussian copula: obligor i moves to the rating whose cumulative-probability
band (in column order AAA…Default) contains x_i = √ρ F + √(1−ρ) Z_i.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

RATINGS: tuple[str, ...] = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC/C", "Default")

HULL_TABLE_24_4 = np.array(
    [
        [89.83, 9.37, 0.55, 0.05, 0.11, 0.03, 0.05, 0.00],
        [0.51, 90.77, 8.06, 0.50, 0.05, 0.06, 0.02, 0.02],
        [0.03, 1.74, 92.49, 5.27, 0.28, 0.12, 0.02, 0.05],
        [0.01, 0.10, 3.59, 91.83, 3.73, 0.47, 0.11, 0.17],
        [0.01, 0.03, 0.12, 5.23, 86.06, 7.27, 0.60, 0.67],
        [0.00, 0.02, 0.08, 0.18, 5.43, 85.38, 5.10, 3.80],
        [0.00, 0.00, 0.13, 0.22, 0.69, 15.33, 51.61, 32.03],
    ]
)
"""Hull 11e Table 24.4: one-year transition probabilities in percent (rows: initial rating)."""


@dataclass(frozen=True)
class TransitionMatrix:
    """Square one-period transition matrix (fractions) with an absorbing default state.

    Rows are kept as printed (no renormalisation) so that the thresholds reproduce
    Hull's page-582 numbers; the rounding residual of a row (≤ ``tol``) therefore
    falls into the last state when sampling.
    """

    probabilities: np.ndarray
    ratings: tuple[str, ...] = RATINGS

    def __post_init__(self) -> None:
        p = np.asarray(self.probabilities, dtype=float)
        n = len(self.ratings)
        if p.shape != (n, n):
            raise ValueError(f"probabilities must be {n}x{n} to match ratings")
        if np.any(p < 0.0) or np.any(~np.isfinite(p)):
            raise ValueError("probabilities must be finite and >= 0")
        if np.any(np.abs(p.sum(axis=1) - 1.0) > 5e-4):
            raise ValueError("each row must sum to 1 within 0.0005")
        object.__setattr__(self, "probabilities", p)
        object.__setattr__(self, "ratings", tuple(self.ratings))

    @classmethod
    def from_percent(
        cls, table, ratings: tuple[str, ...] = RATINGS, tol: float = 5e-4
    ) -> TransitionMatrix:
        """Build from a percent table (live ratings × all states), appending the default row."""
        table = np.asarray(table, dtype=float) / 100.0
        n = len(ratings)
        if table.shape != (n - 1, n):
            raise ValueError(f"table must have shape {(n - 1, n)}")
        if np.any(np.abs(table.sum(axis=1) - 1.0) > tol):
            raise ValueError(f"rows must sum to 100% within {tol * 100:.2f} points")
        absorbing = np.zeros((1, n))
        absorbing[0, -1] = 1.0
        return cls(np.vstack([table, absorbing]), ratings)

    def index(self, rating: str) -> int:
        """Column/row index of a rating label."""
        try:
            return self.ratings.index(rating)
        except ValueError as exc:
            raise ValueError(f"unknown rating {rating!r}") from exc

    def row(self, initial: str) -> np.ndarray:
        """Transition probabilities out of ``initial``."""
        return self.probabilities[self.index(initial)]

    def default_probability(self, initial: str) -> float:
        """One-period probability of moving from ``initial`` to the default state."""
        return float(self.row(initial)[-1])

    def multi_period(self, years: int) -> TransitionMatrix:
        """Transition matrix over ``years`` periods (matrix power; Hull Technical Note 11)."""
        if int(years) != years or years < 1:
            raise ValueError("years must be a positive integer")
        return TransitionMatrix(
            np.linalg.matrix_power(self.probabilities, int(years)), self.ratings
        )


def rating_thresholds(matrix: TransitionMatrix, initial: str) -> np.ndarray:
    """Upper thresholds N⁻¹(·) in column order for a live initial rating (Hull p. 582).

    Boundaries between live ratings come from the cumulative probabilities counted
    from AAA; the default boundary is N⁻¹(1 − p_default) so the default probability
    is exact and the last live rating absorbs the row's rounding residual. For Hull's
    AAA row: 1.2719, 2.4089, 2.8070, …; for BBB: −3.7190, −3.0618, −1.7866, …, 2.9290.
    """
    if initial == matrix.ratings[-1]:
        raise ValueError("thresholds are defined for live ratings only")
    row = matrix.row(initial)
    cumulative = np.clip(np.cumsum(row)[:-2], 0.0, 1.0)
    default_boundary = norm.ppf(np.clip(1.0 - row[-1], 0.0, 1.0))
    return np.concatenate([norm.ppf(cumulative), [default_boundary]])


def migrate(matrix: TransitionMatrix, initial: str, x) -> np.ndarray:
    """Map standard-normal draws to end-of-period rating indices via the thresholds."""
    thresholds = rating_thresholds(matrix, initial)
    return np.searchsorted(thresholds, np.asarray(x, dtype=float), side="right")


def simulate_rating_migrations(
    matrix: TransitionMatrix, initial_ratings, rho: float, n_sims: int, rng=None
) -> np.ndarray:
    """Sample correlated rating changes: x_i = √ρ F + √(1−ρ) Z_i (Hull §24.9 CreditMetrics)."""
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")
    if int(n_sims) != n_sims or n_sims < 1:
        raise ValueError("n_sims must be a positive integer")
    rng = np.random.default_rng() if rng is None else rng
    labels = list(initial_ratings)
    factor = rng.standard_normal((int(n_sims), 1))
    idiosyncratic = rng.standard_normal((int(n_sims), len(labels)))
    x = np.sqrt(rho) * factor + np.sqrt(1.0 - rho) * idiosyncratic
    out = np.empty((int(n_sims), len(labels)), dtype=int)
    for j, label in enumerate(labels):
        out[:, j] = migrate(matrix, label, x[:, j])
    return out


def credit_loss_distribution(
    new_ratings,
    exposures,
    recovery: float,
    ratings: tuple[str, ...] = RATINGS,
    rating_values=None,
    initial_ratings=None,
) -> np.ndarray:
    """Portfolio credit loss per simulation: exposure·(1−R) on default, plus migration losses.

    ``rating_values`` maps live ratings to a value ratio (e.g. BBB 1.00, BB 0.97); with
    ``initial_ratings`` the loss on a non-defaulted obligor is exposure·(v_initial − v_new),
    so upgrades count as negative losses (CreditMetrics convention).
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    new_ratings = np.asarray(new_ratings, dtype=int)
    exposures = np.asarray(exposures, dtype=float)
    if new_ratings.ndim != 2 or new_ratings.shape[1] != exposures.size:
        raise ValueError("new_ratings must be (n_sims, n_obligors) matching exposures")
    default_index = len(ratings) - 1
    defaulted = new_ratings == default_index
    losses = (defaulted * exposures[None, :] * (1.0 - recovery)).sum(axis=1)
    if rating_values is not None:
        if initial_ratings is None:
            raise ValueError("initial_ratings are required with rating_values")
        values = np.array([rating_values[label] for label in ratings[:-1]] + [0.0])
        start = np.array([rating_values[label] for label in initial_ratings])
        migration = (start[None, :] - values[new_ratings]) * exposures[None, :]
        losses = losses + np.where(defaulted, 0.0, migration).sum(axis=1)
    return losses


def credit_var(losses, confidence: float) -> float:
    """Credit VaR: the ``confidence`` quantile of the simulated loss distribution."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
    return float(np.quantile(np.asarray(losses, dtype=float), confidence))


def expected_loss(losses) -> float:
    """Mean simulated credit loss."""
    return float(np.mean(np.asarray(losses, dtype=float)))
