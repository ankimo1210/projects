"""Teacher-only storage source tests; deterministic bounded paths, no finance run."""

import copy
import hashlib
import importlib
import importlib.util
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import run_pilot as pilot  # noqa: E402
import run_reference as runner  # noqa: E402
from hullkit._dynamic_hedging_conditional import primitive_labels, teacher_primitives  # noqa: E402
from hullkit._heston_local_surface import HestonParameters  # noqa: E402

from deep_hedge_price import _dynamic_hedging_protocol as protocol  # noqa: E402

SAMPLES = (
    "raw_samples",
    "conditioned_samples",
    "cv_samples",
    "f_samples",
    "f_x_samples",
    "raw_x_samples",
    "conditioned_x_samples",
    "unreplaced_cv_samples",
    "unreplaced_cv_x_samples",
    "aux_raw_samples",
    "aux_conditioned_samples",
)


def storage():
    assert importlib.util.find_spec("_teacher_storage") is not None, (
        "completed native teachers require the private primitive recipe storage"
    )
    return importlib.import_module("_teacher_storage")


class ConstantSourceField:
    def __init__(self, variance=0.04):
        self.variance = variance

    def evaluate(self, time, spots):
        spots = np.asarray(spots)
        return {
            "variance": np.full(spots.shape, self.variance),
            "supported": np.ones(spots.shape, dtype=bool),
            "status": np.full(spots.shape, "ready"),
        }


def native_teacher(model="Heston", variant="ordinary"):
    """Deterministic source arithmetic with all native envelope/primitives."""
    n = 32
    times = np.arange(25, dtype=float) / 24
    start = 12
    normals = np.sin(np.arange(n * 24 * 2, dtype=float).reshape(n, 24, 2) / 17) / 3
    parameters = HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    state = 0.04 if model == "Heston" else 1.0
    if variant == "atom":
        parameters = HestonParameters(100, 0, 0, 0.04, 2, 0.04, 0.3, -0.7)
    if variant == "underresolved":
        normals[:] = 0
    fixing = np.arange(2, 13, 2)
    primitive = teacher_primitives(
        model.lower(),
        parameters,
        normals[:, start:],
        calendar_times=times[start:],
        fixing_indices=fixing,
        spot=100,
        state=state,
        memory_count=6,
        surface=ConstantSourceField(0.0 if variant == "atom" else 0.04)
        if model == "local"
        else None,
        compact_status=True,
    )
    if variant == "invalid1path":
        primitive["path_mask"][5] = False
        primitive["primitive_status"][5] = "invalid"
        primitive["failure_reasons"][5] = "nonfinite_or_nonpositive_state"
        for key in pilot._PATH_KEYS:
            if primitive[key].dtype.kind == "f":
                primitive[key][5] = np.nan
        primitive["local_step_status"][5] = 0
    thresholds = np.array([-0.25, 0.0, 3.0, 6.0, 8.0, 30.0])
    labels = primitive_labels(primitive, thresholds, blocks=16)
    global_id = hashlib.sha256(normals.tobytes()).hexdigest()
    labels["shared_driver_id"] = global_id
    labels["date_index"] = 6
    return {
        "kind": "teacher",
        "driver": None,
        "model": model,
        "seed": 913,
        "original_n": n,
        "path_ids": np.arange(n),
        "cluster_ids": np.arange(n) // (n // 16),
        "restart": {
            "spot": 100.0,
            "state": state,
            "start_index": start,
            "calendar_times": times,
            "fixing_indices": fixing,
        },
        "stream_identity": runner.payload_digest(
            {"seed": 913, "calendar_times": times, "ordering": "path_step_factor"}
        ),
        "global_driver_id": global_id,
        "chunks": [
            {
                "path_start": 0,
                "path_stop": n,
                "global_steps": 24,
                "start_step": start,
                "stop_step": 24,
                "normal_sha256": global_id,
                "slice_sha256": primitive["shared_driver_id"],
                "path_steps": n * 24,
                "normal_expanded_bytes": n * 24 * 16,
            }
        ],
        "driver_mapping": {
            "global_steps": 24,
            "start_step": start,
            "stop_step": 24,
            "original_n": n,
            "aggregation_factor": 1,
            "slice_sha256": primitive["shared_driver_id"],
        },
        "primitives": primitive,
        "thresholds": thresholds,
        "labels": labels,
        "date_index": 6,
        "expenses": [],
        "financial_qualification": "unknown",
    }


