"""Hull Table7.6 and currency comparative borrowing cash."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s


def test_source_all_twenty_four_currency_cash_values():
    a = s.currency_swap_cash(15e6, 10e6, 0.03, 0.04, np.ones(5))
    assert a["domestic"] / 1e6 == pytest.approx([15, -0.45, -0.45, -0.45, -0.45, -15.45])
    assert a["foreign"] / 1e6 == pytest.approx([-10, 0.4, 0.4, 0.4, 0.4, 10.4])
    b = s.currency_comparative_cash(0.05, 0.07, 0.076, 0.08, 0.069, 0.063, 15e6, 20e6)
    assert [
        b[k]
        for k in [
            "domestic_gap",
            "foreign_gap",
            "joint_gain",
            "a_gain",
            "b_gain",
            "dealer_domestic_rate",
            "dealer_foreign_rate",
            "naive_rate_difference",
        ]
    ] == pytest.approx([0.02, 0.004, 0.016, 0.007, 0.007, 0.013, -0.011, 0.002])
    assert [b["dealer_domestic_cash"], b["dealer_foreign_cash"]] == pytest.approx([195000, -220000])
    assert [-b["dealer_foreign_rate"], -b["dealer_foreign_rate"]] == pytest.approx([0.011, 0.011])


def test_independent_external_currency_borrowing_and_principal_symmetry():
    a = s.currency_swap_cash(15e6, 10e6, 0.03, 0.04, np.ones(5))
    assert a["domestic"][0] == pytest.approx(-a["domestic"][-1] - 0.45e6)
    assert a["foreign"][0] == pytest.approx(-a["foreign"][-1] + 0.4e6)
    b = s.currency_comparative_cash(0.05, 0.07, 0.076, 0.08, 0.069, 0.063, 15e6, 20e6)
    usd_received = 15e6 * 0.063
    usd_paid = 15e6 * 0.05
    aud_received = 20e6 * 0.069
    aud_paid = 20e6 * 0.08
    assert b["dealer_domestic_cash"] == pytest.approx(usd_received - usd_paid)
    assert b["dealer_foreign_cash"] == pytest.approx(aud_received - aud_paid)
    opposite = s.currency_swap_cash(15e6, 10e6, 0.03, 0.04, np.ones(5), receive="domestic")
    assert opposite["domestic"] == pytest.approx(-a["domestic"])
    assert opposite["foreign"] == pytest.approx(-a["foreign"])
