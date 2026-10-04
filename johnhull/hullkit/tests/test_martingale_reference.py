"""Independent source pins: conditional states and one payoff in both measures."""

import importlib

import pytest


def test_signed_cases_conditional_states_and_same_call_price():
    d = importlib.import_module("johnhull.scripts.build_martingale_reference").build()
    assert len(d["cases"]) == 6 and len(d["conditional"]) == 9
    assert d["synthetic"] is True and d["printed_pins"] == []
    for row in d["cases"]:
        assert row["drift"] == pytest.approx(0, abs=1e-15)
        assert row["second_moment"] >= 1.5**2
    for row in d["conditional"]:
        assert row["mean"] == pytest.approx(row["value"])
    for row in d["pricing"]:
        assert row["price"] == pytest.approx(17.24948327902953, abs=1e-12)
    assert d["figure"]["ito"]["values"] == pytest.approx([-0.1, 0.04, 0.06, 0])