def readonly(value):
    if isinstance(value, np.ndarray):
        value.flags.writeable = False
    elif isinstance(value, dict):
        for item in value.values():
            readonly(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            readonly(item)


@pytest.mark.parametrize(
    "model,variant",
    [
        ("Heston", "ordinary"),
        ("local", "ordinary"),
        ("Heston", "invalid1path"),
        ("local", "atom"),
        ("Heston", "underresolved"),
    ],
)
def test_native_teacher_physically_omits_only_11_derived_fields_and_rebuilds_all(
    tmp_path, model, variant
):
    raw = native_teacher(model, variant)
    original = runner.payload_digest(raw)
    readonly(raw)
    path = tmp_path / "teacher"
    pilot.write_pilot_artifact(path, raw)
    metadata, root_arrays, receipt = protocol.read_artifact(path)
    assert "teacher_storage" in metadata, "native completed teacher needs explicit storage recipe"
    assert not root_arrays
    physical, _ = pilot._read_packed_pilot(path, metadata, receipt)
    assert set(physical["labels"]) == set(raw["labels"]) - set(SAMPLES)
    assert set(physical) == set(raw)
    assert runner.payload_digest(raw) == original, "writer must not mutate returned raw"
    restored, _ = pilot.read_pilot_artifact(path)
    runner._same(raw, restored, "full original teacher payload")
    for key in SAMPLES:
        assert restored["labels"][key].shape == (32, 6)
        assert restored["labels"][key].dtype == raw["labels"][key].dtype
    assert restored["labels"]["blocks"] == 16
    assert restored["labels"]["shared_driver_id"] == raw["global_driver_id"]
    assert restored["labels"]["date_index"] == 6
    assert restored["financial_qualification"] == "unknown"
    for pack in path.glob("pack*"):
        with zipfile.ZipFile(pack / "arrays.npz") as archive:
            assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in archive.infolist())


@pytest.mark.parametrize("field", SAMPLES)
def test_writer_rejects_each_original_derived_sample_tamper(tmp_path, field):
    raw = native_teacher()
    raw["labels"][field] = raw["labels"][field].copy()
    raw["labels"][field][0, 2] += 0.01
    with pytest.raises(ValueError, match=r"teacher.*(sample|label|reconstruct|value)"):
        pilot.write_pilot_artifact(tmp_path / "bad", raw)
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize(
    "field",
    [
        "f",
        "component_means",
        "block_means",
        "joint_block_covariance",
        "status",
    ],
)
def test_reader_checks_independently_stored_original_summary(field):
    helper = storage()
    physical, descriptor = helper.prepare_teacher(native_teacher())
    physical = copy.deepcopy(physical)
    if field == "status":
        physical["labels"][field][2] = "unknown_atom"
    else:
        physical["labels"][field].flat[0] += 0.01
    descriptor["physical_payload_sha256"] = runner.payload_digest(physical)
    with pytest.raises(ValueError, match=r"teacher.*(summary|label|reconstruct|value)"):
        helper.restore_teacher(physical, descriptor)


