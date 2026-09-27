"""Immutable, offline artifacts for comparing a synthetic run after restart."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import replace

import pytest
from market_research.services import build_demo_run

COMMIT = "a" * 40
CONFIG = {"strategy": "synthetic-demo", "lag": 1, "base_currency": "USD"}
SPLITS = {"kind": "none", "lockbox": None}
COSTS = {"commission_bps": 3.0, "slippage_bps": 2.0}


def _module():
    return importlib.import_module("market_research.research.run_store")


def _save(root, run, **changes):
    options = {
        "code_commit": COMMIT,
        "config": CONFIG,
        "seed": None,
        "splits": SPLITS,
        "costs": COSTS,
    }
    options.update(changes)
    return _module().save_demo_run(root, run, **options)


def test_saved_demo_survives_reopen_and_matches_rebuilt_run(tmp_path):
    root = tmp_path / "runs"
    run = build_demo_run()
    html = "<!doctype html><html><body>offline</body></html>"

    saved = _save(root, run, html=html)

    assert saved.artifact_id != run.run_id
    assert len(saved.artifact_id) == 64
    assert saved.path == root / saved.artifact_id
    assert saved.manifest["schema_version"] == 1
    assert saved.manifest["artifact_id"] == saved.artifact_id
    assert saved.manifest["source_run_id"] == run.run_id
    assert saved.manifest["input_hash"] == run.input_hash
    assert saved.manifest["code_commit"] == COMMIT
    assert saved.manifest["config"] == CONFIG
    assert saved.manifest["seed"] is None
    assert saved.manifest["splits"] == SPLITS
    assert saved.manifest["costs"] == COSTS
    assert saved.manifest["quality"]["bar_count"] == 120
    assert saved.manifest["failure_reasons"] == []
    assert saved.manifest["mode"] == "synthetic-demo"
    assert saved.manifest["pit_claim"] is False
    assert (
        saved.manifest["result_sha256"]
        == hashlib.sha256((saved.path / "result.json").read_bytes()).hexdigest()
    )
    assert saved.manifest["html_sha256"] == hashlib.sha256(html.encode()).hexdigest()
    assert saved.result["backtest"]["equity"][-1] == pytest.approx(run.backtest.equity.iloc[-1])
    assert saved.html == html
    assert _save(root, run, html=html).artifact_id == saved.artifact_id

    reopened = _module().load_demo_run(root, saved.artifact_id, expected=build_demo_run())
    assert reopened.manifest == saved.manifest
    assert reopened.result == saved.result
    assert reopened.html == html


def test_code_commit_and_configuration_produce_distinct_immutable_ids(tmp_path):
    root = tmp_path / "runs"
    run = build_demo_run()

    first = _save(root, run)
    code_changed = _save(root, run, code_commit="b" * 40)
    config_changed = _save(root, run, config={**CONFIG, "strategy": "revised"})
    failure_recorded = _save(root, run, failure_reasons=("upstream fixture unavailable",))

    assert (
        len(
            {
                first.artifact_id,
                code_changed.artifact_id,
                config_changed.artifact_id,
                failure_recorded.artifact_id,
            }
        )
        == 4
    )
    assert first.manifest["source_run_id"] == code_changed.manifest["source_run_id"]
    assert failure_recorded.manifest["failure_reasons"] == ["upstream fixture unavailable"]
    assert _module().load_demo_run(root, first.artifact_id).manifest == first.manifest
    assert _module().load_demo_run(root, code_changed.artifact_id).manifest == code_changed.manifest


def test_same_artifact_id_cannot_replace_different_result_or_html(tmp_path):
    root = tmp_path / "runs"
    run = build_demo_run()
    first = _save(root, run, html="first report")
    changed_equity = run.backtest.equity.copy()
    changed_equity.iloc[-1] += 0.01
    changed_run = replace(run, backtest=replace(run.backtest, equity=changed_equity))

    with pytest.raises(ValueError, match="different content"):
        _save(root, changed_run, html="first report")
    with pytest.raises(ValueError, match="different content"):
        _save(root, run, html="second report")
    assert _module().load_demo_run(root, first.artifact_id).html == "first report"
    with pytest.raises(ValueError, match="expected run"):
        _module().load_demo_run(root, first.artifact_id, expected=changed_run)


def test_result_or_manifest_hash_tampering_is_detected(tmp_path):
    run = build_demo_run()
    root = tmp_path / "runs"
    saved = _save(root, run)
    result_path = saved.path / "result.json"
    result_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="result hash"):
        _module().load_demo_run(root, saved.artifact_id)

    second = _save(tmp_path / "other-runs", run)
    manifest_path = second.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_commit"] = "b" * 40
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest hash"):
        _module().load_demo_run(tmp_path / "other-runs", second.artifact_id)
    (second.path / "manifest.sha256").write_text(
        hashlib.sha256(manifest_path.read_bytes()).hexdigest(), encoding="ascii"
    )
    with pytest.raises(ValueError, match="artifact ID"):
        _module().load_demo_run(tmp_path / "other-runs", second.artifact_id)


def test_run_paths_and_git_checkout_targets_are_rejected(tmp_path):
    run = build_demo_run()
    root = tmp_path / "runs"
    with pytest.raises(ValueError, match="run_id"):
        _save(root, replace(run, run_id="../escape"))
    with pytest.raises(ValueError, match="artifact ID"):
        _module().load_demo_run(root, "../escape")

    valid = _save(tmp_path / "valid", run)
    root.mkdir()
    (root / valid.artifact_id).symlink_to(
        tmp_path / "valid" / valid.artifact_id, target_is_directory=True
    )
    with pytest.raises(ValueError, match="symlink"):
        _save(root, run)
    with pytest.raises(ValueError, match="symlink"):
        _module().load_demo_run(root, valid.artifact_id)

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    with pytest.raises(ValueError, match="Git"):
        _save(checkout / "runs", run)


def test_secret_config_or_inconsistent_costs_are_rejected(tmp_path):
    run = build_demo_run()
    with pytest.raises(ValueError, match="secret"):
        _save(tmp_path / "secret", run, config={"provider": {"api_key": "do-not-store"}})
    with pytest.raises(ValueError, match="secret"):
        _save(
            tmp_path / "secret-reason", run, failure_reasons=("Authorization: Bearer do-not-store",)
        )
    with pytest.raises(ValueError, match="cost"):
        _save(tmp_path / "cost", run, costs={"commission_bps": 10.0, "slippage_bps": 2.0})
