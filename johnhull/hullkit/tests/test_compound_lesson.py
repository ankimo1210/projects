"""Shared plots expose both thresholds, all four contracts and MC uncertainty."""

import importlib
import json

import pytest

KEYS = {"compound_threshold", "compound_strikes", "compound_timing", "compound_validation"}


def lesson():
    return importlib.import_module("hullkit._compound_lesson")


def test_four_shared_figures_and_market_metadata():
    figures = lesson()._figures()
    assert set(figures) == KEYS
    assert all(fig.layout.meta["section"] == "26.7" for fig in figures.values())
    assert all("K1=10" in fig.layout.meta["market"] for fig in figures.values())
    thresholds = figures["compound_threshold"]
    roles = {trace.meta["role"]: trace for trace in thresholds.data}
    assert roles["critical-call"].x[0] == pytest.approx(105.77296228027585, abs=1e-9)
    assert roles["critical-put"].x[0] == pytest.approx(90.73021992506433, abs=1e-9)
    assert roles["call_on_call"].y[0] == 0
    assert roles["call_on_put"].y[-1] == 0


def test_strikes_put_bound_and_conditional_mc_error_bars():
    figures = lesson()._figures()
    curves = {trace.meta["role"]: trace for trace in figures["compound_strikes"].data}
    assert curves["call_on_put"].y[-1] == 0
    assert curves["put_on_call"].y[0] == 0
    traces = {trace.meta["role"]: trace for trace in figures["compound_validation"].data}
    assert len(traces["mc"].y) == 4
    assert traces["mc"].error_y.visible
    assert all(error > 0 for error in traces["mc"].error_y.array)
    assert len(traces["integral"].y) == 4


@pytest.mark.parametrize("mutation", ["source", "artifact"])
def test_reference_guard_rejects_incomplete_hashes(tmp_path, mutation):
    module = lesson()
    record = json.loads(module._RECORD.read_text(encoding="utf-8"))
    if mutation == "source":
        record["source_sha256"].pop("hullkit/src/hullkit/compound.py")
    else:
        record["artifact_sha256"] = "0" * 64
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        module._load_reference(path)
