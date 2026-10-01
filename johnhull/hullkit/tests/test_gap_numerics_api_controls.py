"""The §26.4 numerics gate must reject a broken public formula, not only changed data.

The saved-data negative controls in ``verify_gap_numerics`` all fail at the
recomputation check, so they never reach the API-versus-reference comparison.
These controls leave the data alone and break ``hullkit.exotics`` instead.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest
from hullkit import exotics

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_gap_reference as reference  # noqa: E402
import verify_gap_numerics as numeric  # noqa: E402

CALL, PUT = exotics.gap_call, exotics.gap_put


def _keywords(pricer, settlement_from_trigger=False, trigger_from_settlement=False, bias=0.0):
    def broken(S, K1, K2, r, sigma, T, q=0.0):
        settlement = K2 if settlement_from_trigger else K1
        trigger = (K1 or K2) if trigger_from_settlement else K2
        return pricer(S, settlement, trigger, r, sigma, T, q) * (1.0 + bias)

    return broken


BROKEN = {
    "d_at_settlement_strike": (
        _keywords(CALL, trigger_from_settlement=True),
        _keywords(PUT, trigger_from_settlement=True),
    ),
    "settlement_at_trigger": (_keywords(CALL, settlement_from_trigger=True), PUT),
    "relative_bias_1e-9": (_keywords(CALL, bias=1e-9), _keywords(PUT, bias=1e-9)),
}


@pytest.fixture(scope="module")
def data():
    return reference.build()


def test_unbroken_api_passes(data):
    assert numeric.verify(data)["case_count"] == len(data["cases"])


@pytest.mark.parametrize("name", sorted(BROKEN))
def test_broken_public_formula_is_rejected(data, name):
    call, put = BROKEN[name]
    with (
        mock.patch.object(exotics, "gap_call", call),
        mock.patch.object(exotics, "gap_put", put),
        pytest.raises(ValueError, match="public gap API differs"),
    ):
        numeric.verify(data)
