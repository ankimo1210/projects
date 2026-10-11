"""Authenticate archived producer and current saved-only verifier separately.

A trusted binding is an EXPECTED recipe already authenticated by the caller's
actual guard and prior review. Its schema or approval flags do not establish its
origin, authority, source review, or permission. Never accept a self-declared
recipe from the raw being checked. This helper cannot authorize a fresh run.

Historical dependency completeness belongs to the authenticated original
producer closure. Its complete expected file roster is rehashed without loading
or running archived Python code. The verifier uses the normal live closure
walker, including required entrypoints and loaded-alias checks.
"""

from pathlib import Path

import _pilot_saved_storage as storage
import run_reference as runner

_SCHEMA = "rb-f04-saved-producer-verifier-binding-v1"
_SCOPE = "saved_original_raw_only"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def authenticate_saved_sources(
    producer_source,
    *,
    producer_root,
    verifier_root,
    locked_plan,
    input_bindings,
    trusted_binding,
):
    """Authenticate original inputs/source and the new verifier, without finance.

    input_bindings is the caller's ID-to-identity map computed from the actual
    original inputs, not a substitute for authenticating those input artifacts.
    Digest fields use the original native payload format. The streaming encoder
    avoids copying the full locked plan; the returned locked_plan is the same
    unchanged object. The caller must retain original raw, failures, and expenses.
    No qualification, financial cap, cost closure, or launch authority is created.
    """
    _require(
        isinstance(trusted_binding, dict)
        and trusted_binding.get("schema") == _SCHEMA
        and trusted_binding.get("planned_before_check") is True
        and trusted_binding.get("root_preapproved") is True
        and trusted_binding.get("scope") == _SCOPE,
        "trusted saved-only expected binding is required",
    )
    _require(
        {
            "producer_source_sha256",
            "producer_source_files",
            "producer_plan_sha256",
            "producer_input_bindings_sha256",
            "verifier_source_sha256",
        }
        <= trusted_binding.keys(),
        "trusted saved expected digests and complete source roster are required",
    )
    producer_digest = storage.payload_digest(producer_source)
    _require(
        producer_digest == trusted_binding["producer_source_sha256"],
        "producer source differs from trusted original identity",
    )
    _require(
        producer_source.get("files")
        and producer_source.get("files") == trusted_binding["producer_source_files"],
        "producer source roster differs from trusted original closure",
    )
    _require(
        producer_source.get("dynamic_imports") == [],
        "original producer closure has unresolved dynamic imports",
    )
    _require(
        storage.payload_digest(locked_plan["source"]) == producer_digest,
        "original plan source differs from original producer",
    )
    plan_digest = storage.payload_digest(locked_plan)
    _require(
        plan_digest == trusted_binding["producer_plan_sha256"],
        "producer plan differs from trusted original plan",
    )
    input_digest = storage.payload_digest(input_bindings)
    _require(
        input_digest == trusted_binding["producer_input_bindings_sha256"]
        and input_bindings == locked_plan["input_bindings"],
        "original input bindings differ from trusted producer plan",
    )
    producer_root = Path(producer_root).resolve(strict=True)
    actual_files = runner.protocol.source_registry(producer_root, sorted(producer_source["files"]))
    _require(
        actual_files == producer_source["files"],
        "archived producer source bytes differ from original closure",
    )

    verifier_root = Path(verifier_root).resolve(strict=True)
    verifier_source = runner.execution_source_identity(verifier_root)
    _require(
        not verifier_source.get("dynamic_imports"),
        "unresolved dynamic imports in current verifier source",
    )
    verifier_digest = storage.payload_digest(verifier_source)
    _require(
        verifier_digest == trusted_binding["verifier_source_sha256"],
        "current verifier source differs from trusted verifier identity",
    )
    return {
        "schema": "rb-f04-saved-source-provenance-v1",
        "producer_source": producer_source,
        "producer_source_sha256": producer_digest,
        "verifier_source": verifier_source,
        "verifier_source_sha256": verifier_digest,
        "locked_plan": locked_plan,
        "producer_plan_sha256": plan_digest,
        "input_bindings": input_bindings,
        "producer_input_bindings_sha256": input_digest,
        "provenance": {
            "scope": _SCOPE,
            "producer_root": str(producer_root),
            "verifier_root": str(verifier_root),
            "trusted_binding_sha256": storage.payload_digest(trusted_binding),
            "basis": "authenticated original closure roster and archived bytes; "
            "normal current verifier closure and loaded-alias checks",
        },
    }