@pytest.mark.parametrize(
    "change",
    [
        "recipe",
        "source",
        "missing_sample_spec",
        "extra_sample_spec",
        "sample_shape",
        "sample_dtype",
        "missing_primitive",
        "primitive_dtype",
        "N",
        "path_order",
        "cluster_order",
        "threshold_order",
        "global_driver",
    ],
)
def test_teacher_reader_rejects_recipe_or_original_scope_mutation(change):
    helper = storage()
    physical, descriptor = helper.prepare_teacher(native_teacher())
    physical, descriptor = copy.deepcopy((physical, descriptor))
    if change == "recipe":
        descriptor["recipe"] = "arbitrary_callable"
    elif change == "source":
        descriptor["source_bindings"][next(iter(descriptor["source_bindings"]))] = "0" * 64
    elif change == "missing_sample_spec":
        del descriptor["samples"]["f_samples"]
    elif change == "extra_sample_spec":
        descriptor["samples"]["new_estimator"] = descriptor["samples"]["f_samples"]
    elif change == "sample_shape":
        descriptor["samples"]["cv_samples"]["shape"] = [16, 6]
    elif change == "sample_dtype":
        descriptor["samples"]["cv_samples"]["dtype"] = "<f4"
    elif change == "missing_primitive":
        del physical["primitives"]["last_z"]
    elif change == "primitive_dtype":
        physical["primitives"]["last_z"] = physical["primitives"]["last_z"].astype("float32")
    elif change == "N":
        physical["original_n"] = 16
    elif change == "path_order":
        physical["path_ids"] = physical["path_ids"][::-1].copy()
    elif change == "cluster_order":
        physical["cluster_ids"] = physical["cluster_ids"][::-1].copy()
    elif change == "threshold_order":
        physical["thresholds"] = physical["thresholds"][::-1].copy()
    elif change == "global_driver":
        physical["global_driver_id"] = "0" * 64
    descriptor["physical_payload_sha256"] = runner.payload_digest(physical)
    with pytest.raises(ValueError):
        helper.restore_teacher(physical, descriptor)


@pytest.mark.parametrize(
    "status",
    [
        "failed_at_declared_cap",
        "unclosed_source_or_solver_defect",
    ],
)
def test_teacher_failure_roots_keep_literal_all_raw_and_unknown(tmp_path, status):
    raw = {
        "kind": "teacher",
        "status": status,
        "original_n": 32,
        "labels": None,
        "raw_chunks": [np.array([np.nan, 0.0])],
        "executed_path_ids": np.arange(8),
        "unexecuted_path_count": 24,
        "financial_qualification": "unknown",
        "cap_evidence": None,
    }
    pilot.write_pilot_artifact(tmp_path / "failure", raw)
    metadata, _, _ = protocol.read_artifact(tmp_path / "failure")
    assert "teacher_storage" not in metadata
    restored, _ = pilot.read_pilot_artifact(tmp_path / "failure")
    runner._same(raw, restored, "full literal failure")
    for pack in (tmp_path / "failure").glob("pack*"):
        with zipfile.ZipFile(pack / "arrays.npz") as archive:
            assert all(i.compress_type == zipfile.ZIP_STORED for i in archive.infolist())


def test_nested_teacher_and_unrelated_artifacts_stay_literal(tmp_path):
    raw = {"kind": "other", "teacher": native_teacher()}
    pilot.write_pilot_artifact(tmp_path / "nested", raw)
    metadata, _, _ = protocol.read_artifact(tmp_path / "nested")
    assert "teacher_storage" not in metadata
    restored, _ = pilot.read_pilot_artifact(tmp_path / "nested")
    runner._same(raw, restored, "unrelated literal payload")


