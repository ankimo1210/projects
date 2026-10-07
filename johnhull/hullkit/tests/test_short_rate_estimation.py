"""§31.4 original 8664 observations, OLS, risk fit and independent methods."""

import csv
import importlib
import math
from datetime import date
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import minimize_scalar

TIMES = np.array([0.5, 1, 2, 3, 5, 7, 10, 20, 30])
MARKET = np.array([0.45, 0.58, 0.74, 0.86, 1.15, 1.40, 1.55, 1.88, 2.24]) / 100
PRINTED_MODEL = np.array([0.40, 0.49, 0.65, 0.80, 1.06, 1.27, 1.52, 2.02, 2.26]) / 100


def model():
    return importlib.import_module("hullkit._short_rate_estimation")


def source():
    with (Path(__file__).parent / "data/hull_31_4_rates.csv").open() as f:
        rows = list(csv.DictReader(f))
    return [date.fromisoformat(r["date"]) for r in rows], np.array(
        [float(r["rate_percent"]) / 100 for r in rows]
    )


def independent_ols(rates):
    x = rates[:-1]
    y = np.diff(rates)
    slope = float((x - x.mean()) @ (y - y.mean()) / ((x - x.mean()) @ (x - x.mean())))
    intercept = float(y.mean() - slope * x.mean())
    residual = y - intercept - slope * x
    return intercept, slope, math.sqrt(float(residual @ residual) / (len(y) - 2))


def test_original_snapshot_quality_units_and_printed_euler_regression():
    dates, rates = source()
    assert len(rates) == 8664 and dates[0] == date(1982, 1, 4) and dates[-1] == date(2016, 8, 23)
    assert len(set(dates)) == len(dates) and all(a < b for a, b in pairwise(dates))
    assert (
        np.all(np.isfinite(rates))
        and rates.min() == pytest.approx(0.0001)
        and rates.max() == pytest.approx(0.1549)
    )
    row = model().fit_vasicek_series(rates, 1 / 250)
    assert row["pairs"] == 8663
    assert row["intercept"] == pytest.approx(0.00000915, abs=0.000000005)
    assert row["slope"] == pytest.approx(-0.000545, abs=0.0000005)
    assert row["residual_sd"] == pytest.approx(0.000754, abs=0.0000005)
    assert row["a"] == pytest.approx(0.136, abs=0.0005)
    assert row["b"] == pytest.approx(0.0168, abs=0.00005)
    assert row["sigma"] == pytest.approx(0.0119, abs=0.00005)
    alpha, beta, sd = independent_ols(rates)
    assert [row["intercept"], row["slope"], row["residual_sd"]] == pytest.approx(
        [alpha, beta, sd], rel=1e-11, abs=1e-15
    )
    assert row["a"] == pytest.approx(0.13615368202810535, abs=1e-11)


def test_table_31_1_and_lambda_reproduced_with_independent_kernel_and_optimizer():
    _, rates = source()
    p = model().fit_vasicek_series(rates, 1 / 250)
    row = model().fit_vasicek_risk_price(0.003, p["a"], p["b"], p["sigma"], TIMES, MARKET)
    assert row["risk_price"] == pytest.approx(-0.175, abs=0.0005)
    assert row["risk_price"] == pytest.approx(-0.1746227999177317, abs=1e-7)
    assert row["model_zeros"] == pytest.approx(PRINTED_MODEL, abs=0.00005)
    assert row["sse"] == pytest.approx(6.64899468309e-6, rel=1e-10)
    a, bp, s = p["a"], p["b"], p["sigma"]

    def zeros(lam):
        b = bp - lam * s / a

        def zero(t):
            B = -math.expm1(-a * t) / a
            variance = s * s * quad(lambda u: (-math.expm1(-a * u) / a) ** 2, 0, t, epsabs=1e-13)[0]
            return (0.003 * B + b * (t - B) - 0.5 * variance) / t

        return np.array([zero(t) for t in TIMES])

    fit = minimize_scalar(
        lambda lam: np.sum((zeros(lam) - MARKET) ** 2),
        bounds=(-2, 2),
        method="bounded",
        options={"xatol": 1e-12},
    )
    assert row["risk_price"] == pytest.approx(fit.x, abs=2e-8)
    assert row["model_zeros"] == pytest.approx(zeros(fit.x), abs=1e-10)
    assert row["residuals"] == pytest.approx(row["model_zeros"] - MARKET, abs=1e-14)


