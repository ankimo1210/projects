"""Numerical gate rejects saved and executable mutations."""

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from hullkit import _numeraire_choices as api

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import verify_numeraire_numerics as gate


@pytest.fixture(scope="module")
def reference():
    return gate.build()


def test_independent_reference_has_every_original_requirement(reference):
    assert reference["source_requirements"] == [f"N{n:02d}" for n in range(1, 13)]
    assert reference["printed_pins"] == []
    assert reference["synthetic"] is True
    assert [len(reference[k]) for k in ("joint", "stock", "rates", "annuity")] == [6, 18, 21, 18]


def test_api_and_saved_mutations_are_rejected(reference):
    rows = gate.negative_controls(reference)
    assert len(rows) == 8
    assert all(row["rejected"] for row in rows)


def test_omitted_payment_tilt_is_detected(reference):
    proxy = SimpleNamespace(**{n: getattr(api, n) for n in gate.API_NAMES})
    proxy.joint_moments = lambda t, T, x, m, payment=None: api.joint_moments(t, T, x, m)
    with pytest.raises(ValueError, match="numerical mismatch"):
        gate.verify(reference, proxy, reference)


def test_modified_reference_is_detected(reference):
    bad = copy.deepcopy(reference)
    bad["annuity"][0]["swap_rate_t"] += 0.01
    with pytest.raises(ValueError, match="independent"):
        gate.verify(bad, reference=reference)
