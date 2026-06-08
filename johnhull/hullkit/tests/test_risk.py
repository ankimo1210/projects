"""Tests for hullkit.risk against Hull 11e Ch.22 examples."""

import math

import numpy as np
import pytest
from hullkit import risk
from scipy.stats import norm


def test_hull_microsoft_att_example():
    # $10M Microsoft sigma=2%/day -> 10-day 99% VaR = 1,471,311 (Hull 1,471,300)
    v_ms = risk.normal_var(200_000.0, alpha=0.99, horizon=10.0)
    assert v_ms == pytest.approx(1_471_311.0, abs=5.0)
    # $5M AT&T sigma=1%/day -> 367,828 (Hull 367,800)
    v_att = risk.normal_var(50_000.0, alpha=0.99, horizon=10.0)
    assert v_att == pytest.approx(367_828.0, abs=5.0)
    # portfolio rho=0.3 -> sigma_P = 220,227, VaR = 1,620,140 (Hull 1,620,100)
    sig_p = risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, 0.3], [0.3, 1.0]])
    assert sig_p == pytest.approx(220_227.0, abs=5.0)
    v_p = risk.normal_var(sig_p, alpha=0.99, horizon=10.0)
    assert v_p == pytest.approx(1_620_114.0, abs=10.0)
    assert v_ms + v_att - v_p == pytest.approx(219_026.0, abs=20.0)  # diversification


def test_normal_es_exceeds_var():
    sigma = 200_000.0
    var_1d = risk.normal_var(sigma)
    es_1d = risk.normal_es(sigma)
    # ES/sigma = phi(z)/(1-alpha) = 2.6652 for alpha=0.99
    assert es_1d / sigma == pytest.approx(norm.pdf(norm.ppf(0.99)) / 0.01, abs=1e-9)
    assert es_1d > var_1d


def test_sqrt_horizon_scaling():
    sigma = 123_456.0
    assert risk.normal_var(sigma, horizon=10.0) == pytest.approx(
        math.sqrt(10.0) * risk.normal_var(sigma, horizon=1.0), abs=1e-9
    )
    assert risk.normal_es(sigma, horizon=10.0) == pytest.approx(
        math.sqrt(10.0) * risk.normal_es(sigma, horizon=1.0), abs=1e-9
    )


def test_historical_var_es_hull_convention():
    # 500 scenarios: P&L = -1..-500 shuffled; 99% -> k=5: VaR = 5th worst = 496
    pnl = -np.arange(1.0, 501.0)
    rng = np.random.default_rng(0)
    rng.shuffle(pnl)
    var, es = risk.historical_var_es(pnl, alpha=0.99)
    assert var == pytest.approx(496.0, abs=1e-12)
    assert es == pytest.approx(np.mean([496.0, 497.0, 498.0, 499.0, 500.0]), abs=1e-12)
    assert es > var


def test_historical_small_sample_k_floor():
    var, es = risk.historical_var_es([-1.0, -2.0, -3.0, 4.0], alpha=0.99)
    assert var == pytest.approx(3.0)
    assert es == pytest.approx(3.0)


def test_portfolio_sigma_single_asset_reduces():
    assert risk.portfolio_sigma([10e6], [0.02], [[1.0]]) == pytest.approx(200_000.0)
