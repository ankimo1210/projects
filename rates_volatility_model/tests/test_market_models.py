import numpy as np
import pytest
from ratesvol.market_models import (
    hjm_drift,
    hjm_simulate,
    lmm_fixings,
    lmm_simulate_spot,
    spot_numeraire,
)
from ratesvol.options import black76_call

# ------------------------------------------------------------------ HJM
T_HJM = np.linspace(0.1, 10, 11)
F0_HJM = 0.02 + 0.03 * (1 - np.exp(-T_HJM / 5))


def flat_vol(t, u):
    return 0.01


def test_hjm_drift_is_integral_from_t_to_maturity():
    # constant sigma: alpha(t,T) = sigma^2 (T - t). The old code integrated from T to T_max.
    alpha = hjm_drift(2.0, T_HJM, flat_vol)
    expected = np.where(T_HJM > 2.0, 1e-4 * (T_HJM - 2.0), 0.0)
    assert np.allclose(alpha, expected, atol=1e-15)


def test_hjm_ho_lee_forward_mean():
    t_grid = np.linspace(0, 5, 26)
    fc = hjm_simulate(T_HJM, F0_HJM, flat_vol, t_grid, 20000, np.random.default_rng(10))
    t, T = 5.0, T_HJM[-1]
    expected = F0_HJM[-1] + 1e-4 * t * (T - t / 2)
    se = fc[:, -1, -1].std() / np.sqrt(20000)
    assert abs(fc[:, -1, -1].mean() - expected) < 4 * se


def test_hjm_freezes_matured_forwards():
    t_grid = np.linspace(0, 5, 26)
    fc = hjm_simulate(T_HJM, F0_HJM, flat_vol, t_grid, 100, np.random.default_rng(11))
    j = 1  # T = 1.09y
    first_after = int(np.searchsorted(t_grid, T_HJM[j]))
    assert np.array_equal(fc[:, first_after, j], fc[:, -1, j])


# ------------------------------------------------------------------ LMM
TENOR = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
L0 = np.array([0.030, 0.032, 0.034, 0.035, 0.036, 0.036])
VOLS = np.array([0.20, 0.19, 0.18, 0.17, 0.16, 0.15])
CORR = np.exp(-0.3 * np.abs(np.subtract.outer(TENOR[:-1], TENOR[:-1])))
TAU = np.diff(TENOR)
P0 = np.cumprod(1 / (1 + TAU * L0))


@pytest.fixture(scope="module")
def lmm_run():
    times, L = lmm_simulate_spot(TENOR, L0, VOLS, CORR, 10, 40000, np.random.default_rng(12))
    fixings = lmm_fixings(times, L, TENOR)
    return times, L, fixings, spot_numeraire(fixings, TENOR)


@pytest.mark.parametrize("n", [2, 4, 6])
def test_lmm_spot_measure_reprices_zero_coupon_bonds(lmm_run, n):
    x = 1 / lmm_run[3][:, n - 1]
    assert abs(x.mean() - P0[n - 1]) < 4 * x.std() / np.sqrt(len(x))


@pytest.mark.parametrize("k", [1, 3, 5])
def test_lmm_caplet_matches_black76(lmm_run, k):
    fixings, B = lmm_run[2], lmm_run[3]
    pay = TAU[k] * np.maximum(fixings[:, k] - L0[k], 0) / B[:, k]
    black = P0[k] * TAU[k] * black76_call(L0[k], L0[k], TENOR[k], VOLS[k])
    assert abs(pay.mean() - black) < 4 * pay.std() / np.sqrt(len(pay))


def test_lmm_freezes_forwards_after_fixing(lmm_run):
    times, L = lmm_run[0], lmm_run[1]
    fix_idx = int(np.argmin(np.abs(times - TENOR[2])))
    assert np.array_equal(L[:, fix_idx, 2], L[:, -1, 2])


def test_lmm_rejects_mismatched_tenors():
    with pytest.raises(ValueError):
        lmm_simulate_spot(TENOR[:-1], L0, VOLS, CORR, 2, 10, np.random.default_rng(0))


def test_lmm_irregular_tenors_reprice_the_last_bond():
    tenor = np.array([0.0, 0.25, 0.5, 1.0, 2.0])
    l0 = np.array([0.03, 0.031, 0.033, 0.035])
    vols = np.array([0.2, 0.2, 0.18, 0.16])
    corr = np.exp(-0.3 * np.abs(np.subtract.outer(tenor[:-1], tenor[:-1])))
    times, paths = lmm_simulate_spot(tenor, l0, vols, corr, 10, 40000, np.random.default_rng(13))
    numeraire = spot_numeraire(lmm_fixings(times, paths, tenor), tenor)
    x = 1 / numeraire[:, -1]
    p0 = np.prod(1 / (1 + np.diff(tenor) * l0))
    assert abs(x.mean() - p0) < 4 * x.std() / np.sqrt(len(x))
