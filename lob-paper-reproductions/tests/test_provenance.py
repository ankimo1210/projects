from __future__ import annotations

from copy import deepcopy

import pytest

from lob_reproductions.evaluation.comparison import comparison_compatibility
from lob_reproductions.provenance.profiles import (
    ProfileValidationError,
    load_profile,
    validate_all_profiles,
    validate_profile,
)
from lob_reproductions.provenance.sources import source_manifests, verify_sources


def test_every_profile_is_valid_and_exact_paper_profiles_are_resolved() -> None:
    results = validate_all_profiles()
    assert results
    assert all(item["valid"] for item in results.values())
    for item in results.values():
        if item["fidelity_class"] == "B_PAPER_EXACT":
            assert item["unresolved_material_fields"] == []


def test_paper_exact_validator_rejects_an_unresolved_material_choice() -> None:
    profile = deepcopy(load_profile("deeplob_ieee_2019"))
    field = profile["material_fields"][0]
    profile["provenance"][field]["confidence"] = "unresolved"
    with pytest.raises(ProfileValidationError, match="B_PAPER_EXACT"):
        validate_profile(profile)


def test_source_manifests_pin_versions_hashes_commits_and_licenses() -> None:
    papers = 0
    repositories = 0
    for _path, manifest in source_manifests():
        if "paper_id" in manifest:
            papers += 1
            assert manifest["arxiv_version"].startswith("v")
            assert len(manifest["sha256"]) == 64
            assert manifest["source_url"].startswith("https://")
        else:
            repositories += 1
            assert len(manifest["commit"]) == 40
            assert len(manifest["commit_tree"]) == 40
            assert len(manifest["archive_sha256"]) == 64
            assert manifest["archive_url"].startswith("https://codeload.github.com/")
            assert manifest["license_status"] in {"absent", "confirmed"}
            assert isinstance(manifest["vendoring_allowed"], bool)
            assert manifest["files_used_as_evidence"]
            assert all(len(item["sha256"]) == 64 for item in manifest["files_used_as_evidence"])
    assert papers == 5
    assert repositories == 2


def test_fetched_sources_match_pinned_hashes_when_present() -> None:
    report = verify_sources()
    assert report["ok"]
    assert report["mismatches"] == []
    for item in report["items"]:
        if item["exists"]:
            assert item["hash_matches"] is True


def test_reporting_guard_marks_mismatched_protocols_non_comparable() -> None:
    common = {
        "dataset_variant": "fi2010_decimal_no_auction",
        "split": "first_7_last_3",
        "label_formula": "fi2010_source",
        "horizon": 100,
        "feature_set": "raw_40",
        "metric": "macro_f1",
    }
    same = comparison_compatibility(common, dict(common))
    different = comparison_compatibility(common, {**common, "split": "random_80_20"})
    assert same["comparable"] is True
    assert different == {
        "comparable": False,
        "differences": {"split": {"left": "first_7_last_3", "right": "random_80_20"}},
        "required_fields": [
            "dataset_variant",
            "split",
            "label_formula",
            "horizon",
            "feature_set",
            "metric",
        ],
    }
