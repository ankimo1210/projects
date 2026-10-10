"""Prepared saved-only whole-pilot observer; no execution before root closes and approves inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

D = Path(__file__).resolve().parent
WT = D.parents[2]
ENTRY = Path(__file__).resolve()
ORIGINAL_GUARD_NAME = "task-5-formal-pilot-root-launch-guard-v3.json"
ORIGINAL_GUARD_SHA = "9e794bd4ec46c72d240a264fdf2dd722297455baf2f3cd0d07243f6d7a0c2842"
ORIGINAL_NATIVE = D / "task-5-formal-pilot-root-v3"
ORIGINAL_PIDS = [372314, 372315, 372316]
BASE_MONITOR_SHA = "a53a73cfc420e2745f8d8d2cb72a6171ab2d166781126b9a96869afb88053981"
HISTORICAL_D = Path(
    "/home/kazumasa/worktrees/johnhull-research-roadmap/.superpowers/sdd/2026-10-09-dynamic-cross-model-hedging"
)
SOURCE_IDENTITY = "75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e"
SOURCE_NATIVE_IDENTITY = "ef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7"
SOURCE_EVIDENCE_NAME = "task-5-formal-prior-lock-rebind-evidence-v5.json"
SOURCE_EVIDENCE_SHA = "d5eab8376c819367defb650f228a0cb844fe4588b77c3f09464f9e18785e9571"
CODEC_NAME = "independent-transport-codec-v2-decision.json"
CODEC_SHA = "26aa45f5902e816053decce2aec2364c58161c387fdcc5378d27e8255a906262"
STAGE_NAME = "independent-stage-cap-binding-v1-decision.json"
STAGE_SHA = "f2fd826e399a08e20e848ac00bfbbb1132433be189779716f66a7e61d1868ea2"
MATERIALIZER_NAME = "task-5-formal-prior-lock-preparation-v5.py"
MATERIALIZER_SHA = "b505500d6c8c3601fd8e04e22d15a2beac41c9e3bae48bfcc7aee5c39236a83a"
INTERFACE_NAME = "task-5-formal-prior-lock-preparation-v5-interface-v1.json"
INTERFACE_SHA = "943021eca1e38396cf44821f727dd307c2e6d19fbb45fb02dc86e4b56039fc1b"
RESOURCE_NAME = "task-5-formal-pilot-root-operational-resource-prior-v3.json"
RESOURCE_SHA = "145bdf322aacd4e699e297c2a4e747d1a021c43771e4b162783f9eb35a390881"
V6_NAME = "task-5-fullmixed-phase-local-reuse-budget-supplement-author-v6.json"
V6_SHA = "b1e3959f468d5611543afbd9adcbda2c7c23c9b974c73e61dc90ca9402b29abb"
V6_MANIFEST_NAME = "task-5-fullmixed-phase-local-reuse-budget-supplement-author-v6-manifest.json"
V6_MANIFEST_SHA = "a47743d83eaf0fb4c72c960ee4dc5a97a1605b822e788b58ab7ead72045ba6d9"
SCHEMA = "rb-f04-root-full-pilot-operational-prior-v1"
GiB = 1024**3


class GuardRejectedError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            result.update(block)
    return result.hexdigest()


def clock():
    return {
        "wall": time.perf_counter(),
        "cpu": time.process_time(),
        "utc": datetime.now(UTC).isoformat(),
    }


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + chr(10))
    temporary.replace(path)


def require(condition, message):
    if not condition:
        raise GuardRejectedError(message)


def absolute(value):
    require(isinstance(value, str) and Path(value).is_absolute(), "prior path must be absolute")
    return Path(value)


def positive(value):
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def tree_binding(spec):
    root = absolute(spec["path"])
    require(root.is_dir(), "bound input artifact directory missing")
    actual = {}
    for file in sorted(root.rglob("*")):
        if file.is_file():
            require(
                not file.is_symlink(), "artifact file symlink not supported by prior tree binding"
            )
            actual[str(file.relative_to(root))] = sha(file)
    require(actual and actual == spec["files"], "artifact file set/physical bytes changed")
    require(digest(actual) == spec["tree_sha256"], "artifact tree SHA differs from prior")
    require(
        "receipt.json" in actual and actual["receipt.json"] == spec["receipt_sha256"],
        "root artifact receipt differs",
    )
    return {
        "path": str(root),
        "files": actual,
        "tree_sha256": digest(actual),
        "receipt_sha256": actual["receipt.json"],
    }


def reference_path(spec, *, historical=False):
    require(isinstance(spec, dict), "actual reference object required")
    expected = spec.get("sha256")
    require(
        isinstance(expected, str)
        and len(expected) == 64
        and all(c in "0123456789abcdef" for c in expected),
        "pending reference SHA cannot authorize execution",
    )
    supplied = absolute(spec.get("path"))
    base = HISTORICAL_D if historical else D
    try:
        supplied.relative_to(base)
        path = supplied.resolve(strict=True)
        path.relative_to(base)
    except (ValueError, OSError) as exc:
        raise GuardRejectedError("reference is absent or outside its fixed evidence root") from exc
    require(
        path.is_file() and not supplied.is_symlink(), "regular immutable reference file required"
    )
    require(sha(path) == expected, "actual prior evidence bytes changed")
    return path


def fixed_reference(spec, name=None, expected_sha=None, *, historical=False):
    path = reference_path(spec, historical=historical)
    if name is not None:
        require(
            path == (HISTORICAL_D if historical else D) / name and sha(path) == expected_sha,
            "fixed evidence binding changed",
        )
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise GuardRejectedError("actual reference is not complete JSON") from exc
    require(isinstance(value, dict), "actual reference JSON object required")
    return value


def limited_source_review(prior):
    refs = prior.get("source_limited_decisions")
    require(
        isinstance(refs, dict) and set(refs) == {"codec", "stage"},
        "both actual limited codec and stage source decisions required",
    )
    values = {}
    for key, name, expected in (("codec", CODEC_NAME, CODEC_SHA), ("stage", STAGE_NAME, STAGE_SHA)):
        require(refs[key].get("status") == "approved", "actual source decision required")
        value = fixed_reference(refs[key], name, expected)
        require(
            value.get("decision") == "approved"
            and value.get("reviewer") == "pilot_v53_independent_review"
            and value.get("financial_qualification") == "unknown",
            "actual independent source-only decision required",
        )
        values[key] = value
    codec, stage = values["codec"], values["stage"]
    require(
        codec.get("schema") == "rb-f04-pilot-transport-independent-review-v2"
        and codec.get("role") == "independent limited storage transport reviewer"
        and all(
            codec.get(key) is False
            for key in (
                "full_capacity_RSS_runtime_or_budget_approved",
                "formal_pilot_or_main_approved",
                "phase_acceptance_approved",
                "resume_with_old_source_identity_approved",
            )
        ),
        "codec review cannot become resource, launch, acceptance or resume approval",
    )
    require(
        stage.get("schema") == "rb-f04-stage-risk-operational-argument-source-fix-independent-v1"
        and stage.get("role") == "independent limited source and metadata reviewer"
        and stage.get("source_canonical_runner_digest_sha256") == SOURCE_IDENTITY
        and stage.get("source_native_payload_digest_sha256") == SOURCE_NATIVE_IDENTITY
        and stage.get("actual_source_file_count") == 82
        and stage.get("dynamic_imports") == []
        and stage.get("actual_closed_source_bytes_match") is True
        and stage.get("actual_cap_full_binding_preserved") is True
        and stage.get("full_financial_five_args_and_extra_keys_preserved") is True
        and all(
            stage.get(key) is False
            for key in (
                "resource_budget_prior_rebinding_approved",
                "formal_pilot_main_launch_approved",
                "phase_or_main_acceptance_approved",
                "old_formal_source_resume_approved",
            )
        ),
        "stage review must bind current82 source without granting resource/launch/resume",
    )
    evidence = fixed_reference(
        prior["source_rebind_evidence"], SOURCE_EVIDENCE_NAME, SOURCE_EVIDENCE_SHA
    )
    require(
        evidence.get("all3138_budget_and_cap_recipe_approved") is False
        and evidence.get("formal_financial_launch_authorized") is False
        and evidence.get("old_partial_resumed_or_relabelled") is False
        and evidence.get("fresh_source_metadata_output_only") is True,
        "source evidence cannot authorize a prior, launch or old raw resume",
    )
    require(evidence["source_limited_decisions"] == refs, "source decision collection differs")
    current = fixed_reference(evidence["current_source_reference"])
    require(current == prior["source_identity"], "exact current82 source inventory required")
    require(
        prior["source_native_payload_sha256"] == SOURCE_NATIVE_IDENTITY,
        "native source binding differs",
    )
    files = current["files"]
    for relative, key in (
        ("johnhull/research/RB-F04/dynamic_hedging/_pilot_transport.py", "helper_sha256"),
        ("johnhull/research/RB-F04/dynamic_hedging/run_pilot.py", "run_pilot_sha256"),
        ("johnhull/research/RB-F04/dynamic_hedging/run_reference.py", "run_reference_sha256"),
        ("johnhull/research/RB-F04/dynamic_hedging/_teacher_storage.py", "teacher_storage_sha256"),
    ):
        require(files[relative] == codec[key], "codec's exact source bytes differ")
    require(
        files["johnhull/research/RB-F04/dynamic_hedging/check_pilot.py"]
        == stage["fixed_checker_sha256"],
        "stage checker source differs",
    )
    return values


def actual_budget_review(prior):
    # Source approval and the v6 counter review cannot substitute for all3138/cap approval.
    fixed_reference(prior["budget_supplement"], V6_NAME, V6_SHA, historical=True)
    fixed_reference(
        prior["budget_supplement_manifest"], V6_MANIFEST_NAME, V6_MANIFEST_SHA, historical=True
    )
    ref = prior["full_budget_and_cap_recipe_review"]
    require(ref.get("status") == "approved", "all3138/cap recipe independent review required")
    value = fixed_reference(ref)
    require(
        value.get("schema") == "rb-f04-independent-fullmixed-prior-budget-review-v1"
        and value.get("decision") == "approved"
        and value.get("role") == "independent static prior resource reviewer"
        and value.get("planned_before_attempt") is True
        and value.get("source_canonical_identity") == SOURCE_IDENTITY
        and value.get("source_native_payload_identity") == SOURCE_NATIVE_IDENTITY,
        "v6 static counter/source approval is not whole budget approval",
    )
    require(
        value.get("financial_qualification") == "unknown"
        and value.get("formal_pilot_run") is False
        and value.get("main_or_phase_approval") is False,
        "resource review must not assert financial acceptance",
    )
    bound = value["approved_bindings"]
    require(
        bound == prior["approved_budget_bindings"]
        and bound["source_identity_sha256"] == SOURCE_IDENTITY
        and bound["source_native_payload_sha256"] == SOURCE_NATIVE_IDENTITY
        and bound["replay_budget_supplement_sha256"] == V6_SHA
        and bound["replay_budget_manifest_sha256"] == V6_MANIFEST_SHA
        and bound["literal_cap_options"] == 573122,
        "actual full budget/cap bindings differ from root prior",
    )
    interface = fixed_reference(prior["materializer_interface"], INTERFACE_NAME, INTERFACE_SHA)
    require(
        interface["new_source"]["canonical_runner_digest"] == SOURCE_IDENTITY
        and interface["new_source"]["native_payload_digest"] == SOURCE_NATIVE_IDENTITY
        and interface["new_source"]["files"] == 82,
        "actual materializer interface differs",
    )
    require(
        bound == interface["approved_binding_set"]
        and bound["source_limited_decisions_sha256"]
        == digest({"codec": CODEC_SHA, "stage": STAGE_SHA})
        and bound["source_rebind_evidence_sha256"] == SOURCE_EVIDENCE_SHA
        and bound["materializer_sha256"] == MATERIALIZER_SHA,
        "actual budget must bind exact two decisions, current recipe and materializer",
    )
    require(
        reference_path(prior["materializer"]) == D / MATERIALIZER_NAME
        and prior["materializer"]["sha256"] == MATERIALIZER_SHA
        and interface["materializer"] == prior["materializer"],
        "fixed materializer source changed",
    )
    return value


def metadata_authority(prior, *, verify_files=True):
    """Authenticate separately approved prior metadata, not financial saved output."""
    review = actual_budget_review(prior)
    interface = fixed_reference(prior["materializer_interface"], INTERFACE_NAME, INTERFACE_SHA)
    require(
        prior["approved_budget_bindings"] == interface["approved_binding_set"],
        "guard must use the exact reviewed v5 bindings",
    )
    approval_ref = prior["actual_root_metadata_approval"]
    approval = fixed_reference(approval_ref)
    require(
        approval.get("schema") == "rb-f04-root-prior-lock-approval-v1"
        and approval.get("status") == "approved_for_prior_materialization_only"
        and approval.get("approved_by") == "root"
        and approval.get("planned_before_attempt") is True
        and approval.get("formal_financial_launch_authorized") is False
        and approval.get("formal_financial_phase_approved") is False
        and approval.get("financial_qualification") == "unknown",
        "actual root metadata-only approval required; it is not launch permission",
    )
    require(
        approval["approved_bindings"] == prior["approved_budget_bindings"]
        and approval["materializer_sha256"] == MATERIALIZER_SHA
        and approval["source_rebind_evidence"] == prior["source_rebind_evidence"]
        and approval["independent_reviews"]["source"] == prior["source_limited_decisions"]
        and approval["independent_reviews"]["prior_budget_and_cap_recipe"]
        == prior["full_budget_and_cap_recipe_review"],
        "actual root/reviewer/current source/recipe bindings differ",
    )
    for key, name, review_key in (
        ("producer", "task-5-formal-pilot-plan-producer.py", "approved_producer_sha256"),
        (
            "candidate_helper",
            "task-5-fullmixed-prior-budget-candidate-author-v1-builder.py",
            "approved_candidate_helper_sha256",
        ),
    ):
        ref = approval["bindings"][key]
        require(
            reference_path(ref, historical=True) == HISTORICAL_D / name
            and ref["sha256"] == review[review_key],
            "actual lock producer/helper source changed",
        )
    rows = approval["reviewed_budgets"]
    require(
        isinstance(rows, dict)
        and len(rows) == 3138
        and all(
            row["budget"]["review_sha256"] == prior["full_budget_and_cap_recipe_review"]["sha256"]
            for row in rows.values()
        ),
        "all original3138 actual reviewed rows required",
    )
    normalized = {
        key: row
        | {
            "budget": {
                name: value for name, value in row["budget"].items() if name != "review_sha256"
            }
        }
        for key, row in rows.items()
    }
    require(
        digest(normalized)
        == prior["approved_budget_bindings"]["budget_rows_without_review_SHA_digest"],
        "actual root normalized3138 rows differ from reviewed recipe",
    )
    cap = approval["cap_options_authority"]
    template = cap["decision_template"]
    require(
        cap.get("status") == "approved"
        and cap["cap_recipe_digest"] == prior["approved_budget_bindings"]["cap_recipe_digest"]
        and template.get("decision") == "approved"
        and template.get("planned_before_attempt") is True
        and template["independent_review_sha256"]
        == prior["full_budget_and_cap_recipe_review"]["sha256"],
        "actual exact573122 recipe authority required",
    )
    aliases = approval["ordinary_inclusive_aliases"]
    require(
        aliases.get("status") == "approved"
        and aliases.get("initial_phase_parent_expense_id") == "pilot-execution-phase:0"
        and aliases.get("resume_requires_actual_covering_phase") is True,
        "fresh initial phase expense lineage required",
    )
    require(
        prior.get("old_raw_resume_or_relabel_authorized") is False
        and prior.get("resume_requested") is False
        and prior.get("numerical_accuracy_and_research_acceptance_authorized") is False,
        "old raw cannot be resumed/relabelled or accepted by this operational monitor",
    )
    resource_ref = prior["operational_resource_choice"]
    resource_prior = fixed_reference(resource_ref, RESOURCE_NAME, RESOURCE_SHA)
    require(
        approval["root_operational_guard_prior"] == resource_ref
        and resource_ref.get("status") == "approved_operational_prior"
        and resource_prior.get("status") == "approved_operational_prior"
        and resource_prior.get("planned_before_attempt") is True
        and resource_prior.get("financial_cap_projection") is False
        and resource_prior.get("formal_financial_execution_authorized") is False
        and resource_prior.get("stop_status") == "partial_unclosed"
        and resource_prior.get("financial_qualification") == "unknown"
        and resource_prior["source_canonical_identity_sha256"] == SOURCE_IDENTITY
        and resource_prior["source_native_payload_identity_sha256"] == SOURCE_NATIVE_IDENTITY,
        "actual administrative source82 resource choice required, not financial approval",
    )
    require(
        prior["phase_wall_limit_seconds"] == resource_prior["wall_limit_seconds"] == 30 * 86400
        and prior["parent_rss_limit_bytes"] == resource_prior["parent_RSS_limit_bytes"] == 16 * GiB
        and prior["child_rss_limit_bytes"] == resource_prior["child_RSS_limit_bytes"] == 16 * GiB
        and prior["poll_seconds"] == resource_prior["poll_seconds"]
        and prior["RSS_metric"] == resource_prior["RSS_metric"],
        "root fixed administrative wall/RSS/poll choices differ",
    )
    require(
        resource_prior["volume_reserve_bytes"]
        == {"WSL": 10 * GiB, "CAS_primary": 10 * GiB, "CAS_mirror": 10 * GiB},
        "original three independent volume reserves differ",
    )
    require(
        prior["typed_inputs"]["path"]
        == str(HISTORICAL_D / "task-5-fullmixed-prior-budget-candidate-author-v1-typed-inputs")
        and prior["typed_inputs"]["tree_sha256"]
        == "1e298d809691a98e3c55df52101142d5b432b417f5886e69efc9ed1ff811f4c7"
        and prior["typed_inputs"]["receipt_sha256"]
        == "36c0d914168f4cdceca55b570471fbb180a11f96939b02cfdc7e34a16e6d8284",
        "original typed inputs, their logical provenance and old source origin must remain intact",
    )
    resource_paths = {row["id"]: row["path"] for row in resource_prior["volume_observations"]}
    require(
        {row["id"]: row["path"] for row in prior["volume_probes"]}
        == {
            "WSL": resource_paths["WSL"],
            "C": resource_paths["CAS_primary"],
            "F": resource_paths["CAS_mirror"],
        },
        "working and both independent vault volume probes must retain exact paths",
    )
    manifest_ref = prior["prior_metadata_materialization"]
    manifest = fixed_reference(manifest_ref)
    root = reference_path(manifest_ref).parent
    require(
        root.parent == D
        and root.name.startswith("task-5-formal-prior-lock-materialized-")
        and manifest.get("schema") == "rb-f04-actual-prior-materialization-manifest-v1"
        and manifest.get("source_identity") == SOURCE_IDENTITY
        and manifest.get("actual_approval")
        == {key: approval_ref[key] for key in ("path", "sha256")}
        and manifest.get("financial_phase_approved") is False,
        "new immediate D2 closed metadata manifest required; old W1 plans are historical",
    )
    require(
        absolute(prior["plan"]["path"]) == root / "locked-prior-metadata",
        "new exact locked plan must belong to its materialization manifest",
    )
    files = manifest["files"]
    require(isinstance(files, dict) and files, "closed materialization roster required")
    observed = set()
    for file in root.rglob("*"):
        require(not file.is_symlink(), "metadata tree symlink forbidden")
        if file.is_file() and file != root / "manifest.json":
            observed.add(str(file.relative_to(root)))
    require(observed == set(files), "extra/missing materialized metadata files")
    for relative, description in files.items():
        path = root / relative
        try:
            path.resolve(strict=True).relative_to(root)
        except (ValueError, OSError) as exc:
            raise GuardRejectedError("unsafe materialized file path") from exc
        require(path.stat().st_size == description["bytes"], "materialized bytes length changed")
        if verify_files:
            require(sha(path) == description["sha256"], "materialized immutable bytes changed")
    expected_plan_files = {
        key[len("locked-prior-metadata/") :]: value["sha256"]
        for key, value in files.items()
        if key.startswith("locked-prior-metadata/")
    }
    require(
        expected_plan_files == prior["plan"]["files"]
        and digest(expected_plan_files) == prior["plan"]["tree_sha256"]
        and expected_plan_files["receipt.json"] == prior["plan"]["receipt_sha256"],
        "root locked plan receipt, parts and physical tree differ",
    )
    progress = json.loads((root / "materialization-progress.json").read_text())
    require(
        progress.get("status") == "actual_approved_prior_metadata_materialized"
        and progress.get("actual_lock_API_validate_and_source_binding") == "PASS"
        and progress.get("source82_before_after_stable") is True
        and progress.get("financial_workers_RNG_solver_SDE_calls") == 0
        and progress.get("formal_financial_phase_approved") is False
        and progress.get("pilot_started") is False
        and progress.get("financial_qualification") == "unknown"
        and progress.get("source_identity") == SOURCE_IDENTITY
        and progress.get("source_native_payload_identity") == SOURCE_NATIVE_IDENTITY
        and {
            key: progress.get(key)
            for key in ("jobs", "cases", "attempts", "teachers", "drivers", "literal_cap_options")
        }
        == {
            "jobs": 3138,
            "cases": 121,
            "attempts": 51,
            "teachers": 20,
            "drivers": 10,
            "literal_cap_options": 573122,
        }
        and progress.get("actual_root_approval") == manifest["actual_approval"]
        and progress.get("actual_independent_review_SHA")
        == prior["full_budget_and_cap_recipe_review"]["sha256"]
        and progress.get("root_operational_guard_is_financial_cap") is False,
        "complete validated current82 metadata required; partial/unknown cannot launch",
    )
    plan_receipt = json.loads((root / "locked-prior-metadata/receipt.json").read_text())
    require(plan_receipt == progress["locked_prior_receipt"], "actual locked plan receipt changed")
    require(
        json.loads((root / "actual-root-approval-copy.json").read_text()) == approval
        and json.loads((root / "root-operational-guard-copy.json").read_text()) == resource_prior
        and json.loads((root / "source-snapshot/source-identity.json").read_text())
        == prior["source_identity"],
        "materialized approval/resource/source snapshot differ",
    )
    for relative, expected in prior["source_identity"]["files"].items():
        require(
            files["source-snapshot/" + relative]["sha256"] == expected,
            "source snapshot is not the current closed82 bytes",
        )
    return {
        "root_approval_sha256": approval_ref["sha256"],
        "independent_prior_sha256": prior["full_budget_and_cap_recipe_review"]["sha256"],
        "source_decisions_sha256": prior["approved_budget_bindings"][
            "source_limited_decisions_sha256"
        ],
        "source_evidence_sha256": SOURCE_EVIDENCE_SHA,
        "materializer_sha256": MATERIALIZER_SHA,
        "interface_sha256": INTERFACE_SHA,
        "operational_resource_sha256": RESOURCE_SHA,
        "materialized_manifest_sha256": manifest_ref["sha256"],
        "locked_plan_receipt_sha256": prior["plan"]["receipt_sha256"],
        "cap_recipe_digest": prior["approved_budget_bindings"]["cap_recipe_digest"],
        "literal_cap_options": 573122,
    }


def original_source_binding(prior):
    limited_source_review(prior)
    identity = prior["source_identity"]
    require(
        isinstance(identity, dict) and len(identity["files"]) == 82,
        "current source closure must retain82 files",
    )
    require(not identity["dynamic_imports"], "unresolved dynamic source closure")
    require(
        digest(identity) == prior["source_identity_sha256"] == SOURCE_IDENTITY,
        "source prior identity is not current fixed closure",
    )
    for relative, expected in identity["files"].items():
        path = (WT / relative).resolve(strict=True)
        path.relative_to(WT)
        require(sha(path) == expected, "current source bytes changed: " + relative)
    return {
        "sha256": digest(identity),
        "file_count": 82,
        "files": identity["files"],
        "metadata_authority": metadata_authority(prior),
    }


def terminal_authority(prior):
    """Reject live/unknown closure before full native hashing or numerical decoding."""
    require(
        prior.get("original_process_ids") == ORIGINAL_PIDS,
        "all three original process identities must remain bound",
    )
    require(
        all(not Path(f"/proc/{pid}").exists() for pid in ORIGINAL_PIDS),
        "original pilot/enclosing/monitor/child processes must all be terminal",
    )
    original = fixed_reference(
        prior["original_launch_guard"], ORIGINAL_GUARD_NAME, ORIGINAL_GUARD_SHA
    )
    require(
        original.get("root_preapproved") is True
        and original.get("formal_financial_launch_authorized") is True
        and original["native_output_path"] == str(ORIGINAL_NATIVE),
        "actual historical launch authority required, not a new launch permission",
    )
    for key in (
        "source_identity",
        "source_identity_sha256",
        "source_native_payload_sha256",
        "source_limited_decisions",
        "source_rebind_evidence",
        "approved_budget_bindings",
        "full_budget_and_cap_recipe_review",
        "actual_root_metadata_approval",
        "prior_metadata_materialization",
        "plan",
        "typed_inputs",
        "original_counts",
        "original_teacher_N_candidates",
        "operational_resource_choice",
    ):
        require(
            prior[key] == original[key],
            "original closed source/plan/input authority differs: " + key,
        )
    monitor_ref = prior["original_terminal_monitor_receipt"]
    outer_ref = prior["original_terminal_enclosing_receipt"]
    require(
        absolute(monitor_ref["path"])
        == D / "task-5-formal-pilot-root-operational-observation-v3/parent-cost-and-status.json",
        "original terminal monitor receipt path differs",
    )
    require(
        absolute(outer_ref["path"])
        == D / "task-5-formal-pilot-root-enclosing-observation-v3/parent-cost-and-status.json",
        "original terminal enclosing receipt path differs",
    )
    monitor, outer = fixed_reference(monitor_ref), fixed_reference(outer_ref)
    require(
        monitor.get("child_exit_code") is not None
        and isinstance(monitor.get("child_exit_code"), int)
        and not isinstance(monitor.get("child_exit_code"), bool)
        and monitor.get("child_pid") == ORIGINAL_PIDS[2]
        and monitor.get("prior_sha256") == ORIGINAL_GUARD_SHA
        and monitor.get("native_output_path") == str(ORIGINAL_NATIVE),
        "original monitor has no authenticated terminal child",
    )
    require(
        outer.get("schema") == "rb-f04-root-formal-monitor-enclosing-cost-v1"
        and outer.get("status") == "terminal_requires_native_and_saved_result_inspection"
        and isinstance(outer.get("monitor_exit_code"), int)
        and not isinstance(outer.get("monitor_exit_code"), bool)
        and outer.get("monitor_pid") == ORIGINAL_PIDS[1]
        and outer.get("guard_sha256") == ORIGINAL_GUARD_SHA,
        "original enclosing receipt is missing or nonterminal",
    )
    return {
        "original_launch_guard_sha256": ORIGINAL_GUARD_SHA,
        "original_process_ids": ORIGINAL_PIDS,
        "monitor": monitor_ref,
        "enclosing": outer_ref,
        "monitor_status": monitor["status"],
        "monitor_exit_code": outer["monitor_exit_code"],
        "native_child_exit_code": monitor["child_exit_code"],
        "historical_cost_or_failure_reclassified": False,
    }


def closed_native_binding(prior):
    """Authenticate an exact finite terminal byte set; no financial arrays are decoded."""
    spec = prior.get("closed_native")
    require(
        isinstance(spec, dict) and spec.get("path") == str(ORIGINAL_NATIVE),
        "only the original current82 closed native tree may be checked",
    )
    expected = spec.get("files")
    require(
        isinstance(expected, dict) and bool(expected),
        "root must bind the terminal native finite file set",
    )
    for relative, value in expected.items():
        name = Path(relative)
        require(
            isinstance(relative, str)
            and not name.is_absolute()
            and ".." not in name.parts
            and isinstance(value, str)
            and len(value) == 64,
            "unsafe or pending native byte binding",
        )
    actual = {}
    for path in sorted(ORIGINAL_NATIVE.rglob("*")):
        require(not path.is_symlink(), "native symbolic links cannot bind closed bytes")
        if path.is_file():
            actual[str(path.relative_to(ORIGINAL_NATIVE))] = sha(path)
    require(
        actual == expected and digest(actual) == spec.get("tree_sha256"),
        "original native byte set changed or incomplete",
    )
    checkpoint = spec.get("latest_checkpoint")
    require(isinstance(checkpoint, dict), "terminal latest checkpoint receipt required")
    choices = sorted(ORIGINAL_NATIVE.glob("checkpoint*"))
    require(
        bool(choices) and choices[-1].is_dir() and checkpoint.get("path") == str(choices[-1]),
        "bound checkpoint is absent or is not the original final saved checkpoint",
    )
    checked = tree_binding(checkpoint)
    relative = str(choices[-1].relative_to(ORIGINAL_NATIVE))
    require(
        {
            key[len(relative) + 1 :]: value
            for key, value in actual.items()
            if key.startswith(relative + "/")
        }
        == checked["files"],
        "checkpoint receipt/parts are not in the terminal native byte set",
    )
    return {
        "path": str(ORIGINAL_NATIVE),
        "tree_sha256": digest(actual),
        "physical_files": len(actual),
        "latest_checkpoint": checked,
        "original_roster_may_be_missing_or_unknown": True,
    }


def source_binding(prior):
    terminal = terminal_authority(prior)
    binding = original_source_binding(prior)
    binding["terminal_native_authority"] = terminal
    binding["closed_native"] = closed_native_binding(prior)
    return binding


def load_guard(path, *, child=False):
    supplied = absolute(str(path))
    require(not supplied.is_symlink(), "fixed guard cannot be a symlink")
    path = supplied.resolve(strict=True)
    require(path.parent == D, "saved-check guard must be an immediate D2 file")
    prior_bytes = path.read_bytes()
    prior = json.loads(prior_bytes)
    # These gates precede source/native hashing, financial imports and any child.
    require(
        prior.get("root_preapproved") is True,
        "root saved-check prior approval required; candidate cannot execute",
    )
    require(
        prior.get("execute_saved_check") is True,
        "separate root saved-only execution authorization required",
    )
    require(
        prior.get("finance_acceptance") is False
        and prior.get("formal_financial_launch_authorized") is False,
        "saved-only execution cannot grant financial launch or acceptance",
    )
    require(
        prior.get("schema") == SCHEMA
        and prior.get("prior_role") == "root_fixed_operational_prior"
        and prior.get("planned_before_attempt") is True
        and prior.get("saved_check_authorized_by") == "root",
        "root separate pre-attempt saved-check authority required",
    )
    terminal_authority(prior)
    require(
        prior.get("source_approval_status") == "approved_fixed_current_source"
        and prior.get("administrative_guard_only") is True
        and prior.get("financial_A_cap_projection_approved") is False
        and prior.get("financial_qualification") == "unknown"
        and prior.get("formal_phase_completion_claimed") is False,
        "source/administrative/unknown state cannot be promoted to finance",
    )
    require(prior["monitor_sha256"] == sha(__file__), "observer source changed after prior")
    require(
        prior["phase_wall_limit_seconds"] == 30 * 86400
        and prior["parent_rss_limit_bytes"] == prior["child_rss_limit_bytes"] == 16 * GiB
        and prior["poll_seconds"] == 1
        and prior["RSS_metric"] == "maximum_individual_process_RSS_not_RLIMIT_AS",
        "original administrative wall/RSS/poll choices differ",
    )
    require(
        prior["original_counts"] == {"jobs": 3138, "cases": 121, "attempts": 51}
        and prior["original_teacher_N_candidates"] == [1024, 4096, 16384, 65536],
        "original complete obligations differ",
    )
    require(prior["python_executable"] == sys.executable, "approved Python invocation differs")
    probes = prior["volume_probes"]
    require(
        [row["id"] for row in probes] == ["WSL", "C", "F"]
        and all(row["reserve_bytes"] == 10 * GiB for row in probes)
        and len({os.stat(absolute(row["path"])).st_dev for row in probes}) == 3,
        "original three independent volume reserves required",
    )
    output, receipts = absolute(prior["native_output_path"]), absolute(prior["receipt_directory"])
    require(
        output.parent == D
        and output.name.startswith("task-5-formal-pilot-saved-check-")
        and receipts.parent == D
        and receipts.name.startswith("task-5-formal-pilot-saved-check-")
        and output != receipts
        and not output.exists(),
        "fresh separate saved-check output required",
    )
    if child:
        require(
            receipts.is_dir() and (receipts / "prior-root-fixed.json").read_bytes() == prior_bytes,
            "child must use the exact observer-fixed preflight prior",
        )
    else:
        require(not receipts.exists(), "fresh saved-check observer receipts required")
    limited_source_review(prior)
    actual_budget_review(prior)
    metadata_authority(prior, verify_files=False)
    spec = prior.get("closed_native")
    require(
        isinstance(spec, dict)
        and bool(spec.get("files"))
        and isinstance(spec.get("latest_checkpoint"), dict),
        "root has not bound terminal native/checkpoint bytes",
    )
    return prior, path, hashlib.sha256(prior_bytes).hexdigest(), prior_bytes


def child(guard_path):
    """No random generation; full saved SDE/label replay is the native checker."""
    prior, _, prior_sha, _ = load_guard(guard_path, child=True)
    # Heavy imports and full hydration occur only after terminal/root authorization.
    from check_pilot import check_pilot
    from run_pilot import read_pilot_artifact, unpack_inputs, write_pilot_artifact

    plan, _ = read_pilot_artifact(Path(prior["plan"]["path"]))
    encoded, _ = read_pilot_artifact(Path(prior["typed_inputs"]["path"]))
    inputs = unpack_inputs(encoded)
    result = check_pilot(
        ORIGINAL_NATIVE,
        expected_plan=plan,
        source_root=WT,
        context={"inputs": inputs, "parameters": inputs["parameters"]},
    )
    # Preserve the complete returned snapshot and original unknown/cap/failure values.
    write_pilot_artifact(Path(prior["native_output_path"]), result)
    print(
        json.dumps(
            {
                "root_prior_sha256": prior_sha,
                "closed": result["closed"],
                "financial_qualification": result["financial_qualification"],
                "missing_cases": result["missing_cases"],
                "missing_attempts": result["missing_attempts"],
                "missing_jobs": result["missing_jobs"],
                "finance_acceptance": False,
                "all_original_roster_checked_no_subset": True,
            },
            allow_nan=False,
        )
    )
    return 0 if result["closed"] else 2


def rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (FileNotFoundError, ProcessLookupError, OSError):
        return None
    return None


def volume_sample(probes):
    return [
        {
            "id": row["id"],
            "path": row["path"],
            "reserve_bytes": row["reserve_bytes"],
            "free_bytes": shutil.disk_usage(row["path"]).free,
        }
        for row in probes
    ]


def choose_stop(elapsed, child_rss, parent_rss, volumes, prior):
    if elapsed >= prior["phase_wall_limit_seconds"]:
        return {
            "metric": "outer_phase_wall",
            "limit_seconds": prior["phase_wall_limit_seconds"],
            "observed_seconds": elapsed,
        }
    if child_rss is not None and child_rss > prior["child_rss_limit_bytes"]:
        return {
            "metric": "individual_child_rss",
            "limit_bytes": prior["child_rss_limit_bytes"],
            "observed_bytes": child_rss,
        }
    if parent_rss is not None and parent_rss > prior["parent_rss_limit_bytes"]:
        return {
            "metric": "individual_parent_rss",
            "limit_bytes": prior["parent_rss_limit_bytes"],
            "observed_bytes": parent_rss,
        }
    for row in volumes:
        if row["free_bytes"] <= row["reserve_bytes"]:
            return {"metric": "volume_reserve", **row}
    return None


def terminal_status(
    exit_code, requested_stop, signal_delivered, observer_errors, bindings_unchanged
):
    if not bindings_unchanged:
        return "unclosed_source_or_input_binding_changed"
    if observer_errors:
        return "unclosed_monitor_observer_error"
    if exit_code is None:
        return "unclosed_child_terminal_unknown"
    if signal_delivered is True:
        return "administrative_partial_unclosed"
    if exit_code != 0:
        return "unclosed_child_exit"
    if requested_stop is not None:
        return "administrative_limit_observed_terminal_unclosed"
    return "saved_checker_terminal_needs_result_inspection"


def run(guard_path):
    started = clock()
    prior, fixed_path, prior_sha, prior_bytes = load_guard(guard_path)
    source_before = source_binding(prior)
    plan_before = tree_binding(prior["plan"])
    inputs_before = tree_binding(prior["typed_inputs"])
    initial_volumes = volume_sample(prior["volume_probes"])
    receipts = absolute(prior["receipt_directory"])
    receipts.mkdir(parents=True, exist_ok=False)
    (receipts / "prior-root-fixed.json").write_bytes(prior_bytes)
    command = [
        prior["python_executable"],
        str(ENTRY),
        "--child",
        "--guard",
        str(fixed_path),
    ]
    python_paths = [
        str(WT / p)
        for p in (
            "johnhull/research/RB-F04/dynamic_hedging",
            "johnhull/hullkit/src",
            "deep_hedge_price/src",
        )
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(python_paths)
    save(
        receipts / "before-bindings-and-command.json",
        {
            "started": started,
            "prior_path": str(fixed_path),
            "prior_sha256": prior_sha,
            "monitor_sha256": sha(__file__),
            "source": source_before,
            "plan": plan_before,
            "typed_inputs": inputs_before,
            "argv": command,
            "PYTHONPATH": python_paths,
            "python_executable": sys.executable,
            "python_version": sys.version,
            "initial_volume_observations": initial_volumes,
            "original_obligations": prior["original_counts"],
            "all_original_jobs_cases_N_unchanged_by_monitor": True,
            "financial_A_cap_projection": False,
        },
    )
    require(sha(fixed_path) == prior_sha, "root fixed prior changed during preflight")
    require(prior["poll_seconds"] <= 60, "poll must allow bounded observations")
    child_usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent_kernel_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    process, code, requested, signal_delivered = None, None, None, False
    child_peak, parent_peak = None, None
    child_unknown, parent_unknown = 0, 0
    observer_errors = []
    last_volumes = initial_volumes
    stop_clock = None
    launched = None
    try:
        requested = choose_stop(
            time.perf_counter() - started["wall"], None, rss(os.getpid()), initial_volumes, prior
        )
        if requested is None:
            with (
                (receipts / "stdout.log").open("wb") as stdout,
                (receipts / "stderr.log").open("wb") as stderr,
                (receipts / "observations.jsonl").open("w") as samples,
            ):
                launched = clock()
                process = subprocess.Popen(
                    command, cwd=WT, env=env, stdout=stdout, stderr=stderr, start_new_session=True
                )
                while process.poll() is None:
                    child_rss, parent_rss = rss(process.pid), rss(os.getpid())
                    if child_rss is None:
                        child_unknown += 1
                    else:
                        child_peak = child_rss if child_peak is None else max(child_peak, child_rss)
                    if parent_rss is None:
                        parent_unknown += 1
                    else:
                        parent_peak = (
                            parent_rss if parent_peak is None else max(parent_peak, parent_rss)
                        )
                    try:
                        last_volumes = volume_sample(prior["volume_probes"])
                    except OSError as exc:
                        observer_errors.append(
                            "volume_read: " + type(exc).__name__ + ": " + str(exc)
                        )
                        requested = {
                            "metric": "volume_observation_unavailable",
                            "administrative_reason": "monitor cannot observe prior reserve",
                        }
                    now = clock()
                    observation = {
                        "clock": now,
                        "elapsed_seconds": now["wall"] - started["wall"],
                        "child_rss_bytes": child_rss,
                        "parent_rss_bytes": parent_rss,
                        "volumes": last_volumes,
                    }
                    samples.write(json.dumps(observation, allow_nan=False) + chr(10))
                    samples.flush()
                    if requested is None:
                        requested = choose_stop(
                            observation["elapsed_seconds"],
                            child_rss,
                            parent_rss,
                            last_volumes,
                            prior,
                        )
                    if requested is not None:
                        stop_clock = clock()
                        requested["observed_clock"] = stop_clock
                        # Poll again: a solver exit racing the observation is not relabeled a resource stop.
                        code = process.poll()
                        if code is None:
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                                signal_delivered = True
                            except ProcessLookupError:
                                requested["signal_delivery"] = (
                                    "process group already absent; order unknown"
                                )
                            except OSError as exc:
                                observer_errors.append(
                                    "signal_delivery: " + type(exc).__name__ + ": " + str(exc)
                                )
                        break
                    remaining = prior["phase_wall_limit_seconds"] - (now["wall"] - started["wall"])
                    time.sleep(min(prior["poll_seconds"], max(0.001, remaining)))
                code = process.wait()
        else:
            stop_clock = clock()
            requested["observed_clock"] = stop_clock
    except BaseException as exc:
        observer_errors.append("parent_operation: " + type(exc).__name__ + ": " + str(exc))
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                signal_delivered = True
            except OSError as cleanup:
                observer_errors.append(
                    "observer_cleanup: " + type(cleanup).__name__ + ": " + str(cleanup)
                )
            code = process.wait()
        elif process is not None:
            code = process.poll()
    child_usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    child_kernel = (
        child_usage_after.ru_maxrss * 1024
        if process is not None and child_usage_before.ru_maxrss == 0
        else None
    )
    bindings_unchanged = True
    after = {}
    try:
        after = {
            "source": source_binding(prior),
            "plan": tree_binding(prior["plan"]),
            "typed_inputs": tree_binding(prior["typed_inputs"]),
            "prior_sha256": sha(fixed_path),
            "monitor_sha256": sha(__file__),
        }
        bindings_unchanged = (
            after["prior_sha256"] == prior_sha
            and after["monitor_sha256"] == prior["monitor_sha256"]
        )
        bindings_unchanged = (
            bindings_unchanged
            and after["source"] == source_before
            and after["plan"] == plan_before
            and after["typed_inputs"] == inputs_before
        )
    except (OSError, ValueError, KeyError) as exc:
        bindings_unchanged = False
        after["binding_error"] = type(exc).__name__ + ": " + str(exc)
    save(receipts / "after-bindings.json", after)
    parent_rss = rss(os.getpid())
    if parent_rss is None:
        parent_unknown += 1
    else:
        parent_peak = parent_rss if parent_peak is None else max(parent_peak, parent_rss)
    parent_kernel = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    try:
        last_volumes = volume_sample(prior["volume_probes"])
    except OSError as exc:
        observer_errors.append("closing_volume_read: " + type(exc).__name__ + ": " + str(exc))
    stopped = clock()
    elapsed = stopped["wall"] - started["wall"]
    child_available = [x for x in (child_peak, child_kernel) if x is not None]
    parent_available = [x for x in (parent_peak, parent_kernel) if x is not None]
    closing_stop = choose_stop(
        elapsed,
        max(child_available) if child_available else None,
        max(parent_available) if parent_available else None,
        last_volumes,
        prior,
    )
    if requested is None and closing_stop is not None:
        requested = closing_stop | {
            "observation_phase": "after_child_wait_and_readonly_binding_check"
        }
        stop_clock = stopped
    status = terminal_status(code, requested, signal_delivered, observer_errors, bindings_unchanged)
    if process is None and requested is not None and not observer_errors and bindings_unchanged:
        status = "administrative_preflight_partial_unclosed"
    receipt = {
        "scope": "root saved-only numerical checker observer; original full native snapshot and fresh output",
        "status": status,
        "child_exit_code": code,
        "child_pid": None if process is None else process.pid,
        "started": started,
        "launched": launched,
        "stopped": stopped,
        "outer_wall_seconds": elapsed,
        "parent_CPU_seconds": stopped["cpu"] - started["cpu"],
        "child_inclusive_CPU_seconds": None
        if process is None
        else (
            child_usage_after.ru_utime
            + child_usage_after.ru_stime
            - child_usage_before.ru_utime
            - child_usage_before.ru_stime
        ),
        "observed_child_peak_RSS_bytes": child_peak,
        "child_kernel_peak_RSS_bytes": child_kernel,
        "child_kernel_highwater_before_bytes": child_usage_before.ru_maxrss * 1024,
        "child_kernel_scope": "waited single child cumulative getrusage; unknown attribution if historical child baseline nonzero",
        "observed_parent_peak_RSS_bytes": parent_peak,
        "parent_kernel_peak_RSS_bytes": parent_kernel,
        "parent_kernel_highwater_before_bytes": parent_kernel_before,
        "parent_kernel_scope": "whole monitor lifetime; baseline retained separately",
        "child_rss_unknown_sample_count": child_unknown,
        "parent_rss_unknown_sample_count": parent_unknown,
        "individual_RSS_is_not_RLIMIT_AS_or_tree_sum": True,
        "wall_overrun_seconds": max(0.0, elapsed - prior["phase_wall_limit_seconds"]),
        "child_rss_overrun_bytes": None
        if not child_available
        else max(0, max(child_available) - prior["child_rss_limit_bytes"]),
        "parent_rss_overrun_bytes": None
        if not parent_available
        else max(0, max(parent_available) - prior["parent_rss_limit_bytes"]),
        "requested_administrative_stop": requested,
        "stop_clock": stop_clock,
        "signal_delivered": signal_delivered,
        "last_volume_observations": last_volumes,
        "observed_volume_reserve_shortfall_bytes": {
            row["id"]: max(0, row["reserve_bytes"] - row["free_bytes"]) for row in last_volumes
        },
        "observer_errors": observer_errors,
        "source_inputs_prior_monitor_unchanged": bindings_unchanged,
        "prior_path": str(fixed_path),
        "prior_sha256": prior_sha,
        "argv": command,
        "native_output_path": prior["native_output_path"],
        "native_data_rewritten_by_monitor": False,
        "original_obligations": prior["original_counts"],
        "original_N_candidates": prior["original_teacher_N_candidates"],
        "financial_qualification": "unknown",
        "formal_pilot_completion_claimed": False,
        "financial_A_cap_projection_approved": False,
        "saved_check_result_inspection_required": True,
        "finance_acceptance": False,
        "original_generation_costs_readded": False,
        "full_job_hydration_and_final_full_result_serialization_in_child_clock": True,
        "legacy_and_native_expenses": "existing inclusive native phase/jobs/driver/history are breakdowns; do not add them to this outer observation again",
        "resource_fault_order": "unknown unless signal/live observation and saved native records establish causation; nonzero exit alone is never a resource cap",
        "partial_raw_policy": "all native saved/checkpoint files retained; unsaved financial arrays remain unavailable; no N/roster change",
        "monitoring_guarantee": "sampled RSS/free-space only; growth between polls and blocking kill-wait/postbind tail may exceed limits",
        "measured_endpoint": "after child wait, final readonly source/input/prior binding and RSS observation; before receipt construction/write/stdout",
        "own_final_receipt_write_stdout_cost": "unknown; root enclosing process receipt must measure separately",
    }
    save(receipts / "parent-cost-and-status.json", receipt)
    print(
        json.dumps(
            {
                "status": status,
                "child_exit_code": code,
                "receipt": str(receipts / "parent-cost-and-status.json"),
            }
        )
    )
    return 0 if status == "saved_checker_terminal_needs_result_inspection" else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--child", action="store_true", help="root observer child API harness")
    args = parser.parse_args(argv)
    try:
        return child(args.guard) if args.child else run(args.guard)
    except GuardRejectedError as exc:
        print(
            json.dumps(
                {
                    "status": "guard_rejected_no_child",
                    "reason": str(exc),
                    "financial_execution": False,
                    "saved_numerical_execution": False,
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
