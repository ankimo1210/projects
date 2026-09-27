"""D1-preflight driver: recheck one accepted section by redraw or by baseline reuse.

Both modes run the section's unmodified browser verifier (declared heading
renames only) inside an overlay root, so new captures never touch accepted
evidence, and both run the section's pytest suite. ``redraw`` stores the
captures in both artifact-store copies. ``reuse`` keeps the new captures only
as observations and points at a redrawn baseline, which it may do only when the
dependency fingerprint and the runtime facts observed in the browser are
unchanged and the baseline images restore from both copies. Either way a
schema-2 record is written next to its raw browser record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

try:
    from . import evidence_fingerprint, evidence_record, evidence_store
except ImportError:  # executed as a script from johnhull/scripts
    import evidence_fingerprint
    import evidence_record
    import evidence_store

SCRIPTS = Path(__file__).resolve().parent
DRIVER_FILES = (
    "scripts/d1_preflight_compare.py",
    "scripts/run_browser_verifier.cjs",
    "scripts/probe_render_runtime.cjs",
    "scripts/evidence_fingerprint.py",
    "scripts/evidence_record.py",
    "scripts/evidence_store.py",
    "scripts/evidence_dependencies.json",
)


def build_overlay(
    project: Path,
    overlay: Path,
    section_dir: str,
    inputs: list[str],
    replacements: dict[str, bytes] | None = None,
) -> Path:
    """Mirror ``project`` with symlinks, except a real, fresh ``section_dir``.

    Only ``inputs`` (files inside ``section_dir``) are copied into it, so a
    verifier that writes there cannot overwrite accepted evidence.
    ``replacements`` substitutes the bytes of existing files (negative
    controls) without touching the project.
    """
    project = Path(project).resolve()
    overlay = Path(overlay)
    section_parts = evidence_store.validate_relative_path(section_dir).parts
    for item in inputs:
        parts = evidence_store.validate_relative_path(item).parts
        if parts[:-1] != section_parts:
            raise ValueError(f"verifier input {item!r} is not in the section directory")
    replacements = dict(replacements or {})
    for item in replacements:
        if not project.joinpath(*evidence_store.validate_relative_path(item).parts).is_file():
            raise FileNotFoundError(f"replacement target does not exist: {item!r}")
    for item in replacements:
        parts = PurePosixPath(item).parts
        if parts[:-1] == section_parts and item not in inputs:
            raise ValueError(
                f"replacement {item!r} is in the section directory but not a verifier input"
            )
    real_dirs = {section_parts[:depth] for depth in range(1, len(section_parts) + 1)}
    for item in replacements:
        parts = PurePosixPath(item).parts
        real_dirs |= {parts[:depth] for depth in range(1, len(parts))}
    overlay.mkdir(parents=True, exist_ok=False)

    def materialize(source: Path, target: Path, prefix: tuple[str, ...]) -> None:
        for entry in sorted(source.iterdir()):
            key = (*prefix, entry.name)
            if key == section_parts:
                (target / entry.name).mkdir()
                for item in inputs:
                    name = Path(item).name
                    data = replacements.get(item)
                    if data is None:
                        data = (entry / name).read_bytes()
                    (target / entry.name / name).write_bytes(data)
            elif key in real_dirs:
                (target / entry.name).mkdir()
                materialize(entry, target / entry.name, key)
            elif "/".join(key) in replacements:
                (target / entry.name).write_bytes(replacements["/".join(key)])
            else:
                (target / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())

    materialize(project, overlay, ())
    return overlay


def parse_json_lines(output: str) -> list[dict]:
    objects = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                objects.append(value)
    return objects


def coverage_states(browser_record: dict) -> list[list]:
    states = []
    for surface, page in (browser_record.get("pages") or {}).items():
        for state in page.get("states", []):
            states.append(
                [surface, state.get("figure"), state.get("width"), state.get("numeric_checked")]
            )
    return sorted(states, key=lambda item: [str(part) for part in item])


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(project: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project, capture_output=True, text=True, check=True
    ).stdout.strip()


def _run(command: list[str], cwd: Path, env: dict) -> dict:
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "seconds": round(time.monotonic() - started, 2),
    }


def _pytest(project: Path, tests: list[str]) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        str(project / part) for part in ("hullkit/src", "scripts", "report")
    )
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests]
    result = _run(command, project, env)
    summary = result["stdout"].strip().splitlines()[-1] if result["stdout"].strip() else ""
    passed = int(summary.split(" passed")[0].split()[-1]) if " passed" in summary else 0
    return {
        "status": "PASS" if result["exit_code"] == 0 else "FAIL",
        "passed": passed,
        "exit_code": result["exit_code"],
        "summary": summary,
        "seconds": result["seconds"],
        "command": "python -m pytest -q -p no:cacheprovider " + " ".join(tests),
    }


def run_check(project: Path, config_path: Path, section_id: str, work: Path) -> dict:
    """Run verifier, runtime probe and section tests once; return observations."""
    config = evidence_fingerprint.load_config(config_path)
    spec = config["sections"][section_id]
    for variable in ("CHROMIUM_BIN", "PLAYWRIGHT_MODULE"):
        if not os.environ.get(variable):
            raise SystemExit(f"{variable} must point at the browser runtime")
    fingerprint = evidence_fingerprint.compute_fingerprint(project, section_id, config)
    overlay = build_overlay(
        project, work / "overlay", spec["verifier_output_dir"], spec["verifier_inputs"]
    )
    env = dict(os.environ)
    verifier = _run(
        [
            "node",
            str(SCRIPTS / "run_browser_verifier.cjs"),
            str(config_path),
            section_id,
            str(project),
            str(overlay),
        ],
        project,
        env,
    )
    lines = parse_json_lines(verifier["stdout"])
    wrapper = next((item["wrapper"] for item in lines if "wrapper" in item), None)
    output_dir = overlay / spec["verifier_output_dir"]
    raw_record_path = output_dir / "browser-check.json"
    browser = json.loads(raw_record_path.read_text(encoding="utf-8"))
    captures = {path.name: path.read_bytes() for path in sorted(output_dir.glob("*.png"))}
    probe = _run(
        [
            "node",
            str(SCRIPTS / "probe_render_runtime.cjs"),
            str(project),
            spec["book"]["page"],
            spec["portal"]["page"],
            spec["portal"]["figures"][0],
        ],
        project,
        env,
    )
    runtime = next(
        (item["runtime"] for item in parse_json_lines(probe["stdout"]) if "runtime" in item),
        {"status": "FAIL", "error": probe["stderr"][-500:]},
    )
    tests = _pytest(project, spec["tests"])
    return {
        "fingerprint": fingerprint,
        "wrapper": wrapper,
        "verifier_run": {
            "exit_code": verifier["exit_code"],
            "seconds": verifier["seconds"],
            "stderr_tail": verifier["stderr"][-500:],
        },
        "browser": browser,
        "raw_browser_record": raw_record_path.read_bytes(),
        "captures": captures,
        "runtime": runtime,
        "probe_run": {"exit_code": probe["exit_code"], "seconds": probe["seconds"]},
        "pytest": tests,
    }


def _browser_check(observed: dict, record_sha256: str) -> dict:
    browser = observed["browser"]
    pages = browser.get("pages") or {}
    passed = (
        observed["verifier_run"]["exit_code"] == 0
        and browser.get("status") == "PASS"
        and all(page.get("numeric_mutation_rejected") for page in pages.values())
        and not any(
            page.get("page_errors") or page.get("external_requests") for page in pages.values()
        )
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "browser_version": browser.get("browser_version"),
        "state_checks": browser.get("state_checks"),
        "screenshots": browser.get("screenshots"),
        "coverage": coverage_states(browser),
        "book_math": browser.get("book_math"),
        "numeric_mutation_rejected": {
            surface: page.get("numeric_mutation_rejected") for surface, page in pages.items()
        },
        "raw_record_sha256": record_sha256,
        "wrapper": observed["wrapper"],
        "seconds": observed["verifier_run"]["seconds"],
    }


def driver_provenance(records_root: Path) -> dict:
    """Digests of the code that produced a record (provenance, not freshness)."""
    return {name: _sha256_file(records_root / name) for name in DRIVER_FILES}


def _source_hashes(records_root: Path, spec: dict, fingerprint: dict) -> dict:
    """Section inputs whose change makes the record stale (ledger freshness)."""
    components = fingerprint.get("components") or {}
    names = set(spec["tests"]) | {spec["notebook"]["path"]}
    for name in ("python_sources", "data_files", "verifier"):
        names |= set((components.get(name) or {}).keys())
    return {name: _sha256_file(records_root / name) for name in sorted(names)}


def _manifest(entries: list[dict]) -> dict:
    return {"schema_version": 1, "kind": evidence_store.MANIFEST_KIND, "entries": entries}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("redraw", "reuse"))
    parser.add_argument("--section", default="27.3")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=SCRIPTS.parent,
        help="checkout whose builds and sources are checked",
    )
    parser.add_argument(
        "--records-root",
        type=Path,
        default=SCRIPTS.parent,
        help="checkout that stores the schema-2 records",
    )
    parser.add_argument("--config", type=Path, default=evidence_fingerprint.DEFAULT_CONFIG)
    parser.add_argument("--baseline", help="records-root relative path of a redrawn record")
    parser.add_argument("--work", type=Path, required=True, help="empty scratch directory")
    args = parser.parse_args(argv)
    project = args.project_root.resolve()
    records_root = args.records_root.resolve()
    config = evidence_fingerprint.load_config(args.config)
    spec = config["sections"][args.section]
    primary = evidence_store.store_from_env("PROJECTS_ARTIFACT_STORE", role="primary")
    mirror = evidence_store.store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"d1pf-{args.section}-{stamp}-{args.mode}"
    work = args.work.resolve() / run_id
    work.mkdir(parents=True)
    observed = run_check(project, args.config.resolve(), args.section, work)
    fingerprint = observed["fingerprint"]
    runtime = observed["runtime"]

    record_dir_rel = f"docs/validation/d1-preflight/section-{args.section.replace('.', '-')}"
    record_dir = records_root / record_dir_rel
    record_dir.mkdir(parents=True, exist_ok=True)
    raw_path = record_dir / f"{run_id}.browser.json"
    raw_path.write_bytes(observed["raw_browser_record"])
    checks = {
        "browser": _browser_check(observed, _sha256_file(raw_path)),
        "runtime_probe": {"status": runtime.get("status", "FAIL"), **observed["probe_run"]},
        "pytest": observed["pytest"],
    }
    capture_digests = {
        name: hashlib.sha256(data).hexdigest() for name, data in observed["captures"].items()
    }
    observations = {
        "capture_sha256": capture_digests,
        "stored_new_bytes": 0,
        "seconds": {
            "verifier": observed["verifier_run"]["seconds"],
            "probe": observed["probe_run"]["seconds"],
            "pytest": observed["pytest"]["seconds"],
        },
    }

    baseline = None
    decision = "redrawn"
    reasons = ["D1-preflight stage 3: full redraw"]
    if args.mode == "reuse":
        if not args.baseline:
            raise SystemExit("reuse needs --baseline")
        saved = json.loads((records_root / args.baseline).read_text(encoding="utf-8"))
        verdict = evidence_fingerprint.decide(saved["dependency_fingerprint"], fingerprint)
        mismatched = evidence_fingerprint.runtime_mismatches(
            saved["environment"]["runtime"], runtime
        )
        baseline_names = {Path(entry["path"]).name: entry for entry in saved["images"]}
        observations["identical_to_baseline"] = sum(
            capture_digests.get(name) == evidence_store.parse_ref(entry["ref"])
            for name, entry in baseline_names.items()
        )
        observations["baseline_images"] = len(baseline_names)
        observations["coverage_equal_to_baseline"] = (
            checks["browser"]["coverage"] == saved["checks"]["browser"]["coverage"]
        )
        baseline = evidence_record.baseline_ref(records_root, args.baseline)
        if verdict["decision"] == "reuse" and not mismatched:
            decision = "reused"
            reasons = ["dependency fingerprint and runtime facts equal the baseline"]
            images = saved["images"]
            checks["reuse"] = {
                "status": "PASS" if observations["coverage_equal_to_baseline"] else "FAIL",
                "fingerprint": "equal",
                "runtime": "equal",
                "coverage_equal_to_baseline": observations["coverage_equal_to_baseline"],
            }
        else:
            reasons = verdict["reasons"] + [f"runtime {key} changed" for key in mismatched]
    if decision == "redrawn":
        images = []
        for name, data in observed["captures"].items():
            info = primary.put_bytes(data)
            evidence_store.replicate(primary, mirror, [info["sha256"]])
            images.append(evidence_store.manifest_entry(f"{record_dir_rel}/{run_id}/{name}", data))
            observations["stored_new_bytes"] += len(data)
    storage = evidence_store.verify_copies(primary, mirror, _manifest(images), work / "verify")
    storage["checked_at"] = datetime.now(UTC).isoformat()

    record = evidence_record.build_record(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        commit=_git(project, "rev-parse", "HEAD"),
        dirty=bool(_git(project, "status", "--porcelain", "--", ".")),
        section_id=args.section,
        decision=decision,
        reasons=reasons,
        fingerprint=fingerprint,
        baseline=baseline,
        images=images,
        checks=checks,
        environment={
            "runtime": {key: runtime.get(key) for key in evidence_fingerprint.RUNTIME_KEYS},
            "static": fingerprint["components"].get("environment"),
            "records_commit": _git(records_root, "rev-parse", "HEAD"),
            "driver_sha256": driver_provenance(records_root),
        },
        storage_verification=storage,
        source_sha256=_source_hashes(records_root, spec, fingerprint),
        artifact_sha256={
            page: _sha256_file(project / page)
            for page in (spec["portal"]["page"], spec["book"]["page"])
        },
        observations=observations,
    )
    record_path = record_dir / f"{run_id}.json"
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": record["status"],
                "decision": decision,
                "record": f"{record_dir_rel}/{run_id}.json",
                "reasons": reasons,
                "checks": {name: check["status"] for name, check in checks.items()},
                "storage": storage["status"],
                "observations": {
                    key: value for key, value in observations.items() if key != "capture_sha256"
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
