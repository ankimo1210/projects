#!/usr/bin/env python3
"""Build and validate the offline region-map pack and its asset-catalog entries."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "ReferenceSources" / "wset_region_map_master.json"
DEFAULT_ASSET_SOURCE_DIR = PROJECT_ROOT / "ReferenceSources" / "RegionMaps"
DEFAULT_QUESTION_PACK = PROJECT_ROOT / "WSET" / "QuestionData" / "question_pack.json"
DEFAULT_REFERENCE_PACK = PROJECT_ROOT / "WSET" / "ReferenceData" / "reference_pack.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "WSET" / "MapData" / "region_map_pack.json"
DEFAULT_ASSET_CATALOG_DIR = PROJECT_ROOT / "WSET" / "Assets.xcassets" / "RegionMaps"
SCHEMA_VERSION = 2
SUPPORTED_LEVELS = {"country", "subregion"}
ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
COMPARISON_AXES = (
    "climateInfluence",
    "temperatureRainfallRisks",
    "soils",
    "grapeVarieties",
    "viticulture",
    "winemakingMaturation",
    "wineStyles",
    "qualityPriceFactors",
    "lawLabels",
)
REVIEW_SCOPES = (
    "regionNamesAndPositions",
    "comparisonContent",
    "sourceLicenses",
    "trademarkAndAttribution",
    "svgOriginality",
)
REVIEW_STATUSES = {"pending_external_review", "published"}
_NON_HUMAN_REVIEWER_PLACEHOLDERS = {
    "AI",
    "生成AI",
    "AI誤答レビュー",
    "AI選択肢論理監査",
}

GEOGRAPHY_ALIASES = {
    "サンルーカル": "サンルーカル・デ・バラメダ",
    "サン・テミリオン": "サンテミリオン",
    "ミュスカ・ドゥ・ボーム・ドゥ・ヴニーズ": "ミュスカ・ド・ボーム・ド・ヴニーズ",
    "ヴァレ・ドゥ・ラ・マルヌ": "ヴァレ・ド・ラ・マルヌ",
}


class RegionMapPackError(ValueError):
    """Raised when region-map data violates the app data contract."""


def canonical_geography(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    return GEOGRAPHY_ALIASES.get(normalized, normalized)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegionMapPackError(f"Invalid {label}: {path}") from error
    if not isinstance(value, dict):
        raise RegionMapPackError(f"{label} must be a JSON object")
    return value


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegionMapPackError(f"{label} must be a non-empty string")
    return value.strip()


def _iso_date(value: Any, label: str) -> str:
    raw = _required_string(value, label)
    try:
        parsed = dt.date.fromisoformat(raw)
    except ValueError as error:
        raise RegionMapPackError(f"{label} must be an ISO 8601 calendar date") from error
    if parsed.isoformat() != raw:
        raise RegionMapPackError(f"{label} must use YYYY-MM-DD format")
    return raw


def _unique_identifiers(records: list[dict[str, Any]], label: str) -> set[str]:
    identifiers: list[str] = []
    for record in records:
        identifier = _required_string(record.get("id"), f"{label}.id")
        if ID_PATTERN.fullmatch(identifier) is None:
            raise RegionMapPackError(f"{label}: invalid id {identifier!r}")
        identifiers.append(identifier)
    duplicates = sorted({value for value in identifiers if identifiers.count(value) > 1})
    if duplicates:
        raise RegionMapPackError(f"{label}: duplicate ids {duplicates}")
    return set(identifiers)


def _normalized_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise RegionMapPackError(f"{label} must be {qualifier}")
    result = [_required_string(item, label) for item in value]
    normalized = [canonical_geography(item) for item in result]
    if len(set(normalized)) != len(normalized):
        raise RegionMapPackError(f"{label} contains duplicate normalized values")
    return result


def _validate_point(value: Any, label: str, *, unit_interval: bool) -> None:
    if not isinstance(value, dict) or set(value) != {"x", "y"}:
        raise RegionMapPackError(f"{label} must contain only x and y")
    for axis in ("x", "y"):
        coordinate = value[axis]
        if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
            raise RegionMapPackError(f"{label}.{axis} must be numeric")
        if not math.isfinite(float(coordinate)):
            raise RegionMapPackError(f"{label}.{axis} must be finite")
        if unit_interval and not 0 <= float(coordinate) <= 1:
            raise RegionMapPackError(f"{label}.{axis} must be between 0 and 1")
        if not unit_interval and not -1 <= float(coordinate) <= 1:
            raise RegionMapPackError(f"{label}.{axis} must be between -1 and 1")


def _svg_aspect_ratio(content: bytes, label: str) -> float:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise RegionMapPackError(f"{label} is not valid SVG") from error
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise RegionMapPackError(f"{label} root element is not svg")
    view_box = root.attrib.get("viewBox", "").split()
    if len(view_box) != 4:
        raise RegionMapPackError(f"{label} must define a four-number viewBox")
    try:
        width, height = float(view_box[2]), float(view_box[3])
    except ValueError as error:
        raise RegionMapPackError(f"{label} has an invalid viewBox") from error
    if width <= 0 or height <= 0:
        raise RegionMapPackError(f"{label} viewBox must have positive dimensions")
    return width / height


def _imageset_contents(asset_file: str) -> bytes:
    payload = {
        "images": [
            {"filename": asset_file, "idiom": "universal"},
        ],
        "info": {"author": "xcode", "version": 1},
        "properties": {"preserves-vector-representation": True},
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def review_target_hash(
    master: dict[str, Any], source_hash_assets: dict[str, str]
) -> str:
    """Fingerprint map content and SVGs without mutable review metadata."""

    content_master = {key: value for key, value in master.items() if key != "review"}
    return sha256(
        canonical_json({"master": content_master, "assets": source_hash_assets})
    )


def _validate_review_metadata(review: Any, target_hash: str) -> dict[str, Any]:
    if not isinstance(review, dict):
        raise RegionMapPackError("review must be an object")
    status = _required_string(review.get("status"), "review.status")
    if status not in REVIEW_STATUSES:
        raise RegionMapPackError(f"review.status is unsupported: {status!r}")
    notes = _required_string(review.get("notes"), "review.notes")
    scopes = review.get("scopes")
    if not isinstance(scopes, dict) or set(scopes) != set(REVIEW_SCOPES):
        raise RegionMapPackError(
            f"review.scopes must contain exactly {list(REVIEW_SCOPES)}"
        )
    if not all(isinstance(scopes[scope], bool) for scope in REVIEW_SCOPES):
        raise RegionMapPackError("review.scopes values must be boolean")

    reviewer = review.get("reviewer")
    reviewed_at = review.get("reviewedAt")
    reviewed_hash = review.get("reviewedContentHash")
    if status == "published":
        reviewer = _required_string(reviewer, "review.reviewer")
        if reviewer in _NON_HUMAN_REVIEWER_PLACEHOLDERS:
            raise RegionMapPackError(
                "published map requires an external human reviewer"
            )
        _iso_date(reviewed_at, "review.reviewedAt")
        if reviewed_hash != target_hash:
            raise RegionMapPackError(
                "review.reviewedContentHash is missing or stale"
            )
        incomplete = [scope for scope in REVIEW_SCOPES if scopes[scope] is not True]
        if incomplete:
            raise RegionMapPackError(
                f"published map has incomplete review scopes: {incomplete}"
            )
    else:
        if reviewer is not None and (
            not isinstance(reviewer, str) or not reviewer.strip()
        ):
            raise RegionMapPackError("review.reviewer must be text or null")
        if reviewed_at is not None:
            _iso_date(reviewed_at, "review.reviewedAt")
        if reviewed_hash is not None and (
            not isinstance(reviewed_hash, str) or len(reviewed_hash) != 64
        ):
            raise RegionMapPackError(
                "review.reviewedContentHash must be a SHA-256 hash or null"
            )
    return {
        "status": status,
        "reviewer": reviewer,
        "reviewedAt": reviewed_at,
        "reviewedContentHash": reviewed_hash,
        "scopes": scopes,
        "notes": notes,
    }


def build_pack(
    input_path: Path = DEFAULT_INPUT,
    question_pack_path: Path = DEFAULT_QUESTION_PACK,
    reference_pack_path: Path = DEFAULT_REFERENCE_PACK,
    asset_source_dir: Path = DEFAULT_ASSET_SOURCE_DIR,
) -> tuple[dict[str, Any], dict[str, dict[str, bytes]]]:
    master = _load_object(input_path, "region-map master")
    question_pack = _load_object(question_pack_path, "question pack")
    reference_pack = _load_object(reference_pack_path, "reference pack")

    if master.get("schemaVersion") != SCHEMA_VERSION:
        raise RegionMapPackError(f"Unsupported schemaVersion: {master.get('schemaVersion')!r}")

    maps = master.get("maps")
    sources = master.get("sources")
    if not isinstance(maps, list) or not maps:
        raise RegionMapPackError("maps must be a non-empty list")
    if not isinstance(sources, list) or not sources:
        raise RegionMapPackError("sources must be a non-empty list")
    if not all(isinstance(item, dict) for item in maps + sources):
        raise RegionMapPackError("maps and sources must contain objects")

    map_ids = _unique_identifiers(maps, "maps")
    source_ids = _unique_identifiers(sources, "sources")
    for source in sources:
        source_id = _required_string(source.get("id"), "sources.id")
        _required_string(source.get("name"), f"{source_id}.name")
        _required_string(source.get("license"), f"{source_id}.license")
        _iso_date(source.get("checkedAt"), f"{source_id}.checkedAt")
        _required_string(source.get("note"), f"{source_id}.note")
        source_url = source.get("url")
        if source_url is not None:
            source_url = _required_string(source_url, f"{source_id}.url")
            if not source_url.startswith("https://"):
                raise RegionMapPackError(f"{source_id}.url must use HTTPS")
    question_source_hash = _required_string(
        question_pack.get("sourceHash"), "questionPack.sourceHash"
    )
    reference_source_hash = _required_string(
        reference_pack.get("sourceHash"), "referencePack.sourceHash"
    )
    questions = question_pack.get("questions")
    terms = reference_pack.get("terms")
    if not isinstance(questions, list) or not isinstance(terms, list):
        raise RegionMapPackError("question/reference packs have invalid collections")
    geography_values = {
        canonical_geography(str(value))
        for question in questions
        if isinstance(question, dict)
        for key in ("countries", "regions", "geography")
        for value in (question.get(key) or [])
        if isinstance(value, str) and value.strip()
    }
    term_ids = {
        str(term.get("id")) for term in terms if isinstance(term, dict) and term.get("id")
    }

    output_maps: list[dict[str, Any]] = []
    generated_assets: dict[str, dict[str, bytes]] = {}
    all_region_ids: set[str] = set()
    source_hash_assets: dict[str, str] = {}
    referenced_source_ids: set[str] = set()

    for map_document in maps:
        map_id = _required_string(map_document.get("id"), "map.id")
        level = _required_string(map_document.get("level"), f"{map_id}.level")
        if level not in SUPPORTED_LEVELS:
            raise RegionMapPackError(f"{map_id}: unsupported level {level!r}")
        _required_string(map_document.get("country"), f"{map_id}.country")
        _required_string(map_document.get("nameJapanese"), f"{map_id}.nameJapanese")
        _required_string(map_document.get("nameOriginal"), f"{map_id}.nameOriginal")
        asset_name = _required_string(map_document.get("assetName"), f"{map_id}.assetName")
        if ID_PATTERN.fullmatch(asset_name) is None:
            raise RegionMapPackError(f"{map_id}: invalid assetName {asset_name!r}")
        asset_file = _required_string(map_document.get("assetFile"), f"{map_id}.assetFile")
        if Path(asset_file).name != asset_file or not asset_file.lower().endswith(".svg"):
            raise RegionMapPackError(f"{map_id}: assetFile must be a local SVG filename")
        aspect_ratio = map_document.get("aspectRatio")
        if isinstance(aspect_ratio, bool) or not isinstance(aspect_ratio, (int, float)):
            raise RegionMapPackError(f"{map_id}: aspectRatio must be numeric")
        if not math.isfinite(float(aspect_ratio)) or float(aspect_ratio) <= 0:
            raise RegionMapPackError(f"{map_id}: aspectRatio must be positive")

        source_id_values = _normalized_list(
            map_document.get("sourceIDs"), f"{map_id}.sourceIDs"
        )
        unknown_sources = set(source_id_values) - source_ids
        if unknown_sources:
            raise RegionMapPackError(f"{map_id}: unknown source IDs {sorted(unknown_sources)}")
        referenced_source_ids.update(source_id_values)

        source_asset = asset_source_dir / asset_file
        try:
            svg_content = source_asset.read_bytes()
        except OSError as error:
            raise RegionMapPackError(f"{map_id}: missing SVG {source_asset}") from error
        actual_ratio = _svg_aspect_ratio(svg_content, f"{map_id}/{asset_file}")
        if abs(actual_ratio - float(aspect_ratio)) > 0.002:
            raise RegionMapPackError(
                f"{map_id}: aspectRatio {aspect_ratio} does not match SVG {actual_ratio}"
            )
        source_hash_assets[asset_file] = sha256(svg_content)
        generated_assets[asset_name] = {
            asset_file: svg_content,
            "Contents.json": _imageset_contents(asset_file),
        }

        regions = map_document.get("regions")
        if not isinstance(regions, list) or not regions or not all(
            isinstance(region, dict) for region in regions
        ):
            raise RegionMapPackError(f"{map_id}.regions must be a non-empty object list")
        local_region_ids = _unique_identifiers(regions, f"{map_id}.regions")
        duplicate_global_ids = all_region_ids & local_region_ids
        if duplicate_global_ids:
            raise RegionMapPackError(
                f"region IDs must be globally unique: {sorted(duplicate_global_ids)}"
            )
        all_region_ids.update(local_region_ids)

        output_regions: list[dict[str, Any]] = []
        for region in regions:
            region_id = _required_string(region.get("id"), f"{map_id}.region.id")
            _required_string(region.get("nameJapanese"), f"{region_id}.nameJapanese")
            _required_string(region.get("nameOriginal"), f"{region_id}.nameOriginal")
            focus_values = _normalized_list(region.get("focusValues"), f"{region_id}.focusValues")
            unknown_focus = sorted(
                value
                for value in focus_values
                if canonical_geography(value) not in geography_values
            )
            if unknown_focus:
                raise RegionMapPackError(
                    f"{region_id}: focusValues do not resolve in question pack: {unknown_focus}"
                )
            _validate_point(region.get("position"), f"{region_id}.position", unit_interval=True)
            _validate_point(
                region.get("labelOffset"), f"{region_id}.labelOffset", unit_interval=False
            )
            term_id_values = _normalized_list(
                region.get("termIDs"), f"{region_id}.termIDs", allow_empty=True
            )
            unknown_terms = sorted(set(term_id_values) - term_ids)
            if unknown_terms:
                raise RegionMapPackError(f"{region_id}: unknown term IDs {unknown_terms}")
            comparison = region.get("comparison")
            if not isinstance(comparison, dict) or set(comparison) != set(COMPARISON_AXES):
                raise RegionMapPackError(
                    f"{region_id}.comparison must contain exactly {list(COMPARISON_AXES)}"
                )
            for axis in COMPARISON_AXES:
                fact = comparison[axis]
                label = f"{region_id}.comparison.{axis}"
                if not isinstance(fact, dict) or set(fact) != {
                    "summary",
                    "keywords",
                    "sourceIDs",
                    "checkedAt",
                    "effectiveDate",
                }:
                    raise RegionMapPackError(
                        f"{label} must contain summary, keywords, sourceIDs, checkedAt and effectiveDate"
                    )
                _required_string(fact.get("summary"), f"{label}.summary")
                _normalized_list(fact.get("keywords"), f"{label}.keywords")
                fact_source_ids = _normalized_list(
                    fact.get("sourceIDs"), f"{label}.sourceIDs"
                )
                unknown_fact_sources = set(fact_source_ids) - source_ids
                if unknown_fact_sources:
                    raise RegionMapPackError(
                        f"{label}: unknown source IDs {sorted(unknown_fact_sources)}"
                    )
                referenced_source_ids.update(fact_source_ids)
                _iso_date(fact.get("checkedAt"), f"{label}.checkedAt")
                _iso_date(fact.get("effectiveDate"), f"{label}.effectiveDate")
            child_map_id = region.get("childMapID")
            if child_map_id is not None and child_map_id not in map_ids:
                raise RegionMapPackError(
                    f"{region_id}: unknown childMapID {child_map_id!r}"
                )
            polygons = region.get("polygons")
            if not isinstance(polygons, list):
                raise RegionMapPackError(f"{region_id}.polygons must be a list")
            for polygon_index, polygon in enumerate(polygons):
                if not isinstance(polygon, list) or len(polygon) < 3:
                    raise RegionMapPackError(
                        f"{region_id}.polygons[{polygon_index}] must have at least 3 points"
                    )
                for point_index, point in enumerate(polygon):
                    _validate_point(
                        point,
                        f"{region_id}.polygons[{polygon_index}][{point_index}]",
                        unit_interval=True,
                    )
            output_regions.append(dict(region))

        output_map = dict(map_document)
        output_map.pop("assetFile", None)
        output_map["regions"] = output_regions
        output_maps.append(output_map)

    orphan_source_ids = source_ids - referenced_source_ids
    if orphan_source_ids:
        raise RegionMapPackError(f"sources are not referenced: {sorted(orphan_source_ids)}")

    hash_material = {
        "master": master,
        "assets": source_hash_assets,
    }
    target_hash = review_target_hash(master, source_hash_assets)
    review = _validate_review_metadata(master.get("review"), target_hash)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "sourceHash": sha256(canonical_json(hash_material)),
        "questionPackSourceHash": question_source_hash,
        "referencePackSourceHash": reference_source_hash,
        "mapCount": len(output_maps),
        "reviewTargetHash": target_hash,
        "review": review,
        "maps": output_maps,
        "sources": sources,
    }
    return payload, generated_assets


def write_pack_and_assets(
    payload: dict[str, Any],
    generated_assets: dict[str, dict[str, bytes]],
    output_path: Path = DEFAULT_OUTPUT,
    asset_catalog_dir: Path = DEFAULT_ASSET_CATALOG_DIR,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    asset_catalog_dir.mkdir(parents=True, exist_ok=True)
    root_contents = {
        "info": {"author": "xcode", "version": 1},
        "properties": {"provides-namespace": False},
    }
    (asset_catalog_dir / "Contents.json").write_text(
        json.dumps(root_contents, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for asset_name, files in generated_assets.items():
        imageset = asset_catalog_dir / f"{asset_name}.imageset"
        imageset.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (imageset / filename).write_bytes(content)


def check_existing_pack(
    input_path: Path = DEFAULT_INPUT,
    question_pack_path: Path = DEFAULT_QUESTION_PACK,
    reference_pack_path: Path = DEFAULT_REFERENCE_PACK,
    asset_source_dir: Path = DEFAULT_ASSET_SOURCE_DIR,
    output_path: Path = DEFAULT_OUTPUT,
    asset_catalog_dir: Path = DEFAULT_ASSET_CATALOG_DIR,
) -> None:
    expected, assets = build_pack(
        input_path,
        question_pack_path,
        reference_pack_path,
        asset_source_dir,
    )
    actual = _load_object(output_path, "generated region-map pack")
    if actual != expected:
        raise RegionMapPackError(
            f"Generated region-map pack is stale; run {Path(__file__).name}"
        )
    expected_root = (
        json.dumps(
            {
                "info": {"author": "xcode", "version": 1},
                "properties": {"provides-namespace": False},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    root_path = asset_catalog_dir / "Contents.json"
    if not root_path.is_file() or root_path.read_bytes() != expected_root:
        raise RegionMapPackError("Generated RegionMaps asset catalog is stale")
    for asset_name, files in assets.items():
        imageset = asset_catalog_dir / f"{asset_name}.imageset"
        for filename, expected_content in files.items():
            path = imageset / filename
            if not path.is_file() or path.read_bytes() != expected_content:
                raise RegionMapPackError(f"Generated map asset is stale: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--question-pack", type=Path, default=DEFAULT_QUESTION_PACK)
    parser.add_argument("--reference-pack", type=Path, default=DEFAULT_REFERENCE_PACK)
    parser.add_argument("--asset-source-dir", type=Path, default=DEFAULT_ASSET_SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--asset-catalog-dir", type=Path, default=DEFAULT_ASSET_CATALOG_DIR)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        if arguments.check:
            check_existing_pack(
                arguments.input,
                arguments.question_pack,
                arguments.reference_pack,
                arguments.asset_source_dir,
                arguments.output,
                arguments.asset_catalog_dir,
            )
        else:
            payload, assets = build_pack(
                arguments.input,
                arguments.question_pack,
                arguments.reference_pack,
                arguments.asset_source_dir,
            )
            write_pack_and_assets(
                payload,
                assets,
                arguments.output,
                arguments.asset_catalog_dir,
            )
    except RegionMapPackError as error:
        print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
