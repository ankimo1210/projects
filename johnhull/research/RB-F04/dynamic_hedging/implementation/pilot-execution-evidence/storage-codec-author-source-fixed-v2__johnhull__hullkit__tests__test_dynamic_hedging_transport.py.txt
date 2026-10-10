"""Small synthetic transport checks; storage provenance, not finance qualification."""

import copy
import hashlib
import importlib
import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import run_reference as runner  # noqa: E402

from deep_hedge_price import _dynamic_hedging_protocol as protocol  # noqa: E402


def codec():
    return importlib.import_module("_pilot_transport")


def write_read(tmp_path, payload, limit=256):
    destination = tmp_path / "saved"
    receipt = codec().write_transport(
        destination, payload, protocol=protocol, runner=runner, page_raw_limit=limit
    )
    metadata, arrays, read_receipt = protocol.read_artifact(destination)
    assert arrays == {}
    assert receipt == read_receipt  # Physical receipt provenance.
    recovered, result_receipt = codec().read_transport(
        destination, metadata, receipt, protocol=protocol, runner=runner
    )
    assert result_receipt == receipt
    assert runner.payload_digest(recovered) == runner.payload_digest(payload)
    return destination, metadata, receipt, recovered


def replace_root(path, metadata):
    """Re-seal only a synthetic root, so format checks cannot rely on its SHA."""
    _, _, old_receipt = protocol.read_artifact(path)
    staging = path.parent / "new-root"
    receipt = protocol.write_artifact(staging, metadata=metadata, arrays={})
    for name in ("metadata.json", "arrays.npz", "receipt.json"):
        (path / name).write_bytes((staging / name).read_bytes())
    return receipt, old_receipt


def replace_page(path, ref, raw=None, compressed=None, metadata_change=None):
    metadata, _, _ = protocol.read_artifact(path / ref["path"])
    if raw is not None:
        compressed = zlib.compress(raw)
        metadata["expanded_length"] = len(raw)
        ref["expanded_length"] = len(raw)
    if metadata_change:
        metadata.update(metadata_change)
    staging = path.parent / "new-page"
    receipt = protocol.write_artifact(
        staging, metadata=metadata, arrays={"blob": np.frombuffer(compressed, dtype=np.uint8)}
    )
    for name in ("metadata.json", "arrays.npz", "receipt.json"):
        (path / ref["path"] / name).write_bytes((staging / name).read_bytes())
    ref["receipt"] = receipt


def test_empty_payload_has_one_metadata_page(tmp_path):
    _, metadata, _, recovered = write_read(tmp_path, {})
    assert recovered == {}
    assert metadata["schema"] == "rb-f04-pilot-typed-dag-v1"
    assert metadata["array_count"] == 0
    assert [page["kind"] for page in metadata["pages"]] == ["metadata"]


def test_normalization_and_independent_occurrences(tmp_path):
    parameters = runner.HestonParameters(100, 0.03, 0, 0.04, 2, 0.04, 0.3, -0.7)
    array = np.arange(12.0).reshape(3, 4)
    shared = {"array": array, "nested": [1, 1.0, True, -0.0, np.float64(2)]}
    payload = {
        "a": shared,
        "b": shared,
        "parameters": (parameters, parameters),
        "nonfinite": [np.nan, np.inf, -np.inf],
        "status": "unknown",
        "cost": {"seconds": 1.2},
        "fits": [{"id": i, "status": "failed"} for i in range(12)],
        "blocks": np.arange(16),
    }
    _, _, _, recovered = write_read(tmp_path, payload)
    runner._same(recovered, payload, "full logical payload")
    assert recovered["a"] is not recovered["b"]
    assert recovered["a"]["nested"] is not recovered["b"]["nested"]
    assert recovered["parameters"][0] is not recovered["parameters"][1]
    left, right = recovered["a"]["array"], recovered["b"]["array"]
    assert left.flags.writeable and right.flags.writeable
    assert not np.shares_memory(left, right)
    left[0, 0] = -10
    recovered["a"]["nested"].append(3)
    assert right[0, 0] == pytest.approx(0)
    assert len(recovered["b"]["nested"]) == 5
    assert np.signbit(recovered["a"]["nested"][3])


