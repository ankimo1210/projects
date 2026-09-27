import numpy as np
import pytest
from ratesvol.short_rate import (
    calibrate_vasicek,
    cir_simulate,
    feller_condition,
    g2pp_simulate,
    hw1f_simulate,
    hw1f_theta,
    mc_zcb_from_short_rate,
    vasicek_simulate,
    vasicek_terminal_moments,
    vasicek_zcb,
    vasicek_zero_rate,
)

T_GRID = np.linspace(0, 10, 201)
Z_MKT = 0.02 + 0.03 * (1 - np.exp(-T_GRID / 5))


def market_zcb(T):
    return np.exp(-np.interp(T, T_GRID, Z_MKT) * T)


def test_vasicek_terminal_distribution_matches_theory():
    paths = vasicek_simulate(0.03, 0.15, 0.05, 0.02, 10.0, 100, 20000, np.random.default_rng(0))
    mean, std = vasicek_terminal_moments(0.03, 0.15, 0.05, 0.02, 10.0)
    assert abs(paths[:, -1].mean() - mean) < 4 * std / np.sqrt(20000)
    assert paths[:, -1].std() == pytest.approx(std, rel=0.03)


def test_vasicek_mc_bond_price_matches_closed_form():
    paths = vasicek_simulate(0.03, 0.15, 0.05, 0.02, 5.0, 500, 20000, np.random.default_rng(1))
    price, se = mc_zcb_from_short_rate(paths, 5.0)
    assert abs(price - vasicek_zcb(0.03, 0.15, 0.05, 0.02, 5.0)) < 4 * se


def test_vasicek_calibration_refits_its_own_curve():
    T = np.linspace(0.5, 10, 20)
    target = vasicek_zero_rate(0.025, 0.3, 0.045, 0.01, T)
    _, rmse_bp = calibrate_vasicek(T, target)
    assert rmse_bp < 0.5


def test_cir_is_non_negative_and_mean_reverts():
    paths = cir_simulate(0.03, 0.15, 0.05, 0.02, 10.0, 200, 20000, np.random.default_rng(2))
    mean_th = 0.05 + (0.03 - 0.05) * np.exp(-1.5)
    assert paths.min() >= 0.0
    assert abs(paths[:, -1].mean() - mean_th) < 4 * paths[:, -1].std() / np.sqrt(20000)


def test_feller_condition():
    assert feller_condition(0.15, 0.05, 0.02)
    assert not feller_condition(0.1, 0.02, 0.1)


def test_hw1f_theta_has_the_right_sign():
    # the previous notebook flipped the sign of df/dt; for this upward curve theta must be > 0
    assert np.all(hw1f_theta(T_GRID, Z_MKT, 0.1, 0.01) > 0)


@pytest.mark.parametrize("T", [2.0, 5.0, 10.0])
def test_hw1f_reprices_the_initial_curve(T):
    paths = hw1f_simulate(
        T_GRID, Z_MKT, 0.1, 0.01, T, int(T * 100), 20000, np.random.default_rng(3)
    )
    price, se = mc_zcb_from_short_rate(paths, T)
    assert abs(price - market_zcb(T)) < 4 * se


@pytest.mark.parametrize("T", [2.0, 5.0, 10.0])
def test_g2pp_reprices_the_initial_curve(T):
    _, _, r = g2pp_simulate(
        T_GRID,
        Z_MKT,
        0.1,
        0.03,
        0.01,
        0.005,
        -0.5,
        T,
        int(T * 100),
        20000,
        np.random.default_rng(4),
    )
    price, se = mc_zcb_from_short_rate(r, T)
    assert abs(price - market_zcb(T)) < 4 * se


def test_g2pp_starts_on_the_curve():
    _, _, r = g2pp_simulate(
        T_GRID, Z_MKT, 0.1, 0.03, 0.01, 0.005, -0.5, 1.0, 10, 5, np.random.default_rng(5)
    )
    assert np.allclose(r[:, 0], Z_MKT[0] + 0.0, atol=1e-4)


def test_cir_stays_non_negative_when_feller_fails():
    paths = cir_simulate(0.01, 0.1, 0.02, 0.1, 5.0, 200, 5000, np.random.default_rng(6))
    assert paths.min() == 0.0  # zero is reached...
    assert (paths >= 0).all()  # ...but never crossed
