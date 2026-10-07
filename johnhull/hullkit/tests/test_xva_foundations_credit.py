"""Hull §9.1 conditional loss sum and historical rate-offset arithmetic."""

import math

import numpy as np
import pytest
from hullkit import _xva_foundations as x
from scipy.integrate import quad


def test_source_both_credit_rate_offsets():
    assert x.credit_rate_offsets(0.022, 0.021, 0.0235) == pytest.approx([10, 15])


def test_independent_hazard_integral_and_seeded_default_cash():
    h, r, t, ee, lgd = 0.02, 0.03, 5, 100, 0.6
    nodes = np.linspace(0, t, 1001)
    mid = (nodes[:-1] + nodes[1:]) / 2
    q = np.exp(-h * nodes[:-1]) - np.exp(-h * nodes[1:])
    losses = ee * lgd * np.exp(-r * mid)
    a = x.credit_adjustments(q, losses)
    exact = quad(lambda u: ee * lgd * h * math.exp(-(h + r) * u), 0, t)[0]
    assert a["cva"] == pytest.approx(exact, rel=1e-7)
    defaults = np.random.default_rng(901).exponential(1 / h, 300000)
    cash = ee * lgd * np.exp(-r * defaults) * (defaults < t)
    se = np.std(cash, ddof=1) / math.sqrt(len(cash))
    assert abs(cash.mean() - a["cva"]) < 6 * se


def test_independent_conditional_loss_ledger_and_perspective_reversal():
    q = [0.01, 0.02]
    loss = [100, 200]
    ownq = [0.02, 0.03]
    ownloss = [50, 100]
    a = x.credit_adjustments(
        q, loss, own_default_probs=ownq, own_losses=ownloss, risk_free_value=10
    )
    assert a["adjusted_value"] == pytest.approx(10 - (1 + 4) + (1 + 3))
    opposite = x.credit_adjustments(
        ownq, ownloss, own_default_probs=q, own_losses=loss, risk_free_value=-10
    )
    assert [opposite["cva"], opposite["dva"], opposite["adjusted_value"]] == pytest.approx(
        [a["dva"], a["cva"], -a["adjusted_value"]]
    )
