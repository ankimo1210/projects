"""Tests for hullkit.tail_risk: filtered historical simulation and EVT/GPD tail risk."""

import math

import numpy as np
import pytest
from hullkit import risk, tail_risk
from scipy import integrate
from scipy.stats import genpareto


def _synthetic_gpd_losses(xi, beta, threshold, n_exceedances, n_below, seed):
    """Mixed sample: n_exceedances GPD(xi, beta) draws above threshold plus
    n_below draws strictly below it, so n_total != n_exceedances."""
    rng = np.random.default_rng(seed)
    exceed = genpareto.rvs(xi, scale=beta, size=n_exceedances, random_state=rng) + threshold
    below = threshold - rng.exponential(scale=beta, size=n_below) - 1e-6
    losses = np.concatenate([exceed, below])
    rng.shuffle(losses)
    return losses


# --- filtered_historical_var_es --------------------------------------------


def test_fhs_constant_sigma_matches_historical_var_es():
    rng = np.random.default_rng(1)
    returns = rng.standard_normal(500) * 0.01
    sigma = np.full(500, 0.02)
    var_fhs, es_fhs = tail_risk.filtered_historical_var_es(returns, sigma, alpha=0.99)
    var_hist, es_hist = risk.historical_var_es(returns, alpha=0.99)
    assert var_fhs == pytest.approx(var_hist, abs=1e-12)
    assert es_fhs == pytest.approx(es_hist, abs=1e-12)


def test_fhs_current_sigma_scales_homogeneously():
    rng = np.random.default_rng(2)
    returns = rng.standard_normal(500) * 0.01
    sigma = 0.005 + 0.02 * rng.random(500)
    var1, es1 = tail_risk.filtered_historical_var_es(returns, sigma, alpha=0.99, current_sigma=0.03)
    var2, es2 = tail_risk.filtered_historical_var_es(returns, sigma, alpha=0.99, current_sigma=0.06)
    assert var2 == pytest.approx(2.0 * var1, abs=1e-10)
    assert es2 == pytest.approx(2.0 * es1, abs=1e-10)


def test_fhs_default_current_sigma_uses_last():
    rng = np.random.default_rng(3)
    returns = rng.standard_normal(200) * 0.01
    sigma = 0.01 + 0.001 * np.arange(200)
    var_default, es_default = tail_risk.filtered_historical_var_es(returns, sigma, alpha=0.99)
    var_explicit, es_explicit = tail_risk.filtered_historical_var_es(
        returns, sigma, alpha=0.99, current_sigma=sigma[-1]
    )
    assert var_default == pytest.approx(var_explicit, abs=1e-12)
    assert es_default == pytest.approx(es_explicit, abs=1e-12)


def test_fhs_nonpositive_sigma_raises():
    returns = np.array([0.01, -0.02, 0.005])
    with pytest.raises(ValueError):
        tail_risk.filtered_historical_var_es(returns, [0.01, 0.0, 0.01])
    with pytest.raises(ValueError):
        tail_risk.filtered_historical_var_es(returns, [0.01, -0.01, 0.01])


def test_fhs_nan_sigma_raises():
    # A NaN sigma must not slip past `sigma <= 0.0` (False for NaN) -- it
    # would otherwise sort to the tail end and silently displace the true
    # worst-loss scenario, corrupting VaR while ES visibly reports NaN.
    rng = np.random.default_rng(99)
    returns = rng.standard_normal(500) * 0.01
    sigma = np.full(500, 0.02)
    sigma[123] = np.nan
    with pytest.raises(ValueError, match="finite"):
        tail_risk.filtered_historical_var_es(returns, sigma, alpha=0.99)


def test_fhs_length_mismatch_raises():
    with pytest.raises(ValueError):
        tail_risk.filtered_historical_var_es([0.01, 0.02], [0.01])


def test_fhs_nonpositive_current_sigma_raises():
    returns = np.array([0.01, -0.02, 0.005])
    sigma = np.array([0.01, 0.02, 0.01])
    with pytest.raises(ValueError):
        tail_risk.filtered_historical_var_es(returns, sigma, current_sigma=0.0)
    with pytest.raises(ValueError):
        tail_risk.filtered_historical_var_es(returns, sigma, current_sigma=-0.02)


# --- fit_gpd_pot ------------------------------------------------------------


def test_fit_gpd_pot_recovers_parameters():
    xi_true, beta_true = 0.2, 1.0
    threshold = 5.0
    losses = _synthetic_gpd_losses(xi_true, beta_true, threshold, 2000, 8000, seed=7)
    fit = tail_risk.fit_gpd_pot(losses, threshold, min_exceedances=30)
    assert fit.threshold == threshold
    assert fit.n_exceedances == 2000
    assert fit.n_total == 10000
    assert abs(fit.xi - xi_true) <= 0.1
    assert abs(fit.beta / beta_true - 1.0) <= 0.15


def test_fit_gpd_pot_too_few_exceedances_raises():
    losses = np.concatenate([np.full(10, 6.0), np.full(50, 1.0)])
    with pytest.raises(ValueError):
        tail_risk.fit_gpd_pot(losses, threshold=5.0, min_exceedances=30)


