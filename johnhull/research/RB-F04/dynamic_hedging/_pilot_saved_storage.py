"""Private saved-pilot references and original-format streaming provenance.

Only one requested saved payload is decoded at a time. Full numerical reports
remain in immutable artifacts; hashes establish provenance, not correctness.
A single decoded job and a numerical comparison can still exceed a RAM cap.
"""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path

import numpy as np
from hullkit._heston_local_surface import HestonParameters

_JSON = json.JSONEncoder(sort_keys=True, separators=(",", ":"), allow_nan=False)
_CHECK_SCHEMA = "rb-f04-pilot-saved-check-value-v1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


class DeferredSequence(Sequence):
    """Read an ordered logical sequence without retaining returned payloads."""

    def __init__(self, length, load):
        self.length, self.load = length, load

    def __len__(self):
        return self.length

    def __getitem__(self, index):
        if isinstance(index, slice):
            indices = range(self.length)[index]
            return DeferredSequence(len(indices), lambda i: self.load(indices[i]))
        if index < 0:
            index += self.length
        if not 0 <= index < self.length:
            raise IndexError(index)
        return self.load(index)

    def __iter__(self):
        for index in range(self.length):
            yield self.load(index)


def _array_digest(value):
    _require(not value.dtype.hasobject, "object array prohibited in saved provenance")
    digest = hashlib.sha256()
    chunk_bytes = 65536
    if value.flags.c_contiguous:
        view = memoryview(value).cast("B") if value.size else memoryview(b"")
        for start in range(0, len(view), chunk_bytes):
            digest.update(view[start : start + chunk_bytes])
    else:
        # Structured padding has no stable buffered-copy convention. Financial
        # arrays are numeric; refuse this unsupported transport shape explicitly.
        _require(value.dtype.fields is None, "strided structured saved array unsupported")
        iterator = np.nditer(
            value,
            flags=["external_loop", "buffered", "zerosize_ok"],
            op_flags=["readonly"],
            order="C",
            buffersize=max(1, chunk_bytes // value.dtype.itemsize),
        )
        for chunk in iterator:
            digest.update(chunk.tobytes(order="C"))
    return digest.hexdigest()


def payload_digest(payload, *, spool_directory=None):
    """Produce exactly the original tree/array-occurrence digest incrementally.

    Array binding metadata grows with occurrence count. The canonical tree is
    spooled to disk, without retaining arrays from earlier logical rows.
    """
    bindings = {}
    with tempfile.TemporaryFile(mode="w+b", dir=spool_directory) as tree:

        def emit(text):
            tree.write(text.encode("utf-8"))

        def scalar(value):
            for text in _JSON.iterencode(value):
                emit(text)

        def encode(value):
            if isinstance(value, np.ndarray):
                name = f"a{len(bindings):06d}"
                bindings[name] = {
                    "shape": list(value.shape),
                    "dtype": value.dtype.str,
                    "sha256": _array_digest(value),
                }
                scalar({"__array__": name})
            elif isinstance(value, np.generic):
                encode(value.item())
            elif isinstance(value, HestonParameters):
                scalar({"__heston_parameters__": vars(value)})
            elif isinstance(value, float) and not np.isfinite(value):
                scalar(
                    {"__nonfinite__": "nan" if np.isnan(value) else "inf" if value > 0 else "-inf"}
                )
            elif isinstance(value, Mapping):
                keys = sorted(value)
                _require(all(isinstance(k, str) for k in keys), "saved string keys required")
                emit("{")
                for index, key in enumerate(keys):
                    if index:
                        emit(",")
                    scalar(key)
                    emit(":")
                    encode(value[key])
                emit("}")
            elif isinstance(value, (list, tuple, DeferredSequence)):
                emit("[")
                for index in range(len(value)):
                    if index:
                        emit(",")
                    item = value[index]
                    encode(item)
                    del item
                emit("]")
            elif value is None or isinstance(value, (str, int, float, bool)):
                scalar(value)
            else:
                raise ValueError(f"unsupported saved value: {type(value).__name__}")

        encode(payload)
        tree.seek(0)
        digest = hashlib.sha256()
        digest.update(b'{"arrays":')
        for text in _JSON.iterencode(bindings):
            digest.update(text.encode("utf-8"))
        digest.update(b',"tree":')
        while block := tree.read(65536):
            digest.update(block)
        digest.update(b"}")
    return digest.hexdigest()


class ReferenceJobs(Mapping):
    """Verify each requested original immutable job, including failed tail rows."""

    def __init__(self, references, *, artifact_context, reader=None):
        self.references = {r["id"]: r for r in references}
        _require(len(self.references) == len(references), "duplicate original job reference")
        self.artifact_context = dict(artifact_context)
        self.reader = reader

    def __contains__(self, key):
        return key in self.references

    def __iter__(self):
        return iter(self.references)

    def __len__(self):
        return len(self.references)

    def __getitem__(self, key):
        from run_pilot import bound_artifact_path, read_pilot_artifact

        reference = self.references[key]
        path = bound_artifact_path(reference["artifact_path"], self.artifact_context)
        value, _ = (self.reader or read_pilot_artifact)(path)
        _require(
            payload_digest(value) == reference["raw_job_payload_sha256"],
            "immutable original job payload differs from checkpoint",
        )
        _require(value.get("id") == key, "immutable original job ID mismatch")
        return value

    def sequence(self, identifiers=None, *, field=None):
        """Keep all requested IDs in original order; do not infer smaller scope."""
        ids = tuple(self if identifiers is None else identifiers)
        if field is None:
            return DeferredSequence(len(ids), lambda i: self[ids[i]])
        return DeferredSequence(len(ids), lambda i: self[ids[i]][field])


class RecordedJobs(ReferenceJobs):
    """Keep saved runtime rows as original checkpoint references, never raw caches.

    Metadata outside raw is retained exactly, including manifest arrays.
    This removes cumulative raw retention, not the RAM cost of a single job.
    Fresh/resumed registration uses the current artifact root as both roots;
    existing references may be read with a distinct restored root.
    """

    def __init__(self, references=(), *, artifact_context, reader=None):
        _require(
            all("raw" not in r for r in references),
            "runtime job references must exclude full raw payloads",
        )
        super().__init__(
            copy.deepcopy(references), artifact_context=artifact_context, reader=reader
        )

    def register(self, row, artifact_path):
        """Bind one already-written original row without retaining its raw value."""
        from run_pilot import bound_artifact_path

        identifier = row["id"]
        _require(identifier not in self.references, "duplicate runtime job reference")
        path = Path(artifact_path)
        actual = bound_artifact_path(path, self.artifact_context)
        _require(actual.is_dir(), "runtime job must already be saved")
        original = {key: value for key, value in row.items() if key != "artifact_path"}
        digest = payload_digest(original)
        reference = copy.deepcopy(
            {key: value for key, value in row.items() if key not in ("raw", "artifact_path")}
        )
        reference.update(
            artifact_path=str(path),
            raw_job_payload_sha256=digest,
        )
        self.references[identifier] = reference
        return reference

    def __getitem__(self, key):
        from run_pilot import bound_artifact_path

        value = super().__getitem__(key)
        path = bound_artifact_path(self.references[key]["artifact_path"], self.artifact_context)
        return {**value, "artifact_path": str(path)}


def read_check_manifest(directory):
    """Read every append-only reference entry; caller binds the full roster."""
    paths = sorted(Path(directory).glob("manifest*.json"))
    _require(bool(paths), "saved check reference manifest missing")
    references = []
    for index, path in enumerate(paths, start=1):
        _require(path.name == f"manifest{index:06d}.json", "saved check manifest gap or reorder")
        value = json.loads(path.read_text())
        _require(
            value.get("schema") == "rb-f04-pilot-saved-check-references-v1",
            "saved check manifest schema mismatch",
        )
        _require(
            isinstance(value.get("references"), list) and len(value["references"]) == 1,
            "saved check manifest reference entry missing",
        )
        references.extend(value["references"])
    _require(
        len({r["id"] for r in references}) == len(references), "duplicate saved check manifest ID"
    )
    return references


class SavedChecks(MutableMapping):
    """Persist full numerical check values and reload only the requested value."""

    def __init__(self, directory, *, references=(), reader=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.references = {r["id"]: r for r in references}
        _require(len(self.references) == len(references), "duplicate saved check reference")
        self.reader = reader

    def __contains__(self, key):
        return key in self.references

    def __iter__(self):
        return iter(self.references)

    def __len__(self):
        return len(self.references)

    def __getitem__(self, key):
        from run_pilot import read_pilot_artifact

        reference = self.references[key]
        relative = Path(reference["path"])
        _require(
            not relative.is_absolute() and ".." not in relative.parts,
            "saved check must belong to this restored copy",
        )
        path = (self.directory / relative).resolve()
        _require(path.is_relative_to(self.directory.resolve()), "saved check path escapes root")
        record, receipt = (self.reader or read_pilot_artifact)(path)
        _require(receipt == reference["receipt"], "immutable saved check receipt changed")
        _require(
            payload_digest(record) == reference["payload_sha256"],
            "immutable saved check payload changed",
        )
        _require(
            record.get("schema") == _CHECK_SCHEMA and record.get("id") == key,
            "saved check identity changed",
        )
        return record["value"]

    def __setitem__(self, key, value):
        from run_pilot import write_pilot_artifact

        _require(key not in self.references, "saved check value is immutable")
        relative = f"check{len(self.references):06d}"
        path = self.directory / relative
        _require(not path.exists(), "saved check artifact is immutable")
        record = {"schema": _CHECK_SCHEMA, "id": key, "value": value}
        digest = payload_digest(record)
        receipt = write_pilot_artifact(path, record)
        self.references[key] = {
            "id": key,
            "path": relative,
            "receipt": receipt,
            "payload_sha256": digest,
        }
        target = self.directory / f"manifest{len(self.references):06d}.json"
        with target.open("x") as stream:
            json.dump(
                {
                    "schema": "rb-f04-pilot-saved-check-references-v1",
                    "references": [self.references[key]],
                },
                stream,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            stream.write("\n")

    def __delitem__(self, key):
        raise ValueError("saved check value is immutable")

    def sequence(self, identifiers):
        ids = tuple(identifiers)
        return DeferredSequence(len(ids), lambda i: self[ids[i]])


class IndexedRows(Mapping):
    """Index ordered delayed stage rows by ID without retaining their payloads."""

    def __init__(self, rows):
        self.rows = rows
        self.indices = {}
        for index in range(len(rows)):
            row = rows[index]
            identifier = row["id"]
            _require(identifier not in self.indices, "duplicate delayed stage row")
            self.indices[identifier] = index
            del row

    def __contains__(self, key):
        return key in self.indices

    def __iter__(self):
        return iter(self.indices)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, key):
        row = self.rows[self.indices[key]]
        _require(row["id"] == key, "delayed original stage row identity changed")
        return row
