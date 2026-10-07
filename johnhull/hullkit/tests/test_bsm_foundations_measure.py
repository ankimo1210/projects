"""Hull GE 15.7: Q valuation, physical expectation contrast and replication."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest
from hullkit import _bsm_foundations as foundations
from hullkit.sde import euler_maruyama
from scipy.integrate import quad
from scipy.stats import lognorm


@pytest.mark.parametrize("mu", [-0.2, 0.1, 0.4])
def test_source_q_forward_identity_against_independent_p_and_q_integrals(mu):
    s, k, r, sigma, t = 42, 40, 0.05, 0.3, 0.5
    discount = math.exp(-r * t)
    density_q = lognorm(s=sigma * math.sqrt(t), scale=s * math.exp((r - sigma**2 / 2) * t))
    density_p = lognorm(s=sigma * math.sqrt(t), scale=s * math.exp((mu - sigma**2 / 2) * t))
    q_value = discount * quad(lambda x: (x - k) * density_q.pdf(x), 0, math.inf)[0]
    wrong_p_value = discount * quad(lambda x: (x - k) * density_p.pdf(x), 0, math.inf)[0]
    assert foundations.forward_contract_value(s, k, r, t) == pytest.approx(q_value, abs=1e-9)
    assert discount * (
        foundations.stock_distribution(s, mu, sigma, t)["price_mean"] - k
    ) == pytest.approx(wrong_p_value, abs=1e-9)
    assert wrong_p_value - q_value == pytest.approx(s * (math.exp((mu - r) * t) - 1), abs=1e-9)
    assert abs(wrong_p_value - q_value) > 0.1


def test_q_forward_price_against_independent_stock_euler_mc():
    s, k, r, sigma, t = 42, 40, 0.05, 0.3, 0.5
    terminal = euler_maruyama(
        lambda x, time: r * x,
        lambda x, time: sigma * x,
        s,
        t,
        500,
        30000,
        rng=np.random.default_rng(157),
    )[:, -1]
    discounted = math.exp(-r * t) * (terminal - k)
    assert abs(
        discounted.mean() - foundations.forward_contract_value(s, k, r, t)
    ) < 6 * discounted.std(ddof=1) / math.sqrt(len(discounted))


def test_forward_against_independent_decimal_stock_and_bank_replication():
    with localcontext() as context:
        context.prec = 40
        s, k, r, t = Decimal(42), Decimal(40), Decimal(".05"), Decimal(".5")
        bank_initial = -k * (-r * t).exp()
        initial_cost = s + bank_initial
        bank_terminal = bank_initial * (r * t).exp()
        for terminal_stock in [Decimal(10), Decimal(40), Decimal(80)]:
            assert float(terminal_stock + bank_terminal) == pytest.approx(
                float(terminal_stock - k), abs=1e-12
            )
    assert foundations.forward_contract_value(42, 40, 0.05, 0.5) == pytest.approx(
        float(initial_cost), abs=1e-12
    )