@pytest.mark.parametrize(
    "array",
    [
        np.array(3.5),
        np.empty((0, 2), dtype=">f8"),
        np.array([1, np.nan, np.inf, -0.0], dtype=">f8"),
        np.arange(24).reshape(4, 6)[:, ::2],
        np.asfortranarray(np.arange(12.0).reshape(3, 4)),
        np.array([(1, 2.5), (3, -0.0)], dtype=[("a", ">i4"), ("b", "<f8")]),
        np.array([(1,)], dtype=[("\u91d1", "<i4")]),
    ],
)
def test_npy_types_and_layout(tmp_path, array):
    _, _, _, recovered = write_read(tmp_path, {"x": array, "y": array})
    assert recovered["x"].dtype == array.dtype
    assert recovered["x"].shape == array.shape
    np.testing.assert_array_equal(recovered["x"], array)
    assert not np.shares_memory(recovered["x"], recovered["y"])
    assert recovered["x"].flags.writeable


def test_same_bytes_different_type_and_shape_not_interned(tmp_path):
    payload = {
        "int": np.array([1065353216], dtype=np.int32),
        "float": np.array([1.0], dtype=np.float32),
        "matrix": np.array([[1.0]], dtype=np.float32),
        "structured1": np.array([(1,)], dtype=[("one", "i4")]),
        "structured2": np.array([(1,)], dtype=[("two", "i4")]),
    }
    _, metadata, _, recovered = write_read(tmp_path, payload)
    assert metadata["array_count"] == 5
    for key in payload:
        assert recovered[key].dtype == payload[key].dtype
        np.testing.assert_array_equal(recovered[key], payload[key])


def test_pages_cross_array_and_metadata_boundaries(tmp_path):
    payload = [{"value": np.arange(257.0), "long": "a" * 401} for _ in range(17)]
    path, metadata, _, recovered = write_read(tmp_path, payload, 128)
    array_pages = [p for p in metadata["pages"] if p["kind"] == "arrays"]
    meta_pages = [p for p in metadata["pages"] if p["kind"] == "metadata"]
    assert len(array_pages) > 1 and len(meta_pages) > 1
    assert all(0 < p["expanded_length"] <= 128 for p in metadata["pages"])
    assert metadata["array_count"] == 1
    assert len(recovered) == 17
    for page in metadata["pages"]:
        page_metadata, arrays, _ = protocol.read_artifact(path / page["path"])
        assert arrays["blob"].dtype == np.uint8
        assert len(zlib.decompress(arrays["blob"].tobytes())) == page_metadata["expanded_length"]


@pytest.mark.parametrize("change", ["missing", "extra", "reordered", "gap", "unsafe"])
def test_root_page_roster_rejects_self_consistent_tamper(tmp_path, change):
    path, metadata, _, _ = write_read(tmp_path, np.arange(80), 128)
    altered = copy.deepcopy(metadata)
    if change == "missing":
        altered["pages"].pop()
    elif change == "extra":
        (path / "unexpected").mkdir()
    elif change == "reordered":
        altered["pages"].reverse()
    elif change == "gap":
        altered["pages"][0]["offset"] += 1
    else:
        altered["pages"][0]["path"] = "../escape"
    receipt, _ = replace_root(path, altered)
    with pytest.raises(ValueError):
        codec().read_transport(path, altered, receipt, protocol=protocol, runner=runner)


