"""P8 independent-unit Monte Carlo checks for R1/R4."""

import math

import numpy as np
import pytest
from hullkit import bsm
from hullkit import surrogate_data as s
from hullkit import zero_dte as z


def cluster_se(values):
    half = (len(values) + 1) // 2
    count = len(values) // 2
    totals = values[:count] + values[half:]
    sizes = np.full(count, 2.0)
    if len(values) % 2:
        totals = np.r_[totals, values[count]]
        sizes = np.r_[sizes, 1.0]
    centered = totals - sizes * values.mean()
    return math.sqrt(len(totals) / (len(totals) - 1) * np.dot(centered, centered)) / len(values)


def test_rbergomi_adapted_variance_and_martingale():
    terminal, variance = s._rbergomi_paths(
        1, 0.03, 1, xi0=0.04, eta=0.6, hurst=0.12, rho=-0.6, n_steps=12, n_paths=100000, seed=801
    )
    assert variance.shape == (100000, 12)
    assert variance[:, 0] == pytest.approx(np.full(100000, 0.04), abs=1e-14)
    for column in range(1, 12):
        values = variance[:, column]
        assert abs(values.mean() - 0.04) <= 6 * cluster_se(values)
    assert abs(terminal.mean() - math.exp(0.03)) < 6 * cluster_se(terminal)


def test_rbergomi_bsm_limit_and_antithetic_cluster_uncertainty():
    config = dict(xi0=0.04, eta=0, hurst=0.12, rho=-0.6, n_steps=12, n_paths=100001, seed=802)
    terminal, _ = s._rbergomi_paths(1, 0.03, 1, **config)
    pay = math.exp(-0.03) * np.maximum(terminal - 1, 0)
    result = s.rbergomi_call_price(1, 1, 0.03, 1, **config)
    assert result.estimate == pytest.approx(pay.mean(), abs=1e-14)
    assert result.standard_error == pytest.approx(cluster_se(pay), abs=1e-14)
    assert abs(result.estimate - bsm.call_price(1, 1, 0.03, 0.2, 1)) < 6 * result.standard_error
    assert result.path_count == 100001


def test_jump_intensity_keeps_the_brownian_path_correspondence():
    config = dict(
        S0=100,
        K=100,
        r=0.01,
        v0=0.04,
        kappa=2,
        theta=0.04,
        vol_of_vol=0.3,
        rho=-0.6,
        jump_mean=0,
        jump_std=0,
        n_paths=2000,
        seed=804,
    )
    base = z.sv_jump_teacher(
        step_year_fractions=np.full(5, 0.01), jump_intensities=np.zeros(5), **config
    )
    bumped = z.sv_jump_teacher(
        step_year_fractions=np.full(5, 0.01), jump_intensities=np.full(5, 200.0), **config
    )
    assert bumped.terminal_spot == pytest.approx(base.terminal_spot, abs=1e-12)
    assert [bumped.price, bumped.delta, bumped.gamma] == pytest.approx(
        [base.price, base.delta, base.gamma], abs=1e-12
    )
