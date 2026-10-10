"""Closed native teacher storage recipe; provenance and numeric replay stay separate.

Only completed root teachers use this representation. All physical primitives,
original summaries and metadata survive. Eleven explicitly derived sample keys
are reconstructed by the source-bound primitive_labels formula at full N.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import run_reference as runner
from hullkit import _dynamic_hedging_conditional as conditional
from hullkit._dynamic_hedging_conditional import primitive_labels

from deep_hedge_price import _dynamic_hedging_protocol as protocol

SCHEMA = "rb-f04-native-teacher-storage-v1"
RECIPE = "primitive_labels-global-driver-date-v1"
SAMPLE_FIELDS = (
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
_FLOAT_PATHS = (
    "b",
    "c",
    "mu",
    "sigma",
    "last_z",
    "last_left_spot",
    "last_left_variance",
    "last_left_coefficient",
    "aux_logG_prefix",
)
_PRIMITIVE_FIELDS = set(_FLOAT_PATHS) | {
    "model",
    "spot",
    "state",
    "memory_count",
    "total_fixings",
    "calendar_times",
    "fixing_indices",
    "fixing_delays",
    "expiry_delay",
    "rate",
    "dividend_yield",
    "original_path_count",
    "N",
    "shared_driver_id",
    "shared_driver_scope",
    "aux_last_loading",
    "control_variance",
    "control_status",
    "aux_first_midpoint",
    "path_mask",
    "primitive_status",
    "failure_reasons",
    "local_step_status",
    "local_step_status_encoding",
    "local_step_status_labels",
    "analytic_conditional",
    "deterministic_model",
    "f_units",
}
_ROOT_FIELDS = {
    "kind",
    "driver",
    "restart",
    "model",
    "seed",
    "original_n",
    "path_ids",
    "cluster_ids",
    "stream_identity",
    "global_driver_id",
    "chunks",
    "driver_mapping",
    "primitives",
    "thresholds",
    "labels",
    "date_index",
    "expenses",
    "financial_qualification",
}
_DESCRIPTOR_FIELDS = {
    "schema",
    "recipe",
    "source_bindings",
    "samples",
    "origin",
    "physical_payload_sha256",
}


def _require(condition, message):
    if not condition:
        raise ValueError("teacher storage: " + message)


def source_bindings():
    """Bind only fixed recipe source files; no executable names from storage."""
    return {
        "teacher_storage": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "primitive_labels": hashlib.sha256(Path(conditional.__file__).read_bytes()).hexdigest(),
    }


def _same(expected, saved, name):
    """Finance uses existing runner rtol=2e-9/atol=2e-10; shape/dtype/unknown remain exact."""
    if isinstance(expected, dict):
        _require(
            isinstance(saved, dict) and set(expected) == set(saved), name + " label keys differ"
        )
        for key, value in expected.items():
            _same(value, saved[key], name + "." + key)
        return
    if isinstance(expected, np.ndarray):
        _require(
            isinstance(saved, np.ndarray)
            and expected.shape == saved.shape
            and expected.dtype == saved.dtype,
            name + " label shape/dtype differ",
        )
    runner._same(expected, saved, "teacher storage " + name)


def _validate_root(raw):
    _require(isinstance(raw, dict) and _ROOT_FIELDS <= set(raw), "native root fields missing")
    _require(raw["kind"] == "teacher" and raw.get("status") is None, "completed root required")
    n = raw["original_n"]
    p = raw["primitives"]
    _require(isinstance(n, int) and n >= 16 and n % 16 == 0, "original 16-block N required")
    _require(isinstance(p, dict) and _PRIMITIVE_FIELDS <= set(p), "primitive fields missing")
    _require(p["N"] == p["original_path_count"] == n, "primitive original N differs")
    _require(
        raw["model"] in ("Heston", "local") and p["model"] == raw["model"].lower(),
        "original model differs",
    )
    _require(np.array_equal(raw["path_ids"], np.arange(n)), "original path order differs")
    _require(
        np.array_equal(raw["cluster_ids"], np.arange(n) // (n // 16)),
        "original 16-block cluster order differs",
    )
    for key in _FLOAT_PATHS:
        value = p[key]
        _require(
            isinstance(value, np.ndarray) and value.shape == (n,) and value.dtype == np.float64,
            key + " primitive shape/dtype differs",
        )
    for key, kind in (("path_mask", "b"), ("primitive_status", "U"), ("failure_reasons", "U")):
        value = p[key]
        _require(
            isinstance(value, np.ndarray) and value.shape == (n,) and value.dtype.kind == kind,
            key + " original shape/dtype differs",
        )
    fixing = np.asarray(p["fixing_indices"])
    step = p["local_step_status"]
    original_steps = int(fixing[-1]) if len(fixing) else 0
    _require(
        isinstance(step, np.ndarray) and step.shape == (n, original_steps),
        "full original local step status differs",
    )
    if p["local_step_status_encoding"] == "uint8_dictionary":
        legend = p["local_step_status_labels"]
        _require(
            step.dtype == np.uint8
            and isinstance(legend, np.ndarray)
            and legend.ndim == 1
            and 1 <= len(legend) <= 256
            and legend.dtype.kind == "U"
            and legend[0] == ""
            and len(set(legend.tolist())) == len(legend)
            and np.all(step < len(legend)),
            "step status dictionary differs",
        )
    else:
        _require(
            p["local_step_status_encoding"] == "unicode"
            and step.dtype.kind == "U"
            and p["local_step_status_labels"] is None,
            "original step status encoding differs",
        )
    x = raw["thresholds"]
    _require(
        isinstance(x, np.ndarray)
        and x.dtype == np.float64
        and x.ndim == 1
        and len(x) > 0
        and np.isfinite(x).all()
        and np.all(np.diff(x) > 0),
        "original threshold shape/dtype/order differs",
    )
    _require(
        raw["driver_mapping"]["original_n"] == n
        and raw["driver_mapping"]["aggregation_factor"] == 1
        and raw["driver_mapping"]["slice_sha256"] == p["shared_driver_id"],
        "original driver mapping differs",
    )
    _require(raw["date_index"] == p["memory_count"], "original teacher date differs")
    _require(isinstance(raw["labels"], dict), "original labels missing")


def _origin(raw):
    """Exact source/input/driver provenance, never a regenerated sample hash."""
    keys = (
        "model",
        "seed",
        "original_n",
        "path_ids",
        "cluster_ids",
        "restart",
        "stream_identity",
        "global_driver_id",
        "driver_mapping",
        "chunks",
        "thresholds",
        "date_index",
        "driver",
    )
    return runner.payload_digest({key: raw[key] for key in keys})


def _labels(raw):
    labels = primitive_labels(raw["primitives"], raw["thresholds"], blocks=16)
    labels["shared_driver_id"] = raw["global_driver_id"]
    labels["date_index"] = raw["date_index"]
    return labels


def prepare_teacher(raw):
    """Check original full labels first; omit only the fixed eleven fields."""
    if not isinstance(raw, dict) or raw.get("kind") != "teacher" or raw.get("status") is not None:
        return raw, None
    _validate_root(raw)
    rebuilt = _labels(raw)
    _same(rebuilt, raw["labels"], "writer original labels")
    physical = dict(raw, labels={k: v for k, v in raw["labels"].items() if k not in SAMPLE_FIELDS})
    descriptor = {
        "schema": SCHEMA,
        "recipe": RECIPE,
        "source_bindings": source_bindings(),
        "samples": {
            key: {"shape": list(raw["labels"][key].shape), "dtype": raw["labels"][key].dtype.str}
            for key in SAMPLE_FIELDS
        },
        "origin": _origin(raw),
        "physical_payload_sha256": runner.payload_digest(physical),
    }
    return physical, descriptor


def restore_teacher(physical, descriptor):
    """Replay all samples while preserving independently stored summaries."""
    _require(
        isinstance(descriptor, dict) and set(descriptor) == _DESCRIPTOR_FIELDS,
        "recipe descriptor keys differ",
    )
    _require(
        descriptor["schema"] == SCHEMA and descriptor["recipe"] == RECIPE, "unknown recipe/schema"
    )
    _require(descriptor["source_bindings"] == source_bindings(), "recipe source binding differs")
    _validate_root(physical)
    _require(
        not (set(SAMPLE_FIELDS) & set(physical["labels"])),
        "physical recipe contains extra derived samples",
    )
    _require(
        descriptor["physical_payload_sha256"] == runner.payload_digest(physical),
        "physical payload provenance differs",
    )
    _require(descriptor["origin"] == _origin(physical), "original input/driver origin differs")
    rebuilt = _labels(physical)
    expected_specs = {
        key: {"shape": list(rebuilt[key].shape), "dtype": rebuilt[key].dtype.str}
        for key in SAMPLE_FIELDS
    }
    _require(
        descriptor["samples"] == expected_specs, "sample manifest shape/dtype/coverage differs"
    )
    summaries = {k: v for k, v in rebuilt.items() if k not in SAMPLE_FIELDS}
    _same(summaries, physical["labels"], "reader original summary")
    labels = dict(physical["labels"])
    labels.update({key: rebuilt[key] for key in SAMPLE_FIELDS})
    return dict(physical, labels=labels)


def check_returned_origin(raw, descriptor):
    """Bind original physical inputs/summaries without hashing rebuilt samples."""
    _validate_root(raw)
    physical = dict(raw, labels={k: v for k, v in raw["labels"].items() if k not in SAMPLE_FIELDS})
    _require(
        descriptor["physical_payload_sha256"] == runner.payload_digest(physical),
        "returned physical origin binding differs",
    )
    _require(descriptor["origin"] == _origin(raw), "returned input/driver origin binding differs")


def physical_artifact_binding(directory):
    """Authenticate root and all physical NPZ receipts, independent of replay floats."""
    directory = Path(directory)
    metadata, arrays, receipt = protocol.read_artifact(directory)
    descriptor = metadata.get("teacher_storage")
    _require(not arrays and isinstance(descriptor, dict), "physical recipe binding missing")
    _require(
        descriptor.get("schema") == SCHEMA and descriptor.get("recipe") == RECIPE,
        "unknown physical binding recipe",
    )
    _require(
        descriptor.get("source_bindings") == source_bindings(), "physical binding source differs"
    )
    # Root descriptors bind the expanded primitive/summary bytes; receipts bind
    # exact compressed physical bytes. The reader independently checks coverage.
    parts = {ref["id"] for row in metadata["arrays"].values() for ref in row["parts"]}
    _require(
        {p.name for p in directory.iterdir() if p.is_dir()} == parts,
        "physical binding extra/missing packs",
    )
    pack_receipts = {}
    for identifier in sorted(parts):
        _require(Path(identifier).name == identifier, "invalid physical pack identifier")
        _, _, part_receipt = protocol.read_artifact(directory / identifier)
        pack_receipts[identifier] = part_receipt["artifact_sha256"]
    origin = {"root": receipt["artifact_sha256"], "packs": pack_receipts}
    return {
        "kind": "teacher_recipe_physical_v1",
        "artifact_sha256": runner._digest(origin),
        "root_artifact_sha256": receipt["artifact_sha256"],
        "packs": pack_receipts,
        "recipe": RECIPE,
        "source_bindings": descriptor["source_bindings"],
    }
