"""The §26.7 comparison itself must reject subtly broken public formulas.

``test_compound_numerics`` breaks the API so grossly that input validation,
the API's negative-value guard or the finiteness check rejects it before the
independent comparison runs.  These mutants pass those guards, so only the
price/parity/threshold comparison can reject them.
"""

import importlib

import pytest
from hullkit import compound

PRICE, CDF, ROOT = compound.compound_price, compound._bivariate_normal, compound._critical_spot


def _swap_positive_strikes(S, K1, K2, r, sigma, T1, T2, q=0.0, *, kind="call_on_call"):
    if K1 > 0:
        K1, K2 = K2, K1
    return PRICE(S, K1, K2, r, sigma, T1, T2, q, kind=kind)


def _biased(S, K1, K2, r, sigma, T1, T2, q=0.0, *, kind="call_on_call"):
    return PRICE(S, K1, K2, r, sigma, T1, T2, q, kind=kind) * (1.0 + 1e-9)


def _shifted_root(*args):
    root = ROOT(*args)
    return None if root is None else root * (1.0 + 1e-7)


MUTANTS = {
    "strike_swap_where_K1_positive": ("compound_price", _swap_positive_strikes),
    "correlation_scaled_0.9999": ("_bivariate_normal", lambda a, b, rho: CDF(a, b, 0.9999 * rho)),
    "critical_spot_shifted_1e-7": ("_critical_spot", _shifted_root),
    "relative_bias_1e-9": ("compound_price", _biased),
}


@pytest.fixture(scope="module")
def modules():
    return (
        importlib.import_module("johnhull.scripts.build_compound_reference"),
        importlib.import_module("johnhull.scripts.verify_compound_numerics"),
    )


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_subtle_api_mutation_is_rejected_by_the_comparison(monkeypatch, modules, name):
    reference, gate = modules
    data = reference.build()
    attribute, broken = MUTANTS[name]
    monkeypatch.setattr(compound, attribute, broken)
    with pytest.raises(ValueError, match="differs from independent reference"):
        gate.verify(data)
