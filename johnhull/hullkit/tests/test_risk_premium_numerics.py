"""The gate rejects valid-looking but numerically wrong API outputs."""

import importlib

import numpy as np
import pytest


def gate():
    return importlib.import_module("johnhull.scripts.verify_risk_premium_numerics")


def reference():
    return importlib.import_module("johnhull.scripts.build_risk_premium_reference").build()


def test_reference_and_negative_controls_are_verified():
    m = gate()
    result = m.verify(reference())
    assert result["case_count"] == 12 and result["power_count"] == 6
    assert result["max_api_error"] < 1e-10
    assert result["max_mc_standard_errors"] < 6
    assert len(m.negative_controls(reference())) == 4
    assert all(row["rejected"] for row in m.negative_controls(reference()))


@pytest.mark.parametrize("mutation", ["abs loading", "drop risk price", "bias", "NaN"])
def test_actual_api_mutations_are_rejected_by_numerical_comparison(monkeypatch, mutation):
    import hullkit.risk_premium as p

    inverse, forward = p.market_price_of_risk, p.required_return
    if mutation == "abs loading":
        monkeypatch.setattr(p, "market_price_of_risk", lambda mu, r, s: inverse(mu, r, np.abs(s)))
    elif mutation == "drop risk price":
        monkeypatch.setattr(
            p, "required_return", lambda r, lam, s: forward(r, np.zeros_like(lam), s)
        )
    elif mutation == "bias":
        monkeypatch.setattr(p, "market_price_of_risk", lambda *a: inverse(*a) + 1e-7)
    else:
        monkeypatch.setattr(p, "market_price_of_risk", lambda *a: np.asarray(inverse(*a)) * np.nan)
    with pytest.raises(ValueError, match=r"independent|finite"):
        gate().verify(reference())
