"""New transport wiring and genuine legacy artifact compatibility; no formal finance."""

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import run_pilot as pilot  # noqa: E402
import run_reference as runner  # noqa: E402

from deep_hedge_price import _dynamic_hedging_protocol as protocol  # noqa: E402

NEW_SCHEMA = "rb-f04-pilot-typed-dag-v1"


def test_default_non_teacher_writer_and_reader_use_new_schema_without_mutable_aliases(tmp_path):
    array = np.arange(16.0).reshape(4, 4)
    shared = {"values": array, "status": np.array(["ready", "unknown"]), "expense": {"wall": 3.0}}
    payload = {
        "kind": "derived",
        "rows": [shared, shared],
        "original_n": 65536,
        "thresholds": np.linspace(0, 1, 65),
        "blocks": np.arange(16),
    }
    pilot.write_pilot_artifact(tmp_path / "raw", payload)
    metadata, _, _ = protocol.read_artifact(tmp_path / "raw")
    assert metadata["schema"] == NEW_SCHEMA
    restored, _ = pilot.read_pilot_artifact(tmp_path / "raw")
    runner._same(payload, restored, "full original logical payload")
    assert restored["rows"][0] is not restored["rows"][1]
    assert restored["rows"][0]["expense"] is not restored["rows"][1]["expense"]
    left, right = restored["rows"][0]["values"], restored["rows"][1]["values"]
    assert left.flags.writeable and right.flags.writeable
    assert not np.shares_memory(left, right)
    left[0, 0] = -7
    restored["rows"][0]["expense"]["wall"] = 9
    assert right[0, 0] == pytest.approx(0)
    assert restored["rows"][1]["expense"]["wall"] == pytest.approx(3)
    assert array[0, 0] == pytest.approx(0)


def test_genuine_legacy_packed_schema_is_still_readable(tmp_path):
    raw = {"original_n": 32, "status": "unknown", "raw": np.array([1.0, np.nan, 0.0])}
    arrays = {}
    tree = runner._encode_tree(raw, arrays)
    key, array = next(iter(arrays.items()))
    path = tmp_path / "legacy"
    protocol.write_artifact(
        path,
        metadata={
            "schema": pilot.PACK_SCHEMA,
            "tree": tree,
            "arrays": {
                key: {
                    "shape": list(array.shape),
                    "dtype": array.dtype.str,
                    "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
                    "parts": [
                        {
                            "id": "pack000000",
                            "value_key": "value000000",
                            "start": 0,
                            "stop": len(array),
                        }
                    ],
                }
            },
        },
        arrays={},
    )
    protocol.write_artifact(
        path / "pack000000",
        metadata={
            "schema": pilot.PACK_SCHEMA,
            "part": "pack000000",
            "entries": {"value000000": {"array": key, "start": 0, "stop": len(array)}},
        },
        arrays={"value000000": array},
    )
    restored, _ = pilot.read_pilot_artifact(path)
    runner._same(raw, restored, "genuine original packed payload")


def test_unknown_schema_is_not_a_legacy_or_new_codec_fallback(tmp_path):
    protocol.write_artifact(
        tmp_path / "unknown", metadata={"schema": "unchecked-new-schema"}, arrays={}
    )
    with pytest.raises(ValueError, match="not a pilot"):
        pilot.read_pilot_artifact(tmp_path / "unknown")


def test_transport_is_mandatory_execution_source(tmp_path, monkeypatch):
    names = [
        "reference_methods",
        "run_fresh",
        "check_fresh",
        "run_pilot",
        "check_pilot",
        "run_main",
        "check_main",
        "run_reference",
        "check_initial_quotes",
        "check_selected_calls",
    ]
    base = tmp_path / "johnhull/research/RB-F04/dynamic_hedging"
    base.mkdir(parents=True)
    for name in names:
        (base / f"{name}.py").write_text("# fake execution source\\n")
    closure = tmp_path / "deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_closure.py"
    closure.parent.mkdir(parents=True)
    closure.write_text("# fake closure source\\n")
    monkeypatch.setattr(runner, "source_identity", lambda *a, **k: {})
    with pytest.raises(ValueError, match="required execution source missing: _pilot_transport"):
        runner.execution_source_identity(tmp_path)


def test_transport_is_in_the_transitive_execution_closure():
    identity = runner.execution_source_identity()
    assert "johnhull/research/RB-F04/dynamic_hedging/_pilot_transport.py" in identity["files"]
    assert identity["dynamic_imports"] == []


def test_root_invalid_npy_header_rejected_before_protocol_array_read(tmp_path, monkeypatch):
    path = tmp_path / "malformed-root"
    path.mkdir()
    header = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        header, {"descr": "|u1", "fortran_order": False, "shape": (1073741824,)}
    )
    pack = io.BytesIO()
    with zipfile.ZipFile(pack, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("blob.npy", header.getvalue())
    manifest = {
        "schema": "rb-f04-array-chunk-v1",
        "metadata": {"schema": NEW_SCHEMA},
        "arrays": {"blob": {"dtype": "|u1", "shape": [1073741824], "nbytes": 1073741824}},
    }
    metadata_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    receipt = {
        "schema": "rb-f04-array-receipt-v1",
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "arrays_sha256": hashlib.sha256(pack.getvalue()).hexdigest(),
        "uncompressed_bytes": len(header.getvalue()),
    }
    receipt["artifact_sha256"] = protocol._digest(receipt)
    (path / "metadata.json").write_bytes(metadata_bytes)
    (path / "arrays.npz").write_bytes(pack.getvalue())
    (path / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(1)
        pytest.fail("protocol array allocation reached before root-empty validation")

    monkeypatch.setattr(protocol, "read_artifact", forbidden)
    with pytest.raises(ValueError, match="root must not contain arrays"):
        pilot.read_pilot_artifact(path)
    assert calls == []