def test_euler_mle_and_exact_ou_likelihood_use_distinct_variance_conventions():
    _, rates = source()
    ols = model().fit_vasicek_series(rates, 1 / 250)
    euler = model().fit_vasicek_series(rates, 1 / 250, method="euler_mle")
    exact = model().fit_vasicek_series(rates, 1 / 250, method="exact_ou_mle")
    n = ols["pairs"]
    rho = 1 + ols["slope"]
    assert euler["sigma"] == pytest.approx(ols["sigma"] * math.sqrt((n - 2) / n), rel=1e-12)
    assert exact["a"] == pytest.approx(-math.log(rho) * 250, rel=1e-12)
    assert exact["b"] == pytest.approx(ols["b"], rel=1e-12)
    variance = euler["residual_sd"] ** 2
    assert exact["sigma"] == pytest.approx(
        math.sqrt(variance * 2 * exact["a"] / (1 - rho * rho)), rel=1e-11
    )
    predicted = exact["b"] + (rates[:-1] - exact["b"]) * math.exp(-exact["a"] / 250)
    innovation = exact["sigma"] ** 2 * (-math.expm1(-2 * exact["a"] / 250)) / (2 * exact["a"])
    loglik = -0.5 * np.sum(
        math.log(2 * math.pi * innovation) + (rates[1:] - predicted) ** 2 / innovation
    )
    assert exact["log_likelihood"] == pytest.approx(loglik, abs=1e-7)


def test_estimation_window_materially_changes_physical_parameters():
    dates, rates = source()
    whole = model().fit_vasicek_series(rates, 1 / 250)
    recent = model().fit_vasicek_series(
        rates[np.array([d >= date(2010, 1, 1) for d in dates])], 1 / 250
    )
    assert abs(recent["a"] - whole["a"]) > 0.01
    assert abs(recent["sigma"] - whole["sigma"]) > 0.001


def test_cir_euler_mle_matches_independent_weighted_least_squares():
    _, rates = source()
    row = model().fit_cir_euler_series(rates, 1 / 250)
    x = rates[:-1]
    y = np.diff(rates)
    design = np.column_stack([np.ones(len(x)), x])
    weights = 1 / x
    alpha, beta = np.linalg.solve(design.T @ (weights[:, None] * design), design.T @ (weights * y))
    residual = y - alpha - beta * x
    expected_sigma = math.sqrt(np.mean(residual * residual / x) * 250)
    assert row["a"] == pytest.approx(-beta * 250, rel=1e-9)
    assert row["b"] == pytest.approx(-alpha / beta, rel=1e-9)
    assert row["sigma"] == pytest.approx(expected_sigma, rel=1e-11)


def test_auxiliary_cir_worksheet_saved_b_differs_from_canonical_model_fit():
    from hullkit._short_rate_models import cir_bond

    aP = 0.200688493067
    bP = 0.024675993141
    s = 0.077192937618
    result = model().fit_cir_risk_price(0.003, aP, bP, s, TIMES, MARKET)
    assert result["risk_price"] == pytest.approx(-0.262302956570, abs=2e-6)
    assert result["sse"] == pytest.approx(3.3036449157e-6, rel=1e-7)
    saved_k = -0.026596672649
    aq = aP + saved_k * s
    bq = aP * bP / aq
    t = 0.5
    g = math.sqrt(aq * aq + 2 * s * s)
    wrong_B = 2 * math.expm1(g * t) / ((g + aq) * math.exp(g * t - 1) + 2 * g)
    canonical_B = cir_bond(0.003, aq, bq, s, t)["B"]
    assert wrong_B == pytest.approx(0.381833613511, abs=1e-10)
    assert canonical_B == pytest.approx(0.475860135328, abs=1e-10)
    assert abs(wrong_B - canonical_B) > 0.09


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.fit_vasicek_series([0.03, 0.04], 0.004),
        lambda m: m.fit_vasicek_series([0.03, 0.04, 0.05], 0),
        lambda m: m.fit_cir_euler_series([0, 0.01, 0.02], 0.004),
        lambda m: m.fit_vasicek_risk_price(0.003, 0, 0.03, 0.01, TIMES, MARKET),
    ],
)
def test_invalid_statistical_domain_rejected(call):
    with pytest.raises(ValueError):
        call(model())