@pytest.mark.parametrize("change", ["overrun", "trailing", "short", "header"])
def test_bounded_page_decoder_rejects_self_consistent_tamper(tmp_path, change):
    path, metadata, _, _ = write_read(tmp_path, np.arange(80), 128)
    altered = copy.deepcopy(metadata)
    ref = next(p for p in altered["pages"] if p["kind"] == "arrays")
    _, arrays, _ = protocol.read_artifact(path / ref["path"])
    raw = zlib.decompress(arrays["blob"].tobytes())
    if change == "overrun":
        compressed = zlib.compress(raw + b"x")
    elif change == "trailing":
        compressed = arrays["blob"].tobytes() + b"trailing"
    elif change == "short":
        compressed = zlib.compress(raw[:-1])
    else:
        changed = bytearray(raw)
        changed[:6] = b"badnpy"
        compressed = zlib.compress(changed)
    replace_page(path, ref, compressed=compressed)
    receipt, _ = replace_root(path, altered)
    with pytest.raises(ValueError):
        codec().read_transport(path, altered, receipt, protocol=protocol, runner=runner)


def test_root_supplied_metadata_and_receipt_are_authenticated(tmp_path):
    path, metadata, receipt, _ = write_read(tmp_path, {"value": 1})
    altered = copy.deepcopy(metadata)
    altered["payload_sha256"] = hashlib.sha256(b"unrelated").hexdigest()
    with pytest.raises(ValueError):
        codec().read_transport(path, altered, receipt, protocol=protocol, runner=runner)


def test_rejects_cycles_objects_symlinks_and_existing_root(tmp_path):
    circular = []
    circular.append(circular)
    for index, payload in enumerate((circular, np.array([object()], dtype=object))):
        with pytest.raises(ValueError):
            codec().write_transport(
                tmp_path / str(index), payload, protocol=protocol, runner=runner
            )
    destination = tmp_path / "exists"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        codec().write_transport(destination, {}, protocol=protocol, runner=runner)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        codec().write_transport(link / "artifact", {}, protocol=protocol, runner=runner)


def test_read_rejects_page_symlink(tmp_path):
    path, metadata, receipt, _ = write_read(tmp_path, np.arange(3))
    ref = metadata["pages"][0]
    page = path / ref["path"]
    moved = tmp_path / "moved"
    page.rename(moved)
    page.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError):
        codec().read_transport(path, metadata, receipt, protocol=protocol, runner=runner)


def test_structured_padding_and_nan_payload_provenance(tmp_path):
    padded = np.ndarray(3, dtype=np.dtype([("first", "i1"), ("second", "i4")], align=True))
    padded.view("u1")[:] = np.arange(padded.nbytes, dtype="u1")
    nan_payload = np.array([0x7FF8000000000001, 0x8000000000000000], dtype="u8").view("f8")
    _, _, _, recovered = write_read(tmp_path, {"pad": [padded, padded], "bits": nan_payload})
    # These are storage-byte provenance assertions, not numerical tolerances.
    assert recovered["pad"][0].tobytes() == padded.tobytes()
    assert recovered["pad"][1].tobytes() == padded.tobytes()
    assert recovered["bits"].tobytes() == nan_payload.tobytes()
    recovered["pad"][0].view("u1")[1] ^= 1
    assert recovered["pad"][1].tobytes() == padded.tobytes()


@pytest.mark.parametrize(
    "change",
    [
        "unused_node",
        "unused_array",
        "forward_edge",
        "node_order",
        "array_gap",
        "array_shape",
        "array_dtype",
        "unknown_tag",
    ],
)
def test_metadata_table_full_coverage_and_types(tmp_path, change):
    path, metadata, _, _ = write_read(tmp_path, {"x": np.arange(3)}, 4096)
    altered = copy.deepcopy(metadata)
    ref = next(p for p in altered["pages"] if p["kind"] == "metadata")
    _, arrays, _ = protocol.read_artifact(path / ref["path"])
    records = [json.loads(line) for line in zlib.decompress(arrays["blob"].tobytes()).splitlines()]
    header = records[0][1]
    node_rows = [row for row in records if row[0] == "node"]
    array_rows = [row for row in records if row[0] == "array"]
    if change == "unused_node":
        records.insert(1 + len(node_rows), ["node", len(node_rows), ["str", "unused"]])
        header["nodes"] += 1
        altered["node_count"] += 1
    elif change == "unused_array":
        records.append(["array", len(array_rows), copy.deepcopy(array_rows[0][2])])
        header["arrays"] += 1
        altered["array_count"] += 1
    elif change == "forward_edge":
        node_rows[-1][2] = ["list", [node_rows[-1][1]]]
    elif change == "node_order":
        node_rows[0][1] += 1
    elif change == "array_gap":
        array_rows[0][2]["offset"] = 1
    elif change == "array_shape":
        array_rows[0][2]["shape"] = [4]
    elif change == "array_dtype":
        array_rows[0][2]["dtype_str"] = "<f8"
    else:
        node_rows[-1][2][0] = "unrecognized"
    raw = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode() for row in records
    )
    replace_page(path, ref, raw=raw)
    altered["metadata_bytes"] = len(raw)
    receipt, _ = replace_root(path, altered)
    with pytest.raises(ValueError):
        codec().read_transport(path, altered, receipt, protocol=protocol, runner=runner)


