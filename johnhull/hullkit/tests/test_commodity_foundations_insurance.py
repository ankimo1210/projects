"""Hull §35.6 indemnity, writer signs and independent dollar ledgers."""

import numpy as np
import pytest
from hullkit import _commodity_foundations as c


def test_source_proportional_and_layer_amounts():
    assert c.proportional_reinsurance(100e6, 0.7)["retained_loss"] == pytest.approx(30e6)
    assert c.proportional_reinsurance(50e6, 0.7)["retained_loss"] == pytest.approx(15e6)
    layer = c.reinsurance_layer(50e6, 30e6, 10e6)
    assert layer["indemnity"] == pytest.approx(10e6)
    assert c.cat_bond_principal(10e6, 50e6, 30e6)["remaining_principal"] == pytest.approx(0)


def test_independent_layer_cases_spread_and_insurer_investor_conservation():
    losses = np.array([0, 20, 30, 35, 40, 50]) * 1e6
    hand = np.array([0, 0, 0, 5, 10, 10]) * 1e6
    a = c.reinsurance_layer(losses, 30e6, 10e6, premium=1e6)
    spread = np.maximum(losses - 30e6, 0) - np.maximum(losses - 40e6, 0)
    assert a["indemnity"] == pytest.approx(hand)
    assert a["indemnity"] == pytest.approx(spread)
    assert a["buyer_net"] + a["writer_net"] == pytest.approx(np.zeros(6))
    assert a["retained_loss"] + a["indemnity"] == pytest.approx(losses)
    bond = c.cat_bond_principal(10e6, losses, 30e6)
    assert bond["remaining_principal"] + bond["released_principal"] == pytest.approx(
        np.full(6, 10e6)
    )
    p = c.proportional_reinsurance(losses, 0.7)
    assert p["retained_loss"] + p["ceded_loss"] == pytest.approx(losses)
