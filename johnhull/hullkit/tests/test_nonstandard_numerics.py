"""Tamper controls for the independent §26.3 numerical record."""

import copy
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_nonstandard_reference as ref  # noqa: E402
import verify_nonstandard_numerics as numeric  # noqa: E402


def test_all_reference_cases_match_public_api_and_exercise_mask():
    result = numeric.verify(ref.build())
    assert result["case_count"] == 11
    assert result["max_price_error"] < 1e-10
    assert result["forbidden_exercise_count"] == 0


@pytest.mark.parametrize("mutation", ["price", "schedule", "warrant_strike"])
def test_saved_reference_tampering_is_rejected(mutation):
    data = copy.deepcopy(ref.build())
    if mutation == "price":
        data["cases"][1]["price"] += 0.25
    elif mutation == "schedule":
        data["cases"][1]["exercise_strikes"]["10"] = 110.0
    else:
        data["warrant"]["exercise_strikes"]["50"] = 30.0
    with pytest.raises(ValueError, match="reference"):
        numeric.verify(data)