def test_npy_header_allocation_is_bounded_before_array_creation(tmp_path, monkeypatch):
    path, metadata, _, _ = write_read(tmp_path, np.arange(3), 4096)
    altered = copy.deepcopy(metadata)
    ref = next(p for p in altered["pages"] if p["kind"] == "arrays")
    _, arrays, _ = protocol.read_artifact(path / ref["path"])
    raw = bytearray(zlib.decompress(arrays["blob"].tobytes()))
    assert raw[6:8] == b"\x02\x00"
    raw[8:12] = b"\xff\xff\xff\x7f"
    replace_page(path, ref, raw=raw)
    receipt, _ = replace_root(path, altered)
    with pytest.raises(ValueError, match="oversized NPY header"):
        codec().read_transport(path, altered, receipt, protocol=protocol, runner=runner)


def test_zip_expansion_is_bounded_before_protocol_read(tmp_path):
    import io
    import zipfile

    path, metadata, _, _ = write_read(tmp_path, np.arange(3), 128)
    altered = copy.deepcopy(metadata)
    ref = next(p for p in altered["pages"] if p["kind"] == "arrays")
    metadata_bytes = (path / ref["path"] / "metadata.json").read_bytes()
    # Tiny compressed NPZ with a larger expanded member. Re-seal the physical
    # receipt explicitly so rejection proves the pre-allocation format bound.
    packed = io.BytesIO()
    np.savez_compressed(packed, blob=np.zeros(128 * 1024, dtype="u1"))
    npz = packed.getvalue()
    with zipfile.ZipFile(io.BytesIO(npz)) as archive:
        expanded = sum(item.file_size for item in archive.infolist())
    page_receipt = {
        "schema": "rb-f04-array-receipt-v1",
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "arrays_sha256": hashlib.sha256(npz).hexdigest(),
        "uncompressed_bytes": expanded,
    }
    page_receipt["artifact_sha256"] = runner._digest(page_receipt)
    (path / ref["path"] / "arrays.npz").write_bytes(npz)
    (path / ref["path"] / "receipt.json").write_text(
        json.dumps(page_receipt, sort_keys=True, separators=(",", ":"))
    )
    ref["receipt"] = page_receipt
    receipt, _ = replace_root(path, altered)

    class ObservedProtocol:
        def __init__(self):
            self.reads = []

        def read_artifact(self, directory):
            self.reads.append(Path(directory))
            return protocol.read_artifact(directory)

    observer = ObservedProtocol()
    with pytest.raises(ValueError, match="NPY container"):
        codec().read_transport(path, altered, receipt, protocol=observer, runner=runner)
    assert path / ref["path"] not in observer.reads


def test_page_physical_receipt_and_root_file_symlink(tmp_path):
    path, metadata, receipt, _ = write_read(tmp_path, {"x": np.arange(3)})
    page = path / metadata["pages"][0]["path"] / "arrays.npz"
    physical = bytearray(page.read_bytes())
    physical[-1] ^= 1
    page.write_bytes(physical)
    with pytest.raises(ValueError):
        codec().read_transport(path, metadata, receipt, protocol=protocol, runner=runner)
    metadata_file = path / "metadata.json"
    metadata_file.rename(tmp_path / "root-meta")
    metadata_file.symlink_to(tmp_path / "root-meta")
    with pytest.raises(ValueError, match="root file"):
        codec().read_transport(path, metadata, receipt, protocol=protocol, runner=runner)