def test_new_node_binds_physical_origin_and_legacy_literal_remains_compatible(tmp_path):
    raw = native_teacher()
    pilot.write_pilot_artifact(tmp_path / "teacher", raw)
    assert hasattr(pilot, "_teacher_node_binding"), "teacher nodes need explicit binding kind"
    binding = pilot._teacher_node_binding(tmp_path / "teacher", raw)
    assert binding["kind"] == "teacher_recipe_physical_v1"
    restored, _ = pilot.read_pilot_artifact(tmp_path / "teacher")
    node = {"raw_binding": binding}
    pilot._check_teacher_node_binding(node, tmp_path / "teacher", restored)
    changed = copy.deepcopy(node)
    changed["raw_binding"]["artifact_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=r"teacher.*binding"):
        pilot._check_teacher_node_binding(changed, tmp_path / "teacher", restored)
    literal = {
        "kind": "teacher",
        "status": "failed_at_declared_cap",
        "labels": None,
        "original_n": 32,
    }
    pilot.write_pilot_artifact(tmp_path / "literal", literal)
    pilot._check_teacher_node_binding(
        {"raw_sha256": runner.payload_digest(literal)}, tmp_path / "literal", literal
    )


def test_numeric_reconstruction_tolerance_is_not_a_full_sample_sha_gate(tmp_path, monkeypatch):
    helper = storage()
    raw = native_teacher()
    pilot.write_pilot_artifact(tmp_path / "teacher", raw)
    node = {"raw_binding": pilot._teacher_node_binding(tmp_path / "teacher", raw)}
    original = helper.primitive_labels

    def tiny_rounding(*args, **kwargs):
        result = original(*args, **kwargs)
        for key in SAMPLES:
            result[key] = result[key].copy()
            result[key][0, 2] += 1e-12
        return result

    monkeypatch.setattr(helper, "primitive_labels", tiny_rounding)
    restored, _ = pilot.read_pilot_artifact(tmp_path / "teacher")
    assert runner.payload_digest(restored) != runner.payload_digest(raw)
    runner._same(raw, restored, "allowed numeric reconstruction roundoff")
    pilot._check_teacher_node_binding(node, tmp_path / "teacher", restored)


def test_node_physical_origin_cannot_bind_a_different_returned_producer(tmp_path):
    first = native_teacher()
    other = copy.deepcopy(first)
    other["seed"] += 1
    pilot.write_pilot_artifact(tmp_path / "other", other)
    with pytest.raises(ValueError, match=r"teacher.*(origin|binding)"):
        pilot._teacher_node_binding(tmp_path / "other", first)


def test_unknown_node_binding_kind_never_falls_back_to_literal(tmp_path):
    raw = native_teacher()
    pilot.write_pilot_artifact(tmp_path / "teacher", raw)
    node = {
        "raw_binding": {"kind": "unchecked_foreign_recipe"},
        "raw_sha256": runner.payload_digest(raw),
    }
    with pytest.raises(ValueError, match=r"unknown teacher node binding"):
        pilot._check_teacher_node_binding(node, tmp_path / "teacher", raw)


def test_old_completed_literal_teacher_remains_readable_with_full_keys_and_dtypes(
    tmp_path, monkeypatch
):
    helper = storage()
    raw = native_teacher()
    monkeypatch.setattr(helper, "prepare_teacher", lambda value: (value, None))
    pilot.write_pilot_artifact(tmp_path / "old", raw)
    metadata, _, _ = protocol.read_artifact(tmp_path / "old")
    assert "teacher_storage" not in metadata
    restored, _ = pilot.read_pilot_artifact(tmp_path / "old")
    helper._same(raw, restored, "old literal keys/shape/dtype")
    pilot._check_teacher_node_binding(
        {"raw_sha256": runner.payload_digest(raw)}, tmp_path / "old", restored
    )


@pytest.mark.parametrize("filename", ["metadata.json", "arrays.npz", "receipt.json"])
def test_actual_physical_pack_byte_tamper_is_rejected(tmp_path, filename):
    raw = native_teacher()
    pilot.write_pilot_artifact(tmp_path / "teacher", raw)
    pack = next((tmp_path / "teacher").glob("pack*"))
    target = pack / filename
    original = target.read_bytes()
    target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(ValueError):
        pilot.read_pilot_artifact(tmp_path / "teacher")


def test_recipe_parts_extra_directory_is_not_an_ignored_sidecar(tmp_path):
    pilot.write_pilot_artifact(tmp_path / "teacher", native_teacher())
    (tmp_path / "teacher" / "pack999999").mkdir()
    with pytest.raises(ValueError, match=r"extra or missing"):
        pilot.read_pilot_artifact(tmp_path / "teacher")
