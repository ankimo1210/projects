"""Physical storage-growth guards use saved bytes, not smaller financial jobs."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import run_pilot as pilot  # noqa: E402


def budget_module():
    return importlib.import_module("_pilot_storage_budget")


def allocated(path):
    seen = set()
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            stat = item.stat()
            key = (stat.st_dev, stat.st_ino)
            if key not in seen:
                seen.add(key)
                total += stat.st_blocks * 512
    return total


def test_existing_physical_allocation_is_counted_before_any_write(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "saved.bin").write_bytes(b"x" * 20000)
    (existing / "same.bin").hardlink_to(existing / "saved.bin")
    actual = allocated(existing)
    assert actual == (existing / "saved.bin").stat().st_blocks * 512
    with pytest.raises(OSError, match="storage growth"):
        budget_module().StorageBudget(existing, max_bytes=actual - 1)
    assert (existing / "saved.bin").read_bytes() == b"x" * 20000


def test_budget_stops_before_publishing_an_oversized_transport(tmp_path):
    module = budget_module()
    payload = {"raw": np.random.default_rng(913).normal(size=20000), "original_n": 65536}
    budget = module.StorageBudget(tmp_path, max_bytes=32768)
    with module.storage_scope(budget):
        with pytest.raises(OSError, match="storage growth"):
            pilot.write_pilot_artifact(tmp_path / "new-job", payload)
    assert not (tmp_path / "new-job").exists()
    assert list(tmp_path.iterdir()) == []
    assert payload["original_n"] == 65536


def test_inclusive_budget_counts_teacher_packs_and_transport_pages(tmp_path):
    module = budget_module()
    budget = module.StorageBudget(tmp_path, max_bytes=1024 * 1024)
    from test_dynamic_hedging_teacher_storage import native_teacher

    with module.storage_scope(budget):
        pilot.write_pilot_artifact(tmp_path / "teacher", native_teacher())
        pilot.write_pilot_artifact(tmp_path / "job-a", {"raw": np.arange(256)})
        pilot.write_pilot_artifact(tmp_path / "job-b", {"raw": np.arange(256)})
    assert budget.used_bytes == allocated(tmp_path)
    assert budget.used_bytes > 0


def test_storage_scope_is_reset_after_exception(tmp_path):
    module = budget_module()
    with pytest.raises(RuntimeError, match="synthetic"):
        with module.storage_scope(module.StorageBudget(tmp_path, max_bytes=1)):
            raise RuntimeError("synthetic")
    assert module.current_budget() is None
    pilot.write_pilot_artifact(tmp_path / "outside", {"value": 1})
    assert (tmp_path / "outside" / "receipt.json").exists()


def test_saved_checks_enforce_one_budget_across_check_results(tmp_path):
    import _pilot_saved_storage as storage

    module = budget_module()
    checks = storage.SavedChecks(tmp_path / "checks")
    assert hasattr(checks, "storage_budget"), "saved results need one inclusive budget"
    checks.storage_budget = module.StorageBudget(tmp_path / "checks", max_bytes=32768)
    with pytest.raises(OSError, match="storage growth"):
        checks["large"] = {"raw": np.random.default_rng(917).normal(size=20000)}
    assert checks.references == {}
    assert list((tmp_path / "checks").iterdir()) == []


def test_saved_check_reading_does_not_apply_a_new_write_budget(tmp_path, monkeypatch):
    import _pilot_saved_storage as storage

    module = budget_module()
    first = storage.SavedChecks(tmp_path / "checks")
    expected = {"raw": np.arange(256.0)}
    first["saved"] = expected
    original_budget = module.StorageBudget
    monkeypatch.setattr(
        module, "StorageBudget", lambda directory: original_budget(directory, max_bytes=1)
    )
    restored = storage.SavedChecks(
        tmp_path / "checks", references=storage.read_check_manifest(tmp_path / "checks")
    )
    np.testing.assert_allclose(restored["saved"]["raw"], expected["raw"])


def test_refused_write_releases_unpublished_bytes_from_the_budget(tmp_path):
    module = budget_module()
    budget = module.StorageBudget(tmp_path, max_bytes=32768)
    with module.storage_scope(budget):
        with pytest.raises(OSError, match="storage growth"):
            pilot.write_pilot_artifact(
                tmp_path / "large", {"raw": np.random.default_rng(918).normal(size=20000)}
            )
        assert budget.used_bytes == 0
        pilot.write_pilot_artifact(tmp_path / "small", {"value": 1})
    assert budget.used_bytes == allocated(tmp_path)


def test_teacher_budget_refusal_never_publishes_an_incomplete_root(tmp_path):
    from test_dynamic_hedging_teacher_storage import native_teacher

    module = budget_module()
    budget = module.StorageBudget(tmp_path, max_bytes=1)
    with module.storage_scope(budget):
        with pytest.raises(OSError, match="storage growth"):
            pilot.write_pilot_artifact(tmp_path / "teacher", native_teacher())
    assert not (tmp_path / "teacher").exists()
    assert list(tmp_path.iterdir()) == []
    assert budget.used_bytes == 0


def test_closure_refusal_is_inclusive_and_does_not_publish_partial_boundaries(tmp_path):
    module = budget_module()
    budget = module.StorageBudget(tmp_path, max_bytes=32768)
    raw = {"fits": [{"raw": np.random.default_rng(919).normal(size=20000)}]}
    with module.storage_scope(budget):
        with pytest.raises(OSError, match="storage growth"):
            pilot.write_closure_artifact(tmp_path / "closure", raw)
    assert list(tmp_path.iterdir()) == []
    assert budget.used_bytes == 0


def test_actual_pilot_writer_shares_common_input_without_changing_raw_values(tmp_path):
    shared = np.random.default_rng(920).integers(0, 256, size=16 * 1024**2, dtype=np.uint8)
    left = {"id": "left", "raw": {"dataset": shared, "rollout": np.arange(16.0)}}
    right = {"id": "right", "raw": {"dataset": shared, "rollout": np.arange(16.0) + 1}}
    for name, payload in (("left", left), ("right", right)):
        pilot.write_pilot_artifact(tmp_path / name, payload)
        recovered, _ = pilot.read_pilot_artifact(tmp_path / name)
        np.testing.assert_array_equal(recovered["raw"]["dataset"], shared)
        np.testing.assert_allclose(recovered["raw"]["rollout"], payload["raw"]["rollout"])
    left_inodes = {
        (p.stat().st_dev, p.stat().st_ino) for p in (tmp_path / "left").rglob("arrays.npz")
    }
    common = [
        p
        for p in (tmp_path / "right").rglob("arrays.npz")
        if (p.stat().st_dev, p.stat().st_ino) in left_inodes
    ]
    assert len(common) >= 2, "real writer pages must share the common 16 MiB input"


def test_main_entry_shares_one_growth_budget_across_saved_jobs(tmp_path, monkeypatch):
    import run_main as main

    module = budget_module()
    original_budget = module.StorageBudget
    monkeypatch.setattr(
        module, "StorageBudget", lambda directory: original_budget(directory, max_bytes=256 * 1024)
    )
    payload = {"raw": np.random.default_rng(921).normal(size=20000), "original_n": 65536}
    directory = tmp_path / "main-run"

    def saved_pretest(*args):
        main.write_main_artifact(directory / "job-a", payload)
        main.write_main_artifact(
            directory / "job-b", payload | {"raw": payload["raw"] + 1, "id": "different-page"}
        )
        pytest.fail("main must stop before a cumulative storage overrun")

    monkeypatch.setattr(main, "_pretest", saved_pretest)
    with pytest.raises(OSError, match="storage growth"):
        main.run_main_experiment(directory, inputs={}, locked_plan={})
    assert (directory / "job-a" / "receipt.json").exists()
    assert not (directory / "job-b").exists()
    assert module.current_budget() is None
    restored, _ = main.read_main_artifact(directory / "job-a")
    np.testing.assert_allclose(restored["raw"], payload["raw"])
    assert restored["original_n"] == 65536
