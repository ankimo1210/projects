from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

FIDELITY_CLASSES = {
    "A_AUTHOR_CODE_EXACT",
    "B_PAPER_EXACT",
    "C_PAPER_CONSTRAINED",
    "D_MODERNIZED_AUDIT",
}
CONFIDENCE_LEVELS = {"verified", "inferred_from_shape", "unresolved"}
SOURCE_TYPES = {"PAPER", "AUTHOR_CODE", "DATASET_DOC", "ASSUMPTION"}
RUN_IDENTITY_FIELDS = {
    "paper_id",
    "implementation_profile",
    "fidelity_class",
    "paper_version",
    "source_code_commit",
    "dataset_profile",
    "random_seed",
}


class ProfileValidationError(ValueError):
    """Raised when a profile violates the fidelity/provenance contract."""


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def profile_directory() -> Path:
    return project_root() / "configs" / "profiles"


def _lookup(document: dict[str, Any], dotted_path: str) -> Any:
    current: Any = document
    for component in dotted_path.split("."):
        if not isinstance(current, dict) or component not in current:
            raise ProfileValidationError(f"material field is missing: {dotted_path}")
        current = current[component]
    return current


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    missing_identity = sorted(RUN_IDENTITY_FIELDS - profile.keys())
    if missing_identity:
        raise ProfileValidationError(f"missing run identity fields: {missing_identity}")
    fidelity = profile["fidelity_class"]
    if fidelity not in FIDELITY_CLASSES:
        raise ProfileValidationError(f"unknown fidelity class: {fidelity}")

    material_fields = profile.get("material_fields")
    if not isinstance(material_fields, list) or not material_fields:
        raise ProfileValidationError("material_fields must be a non-empty list")
    if len(set(material_fields)) != len(material_fields):
        raise ProfileValidationError("material_fields contains duplicates")

    provenance = profile.get("provenance")
    if not isinstance(provenance, dict):
        raise ProfileValidationError("provenance must be a mapping")

    unresolved: list[str] = []
    for field in material_fields:
        _lookup(profile, field)
        evidence = provenance.get(field)
        if not isinstance(evidence, dict):
            raise ProfileValidationError(f"missing provenance for material field: {field}")
        if evidence.get("source_type") not in SOURCE_TYPES:
            raise ProfileValidationError(f"invalid source_type for {field}")
        if not evidence.get("locator"):
            raise ProfileValidationError(f"empty provenance locator for {field}")
        confidence = evidence.get("confidence")
        if confidence not in CONFIDENCE_LEVELS:
            raise ProfileValidationError(f"invalid confidence for {field}: {confidence}")
        if confidence == "unresolved":
            unresolved.append(field)

    if fidelity == "B_PAPER_EXACT" and unresolved:
        raise ProfileValidationError(
            "B_PAPER_EXACT cannot contain unresolved material fields: " + ", ".join(unresolved)
        )

    profile["unresolved_material_fields"] = unresolved
    return profile


def load_profile(name: str, *, validate: bool = True) -> dict[str, Any]:
    if Path(name).name != name or not name.replace("_", "").isalnum():
        raise ProfileValidationError(f"invalid profile name: {name!r}")
    path = profile_directory() / f"{name}.yaml"
    if not path.is_file():
        available = ", ".join(sorted(item.stem for item in profile_directory().glob("*.yaml")))
        raise FileNotFoundError(f"profile {name!r} not found; available: {available}")
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise ProfileValidationError(f"profile is not a mapping: {path}")
    document = deepcopy(document)
    if document.get("implementation_profile") != name:
        raise ProfileValidationError(
            f"filename/profile mismatch: {name!r} != {document.get('implementation_profile')!r}"
        )
    return validate_profile(document) if validate else document


def validate_all_profiles() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for path in sorted(profile_directory().glob("*.yaml")):
        try:
            profile = load_profile(path.stem)
        except Exception as exc:  # validation report intentionally captures every profile
            results[path.stem] = {"valid": False, "error": str(exc)}
        else:
            results[path.stem] = {
                "valid": True,
                "fidelity_class": profile["fidelity_class"],
                "unresolved_material_fields": profile["unresolved_material_fields"],
            }
    return results
