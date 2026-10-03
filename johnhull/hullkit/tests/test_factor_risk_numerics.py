"""Saved-output and actual API faults must fail the independent numerical gate."""

import importlib

import numpy as np
import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_factor_risk_reference"),
        importlib.import_module("johnhull.scripts.verify_factor_risk_numerics"),
    )


def test_independent_numerical_gate_and_saved_mutations():
    b, m = modules()
    result = m.verify(b.build())
    assert result["case_count"] == 12
    assert result["max_api_error"] < 1e-12
    assert result["max_hedge_error"] < 1e-12
    assert result["max_rotation_error"] < 1e-12
    assert len(m.negative_controls(b.build())) == 8
    assert all(row["rejected"] for row in m.negative_controls(b.build()))


@pytest.mark.parametrize(
    "name", ["absolute_loading", "drop_last_factor", "sum_all_axes", "add_rate_twice"]
)
def test_real_api_mutations_are_rejected(monkeypatch, name):
    from hullkit import factor_risk as api

    b, m = modules()
    if name == "absolute_loading":
        old = api.factor_contributions
        monkeypatch.setattr(api, "factor_contributions", lambda lam, s: old(lam, np.abs(s)))
    elif name == "drop_last_factor":
        old = api.factor_excess_return
        monkeypatch.setattr(
            api,
            "factor_excess_return",
            lambda lam, s: old(np.asarray(lam)[..., :-1], np.asarray(s)[..., :-1]),
        )
    elif name == "sum_all_axes":
        monkeypatch.setattr(
            api,
            "factor_excess_return",
            lambda lam, s: float(np.sum(api.factor_contributions(lam, s))),
        )
    else:
        old = api.factor_required_return
        monkeypatch.setattr(api, "factor_required_return", lambda r, lam, s: old(r, lam, s) + r)
    with pytest.raises(ValueError):
        m.verify(b.build())
