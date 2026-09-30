"""Tamper controls for the independent §26.4 numerical record."""

import copy
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_gap_reference as ref  # noqa: E402
import verify_gap_numerics as numeric  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return ref.build()


def test_public_api_matches_every_reference_case(data):
    result = numeric.verify(data)
    assert result["case_count"] == 38
    assert max(result["max_relative_error"].values()) < 1e-12
    assert result["zero_value_settlement_error"] < 1e-10
    assert result["example_26_1_printed"] == {
        "regular_put": 3436,
        "gap_put": 1896,
        "reduction_percent": 45,
    }


@pytest.mark.parametrize("mutation", ["price", "settlement_strike", "printed_value"])
def test_saved_reference_tampering_is_rejected(data, mutation):
    changed = copy.deepcopy(data)
    if mutation == "price":
        changed["cases"][0]["price"] += 0.01
    elif mutation == "settlement_strike":
        changed["cases"][4]["K1"] = 105.0
    else:
        changed["example_26_1"]["printed"]["gap_put"] = 1_900
    with pytest.raises(ValueError, match="reference"):
        numeric.verify(changed)


def test_every_negative_control_is_rejected(data):
    assert all(row["rejected"] for row in numeric.negative_controls(data))


def test_broken_public_formulas_are_rejected_by_the_comparison(data):
    controls = numeric.api_negative_controls(data)
    assert [row["mutation"] for row in controls] == [
        "d_at_settlement_strike",
        "swapped_put_strikes",
        "relative_bias_1e-9",
    ]
    assert all(row["rejected"] for row in controls)
