"""The §26.5 gate detects wrong option life, fixing and dividend discount."""

import copy
import importlib
import math

import pytest


def gate():
    return importlib.import_module("johnhull.scripts.verify_forward_start_numerics")


def data():
    return importlib.import_module("johnhull.scripts.build_forward_start_reference").build()


def test_api_and_monte_carlo_agree_with_independent_payoff_integral():
    result = gate().verify(data())
    assert result["case_count"] == 36
    assert result["max_price_error"] < 1e-9
    assert result["max_mc_standard_errors"] < 6


@pytest.mark.parametrize("mutation", ["price", "tenor", "fixing", "discount"])
def test_four_reference_mutations_are_rejected(mutation):
    controls = gate().negative_controls(data())
    assert next(row for row in controls if row["mutation"] == mutation)["rejected"]


def test_wrong_full_maturity_api_is_detected(monkeypatch):
    module = gate()
    from hullkit import bsm

    monkeypatch.setattr(
        module.forward_start,
        "forward_start_call",
        lambda S, r, sigma, T1, T2, q=0: bsm.call_price(S, S, r, sigma, T2, q),
    )
    with pytest.raises(ValueError, match="API differs"):
        module.verify(data())


def test_omitted_start_dividend_discount_api_is_detected(monkeypatch):
    module = gate()
    original = module.forward_start.forward_start_call
    monkeypatch.setattr(
        module.forward_start,
        "forward_start_call",
        lambda S, r, sigma, T1, T2, q=0: original(S, r, sigma, T1, T2, q) * math.exp(q * T1),
    )
    with pytest.raises(ValueError, match="API differs"):
        module.verify(data())


def test_changed_monte_carlo_interval_is_rejected():
    changed = copy.deepcopy(data())
    changed["mc"][0]["ci95"][1] += 1
    with pytest.raises(ValueError):
        gate().verify(changed)
