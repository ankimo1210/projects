"""Independent signed-payoff and insurer/policyholder references for §26.4."""

import importlib

import pytest


def _ref():
    return importlib.import_module("johnhull.scripts.build_gap_reference")


def test_printed_insurance_prices_are_integer_dollar_pins():
    example = _ref().build()["example"]
    assert example["ordinary_put"] == pytest.approx(3435.9470199, abs=1e-6)
    assert example["insurer_gap_put"] == pytest.approx(1895.6889444, abs=1e-6)
    assert round(example["ordinary_put"]) == 3436
    assert round(example["insurer_gap_put"]) == 1896
    assert example["reduction_percent"] == pytest.approx(44.8277598, abs=1e-6)


def test_trigger_is_strict_and_signed_payoffs_are_preserved():
    payoff = _ref().gap_payoff
    assert payoff("call", 105, 120, 100) == -15
    assert payoff("put", 95, 80, 100) == -15
    assert payoff("call", 100, 120, 100) == 0
    assert payoff("put", 100, 80, 100) == 0


def test_signed_gap_can_have_negative_price():
    price, error = _ref().integrate_gap("call", 100, 160, 90, 0.05, 0.2, 1)
    assert price < -20
    assert 0 <= error < 1e-7


def test_policyholder_net_and_insurer_payment_differ_by_transfer_cost():
    row = _ref().build()["example"]
    assert row["insurer_gap_put"] > row["policyholder_net_put"] > 0
    assert row["insurer_gap_put"] - row["policyholder_net_put"] == pytest.approx(
        row["discounted_transfer_cost"], abs=1e-8
    )
    hand = row["terminal_hand_check"]
    assert hand[0] == {
        "asset": 340000,
        "insurer": 60000,
        "transfer_cost": 50000,
        "holder_net": 10000,
    }
    assert hand[1] == {"asset": 350000, "insurer": 0, "transfer_cost": 0, "holder_net": 0}
    assert hand[2] == {"asset": 360000, "insurer": 0, "transfer_cost": 0, "holder_net": 0}
