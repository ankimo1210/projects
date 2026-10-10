"""Freeze terminal provenance into a false saved-check candidate; never grant execution.

The CLI has only --output. It uses the fixed real observer/template and refuses live
original processes before native collection. The freeze_candidate(observer,
template, output, capacity_reader=...) seam permits small isolated fixtures with a
fresh observer namespace; no fixture override is available through the CLI.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

D = Path(__file__).resolve().parent
OBSERVER = D / "task-5-full-pilot-root-saved-check-observer-v1.py"
OBSERVER_SHA = "9277b8097cf499129f93a8e8d44e41063c0f0279a5865a9b0f5cc68249b4efb4"
TEMPLATE = D / "task-5-full-pilot-root-saved-check-resource-candidate-v1.json"
TEMPLATE_SHA = "a5face84365a5ee437d55e680da1414075b7ef761894e842f2377aff73a5723e"


def file_sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            value.update(block)
    return value.hexdigest()


def witness(path):
    value = path.stat(follow_symlinks=False)
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _fixed_contract():
    for path, expected in ((OBSERVER, OBSERVER_SHA), (TEMPLATE, TEMPLATE_SHA)):
        if path.is_symlink() or not path.is_file() or file_sha(path) != expected:
            raise ValueError("fixed observer/template physical bytes changed")
    spec = importlib.util.spec_from_file_location("terminal_candidate_fixed_observer", OBSERVER)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    return observer, json.loads(TEMPLATE.read_text())


def _receipt_refs(observer, prior):
    # Check the original PID boundary before even reading terminal receipt bodies.
    observer.require(
        prior.get("original_process_ids") == observer.ORIGINAL_PIDS,
        "all three original process identities must remain bound",
    )
    observer.require(
        all(not Path(f"/proc/{pid}").exists() for pid in observer.ORIGINAL_PIDS),
        "original pilot/enclosing/monitor/child processes must all be terminal",
    )
    for key, relative in (
        (
            "original_terminal_monitor_receipt",
            "task-5-formal-pilot-root-operational-observation-v3/parent-cost-and-status.json",
        ),
        (
            "original_terminal_enclosing_receipt",
            "task-5-formal-pilot-root-enclosing-observation-v3/parent-cost-and-status.json",
        ),
    ):
        path = observer.absolute(prior[key]["path"])
        observer.require(
            path == observer.D / relative and path.is_file() and not path.is_symlink(),
            "complete original terminal receipt required",
        )
        before = witness(path)
        actual_sha = file_sha(path)
        observer.require(witness(path) == before, "terminal receipt changed while read")
        if prior[key].get("sha256") is not None:
            observer.require(
                prior[key]["sha256"] == actual_sha, "previous terminal receipt bytes changed"
            )
        prior[key] = prior[key] | {"sha256": actual_sha}
    return observer.terminal_authority(prior)


def _native_inventory(observer):
    """Stream only physical bytes, rejecting in-progress/symlink or racing files."""
    root = observer.ORIGINAL_NATIVE
    observer.require(
        root.is_dir() and not root.is_symlink(), "original terminal native directory missing"
    )
    paths = sorted(root.rglob("*"))
    files, stats = {}, {}
    for path in paths:
        observer.require(not path.is_symlink(), "native symbolic links are unsupported")
        if path.is_file():
            relative = str(path.relative_to(root))
            before = witness(path)
            files[relative] = file_sha(path)
            observer.require(witness(path) == before, "native file changed while streamed")
            stats[relative] = before
        else:
            observer.require(path.is_dir(), "native special file cannot bind closed bytes")
    observer.require(bool(files), "finite original native file set is empty")
    observer.require(
        [str(path.relative_to(root)) for path in sorted(root.rglob("*"))]
        == [str(path.relative_to(root)) for path in paths],
        "native inventory changed during collection",
    )
    checkpoints = sorted(root.glob("checkpoint*"))
    observer.require(
        bool(checkpoints) and checkpoints[-1].is_dir(), "terminal latest checkpoint is absent"
    )
    checkpoint = checkpoints[-1]
    relative = str(checkpoint.relative_to(root))
    checkpoint_files = {
        key[len(relative) + 1 :]: value
        for key, value in files.items()
        if key.startswith(relative + "/")
    }
    observer.require("receipt.json" in checkpoint_files, "latest checkpoint receipt is absent")
    return {
        "path": str(root),
        "files": files,
        "tree_sha256": observer.digest(files),
        "latest_checkpoint": {
            "path": str(checkpoint),
            "files": checkpoint_files,
            "tree_sha256": observer.digest(checkpoint_files),
            "receipt_sha256": checkpoint_files["receipt.json"],
        },
    }, stats


def _capacity_snapshot(observer, prior):
    errors = []
    available = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
    except (OSError, ValueError) as exc:
        errors.append("memory: " + type(exc).__name__ + ": " + str(exc))
    try:
        volumes = observer.volume_sample(prior["volume_probes"])
    except OSError as exc:
        volumes = None
        errors.append("volume: " + type(exc).__name__ + ": " + str(exc))
    return {
        "scope": "observation data only; not permission or whole-checker capacity guarantee",
        "observed_UTC": datetime.now(UTC).isoformat(),
        "MemAvailable_bytes": available,
        "volumes": volumes,
        "observation_errors": errors,
        "whole_capacity_or_duration_guarantee": False,
        "whole_hydrated_checker_16GiB_fit": None,
        "administrative_resource_approval": False,
    }


def _publish_new(observer, output, data):
    """No-replace publication; a pre-existing user path is never overwritten."""
    temporary = output.with_name(output.name + ".candidate-" + uuid.uuid4().hex + ".tmp")
    created_identity = None
    try:
        with temporary.open("x") as stream:
            created = os.fstat(stream.fileno())
            created_identity = (created.st_dev, created.st_ino)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    except FileExistsError as exc:
        raise observer.GuardRejectedError("candidate output already exists") from exc
    finally:
        if created_identity is not None:
            try:
                current = temporary.stat(follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if (current.st_dev, current.st_ino) == created_identity:
                    temporary.unlink()


def freeze_candidate(observer, template, output, *, capacity_reader=None):
    """Prepare provenance only. Fixture seam must supply an isolated observer namespace."""
    started, cpu_start = time.perf_counter(), time.process_time()
    prior = copy.deepcopy(template)
    observer.require(
        prior.get("candidate_only") is True, "only the original false candidate may be completed"
    )
    for key in (
        "root_preapproved",
        "execute_saved_check",
        "finance_acceptance",
        "new_saved_check_budget_approved",
        "formal_financial_launch_authorized",
        "financial_A_cap_projection_approved",
        "formal_phase_completion_claimed",
    ):
        observer.require(prior.get(key) is False, "candidate cannot supply approval: " + key)
    observer.require(
        prior.get("financial_qualification") == "unknown",
        "candidate cannot grant financial qualification",
    )
    output = Path(output)
    observer.require(
        output.is_absolute()
        and output.parent == observer.D
        and not output.is_symlink()
        and not output.exists(),
        "candidate output already exists or is outside fixed D2",
    )
    terminal = _receipt_refs(observer, prior)
    # Existing canonical source/input/plan/authority checks are preserved, no new math.
    authority = observer.original_source_binding(prior)
    binding, stats = _native_inventory(observer)
    prior["closed_native"] = binding
    capacity = (capacity_reader or (lambda value: _capacity_snapshot(observer, value)))(prior)
    # Reauthenticate all bytes/receipts/latest checkpoint after collection/capacity read.
    observer.terminal_authority(prior)
    observer.closed_native_binding(prior)
    authority_after = observer.original_source_binding(prior)
    observer.require(
        authority_after == authority,
        "original source/input/plan authority changed after native collection",
    )
    for relative, expected in stats.items():
        observer.require(
            witness(observer.ORIGINAL_NATIVE / relative) == expected,
            "native physical file changed after inventory",
        )
    prior["root_fresh_capacity_snapshot"] = capacity
    prior["terminal_provenance_preparation"] = {
        "scope": "false saved-check candidate physical provenance only; not numerical verification",
        "terminal_authority": terminal,
        "original_authority": authority,
        "helper_sha256": file_sha(Path(__file__)),
        "observer_sha256": OBSERVER_SHA,
        "template_sha256": TEMPLATE_SHA,
        "physical_files": len(binding["files"]),
        "wall_seconds": time.perf_counter() - started,
        "parent_CPU_seconds": time.process_time() - cpu_start,
        "measured_endpoint": "after physical/terminal reauthentication; candidate JSON serialization/write tail remains outside this local clock",
        "own_candidate_serialization_write_cost": None,
        "costs_added_to_original_generation_or_checker": False,
        "financial_arrays_decoded": False,
        "root_permission_granted": False,
    }
    data = json.dumps(prior, indent=2, sort_keys=True, allow_nan=False) + "\n"
    _publish_new(observer, output, data)
    observer.require(
        json.loads(output.read_text()) == prior,
        "candidate byte publication did not preserve provenance",
    )
    return prior


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    observer, template = _fixed_contract()
    try:
        result = freeze_candidate(observer, template, args.output)
    except (observer.GuardRejectedError, OSError, ValueError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "status": "unclosed_candidate_provenance",
                    "reason": type(exc).__name__ + ": " + str(exc),
                    "root_preapproved": False,
                    "execute_saved_check": False,
                    "finance_acceptance": False,
                }
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": "unapproved_terminal_provenance_candidate_only",
                "output": str(args.output),
                "sha256": file_sha(args.output),
                "physical_files": len(result["closed_native"]["files"]),
                "root_preapproved": False,
                "execute_saved_check": False,
                "finance_acceptance": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
