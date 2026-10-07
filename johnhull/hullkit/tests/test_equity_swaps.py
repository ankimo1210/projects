import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._equity_swaps")


def test_tn19_simple_known_coupon_replication_and_intermediate_value():
    m = model()
    N = 100.0
    ratio = 1.04
    r0 = 0.05
    original = 0.5
    now = 0.045
    remaining = 0.2
    row = m.tn19_equity_swap(N, ratio, r0, original, now, remaining)
    discount = 1 / (1 + now * remaining)
    equity = quad(
        lambda z: (
            N
            * (
                (ratio / discount)
                * math.exp(-0.5 * 0.2**2 * remaining + 0.2 * math.sqrt(remaining) * z)
                - 1
            )
            * discount
            * norm.pdf(z)
        ),
        -12,
        12,
    )[0]
    funding = N * r0 * original * discount
    assert row["equity_pv"] == pytest.approx(equity, abs=1e-11)
    assert row["funding_pv"] == pytest.approx(funding, abs=1e-12)
    assert row["net_pv"] == pytest.approx(
        N * (ratio - (1 + r0 * original) / (1 + now * remaining)), abs=1e-12
    )
    assert abs(row["equity_pv"] - N * (ratio - 1)) > 0.5


@pytest.mark.parametrize("basis", [0.0, 0.007])
def test_compounded_known_remaining_funding_and_independent_stochastic_replication(basis):
    m = model()
    N = 1e6
    ratio = 1.04
    A = 1.012
    h = 0.25
    r = 0.04
    eta = 0.03
    s = 0.2
    rho = 0.5
    n = 32768
    rng = np.random.default_rng(3442026)
    z = rng.standard_normal((3, n))
    integral = r * h + eta * (0.5 * h * math.sqrt(h) * z[0] + math.sqrt(h**3 / 12) * z[1])
    discount = np.exp(-integral)
    stock_noise = s * math.sqrt(h) * (rho * z[0] + math.sqrt(1 - rho * rho) * z[2])
    terminal_ratio = ratio * np.exp(integral - 0.5 * s * s * h + stock_noise)
    growth = np.exp(integral + basis * h)
    pe = math.exp(-r * h + 0.5 * eta * eta * h**3 / 3)
    forward_growth = math.exp(basis * h) / pe
    row = m.equity_rfr_period(N, ratio, A, pe, forward_growth)
    for key, samples in [
        ("equity_pv", N * discount * (terminal_ratio - 1)),
        ("funding_pv", N * discount * (A * growth - 1)),
        ("net_pv", N * discount * (terminal_ratio - A * growth)),
    ]:
        se = samples.std(ddof=1) / math.sqrt(n)
        assert abs(samples.mean() - row[key]) < 5 * se
    assert row["net_pv"] == pytest.approx(N * (ratio - A * math.exp(basis * h)), abs=1e-9)
    if basis == 0:
        assert row["net_pv"] == pytest.approx(N * (ratio - A), abs=1e-9)
    wrong_funding = N * pe * ((A - 1) + (forward_growth - 1))
    assert abs(row["funding_pv"] - wrong_funding) > 100


def test_total_return_dividend_reinvestment_and_reset_pending_receivable():
    m = model()
    row = m.total_return_index([100, 98, 102], [0, 2, 0])
    assert row["indices"] == pytest.approx([100, 100, 102 * 100 / 98], abs=1e-12)
    assert row["indices"][-1] / 100 - 1 > 0.02
    paid = m.equity_reset(1e8, 100, 104, 1.01, settled=True)
    waiting = m.equity_reset(1e8, 100, 104, 1.01, settled=False)
    assert paid["net_cash"] == pytest.approx(3e6, abs=1e-7)
    assert paid["pending_net_cash"] == pytest.approx(0)
    assert waiting["pending_net_cash"] == pytest.approx(3e6, abs=1e-7)
    assert paid["new_index_units"] == pytest.approx(1e8 / 104, abs=1e-7)
    assert paid["new_known_accumulation"] == pytest.approx(1)


def test_reset_zero_condition_future_tails_and_lag_explicit_discounted_ratio():
    m = model()
    N = 1e6
    h = 0.25
    pd = math.exp(-0.04 * h)
    assert m.equity_rfr_period(N, 1, 1, pd, 1 / pd)["net_pv"] == pytest.approx(0, abs=1e-9)
    basis = m.equity_rfr_period(N, 1, 1, pd, math.exp(0.047 * h))
    assert basis["net_pv"] < 0
    tails = m.future_reset_periods(N, [0.99, 0.98], [0.98, 0.96], [0.99 / 0.98, 0.98 / 0.96])
    assert tails == pytest.approx([0, 0], abs=1e-9)
    lag = 0.01
    ratio = 1.04
    known = 1.012
    paydf = math.exp(-0.04 * (h + lag))
    row = m.equity_rfr_period(
        N,
        ratio,
        known,
        paydf,
        math.exp(0.04 * h),
        discounted_equity_ratio=ratio * math.exp(-0.04 * lag),
    )
    assert row["net_pv"] == pytest.approx(N * math.exp(-0.04 * lag) * (ratio - known), abs=1e-9)
    with pytest.raises(ValueError):
        m.equity_rfr_period(N, ratio, 0, pd, 1 / pd)
