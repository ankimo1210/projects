"""MC diagnostic replay, independent moments and predeclared rare-event handling."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parents[2] / "research/RB-F07/quote_dml"


@pytest.fixture(scope="module")
def diagnostics():
    def load():
        path = HERE / "diagnostics.py"
        assert path.exists(), "quote-DML MC diagnostics are missing"
        spec = importlib.util.spec_from_file_location("quote_mc_diagnostics", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


@pytest.fixture
def protocol():
    return json.loads((HERE / "protocol.json").read_text())


def test_smoke_diagnostics_shapes_streams_and_method_order(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    assert arrays["mc_z"].shape == arrays["mc_pilot_z"].shape == (2048,)
    assert not np.allclose(arrays["mc_z"], arrays["mc_pilot_z"])
    assert arrays["mc_mean"].shape == arrays["mc_se"].shape == (13, 4, 7)
    assert arrays["mc_pilot_mean"].shape == (13, 4, 7)
    assert arrays["mc_exact_mean"].shape == (13, 7)
    assert arrays["mc_lrm_second"].shape == (13, 6)
    assert arrays["mc_conditional_second"].shape == (13, 6)
    assert list(arrays["mc_method"]) == ["lrm", "conditional", "naive_pathwise", "discount_omitted"]
    expected = [(s, t) for s in [95, 100, 105] for t in [0.05, 0.25, 1.5, 4.5]]
    np.testing.assert_allclose(
        np.column_stack([arrays["mc_spot"][:12], arrays["mc_maturity"][:12]]), expected, atol=1e-14
    )
    diagnostics.check_diagnostics(arrays, protocol)


def test_main_diagnostics_keep_fixed_paths_and_se_multiplier(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol)
    assert arrays["mc_z"].shape == (65536,)
    assert float(arrays["mc_se_multiplier"]) == 6.0
    assert not bool(arrays["mc_smoke"])
    diagnostics.check_diagnostics(arrays, protocol)


def test_saved_draws_reproduce_payoff_and_six_lrm_statistics(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    market = teacher.prepare_market(np.asarray(protocol["curve"]["base_quotes"]))
    sample = teacher.samples(market, arrays["mc_spot"][0], arrays["mc_maturity"][0], arrays["mc_z"])
    rows = np.column_stack([sample["payoff"], sample["lrm"]])
    np.testing.assert_allclose(arrays["mc_mean"][0, 0], rows.mean(axis=0), atol=1e-12, rtol=1e-10)
    np.testing.assert_allclose(
        arrays["mc_se"][0, 0], rows.std(axis=0, ddof=1) / np.sqrt(len(rows)), atol=1e-12, rtol=1e-10
    )


def test_negative_controls_are_compared_to_their_biases_not_exact_greeks(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    exact = arrays["mc_exact_mean"]
    expected = arrays["mc_method_expected"]
    np.testing.assert_allclose(expected[:, 0], exact, atol=1e-10, rtol=1e-9)
    np.testing.assert_allclose(expected[:, 1], exact, atol=1e-10, rtol=1e-9)
    np.testing.assert_allclose(expected[:, 2, 1], 0.0, atol=1e-14)
    assert np.all(exact[:12, 1] > 0)
    assert np.max(np.abs(expected[:12, 3, 2:] - exact[:12, 2:])) > 0.1
    np.testing.assert_allclose(
        arrays["mc_negative_bias"], expected[:, 2:, 1:] - exact[:, None, 1:], atol=1e-10, rtol=1e-9
    )
    diagnostics.check_diagnostics(arrays, protocol)


def test_rare_zero_hit_case_is_not_assessed_by_six_se(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    index = 12
    assert arrays["mc_spot"][index] == 80 and arrays["mc_maturity"][index] == 0.05
    assert arrays["mc_expected_hits"][index] < 20
    assert arrays["mc_rare"][index] and not arrays["mc_assessed"][index]
    assert arrays["mc_observed_hits"][index] == 0
    assert arrays["mc_se"][index, 0, 0] == 0
    assert arrays["mc_exact_mean"][index, 0] > 0
    diagnostics.check_diagnostics(arrays, protocol)


@pytest.mark.parametrize(
    "key",
    [
        "mc_mean",
        "mc_se",
        "mc_pilot_mean",
        "mc_lrm_second",
        "mc_conditional_second",
        "mc_negative_bias",
    ],
)
def test_tampered_statistics_fail_fresh_numeric_recomputation(diagnostics, protocol, key):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    changed = {name: values.copy() for name, values in arrays.items()}
    changed[key].flat[0] += 0.01
    with pytest.raises(ValueError):
        diagnostics.check_diagnostics(changed, protocol)


def test_tampered_draws_fail_saved_statistics_replay(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    arrays["mc_z"][0] += 2.0
    with pytest.raises(ValueError):
        diagnostics.check_diagnostics(arrays, protocol)


def test_rare_assessment_cannot_be_changed_to_an_ordinary_pass(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    arrays["mc_assessed"][12] = True
    with pytest.raises(ValueError):
        diagnostics.check_diagnostics(arrays, protocol)


def test_pilot_cannot_widen_six_se_limit(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    arrays["mc_se_multiplier"] = np.array(20.0)
    with pytest.raises(ValueError):
        diagnostics.check_diagnostics(arrays, protocol)


@pytest.mark.parametrize(
    "field,value", [("paths", 4096), ("seed", 999), ("rare_event_min_count", 100)]
)
def test_fixed_mc_protocol_cannot_silently_change(diagnostics, protocol, field, value):
    diagnostics = diagnostics()
    changed = deepcopy(protocol)
    changed["mc"][field] = value
    with pytest.raises(ValueError):
        diagnostics.make_diagnostics(changed)


def test_checker_rejects_a_pilot_replaced_by_the_main_stream(diagnostics, protocol):
    diagnostics = diagnostics()
    arrays = diagnostics.make_diagnostics(protocol, smoke=True)
    changed = deepcopy(protocol)
    changed["mc"]["pilot_seed"] = changed["mc"]["seed"]
    arrays["mc_pilot_seed"] = arrays["mc_seed"].copy()
    arrays["mc_pilot_z"] = arrays["mc_z"].copy()
    for suffix in ["mean", "se", "second", "second_se", "observed_hits"]:
        arrays[f"mc_pilot_{suffix}"] = arrays[f"mc_{suffix}"].copy()
    with pytest.raises(ValueError):
        diagnostics.check_diagnostics(arrays, changed)
