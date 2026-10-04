"""Independent original requirements and executable/saved mutation gates."""

import copy
import importlib
from types import SimpleNamespace

import pytest


def modules():
    return (
        importlib.import_module("johnhull.scripts.build_multifactor_reference"),
        importlib.import_module("johnhull.scripts.verify_multifactor_numerics"),
    )


def test_all_factor_source_requirements_and_conditioned_states():
    b, m = modules()
    data = b.build()
    assert data["source_requirements"] == [f"MF{i:02}" for i in range(1, 7)]
    assert data["source_printed_pins"] == [] and data["synthetic"] is True
    assert len(data["cases"]) == 11
    assert sum(len(c["conditional"]) for c in data["cases"]) == 132
    result = m.verify(data)
    assert result["case_count"] == 11 and result["conditional_count"] == 132
    assert result["max_api_error"] < 1e-12
    assert result["max_mc_se"] < 5


def test_executable_and_saved_mutations_rejected():
    b, m = modules()
    rows = m.negative_controls(b.build())
    assert len(rows) == 8 and all(r["rejected"] for r in rows)


def test_missing_correlated_basis_cannot_match_teacher():
    from hullkit import _multi_factor_martingales as api

    b, m = modules()
    proxy = SimpleNamespace(**{n: getattr(api, n) for n in m.API_NAMES})
    proxy.factor_numeraire_drifts = lambda r, f, g, C=None: api.factor_numeraire_drifts(r, f, g)
    with pytest.raises(ValueError, match="numerical mismatch"):
        m.verify(b.build(), proxy, mc=False)


def test_modified_independent_result_rejected():
    b, m = modules()
    teacher = b.build()
    bad = copy.deepcopy(teacher)
    bad["cases"][1]["ratio_q_drift"] += 0.01
    with pytest.raises(ValueError, match="independent"):
        m.verify(bad, reference=teacher, mc=False)
