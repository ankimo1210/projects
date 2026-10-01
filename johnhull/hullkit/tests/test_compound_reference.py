"""Conditional payoff integrals independent of Geske's bivariate CDF."""

import importlib

import pytest

KINDS = ("call_on_call", "put_on_call", "call_on_put", "put_on_put")
PINS = (3.2568270197744167, 3.7829206319036883, 1.299803100157501, 4.722821592890913)


def reference():
    return importlib.import_module("johnhull.scripts.build_compound_reference")


@pytest.mark.parametrize("kind,pin", zip(KINDS, PINS, strict=True))
def test_conditional_integral_pins(kind, pin):
    value, error = reference().integrate_compound(100, 10, 100, 0.05, 0.2, 0.5, 1, 0.02, kind)
    assert value == pytest.approx(pin, abs=1e-10)
    assert error < 1e-8


def test_reference_inventory_and_mc_uncertainty():
    data = reference().build()
    assert len(data["cases"]) == 104
    assert len(data["mc"]) == 4
    assert all(row["paths"] == 524288 for row in data["mc"])
    assert all(
        abs(row["price"] - row["reference_price"]) < 6 * row["standard_error"] for row in data["mc"]
    )
    assert any(row["sigma"] == 0 for row in data["cases"])
    assert any(row["T1"] / row["T2"] > 0.999 for row in data["cases"])
    assert any(row["K1"] > row["K2"] for row in data["cases"])


def test_threshold_payoffs_and_curve_limits():
    data = reference().build()
    threshold = data["figure"]["threshold"]
    assert threshold["critical"]["call"] == pytest.approx(105.77296228027585, abs=1e-9)
    assert threshold["critical"]["put"] == pytest.approx(90.73021992506433, abs=1e-9)
    assert threshold["call_on_call"][0] == 0
    assert threshold["call_on_put"][-1] == 0
    strikes = data["figure"]["strikes"]
    assert strikes["call_on_put"][-1] == 0
    assert strikes["put_on_call"][0] == 0
    assert data["figure"]["timing"]["T1"][-1] == 0.9999


def test_near_expiry_inner_transition_is_resolved():
    # Independent review found that a tiny reported QUADPACK error could hide
    # an unresolved inner vanilla transition. Pin its separately split integral.
    value, error = reference().integrate_compound(
        100, 0.01, 100, 0.05, 0.2, 0.999999, 1, 0.02, "put_on_call"
    )
    assert value == pytest.approx(0.004564661869643963, abs=1e-10)
    assert error < 1e-9
