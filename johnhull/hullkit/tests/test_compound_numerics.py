"""Independent comparisons reject wrong strikes, correlations, roots and NaN."""

import importlib

import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_compound_reference"),
        importlib.import_module("johnhull.scripts.verify_compound_numerics"),
    )


def test_independent_cases_and_four_saved_mutations():
    reference, gate = modules()
    result = gate.verify(reference.build())
    assert result["case_count"] == 104
    assert result["max_price_error"] < 1e-8
    assert result["max_root_residual"] < 1e-9
    assert result["max_parity_error"] < 1e-8
    assert result["max_mc_standard_errors"] < 6
    assert all(row["rejected"] for row in gate.negative_controls(reference.build()))


@pytest.mark.parametrize("mutation", ["strikes", "correlation", "critical", "nan"])
def test_actual_api_mutations_are_rejected(monkeypatch, mutation):
    from hullkit import compound

    reference, gate = modules()
    price, cdf, root = compound.compound_price, compound._bivariate_normal, compound._critical_spot
    if mutation == "strikes":

        def swapped(S, K1, K2, r, sigma, T1, T2, q=0, **kwargs):
            return price(S, K2, K1, r, sigma, T1, T2, q, **kwargs)

        monkeypatch.setattr(compound, "compound_price", swapped)
    elif mutation == "correlation":
        monkeypatch.setattr(compound, "_bivariate_normal", lambda a, b, rho: cdf(a, b, 0))
    elif mutation == "critical":
        monkeypatch.setattr(
            compound, "_critical_spot", lambda *args: root(*args) * 1.2 if root(*args) else None
        )
    else:
        monkeypatch.setattr(compound, "compound_price", lambda *args, **kwargs: float("nan"))
    with pytest.raises(ValueError):
        gate.verify(reference.build())
