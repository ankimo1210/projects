"""Verify the delivered HTML is portable and matches its editable sources."""

import importlib.util
import json
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT / "playground"


def test_playground_is_current_and_self_contained():
    spec = importlib.util.spec_from_file_location("playground_build", PLAYGROUND / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    html = (PLAYGROUND / "index.html").read_text()
    assert html == module.render()
    assert '<html lang="ja"' in html

    class ExternalResources(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            assert not (tag == "script" and "src" in attrs)
            assert not (tag == "link" and attrs.get("rel") == "stylesheet")

    # CSS comments include a font-link example; inspect actual tags only.
    ExternalResources().feed(html)
    assert "fetch(" not in html
    assert "/*__" not in html
    assert (ROOT.parents[1] / "docs/templates/claude-report/tokens.css").read_text() in html


def test_playground_contains_accessible_controls_and_actual_engine():
    html = (PLAYGROUND / "index.html").read_text()
    for control in [
        "start",
        "step",
        "reset",
        "finalize",
        "dataset",
        "depth",
        "width",
        "lr",
        "seed",
        "theme",
        "export",
    ]:
        assert f'id="{control}"' in html
    assert 'id="engine-source"' in html
    assert "class Experiment" in html
    assert 'aria-live="polite"' in html


def test_scale_snapshot_rejects_incomplete_or_inconsistent_results(tmp_path):
    spec = importlib.util.spec_from_file_location("playground_build", PLAYGROUND / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshot = json.loads((PLAYGROUND / "benchmark-results.json").read_text())
    target = tmp_path / "results.json"
    target.write_text(json.dumps(snapshot))
    assert module.load_snapshot(target) == snapshot
    for field, bad in [("status", "running"), ("runs", [])]:
        altered = {**snapshot, field: bad}
        target.write_text(json.dumps(altered))
        with pytest.raises(ValueError):
            module.load_snapshot(target)
    altered = deepcopy(snapshot)
    altered["summary"][0]["test_accuracy_mean"] = 0.9
    target.write_text(json.dumps(altered))
    with pytest.raises(ValueError):
        module.load_snapshot(target)


def test_scale_snapshot_rejects_missing_ui_metadata_and_invalid_costs(tmp_path):
    spec = importlib.util.spec_from_file_location("playground_build", PLAYGROUND / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((PLAYGROUND / "benchmark-results.json").read_text())
    variants = []
    missing_hardware = deepcopy(original)
    del missing_hardware["hardware"]
    variants.append(missing_hardware)
    bad_timing = deepcopy(original)
    bad_timing["models"][0]["timings"][0]["step_ms"] = -1
    variants.append(bad_timing)
    bad_memory = deepcopy(original)
    bad_memory["summary"][0]["peak_allocated_bytes"] = 2**60
    variants.append(bad_memory)
    for index, data in enumerate(variants):
        path = tmp_path / f"bad-{index}.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            module.load_snapshot(path)


def test_digit_snapshot_checks_weights_updates_metrics_and_validation_selection(tmp_path):
    spec = importlib.util.spec_from_file_location("playground_build", PLAYGROUND / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((PLAYGROUND / "digit-results.json").read_text())
    assert module.load_digits(PLAYGROUND / "digit-results.json") == original
    variants = []
    bad_weights = deepcopy(original)
    bad_weights["models"][0]["history"][0]["weights"]["conv1.weight"] = "AAAA"
    variants.append(bad_weights)
    bad_update = deepcopy(original)
    bad_update["models"][0]["history"][1]["update"]["after"] = original["models"][0]["history"][0][
        "weights"
    ]["conv1.weight"]
    variants.append(bad_update)
    bad_selection = deepcopy(original)
    bad_selection["models"][0]["best_epoch"] = 0
    variants.append(bad_selection)
    bad_metrics = deepcopy(original)
    bad_metrics["models"][0]["test"]["correct"] += 1
    variants.append(bad_metrics)
    for i, variant in enumerate(variants):
        target = tmp_path / f"digits-{i}.json"
        target.write_text(json.dumps(variant))
        with pytest.raises(ValueError):
            module.load_digits(target)
