"""Tests for hullkit.trees against Hull 11e Ch.13 examples."""

import math

import pytest
from hullkit import bsm, trees


def test_one_step_call_hull_13_1_global_edition():
    # 11e Global Edition (the PDF in johnhull/): S0=20, u=1.1, d=0.9, K=21, r=4%,
    # T=3 months -> p=0.5503, f=0.545, delta=0.25
    stock, option = trees.binomial_tree(20.0, 21.0, 0.04, 0.25, 1, u=1.1, d=0.9)
    assert stock[1][0] > stock[1][1]  # j=0 is the up node
    p = (math.exp(0.04 * 0.25) - 0.9) / (1.1 - 0.9)
    assert p == pytest.approx(0.5503, abs=5e-5)
    assert option[0][0] == pytest.approx(0.545, abs=5e-4)
    assert trees.tree_delta(stock, option) == pytest.approx(0.25, abs=1e-12)


def test_two_step_call_hull_fig_13_4_global_edition():
    # GE Figure 13.4 (r=4%): node B 1.7433, root 0.9497; deltas 0.4358 and 0.7273 (§13.6)
    stock, option = trees.binomial_tree(20.0, 21.0, 0.04, 0.5, 2, u=1.1, d=0.9)
    assert option[1][0] == pytest.approx(1.7433, abs=5e-5)
    assert option[0][0] == pytest.approx(0.9497, abs=5e-5)
    first_step_delta = (option[1][0] - option[1][1]) / (stock[1][0] - stock[1][1])
    second_step_delta = (option[2][0] - option[2][1]) / (stock[2][0] - stock[2][1])
    assert first_step_delta == pytest.approx(0.4358, abs=5e-5)
    assert second_step_delta == pytest.approx(0.7273, abs=5e-5)


def test_one_and_two_step_call_us_edition_classic():
    # The US-edition classic uses r=12% (f=0.633, two-step 1.2823); vol 01 teaches it
    # alongside the Global Edition values above.
    _, one = trees.binomial_tree(20.0, 21.0, 0.12, 0.25, 1, u=1.1, d=0.9)
    _, two = trees.binomial_tree(20.0, 21.0, 0.12, 0.5, 2, u=1.1, d=0.9)
    assert one[0][0] == pytest.approx(0.633, abs=5e-4)
    assert two[0][0] == pytest.approx(1.2823, abs=5e-4)


def test_american_put_hull_fig_13_8():
    # European 4.1927 / American 5.0896 (Hull prints 4.1923 / 5.0894 from rounded p)
    _, eu = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put")
    _, am = trees.binomial_tree(50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8, kind="put", american=True)
    assert eu[0][0] == pytest.approx(4.1927, abs=1e-3)
    assert am[0][0] == pytest.approx(5.0896, abs=1e-3)
    assert am[0][0] > eu[0][0]  # early-exercise premium


def test_crr_converges_to_bsm():
    price = trees.crr_price(100.0, 100.0, 0.05, 0.20, 1.0, 500)
    target = bsm.call_price(100.0, 100.0, 0.05, 0.20, 1.0)  # 10.4506
    assert price == pytest.approx(target, abs=1e-2)


def test_crr_american_put_above_european():
    eu = trees.crr_price(100.0, 110.0, 0.05, 0.3, 1.0, 200, kind="put")
    am = trees.crr_price(100.0, 110.0, 0.05, 0.3, 1.0, 200, kind="put", american=True)
    assert am > eu


def test_futures_option_p_equals_one_minus_d_over_u_minus_d():
    # Futures: a=1 -> p=(1-d)/(u-d) (Hull §13.11) — achieved with q=r
    u, d, r, dt = 1.1, 0.9, 0.05, 0.25
    p = trees.risk_neutral_p(u, d, r, dt, q=r)
    assert p == pytest.approx((1.0 - d) / (u - d), abs=1e-12)


def test_risk_neutral_p_bounds_check():
    # d < e^{r dt} < u violated -> ValueError
    with pytest.raises(ValueError):
        trees.risk_neutral_p(1.01, 0.99, 0.50, 1.0)  # e^{0.5}=1.65 > u


def test_crr_params():
    u, d = trees.crr_params(0.3, 0.25)
    assert u == pytest.approx(math.exp(0.3 * 0.5), abs=1e-12)
    assert d == pytest.approx(1.0 / u, abs=1e-12)


def test_invalid_kind_raises():
    with pytest.raises(ValueError):
        trees.binomial_tree(100.0, 100.0, 0.05, 1.0, 2, u=1.1, d=0.9, kind="cal")


# --- input-guard tests ---


def test_binomial_tree_n_zero_raises():
    with pytest.raises(ValueError, match="N must be >= 1"):
        trees.binomial_tree(100.0, 100.0, 0.05, 1.0, 0, u=1.1, d=0.9)


def test_binomial_tree_u_equals_d_raises():
    with pytest.raises(ValueError, match="u and d must differ"):
        trees.binomial_tree(100.0, 100.0, 0.05, 1.0, 2, u=1.0, d=1.0)
