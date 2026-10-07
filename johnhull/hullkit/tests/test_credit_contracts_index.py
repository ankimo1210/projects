"""Hull §25.3 source index payments and annuity-weighted index spread."""

import math

import numpy as np
import pytest
from hullkit import _credit_contracts as c
from scipy.optimize import brentq


def test_source_index_four_arithmetic_values():
    ask = c.index_premium(800000, 0.0066, 125)
    bid = c.index_premium(800000, 0.0065, 125)
    after = c.index_premium(800000, 0.0066, 125, defaults=1)
    assert ask["annual_payment"] == 660000
    assert bid["annual_payment"] == 650000
    assert ask["annual_payment"] - after["annual_payment"] == 5280
    assert (0.1 + 0.001) / 2 * 10000 == pytest.approx(505)


def test_index_weighted_spread_against_default_state_zero_npv():
    hazards = [
        c.calibrated_cds(quote, 0.4, 0.05, 5, frequency=4)["hazard"] for quote in [0.1, 0.001]
    ]
    result = c.cds_index_value(hazards, [0.4, 0.4], [1, 1], 0.05, 5, frequency=4)

    def independent_legs(hazard):
        annuity, protection = 0, 0
        for period in range(1, 21):
            end = period / 4
            mid = end - 0.125
            pd = math.exp(-hazard * (end - 0.25)) - math.exp(-hazard * end)
            paid = sum(0.25 * math.exp(-0.05 * j / 4) for j in range(1, period))
            annuity += pd * (paid + 0.125 * math.exp(-0.05 * mid))
            protection += pd * 0.6 * math.exp(-0.05 * mid)
        annuity += math.exp(-hazard * 5) * sum(0.25 * math.exp(-0.05 * j / 4) for j in range(1, 21))
        return annuity, protection

    legs = [independent_legs(h) for h in hazards]
    root = brentq(
        lambda spread: sum(protection - spread * annuity for annuity, protection in legs), 0, 0.1
    )
    assert result["par_spread"] == pytest.approx(root, abs=1e-12)
    assert result["par_spread"] < 0.0505
    assert result["annuity_weights"].sum() == pytest.approx(1)
    assert result["annuity_weights"][0] < 0.5


def test_index_notional_weighting_and_contract_value_sign():
    result = c.cds_index_value([0.02, 0.04], [0.4, 0.5], [2, 1], 0.05, 5, contract_spread=0.01)
    protection = sum(
        n * c.cds_leg_table(h, r, 0.05, 5, frequency=4)["protection"]
        for n, h, r in zip([2, 1], [0.02, 0.04], [0.4, 0.5], strict=True)
    )
    assert result["protection"] == pytest.approx(protection)
    assert result["buyer_value"] > 0
    assert np.all(result["annuity_weights"] >= 0)
