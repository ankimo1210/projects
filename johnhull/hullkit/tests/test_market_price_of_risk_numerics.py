"""Real API faults must fail the independent comparison (§28.1)."""

import importlib

import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_market_price_of_risk_reference"),
        importlib.import_module("johnhull.scripts.verify_market_price_of_risk_numerics"),
    )


def test_independent_comparison_and_saved_mutations():
    ref, gate = modules()
    result = gate.verify(ref.build())
    assert result["claim_count"] == 38
    assert result["max_lambda_error"] < 1e-8
    assert result["max_ito_error"] < 1e-8
    assert result["max_mc_standard_errors"] < 6
    assert all(r["rejected"] for r in gate.negative_controls(ref.build()))


@pytest.mark.parametrize("mutation", ["abs_loading", "drop_drift", "bias", "nan"])
def test_real_api_mutations_rejected(monkeypatch, mutation):
    from hullkit import market_price_of_risk as mpr

    ref, gate = modules()
    lam, ito = mpr.market_price_of_risk, mpr.ito_growth_and_loading

    if mutation == "abs_loading":
        monkeypatch.setattr(mpr, "market_price_of_risk", lambda m, s, r: lam(m, abs(s), r))
    elif mutation == "drop_drift":
        monkeypatch.setattr(
            mpr,
            "ito_growth_and_loading",
            lambda f, ft, fu, fuu, u, m, s: ito(f, ft, fu, fuu, u, 0.0, s),
        )
    elif mutation == "bias":
        monkeypatch.setattr(mpr, "required_growth", lambda r, lam_, s: r + lam_ * s + 1e-7)
    else:
        monkeypatch.setattr(mpr, "market_price_of_risk", lambda m, s, r: float("nan"))
    with pytest.raises(ValueError, match="nonfinite" if mutation == "nan" else "differs"):
        gate.verify(ref.build())
