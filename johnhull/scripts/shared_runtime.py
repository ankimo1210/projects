"""Book/portal runtime shared by every section, checked once instead of per D1 record.

The Book configuration, its Sphinx extension, the vendored static assets, and
the portal stylesheet are the same for all 306 sections. Pinning them in each
section's acceptance record made one Book-wide change (such as packaging
MathJax locally) stale every accepted section at once. These files are now
excluded from per-section source hashes and validated together against
``docs/validation/shared-runtime.json``, which records the hashes and the
checks that were run when the runtime last changed.

Hashes of these files inside older records are historical; they are no longer
compared with the current files. Section-specific inputs (notebook slices,
python closures, data, verifiers, tests, and ``report/report_builder``) remain
pinned per section.

    uv run --no-sync --package hullkit python johnhull/scripts/shared_runtime.py --check
    uv run --no-sync --package hullkit python johnhull/scripts/shared_runtime.py \\
        --write --check-run "make hull-book: PASS" --check-run "make hull-release-check: PASS"
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/validation/shared-runtime.json"
RUNTIME_FILES = ("book/_config.yml", "book/_toc.yml")
RUNTIME_DIRS = {
    "book/_ext": frozenset({".py"}),
    "book/_static": frozenset({".js", ".css"}),
    "report/assets": frozenset({".css", ".js"}),
}


def is_runtime(name: str) -> bool:
    """Whether a project-relative path is part of the shared runtime.

    Decided from the path alone so that hashes of since-deleted files in old
    records are classified the same way as current files.
    """
    if name in RUNTIME_FILES:
        return True
    path = PurePosixPath(name)
    if "__pycache__" in path.parts:
        return False
    return any(
        name.startswith(directory + "/") and path.suffix in suffixes
        for directory, suffixes in RUNTIME_DIRS.items()
    )


def runtime_paths(project: Path) -> set[str]:
    """Current shared-runtime files under ``project``."""
    names = {name for name in RUNTIME_FILES if (project / name).is_file()}
    for directory in RUNTIME_DIRS:
        names |= {
            path.relative_to(project).as_posix()
            for path in (project / directory).rglob("*")
            if path.is_file() and is_runtime(path.relative_to(project).as_posix())
        }
    return names


def current_hashes(project: Path) -> dict[str, str]:
    """SHA-256 of every current shared-runtime file, sorted by path."""
    return {
        name: hashlib.sha256((project / name).read_bytes()).hexdigest()
        for name in sorted(runtime_paths(project))
    }


def check(project: Path = PROJECT) -> list[str]:
    """Compare the current runtime with the manifest; return problems (empty = PASS)."""
    manifest_path = project / MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"shared_runtime: cannot read {MANIFEST}: {exc}"]
    recorded = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(recorded, dict) or not recorded:
        return [f"shared_runtime: {MANIFEST} has no files"]
    if not isinstance(manifest.get("checks"), list) or not manifest["checks"]:
        return [f"shared_runtime: {MANIFEST} records no checks"]
    current = current_hashes(project)
    problems = [
        f"shared_runtime: {name} is not recorded in {MANIFEST}"
        for name in sorted(current.keys() - recorded.keys())
    ]
    problems += [
        f"shared_runtime: {name} is recorded but missing"
        for name in sorted(recorded.keys() - current.keys())
    ]
    problems += [
        f"shared_runtime: {name} changed since {MANIFEST} was written"
        for name in sorted(current.keys() & recorded.keys())
        if current[name] != recorded[name]
    ]
    return problems


def write(project: Path, checks: list[str], note: str) -> dict:
    """Record the current runtime and the checks run against it."""
    manifest = {
        "schema_version": 1,
        "description": (
            "Book/portal runtime shared by every section. Section acceptance records "
            "do not pin these files; rewrite this manifest only after rebuilding the "
            "Book and running the release check against the changed runtime."
        ),
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks,
        "note": note,
        "files": current_hashes(project),
    }
    (project / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check", action="store_true", help="compare current files with the manifest"
    )
    mode.add_argument("--write", action="store_true", help="record the current files")
    parser.add_argument(
        "--check-run", action="append", default=[], help="a check run against this runtime"
    )
    parser.add_argument("--note", default="", help="why the runtime changed")
    args = parser.parse_args(argv)
    if args.write:
        if not args.check_run:
            parser.error("--write needs at least one --check-run")
        manifest = write(PROJECT, args.check_run, args.note)
        print(f"[PASS] wrote {MANIFEST} ({len(manifest['files'])} files)")
        return 0
    problems = check(PROJECT)
    for problem in problems:
        print(f"[FAIL] {problem}")
    if not problems:
        print(f"[PASS] shared runtime matches {MANIFEST}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
