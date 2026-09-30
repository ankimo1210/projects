"""§26.4 numerical gate rejects stale and sign-clipped reference values."""

import copy
import importlib

import pytest


def _modules():
    return (
        importlib.import_module("johnhull.scripts.build_gap_reference"),
        importlib.import_module("johnhull.scripts.verify_gap_numerics"),
    )


def test_independent_cases_match_public_gap_api():
    ref, gate = _modules()
    result = gate.verify(ref.build())
    assert result["case_count"] == 30
    assert result["max_price_error"] < 1e-7
    assert result["max_decomposition_error"] < 1e-7
    assert result["max_parity_error"] < 1e-7
    assert result["negative_price_cases"] > 0


@pytest.mark.parametrize("mutation", ["price", "trigger", "insurer_as_holder", "clipped_payoff"])
def test_saved_reference_mutations_are_rejected(mutation):
    ref, gate = _modules()
    data = copy.deepcopy(ref.build())
    if mutation == "price":
        data["cases"][0]["price"] += 1
        data["cases"][1]["price"] += 1
    elif mutation == "trigger":
        data["example"]["K2"] = 400000
    elif mutation == "insurer_as_holder":
        data["example"]["insurer_gap_put"] = data["example"]["policyholder_net_put"]
    else:
        data["figure"]["payoff"]["call"] = [
            max(value, 0) for value in data["figure"]["payoff"]["call"]
        ]
    with pytest.raises(ValueError, match="reference"):
        gate.verify(data)


def test_public_api_sign_clipping_is_detected(monkeypatch):
    from hullkit import exotics

    ref, gate = _modules()
    original = exotics.gap_call
    monkeypatch.setattr(exotics, "gap_call", lambda *a, **kw: max(original(*a, **kw), 0))
    with pytest.raises(ValueError, match="API"):
        gate.verify(ref.build())
