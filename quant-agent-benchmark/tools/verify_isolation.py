#!/usr/bin/env python3
"""Fail-closed preflight for a benchmark candidate's visible filesystem grant."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = (ROOT / "input").resolve()
EVALUATOR = (ROOT / "evaluator").resolve()
RESULTS = (ROOT / "results").resolve()
MODELS = ("astra", "sol", "opus", "fable")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def contains_symlink(path: Path) -> bool:
    return any(p.is_symlink() for p in path.rglob("*"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=MODELS, required=True)
    parser.add_argument(
        "--accessible-path", action="append", type=Path, required=True,
        help="repeat for every path granted to the runtime; must be exactly input and the selected result directory",
    )
    args = parser.parse_args()
    result = (RESULTS / args.candidate).resolve()
    errors: list[str] = []
    if not result.is_dir():
        errors.append(f"result directory missing: {result}")
    elif any(result.iterdir()):
        errors.append(f"result directory is not empty: {result}")

    manifest_path = INPUT / "MANIFEST.json"
    if not manifest_path.is_file():
        errors.append("input manifest missing")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, expected in manifest.get("public_file_hashes", {}).items():
            path = INPUT / rel
            if not path.is_file():
                errors.append(f"public input missing: {rel}")
            elif sha256(path) != expected:
                errors.append(f"public input hash mismatch: {rel}")

    granted = {p.expanduser().resolve() for p in args.accessible_path}
    expected_grants = {INPUT, result}
    if granted != expected_grants:
        errors.append("accessible paths must be exactly the immutable input directory and selected empty result directory")
    for path in granted:
        if path == EVALUATOR or EVALUATOR.is_relative_to(path):
            errors.append(f"evaluator is exposed through granted path: {path}")
        for model in MODELS:
            other = (RESULTS / model).resolve()
            if model != args.candidate and (path == other or other.is_relative_to(path)):
                errors.append(f"another model result is exposed through granted path: {path}")
    if INPUT.exists() and contains_symlink(INPUT):
        errors.append("input contains symlinks; target visibility cannot be proven")
    if result.exists() and contains_symlink(result):
        errors.append("result directory contains symlinks; target visibility cannot be proven")

    report = {
        "candidate": args.candidate,
        "input": str(INPUT),
        "result": str(result),
        "declared_accessible_paths": sorted(map(str, granted)),
        "isolation_verified": not errors,
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
