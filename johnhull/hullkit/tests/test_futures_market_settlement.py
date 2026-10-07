"""Hull §2.11 source aggregate gain and independent cash reinvestment."""

import math

import numpy as np
import pytest
from hullkit import _futures_market as f


def test_source_contracts_gain_and_inverse_quote():
    # Only endpoints are printed; intermediate quotes are explicitly synthetic.
    a = f.settlement_timing([1.2, 1.21, 1.17, 1.4], units=1000000, contract_size=62500)
    assert [a["contracts"], a["forward_terminal"], a["futures_terminal"]] == pytest.approx(
        [16, 200000, 200000]
    )
    assert f.inverse_quote(0.75) == pytest.approx(1.3333, abs=5e-5)


def test_independent_cash_ode_between_settlement_knots():
    prices = np.array([1.2, 1.21, 1.17, 1.4])
    times = np.array([0, 0.1, 0.15, 0.25])
    r = 0.08
    a = f.settlement_timing(
        prices, units=1000000, contract_size=62500, deposit_growth=np.exp(r * np.diff(times))
    )
    bank = 0.0
    for i in range(1, len(times)):
        bank *= math.exp(r * (times[i] - times[i - 1]))
        bank += 1000000 * (prices[i] - prices[i - 1])
    assert a["futures_terminal"] == pytest.approx(bank, abs=1e-7)
    assert a["forward_terminal"] == pytest.approx(200000)
    assert abs(bank - 200000) > 1
    assert f.inverse_quote(f.inverse_quote(1.234)) == pytest.approx(1.234)
