"""Deterministic raw-price versus BSM-residual surrogate comparison."""

from __future__ import annotations

import importlib
from collections.abc import Callable

import numpy as np

from .pricing_data import black_scholes_labels
from .pricing_policy import PolynomialRidge


def _heston_teacher(inputs: np.ndarray, *, n_terms: int) -> np.ndarray:
    try:
        teacher = importlib.import_module("hullkit.surrogate_data").heston_cos_price
    except (ImportError, ModuleNotFoundError, AttributeError) as exc:
        raise RuntimeError(
            "hullkit with heston_cos_price is required for the Heston residual comparison"
        ) from exc
    prices = []
    for x, tau, rate, dividend, sigma in np.asarray(inputs, dtype=np.float64):
        prices.append(
            teacher(
                x * np.exp(-dividend * tau),
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


def compare_heston_bsm_residual(
    train_inputs: np.ndarray,
    test_inputs: np.ndarray,
    *,
    n_terms: int = 128,
    teacher_function: Callable[[np.ndarray], np.ndarray] | None = None,
) -> dict[str, float | int | str | bool]:
    """Compare equal-capacity raw and BSM-residual polynomial surrogates.

    The analytical BSM value is a disclosed control variate, not a hidden
    Heston formula.  Both routes use the same rows and polynomial capacity.
    """

    train = np.asarray(train_inputs, dtype=np.float64)
    test = np.asarray(test_inputs, dtype=np.float64)
    if (
        train.ndim != 2
        or test.ndim != 2
        or train.shape[1:] != (5,)
        or test.shape[1:] != (5,)
        or len(train) < 16
        or len(test) < 8
        or n_terms <= 1
    ):
        raise ValueError("residual comparison needs >=16 train and >=8 test rows of width five")
    teacher = teacher_function or (lambda rows: _heston_teacher(rows, n_terms=n_terms))
    train_teacher = np.asarray(teacher(train), dtype=np.float64)
    test_teacher = np.asarray(teacher(test), dtype=np.float64)
    if train_teacher.shape != (len(train),) or test_teacher.shape != (len(test),):
        raise ValueError("teacher_function must return one finite price per row")
    if np.any(~np.isfinite(train_teacher)) or np.any(~np.isfinite(test_teacher)):
        raise ValueError("teacher prices must be finite")
    train_bsm = black_scholes_labels(train)["price"]
    test_bsm = black_scholes_labels(test)["price"]
    raw_model = PolynomialRidge(degree=3, alpha=1e-8).fit(train, train_teacher)
    residual_model = PolynomialRidge(degree=3, alpha=1e-8).fit(
        train,
        train_teacher - train_bsm,
    )
    raw_prediction = raw_model.predict(test)
    corrected_prediction = test_bsm + residual_model.predict(test)
    raw_mae = float(np.mean(np.abs(raw_prediction - test_teacher)))
    residual_mae = float(np.mean(np.abs(corrected_prediction - test_teacher)))
    return {
        "teacher": "heston_cos",
        "baseline": "analytic_bsm",
        "surrogate": "degree_3_polynomial_ridge",
        "train_rows": len(train),
        "test_rows": len(test),
        "cos_terms": n_terms,
        "raw_price_mae": raw_mae,
        "bsm_residual_mae": residual_mae,
        "residual_improved": residual_mae < raw_mae,
        "adopted": "bsm_residual" if residual_mae < raw_mae else "raw_price",
    }
