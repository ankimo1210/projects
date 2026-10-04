"""Saved-reference and real API faults cannot pass the numerical gate."""

import importlib

import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_martingale_reference"),
        importlib.import_module("johnhull.scripts.verify_martingale_numerics"),
    )


def test_numerics_validate_conditional_states_prices_and_eight_mutations():
    b, m = modules()
    result = m.verify(b.build())
    assert result["max_api_error"] < 1e-12
    assert result["max_quadrature_error"] < 1e-9
    assert result["max_mc_se"] <= 5
    assert len(result["conditional_mc"]) == 9 and len(result["pricing"]) == 4
    assert len(m.negative_controls(b.build())) == 8
    assert all(row["rejected"] for row in m.negative_controls(b.build()))


@pytest.mark.parametrize("mutation", ["zero drift", "omit Ito", "ignore horizon", "wrong measure"])
def test_real_api_faults_rejected(monkeypatch, mutation):
    from hullkit import _martingales as api

    b, m = modules()
    if mutation == "zero drift":
        monkeypatch.setattr(api, "ratio_drift", lambda *a: 0.0)
    elif mutation == "omit Ito":
        monkeypatch.setattr(api, "ratio_drift", lambda mf, mg, sf, sg: mf - mg)
    elif mutation == "ignore horizon":
        monkeypatch.setattr(api, "ratio_conditional_mean", lambda x, *args: x)
    else:
        monkeypatch.setattr(api, "numeraire_drifts", lambda r, sf, sg: (r, r))
    with pytest.raises(ValueError):
        m.verify(b.build())
