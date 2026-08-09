"""Deterministic synthetic data for the B1 numerical experiments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.random import Generator
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]
Seed = int | np.integer | Generator | None


def _rng(seed: Seed) -> Generator:
    """Return a generator without touching NumPy's process-global RNG."""

    if isinstance(seed, Generator):
        return seed
    return np.random.default_rng(seed)


def _positive_integer(value: int, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


@dataclass(frozen=True)
class RegressionDataset:
    """A synthetic regression problem with known data-generating parameters.

    ``X`` contains feature columns only.  Use ``design_with_intercept`` when
    fitting data generated with a non-zero ``intercept``.
    """

    X: FloatArray
    y: FloatArray
    coefficients: FloatArray
    intercept: float

    @property
    def design_with_intercept(self) -> FloatArray:
        """Return ``X`` with a leading column of ones."""

        return np.column_stack((np.ones(self.X.shape[0]), self.X))


def make_regression_dataset(
    n_samples: int = 200,
    n_features: int = 4,
    *,
    coefficients: ArrayLike | None = None,
    intercept: float = 0.0,
    noise_std: float = 0.1,
    condition_number: float = 10.0,
    rank_deficient: bool = False,
    seed: Seed = 0,
) -> RegressionDataset:
    """Create a regression design with controlled singular values.

    ``condition_number`` controls the ratio of largest to smallest non-zero
    singular value.  When ``rank_deficient=True``, the final singular value
    is set exactly to zero, so individual coefficients are not identifiable.
    ``X`` excludes the intercept column by design.
    """

    n_samples = _positive_integer(n_samples, name="n_samples", minimum=2)
    n_features = _positive_integer(n_features, name="n_features")
    if n_samples < n_features:
        raise ValueError("n_samples must be at least n_features")
    if not np.isfinite(condition_number) or condition_number < 1.0:
        raise ValueError("condition_number must be finite and at least one")
    if not np.isfinite(noise_std) or noise_std < 0.0:
        raise ValueError("noise_std must be a finite non-negative number")
    if not np.isfinite(intercept):
        raise ValueError("intercept must be finite")
    if not isinstance(rank_deficient, (bool, np.bool_)):
        raise TypeError("rank_deficient must be a boolean")

    if coefficients is None:
        signs = np.where(np.arange(n_features) % 2 == 0, 1.0, -1.0)
        true_coefficients = signs * np.linspace(1.25, 0.5, n_features)
    else:
        true_coefficients = np.asarray(coefficients, dtype=float)
        if true_coefficients.shape != (n_features,):
            raise ValueError("coefficients must have one entry per feature")
        if not np.all(np.isfinite(true_coefficients)):
            raise ValueError("coefficients must contain only finite values")

    generator = _rng(seed)
    left, _ = np.linalg.qr(generator.normal(size=(n_samples, n_features)))
    right, _ = np.linalg.qr(generator.normal(size=(n_features, n_features)))
    if rank_deficient and n_features == 1:
        singular_values = np.zeros(1)
    elif rank_deficient:
        nonzero = np.geomspace(1.0, 1.0 / condition_number, n_features - 1)
        singular_values = np.concatenate((nonzero, np.zeros(1)))
    else:
        singular_values = np.geomspace(1.0, 1.0 / condition_number, n_features)
    design = np.sqrt(n_samples) * (left @ np.diag(singular_values) @ right.T)
    noise = generator.normal(scale=noise_std, size=n_samples)
    response = intercept + design @ true_coefficients + noise

    return RegressionDataset(
        X=np.asarray(design, dtype=float),
        y=np.asarray(response, dtype=float),
        coefficients=np.asarray(true_coefficients, dtype=float),
        intercept=float(intercept),
    )


# A descriptive alias retained for prose and exploratory notebooks.
make_synthetic_regression = make_regression_dataset


@dataclass(frozen=True)
class YieldChangePanel:
    """Synthetic yield changes and their latent level/slope/curvature factors.

    All values are changes in decimal yield units: ``0.0001`` is one basis
    point.  ``loadings`` has maturities in years as its index.
    """

    changes: pd.DataFrame
    factors: pd.DataFrame
    loadings: pd.DataFrame
    regime_shift_at: int | None


def _maturity_array(maturities: Sequence[float] | ArrayLike) -> FloatArray:
    values = np.asarray(maturities, dtype=float)
    if values.ndim != 1 or values.size < 3:
        raise ValueError("maturities must be a one-dimensional array of at least three tenors")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("maturities must be finite and strictly positive")
    if np.any(np.diff(values) <= 0.0):
        raise ValueError("maturities must be strictly increasing")
    return values


def _factor_tuple(values: Sequence[float], *, name: str) -> FloatArray:
    array = np.asarray(values, dtype=float)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain three finite numbers")
    return array


def make_yield_change_panel(
    n_observations: int = 500,
    *,
    maturities: Sequence[float] = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0),
    factor_volatilities: Sequence[float] = (0.0007, 0.0004, 0.00025),
    noise_std: float = 0.00004,
    regime_shift_at: int | None = None,
    regime_volatility: float = 2.0,
    regime_mean_shift: Sequence[float] = (0.0, 0.0, 0.0),
    seed: Seed = 0,
) -> YieldChangePanel:
    """Generate a yield-change panel with level, slope, and curvature modes.

    The loading vectors are orthonormalized before simulation.  An optional
    regime shift scales factor volatility and adds a factor mean from
    ``regime_shift_at`` onward; no future data are used to define the shift.
    """

    n_observations = _positive_integer(n_observations, name="n_observations", minimum=2)
    tenor = _maturity_array(maturities)
    volatilities = _factor_tuple(factor_volatilities, name="factor_volatilities")
    if np.any(volatilities <= 0.0):
        raise ValueError("factor_volatilities must be strictly positive")
    mean_shift = _factor_tuple(regime_mean_shift, name="regime_mean_shift")
    if not np.isfinite(noise_std) or noise_std < 0.0:
        raise ValueError("noise_std must be a finite non-negative number")
    if not np.isfinite(regime_volatility) or regime_volatility <= 0.0:
        raise ValueError("regime_volatility must be finite and strictly positive")
    if regime_shift_at is not None:
        regime_shift_at = _positive_integer(regime_shift_at, name="regime_shift_at", minimum=1)
        if regime_shift_at >= n_observations:
            raise ValueError("regime_shift_at must be before the final observation")

    scaled_tenor = 2.0 * (tenor - tenor.min()) / (tenor.max() - tenor.min()) - 1.0
    raw_loadings = np.column_stack(
        (
            np.ones(tenor.size),
            scaled_tenor,
            1.0 - 2.0 * scaled_tenor**2,
        )
    )
    loadings, _ = np.linalg.qr(raw_loadings, mode="reduced")
    # Preserve the intuitive orientation of each named raw loading.
    signs = np.sign(np.einsum("ij,ij->j", loadings, raw_loadings))
    signs[signs == 0.0] = 1.0
    loadings = loadings * signs

    generator = _rng(seed)
    innovations = generator.normal(size=(n_observations, 3))
    scale = np.ones((n_observations, 1))
    shifts = np.zeros((n_observations, 3))
    if regime_shift_at is not None:
        scale[regime_shift_at:] = regime_volatility
        shifts[regime_shift_at:] = mean_shift
    factors = innovations * volatilities * scale + shifts
    idiosyncratic_noise = generator.normal(scale=noise_std, size=(n_observations, tenor.size))
    changes = factors @ loadings.T + idiosyncratic_noise

    factor_names = ["level", "slope", "curvature"]
    observation_index = pd.RangeIndex(n_observations, name="observation")
    maturity_index = pd.Index(tenor, name="maturity_years")
    return YieldChangePanel(
        changes=pd.DataFrame(changes, index=observation_index, columns=maturity_index),
        factors=pd.DataFrame(factors, index=observation_index, columns=factor_names),
        loadings=pd.DataFrame(loadings, index=maturity_index, columns=factor_names),
        regime_shift_at=regime_shift_at,
    )