def test_fit_gpd_pot_raises_when_optimizer_does_not_converge(monkeypatch):
    class _FailedResult:
        success = False
        message = "did not converge (test double)"
        x = (0.1, 1.0)

    monkeypatch.setattr(tail_risk, "minimize", lambda *args, **kwargs: _FailedResult())

    rng = np.random.default_rng(41)
    losses = rng.exponential(scale=1.0, size=200) + 5.0
    with pytest.raises(ValueError, match="did not converge"):
        tail_risk.fit_gpd_pot(losses, threshold=0.0, min_exceedances=30)


def test_fit_gpd_pot_exponential_limit_recovers_near_zero_xi():
    rng = np.random.default_rng(23)
    threshold = 5.0
    beta_true = 1.0
    exceed = rng.exponential(scale=beta_true, size=2000) + threshold
    below = threshold - rng.exponential(scale=beta_true, size=8000) - 1e-6
    losses = np.concatenate([exceed, below])
    fit = tail_risk.fit_gpd_pot(losses, threshold, min_exceedances=30)
    assert abs(fit.xi) < 0.1
    # exercise evt_var_es without error regardless of which branch the fitted xi lands in
    var, es = tail_risk.evt_var_es(fit, alpha=0.99)
    assert math.isfinite(var)
    assert math.isfinite(es)


# --- evt_var_es --------------------------------------------------------------


def test_evt_var_es_matches_genpareto_ppf_quantile():
    xi_true, beta_true = 0.2, 1.0
    threshold = 5.0
    losses = _synthetic_gpd_losses(xi_true, beta_true, threshold, 2000, 8000, seed=11)
    fit = tail_risk.fit_gpd_pot(losses, threshold, min_exceedances=30)

    alpha = 0.999
    var, es = tail_risk.evt_var_es(fit, alpha=alpha)

    p = 1.0 - alpha
    ratio = (fit.n_total / fit.n_exceedances) * p
    y_quantile = genpareto.ppf(1.0 - ratio, fit.xi, scale=fit.beta)
    expected_var = fit.threshold + y_quantile
    assert var == pytest.approx(expected_var, abs=1e-8)

    expected_es = (var + fit.beta - fit.xi * fit.threshold) / (1.0 - fit.xi)
    assert es == pytest.approx(expected_es, abs=1e-12)


def test_evt_var_es_exponential_branch_formula():
    threshold = 5.0
    n_exceedances = 200
    n_total = 2000
    beta = 1.0
    fit = tail_risk.GPDFit(
        xi=0.0, beta=beta, threshold=threshold, n_exceedances=n_exceedances, n_total=n_total
    )
    alpha = 0.999
    var, es = tail_risk.evt_var_es(fit, alpha=alpha)

    p = 1.0 - alpha
    ratio = (n_total / n_exceedances) * p
    expected_var = threshold + beta * math.log(1.0 / ratio)
    expected_es = expected_var + beta
    assert var == pytest.approx(expected_var, abs=1e-10)
    assert es == pytest.approx(expected_es, abs=1e-10)


def test_evt_var_es_xi_ge_one_raises():
    fit = tail_risk.GPDFit(xi=1.2, beta=1.0, threshold=5.0, n_exceedances=100, n_total=1000)
    with pytest.raises(ValueError):
        tail_risk.evt_var_es(fit, alpha=0.99)


def test_evt_var_es_below_threshold_raises():
    # not extreme enough: implied VaR falls back below the fitted threshold
    fit = tail_risk.GPDFit(xi=0.2, beta=1.0, threshold=5.0, n_exceedances=100, n_total=1000)
    with pytest.raises(ValueError):
        tail_risk.evt_var_es(fit, alpha=0.85)


# --- mean_excess --------------------------------------------------------------


def test_mean_excess_basic():
    losses = np.array([1.0, 2.0, 3.0, 4.0, 10.0])
    thresholds = np.array([0.0, 2.5, 9.0, 20.0])
    result = tail_risk.mean_excess(losses, thresholds)
    assert result[0] == pytest.approx(np.mean(losses))
    assert result[1] == pytest.approx(np.mean([0.5, 1.5, 7.5]))
    assert result[2] == pytest.approx(1.0)
    assert math.isnan(result[3])


def test_mean_excess_gpd_theoretical_slope_matches_formula():
    # Independent quadrature re-derivation of e(u) for a true GPD(xi, beta)
    # (scipy.integrate.quad over genpareto.pdf/sf, not the module's own
    # closed form) -- checks the linear slope xi/(1-xi) claim to high
    # precision, decoupled from any finite-sample noise in mean_excess().
    xi, beta = 0.2, 1.0
    vs = np.array([0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0])

    def exact_e(v):
        num = integrate.quad(lambda y: (y - v) * genpareto.pdf(y, xi, scale=beta), v, np.inf)[0]
        den = genpareto.sf(v, xi, scale=beta)
        return num / den

    es = np.array([exact_e(v) for v in vs])
    slope, _ = np.polyfit(vs, es, 1)
    assert slope == pytest.approx(xi / (1.0 - xi), abs=1e-6)


def test_mean_excess_empirical_slope_consistent_with_gpd_sample():
    xi_true, beta_true = 0.2, 1.0
    rng = np.random.default_rng(31)
    losses = genpareto.rvs(xi_true, scale=beta_true, size=200_000, random_state=rng)
    thresholds = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    e = tail_risk.mean_excess(losses, thresholds)
    assert not np.any(np.isnan(e))
    slope, _ = np.polyfit(thresholds, e, 1)
    assert slope == pytest.approx(xi_true / (1.0 - xi_true), abs=0.05)
