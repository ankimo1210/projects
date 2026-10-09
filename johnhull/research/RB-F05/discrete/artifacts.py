"""Local/CAS artifact boundary for frozen synthetic research results."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STORE_SCRIPT = HERE.parents[2] / "scripts/evidence_store.py"
MAX_GIT_BYTES = 20_000_000


def load_bundle(directory=HERE, *, stem="pilot"):
    """Restore a missing declared bundle, verify integrity, then disable pickle."""
    if stem not in ("pilot", "reference", "diagnostic"):
        raise ValueError("known study artifact stem required")
    directory = Path(directory)
    record = json.loads((directory / (stem + ".json")).read_text())
    archive = directory / (stem + ".npz")
    manifest = directory / (stem + "_manifest.json")
    if not archive.exists() and manifest.exists():
        subprocess.run(
            [sys.executable, str(STORE_SCRIPT), "restore", str(manifest), "--dest", str(directory)],
            check=True,
        )
    metadata = record.get("artifact")
    if metadata is not None:
        assert archive.stat().st_size == metadata["bytes"], "artifact size"
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata["sha256"], (
            "artifact integrity"
        )
    with np.load(archive, allow_pickle=False) as saved:
        arrays = {key: saved[key] for key in saved.files}
    return record, arrays


def store_large(directory=HERE, *, stem="pilot"):
    """Use the existing primary/mirror store and independently restore both."""
    if stem not in ("pilot", "reference", "diagnostic"):
        raise ValueError("known study artifact stem required")
    directory = Path(directory)
    archive = directory / (stem + ".npz")
    metadata = {
        "bytes": archive.stat().st_size,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    if metadata["bytes"] > MAX_GIT_BYTES:
        manifest = directory / (stem + "_manifest.json")
        subprocess.run(
            [
                sys.executable,
                str(STORE_SCRIPT),
                "put",
                "--project-root",
                str(directory),
                "--manifest-out",
                str(manifest),
                archive.name,
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(STORE_SCRIPT),
                "verify",
                str(manifest),
                "--work",
                str(directory / "artifact-cache" / stem / metadata["sha256"][:16]),
            ],
            check=True,
        )
        metadata["storage"] = manifest.name
    else:
        metadata["storage"] = "small synthetic archive tracked with study"
    return metadata
