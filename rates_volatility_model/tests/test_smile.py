import numpy as np
import pytest
from ratesvol.smile import (
    calibrate_sabr,
    calibrate_svi,
    delta_strike,
    sabr_alpha_from_atm_vol,
    sabr_black_vol,
    smile_metrics,
    svi_density_g,
    svi_total_variance,
)
from scipy.stats import norm

# Golden values: identical to machine precision with the independent implementation
# hullkit.sabr.sabr_implied_vol (johnhull/hullkit), checked 2026-09-27.
GOLDEN = [
    ((0.03, 0.02, 1.0, 0.02, 0.5, -0.3, 0.4), 0.16976693425780964),
    ((0.03, 0.03, 1.0, 0.02, 0.5, -0.3, 0.4), 0.11661784596633339),
    ((0.03, 0.045, 5.0, 0.01, 0.5, -0.2, 0.5), 0.09900176371397934),
    ((0.05, 0.04, 2.0, 0.25, 1.0, -0.5, 0.3), 0.265763885941224),
]


@pytest.mark.parametrize("args,expected", GOLDEN)
def test_sabr_matches_golden_values(args, expected):
    assert sabr_black_vol(*args) == pytest.approx(expected, rel=1e-12)


def test_sabr_lognormal_without_volvol_is_flat_at_alpha():
    for K in [0.01, 0.03, 0.06]:
        assert sabr_black_vol(0.03, K, 2.0, 0.2, 1.0, 0.0, 0.0) == pytest.approx(0.2, rel=1e-12)


def test_sabr_is_continuous_at_the_money():
    F = 0.03
    atm = sabr_black_vol(F, F, 1.0, 0.02, 0.5, -0.3, 0.4)
    assert sabr_black_vol(F, F * (1 + 1e-7), 1.0, 0.02, 0.5, -0.3, 0.4) == pytest.approx(
        atm, rel=1e-6
    )


def test_sabr_alpha_from_atm_vol_round_trips():
    alpha = sabr_alpha_from_atm_vol(0.03, 1.0, 0.2, 0.5, -0.3, 0.4)
    assert sabr_black_vol(0.03, 0.03, 1.0, alpha, 0.5, -0.3, 0.4) == pytest.approx(0.2, abs=1e-10)


def test_sabr_alpha_from_atm_vol_uses_the_first_positive_root():
    # Hagan ATM vol bends down at large alpha; the endpoint at alpha=10 has the wrong sign.
    alpha = sabr_alpha_from_atm_vol(0.03, 1.0, 0.2, 1.0, -0.9, 1.0)
    assert alpha == pytest.approx(0.2141561015478571, abs=1e-10)
    assert sabr_black_vol(0.03, 0.03, 1.0, alpha, 1.0, -0.9, 1.0) == pytest.approx(0.2)


def test_sabr_alpha_from_atm_vol_returns_nan_when_target_is_unattainable():
    # At beta=1, rho=-0.9, nu=2, the ATM approximation peaks below 60%.
    assert np.isnan(sabr_alpha_from_atm_vol(0.03, 1.0, 0.6, 1.0, -0.9, 2.0))


def test_sabr_calibration_recovers_noise_free_parameters():
    F, T = 0.031, 1.0
    strikes = F + np.arange(-100, 101, 25) / 1e4
    vols = np.array([sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45) for K in strikes])
    alpha, rho, nu, rmse_bp, _ = calibrate_sabr(F, T, strikes, vols, 0.5)
    assert (alpha, rho, nu) == pytest.approx((0.014, -0.45, 0.45), abs=2e-3)
    assert rmse_bp < 0.1


def test_svi_g_matches_finite_differences():
    p = (0.04, 0.4, -0.4, 0.0, 0.1)
    k = np.linspace(-1.5, 1.5, 301)
    h = 1e-5
    w = svi_total_variance(k, *p)
    w1 = (svi_total_variance(k + h, *p) - svi_total_variance(k - h, *p)) / (2 * h)
    w2 = (svi_total_variance(k + h, *p) - 2 * w + svi_total_variance(k - h, *p)) / h**2
    g_fd = (1 - k * w1 / (2 * w)) ** 2 - w1**2 / 4 * (1 / w + 0.25) + w2 / 2
    assert np.max(np.abs(svi_density_g(k, *p) - g_fd)) < 1e-4


def test_svi_vogt_example_has_butterfly_arbitrage_despite_slope_bound():
    # Gatheral-Jacquier (2014) / Axel Vogt: satisfies b(1+|rho|) < 4 but g(k) < 0 somewhere
    vogt = (-0.0410, 0.1331, 0.3060, 0.3586, 0.4153)
    assert vogt[1] * (1 + abs(vogt[2])) < 4
    assert svi_density_g(np.linspace(-1.5, 1.5, 3001), *vogt).min() < 0


def test_svi_calibration_is_arbitrage_free_and_close():
    F, T = 0.031, 1.0
    strikes = F * np.exp(np.linspace(-0.4, 0.4, 9))
    vols = np.array([sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45) for K in strikes])
    params, rmse_bp, _ = calibrate_svi(F, T, strikes, vols)
    assert rmse_bp < 10
    assert svi_density_g(np.linspace(-1.5, 1.5, 301), *params).min() >= 0


def test_delta_strike_uses_the_smile_vol():
    F, T = 0.031, 1.0

    def smile(K):
        return sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45)

    K = delta_strike(F, T, smile, 0.25)
    s = smile(K)
    assert norm.cdf((np.log(F / K) + 0.5 * s**2 * T) / (s * np.sqrt(T))) == pytest.approx(
        0.25, abs=1e-8
    )


def test_flat_smile_has_zero_risk_reversal_and_butterfly():
    atm, rr, bf = smile_metrics(0.03, 1.0, lambda K: 0.2)
    assert (atm, rr, bf) == pytest.approx((0.2, 0.0, 0.0), abs=1e-12)


def test_smile_metrics_return_nan_when_delta_cannot_be_bracketed():
    atm, rr, bf = smile_metrics(
        0.034, 10.0, lambda K: sabr_black_vol(0.034, K, 10.0, 0.039, 1.0, 0.9, 1.5)
    )
    assert np.isfinite(atm) and np.isnan(rr) and np.isnan(bf)
