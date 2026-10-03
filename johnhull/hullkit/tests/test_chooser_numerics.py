"""Real API faults must fail comparison, even when inputs and outputs stay valid."""

import importlib

import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_chooser_reference"),
        importlib.import_module("johnhull.scripts.verify_chooser_numerics"),
    )


def test_independent_comparison_and_saved_mutations():
    ref, gate = modules()
    result = gate.verify(ref.build())
    assert result["case_count"] == 64
    assert result["max_price_error"] < 1e-8
    assert result["max_linearity_error"] < 1e-8
    assert result["max_mc_standard_errors"] < 6
    assert all(r["rejected"] for r in gate.negative_controls(ref.build()))


@pytest.mark.parametrize("mutation", ["yield", "decision", "bias", "nan"])
def test_real_api_mutations_rejected(monkeypatch, mutation):
    from hullkit import chooser

    ref, gate = modules()
    price = chooser.chooser_price

    def changed(S, K, r, sigma, T1, T2, q=0):
        if mutation == "nan":
            return float("nan")
        if mutation == "yield":
            return price(S, K, r, sigma, T1, T2, 0)
        if mutation == "decision":
            return price(S, K, r, sigma, T1 / 2, T2, q)
        return price(S, K, r, sigma, T1, T2, q) + 1e-7

    monkeypatch.setattr(chooser, "chooser_price", changed)
    with pytest.raises(
        ValueError, match="nonfinite" if mutation == "nan" else "differs from independent reference"
    ):
        gate.verify(ref.build())
