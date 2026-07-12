"""Tests for local ATM-skew and maturity power-law estimation."""

import numpy as np
import pandas as pd
import pytest
from rough_volatility.skew import (
    atm_skew,
    power_law_fit,
    skew_term_structure,
    skew_window,
)


def test_skew_window_uses_maturity_scale_and_clamps() -> None:
    assert skew_window(1e-5, 0.04) == 0.03
    assert skew_window(1.0, 0.04) == 0.10
    assert skew_window(0.10, 0.04) == pytest.approx(1.5 * np.sqrt(0.004))


def test_weighted_quadratic_recovers_synthetic_atm_slope() -> None:
    rng = np.random.default_rng(90)
    k = np.linspace(-0.08, 0.08, 9)
    standard_error = np.full(k.size, 0.001)
    true_slope = -0.42
    iv = 0.22 + true_slope * k + 0.7 * k**2 + rng.normal(0.0, standard_error)
    smile = pd.DataFrame({"k": k, "iv": iv, "iv_se": standard_error, "ok": True})
    estimate = atm_skew(smile, window=0.08)
    assert estimate.ok
    assert estimate.n_used == 9
    assert abs(estimate.slope - true_slope) < 3 * estimate.se


def test_fewer_than_five_valid_smile_points_propagates_failure() -> None:
    smile = pd.DataFrame(
        {
            "k": [-0.1, 0.0, 0.1, 0.2],
            "iv": [0.3, 0.2, 0.2, 0.3],
            "iv_se": [0.01] * 4,
            "ok": [True] * 4,
        }
    )
    estimate = atm_skew(smile, window=0.3)
    assert not estimate.ok
    assert np.isnan(estimate.slope)
    assert estimate.n_used == 4


def test_exact_power_law_recovers_beta() -> None:
    maturities = np.array([0.02, 0.05, 0.10, 0.25, 0.50, 1.0])
    beta = -0.4
    term = pd.DataFrame(
        {
            "maturity": maturities,
            "skew": -0.3 * maturities**beta,
            "skew_se": np.full(maturities.size, 0.01),
            "ok": True,
        }
    )
    fit = power_law_fit(term)
    assert fit.ok
    assert fit.beta == pytest.approx(beta, abs=1e-12)
    assert fit.h_implied == pytest.approx(0.1, abs=1e-12)
    assert fit.r_squared == pytest.approx(1.0)


def test_term_structure_groups_maturities_and_retains_failed_rows() -> None:
    rows = []
    for maturity, n_points in [(0.1, 9), (0.5, 4)]:
        for k in np.linspace(-0.08, 0.08, n_points):
            rows.append(
                {
                    "maturity": maturity,
                    "k": k,
                    "iv": 0.2 - 0.3 * k,
                    "iv_se": 0.002,
                    "ok": True,
                }
            )
    term = skew_term_structure(pd.DataFrame(rows), xi0=0.04)
    assert list(term["maturity"]) == [0.1, 0.5]
    assert bool(term.loc[term["maturity"] == 0.1, "ok"].iloc[0])
    assert not bool(term.loc[term["maturity"] == 0.5, "ok"].iloc[0])