@pytest.mark.parametrize("failure", ["page", "publish"])
def test_writer_failure_does_not_expose_or_overwrite_root(tmp_path, monkeypatch, failure):
    destination = tmp_path / "saved"
    if failure == "page":

        class FailedProtocol:
            def write_artifact(self, directory, **kwargs):
                raise OSError("synthetic page failure")

        selected = FailedProtocol()
    else:
        selected = protocol

        def fail_publish(*args):
            raise OSError("synthetic publish failure")

        monkeypatch.setattr(codec().os, "replace", fail_publish)
    with pytest.raises(OSError):
        codec().write_transport(destination, {"x": np.arange(3)}, protocol=selected, runner=runner)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "descriptor,order,shape,body",
    [
        ("|u1", False, (1073741824,), b""),
        ("|u1", False, (17,), b""),
        ("<i4", False, (1,), b"\0" * 4),
        ("|u1", True, (1,), b"\0"),
        ("|u1", False, (1, 1), b"\0"),
        ("|u1", False, (True,), b"\0"),
    ],
)
def test_page_blob_npy_header_is_checked_before_protocol_allocation(
    tmp_path, descriptor, order, shape, body
):
    import io
    import struct
    import zipfile

    path, metadata, _, _ = write_read(tmp_path, np.arange(3), 256)
    altered = copy.deepcopy(metadata)
    ref = next(p for p in altered["pages"] if p["kind"] == "arrays")
    page = path / ref["path"]
    manifest = json.loads((page / "metadata.json").read_bytes())
    header = repr({"descr": descriptor, "fortran_order": order, "shape": shape}).encode()
    header += b" " * max(0, 70 - len(header) - 1) + b"\n"
    npy = np.lib.format.magic(1, 0) + struct.pack("<H", len(header)) + header + body
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("blob.npy", npy)
    manifest["arrays"] = {
        "blob": {
            "dtype": descriptor,
            "shape": list(shape),
            "nbytes": int(np.prod(shape)) * np.dtype(descriptor).itemsize,
        }
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    npz = packed.getvalue()
    page_receipt = {
        "schema": "rb-f04-array-receipt-v1",
        "metadata_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "arrays_sha256": hashlib.sha256(npz).hexdigest(),
        "uncompressed_bytes": len(npy),
    }
    page_receipt["artifact_sha256"] = runner._digest(page_receipt)
    (page / "metadata.json").write_bytes(manifest_bytes)
    (page / "arrays.npz").write_bytes(npz)
    (page / "receipt.json").write_text(
        json.dumps(page_receipt, sort_keys=True, separators=(",", ":"))
    )
    ref["receipt"] = page_receipt
    receipt, _ = replace_root(path, altered)

    class ObservedProtocol:
        def __init__(self):
            self.forbidden_reads = 0

        def read_artifact(self, directory):
            if Path(directory) == page:
                self.forbidden_reads += 1
                pytest.fail("page array allocation reached before NPY header validation")
            return protocol.read_artifact(directory)

    observer = ObservedProtocol()
    with pytest.raises(ValueError):
        codec().read_transport(path, altered, receipt, protocol=observer, runner=runner)
    assert observer.forbidden_reads == 0


def test_empty_root_container_guard_is_available_before_protocol_read(tmp_path):
    import io
    import struct
    import zipfile

    path = tmp_path / "malformed-root"
    path.mkdir()
    header = b"{'descr': '|u1', 'fortran_order': False, 'shape': (1073741824,), }\n"
    npy = np.lib.format.magic(1, 0) + struct.pack("<H", len(header)) + header
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("blob.npy", npy)
    (path / "arrays.npz").write_bytes(packed.getvalue())
    for name in ("metadata.json", "receipt.json"):
        (path / name).write_text("{}")
    assert hasattr(codec(), "validate_empty_root_container")
    with pytest.raises(ValueError, match="root must not contain arrays"):
        codec().validate_empty_root_container(path)
