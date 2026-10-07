"""Hull §25.5 contract settings; illustrative Black prices independently integrated."""

import math

import numpy as np
import pytest
from hullkit import _credit_contracts as c
from scipy.integrate import quad
from scipy.stats import norm


def test_source_one_year_start_five_year_protection_280bp_forward_obligation():
    contract = c.forward_cds_contract(0.02, 0.4, 0.05, 1, 6, 0.028, frequency=4)
    assert contract["start"] == 1
    assert contract["maturity"] - contract["start"] == 5
    assert contract["contract_spread"] == 0.028
    assert contract["buyer_value"] < 0
    at_par = c.forward_cds_contract(0.02, 0.4, 0.05, 1, 6, contract["forward_spread"], frequency=4)
    assert at_par["buyer_value"] == pytest.approx(0, abs=1e-14)


def test_black_knockout_option_against_logspread_payoff_integral_and_parity():
    # Source has no price/vol; .02 hazard/.05 rate/.35 vol are illustrative inputs.
    result = c.cds_option_value(0.02, 0.4, 0.05, 1, 6, 0.028, 0.35, frequency=4)
    forward, annuity, sd = result["forward_spread"], result["risky_annuity"], 0.35
    threshold = (math.log(0.028 / forward) + 0.5 * sd * sd) / sd

    def spread(z):
        return forward * math.exp(-0.5 * sd * sd + sd * z)

    payer = annuity * quad(lambda z: (spread(z) - 0.028) * norm.pdf(z), threshold, 12)[0]
    receiver = annuity * quad(lambda z: (0.028 - spread(z)) * norm.pdf(z), -12, threshold)[0]
    assert result["payer"] == pytest.approx(payer, rel=1e-10)
    assert result["receiver"] == pytest.approx(receiver, rel=1e-10)
    assert result["payer"] - result["receiver"] == pytest.approx(annuity * (forward - 0.028))
    zero = c.cds_option_value(0.02, 0.4, 0.05, 1, 6, 0.028, 0, frequency=4)
    assert zero["receiver"] == pytest.approx(annuity * max(0.028 - forward, 0))


def test_early_default_knockout_and_payer_receiver_exercise_direction():
    defaults = [0.5, 2, 2]
    spreads = [0.04, 0.04, 0.02]
    payer = c.knockout_spread_payoff(defaults, 1, spreads, 0.028, 4, kind="payer")
    receiver = c.knockout_spread_payoff(defaults, 1, spreads, 0.028, 4, kind="receiver")
    obligation = c.knockout_spread_payoff(defaults, 1, spreads, 0.028, 4, kind="forward")
    assert payer == pytest.approx([0, 0.048, 0])
    assert receiver == pytest.approx([0, 0, 0.032])
    assert obligation == pytest.approx(payer - receiver)
    assert np.all(payer >= 0)


@pytest.mark.parametrize("volatility", [np.nan, np.inf, -np.inf, -0.1])
def test_review_r7_rejects_nonfinite_or_negative_external_option_volatility(volatility):
    with pytest.raises(ValueError, match="volatility"):
        c.cds_option_value(0.02, 0.4, 0.05, 1, 6, 0.028, volatility)
