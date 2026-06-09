"""Tests for hullkit.mc pricing extensions (Hull 11e Ch.21/27)."""

import numpy as np
import pytest
from hullkit import bsm, mc, trees

AM = dict(S0=50.0, K=50.0, r=0.10, sigma=0.40, T=5.0 / 12.0)


def test_european_mc_within_3se_and_se_positive():
    target = bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)
    price, se = mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, n_paths=200_000)
    assert se > 0.0
    assert abs(price - target) < 3.0 * se


def test_antithetic_reduces_se():
    kwargs = dict(S0=100.0, K=100.0, r=0.05, sigma=0.2, T=1.0, n_paths=100_000)
    _, se_plain = mc.price_european_mc(**kwargs, rng=np.random.default_rng(1))
    _, se_anti = mc.price_european_mc(**kwargs, antithetic=True, rng=np.random.default_rng(1))
    assert se_anti < se_plain


def test_mc_put_and_kind_validation():
    target = bsm.put_price(100.0, 110.0, 0.05, 0.3, 0.5)
    price, se = mc.price_european_mc(100.0, 110.0, 0.05, 0.3, 0.5, kind="put", n_paths=200_000)
    assert abs(price - target) < 3.0 * se
    with pytest.raises(ValueError):
        mc.price_european_mc(100.0, 100.0, 0.05, 0.2, 1.0, kind="cal")


def test_lsm_american_put_matches_crr():
    ref = trees.crr_price(**AM, N=500, kind="put", american=True)
    got = mc.price_american_lsm(**AM, kind="put", n_steps=50, n_paths=100_000)
    assert got == pytest.approx(ref, abs=5e-2)
    # early-exercise premium nonnegative (within MC noise)
    eu = bsm.put_price(AM["S0"], AM["K"], AM["r"], AM["sigma"], AM["T"])
    assert got > eu - 5e-2


def test_lsm_deterministic_default_seed():
    a = mc.price_american_lsm(**AM, n_steps=20, n_paths=20_000)
    b = mc.price_american_lsm(**AM, n_steps=20, n_paths=20_000)
    assert a == b


def test_lsm_respects_intrinsic_lower_bound():
    # Deep-ITM American put must be worth at least its immediate-exercise value
    price = mc.price_american_lsm(
        40.0, 100.0, 0.05, 0.30, 0.5, kind="put", n_steps=50, n_paths=50_000
    )
    assert price >= 100.0 - 40.0  # intrinsic = 60, no-arbitrage lower bound
