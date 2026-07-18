from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.build_region_map_pack import (
    COMPARISON_AXES,
    DEFAULT_ASSET_SOURCE_DIR,
    DEFAULT_INPUT,
    DEFAULT_QUESTION_PACK,
    DEFAULT_REFERENCE_PACK,
    REVIEW_SCOPES,
    RegionMapPackError,
    build_pack,
    canonical_geography,
    check_existing_pack,
    write_pack_and_assets,
)


class RegionMapPackBuilderTests(unittest.TestCase):
    payload: dict[str, Any]
    assets: dict[str, dict[str, bytes]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload, cls.assets = build_pack()

    def test_france_pack_has_expected_regions_and_references(self) -> None:
        self.assertEqual(self.payload["schemaVersion"], 2)
        self.assertEqual(self.payload["mapCount"], 1)
        self.assertEqual(self.payload["review"]["status"], "pending_external_review")
        self.assertEqual(len(self.payload["reviewTargetHash"]), 64)
        france = self.payload["maps"][0]
        self.assertEqual(france["id"], "france")
        self.assertEqual(len(france["regions"]), 10)
        self.assertNotIn("assetFile", france)
        self.assertEqual(
            {region["id"] for region in france["regions"]},
            {
                "france_bordeaux",
                "france_burgundy",
                "france_champagne",
                "france_loire",
                "france_alsace",
                "france_northern_rhone",
                "france_southern_rhone",
                "france_provence",
                "france_beaujolais",
                "france_languedoc_roussillon",
            },
        )
        source_ids = {source["id"] for source in self.payload["sources"]}
        for region in france["regions"]:
            with self.subTest(region=region["id"]):
                self.assertEqual(set(region["comparison"]), set(COMPARISON_AXES))
                for axis in COMPARISON_AXES:
                    fact = region["comparison"][axis]
                    self.assertTrue(fact["summary"])
                    self.assertTrue(fact["keywords"])
                    self.assertTrue(set(fact["sourceIDs"]).issubset(source_ids))
                    self.assertRegex(fact["checkedAt"], r"^\d{4}-\d{2}-\d{2}$")
                    self.assertRegex(fact["effectiveDate"], r"^\d{4}-\d{2}-\d{2}$")

    def test_comparison_contract_requires_all_axes_and_valid_sources_and_dates(self) -> None:
        mutations = (
            (
                lambda master: master["maps"][0]["regions"][0]["comparison"].pop(
                    "lawLabels"
                ),
                "must contain exactly",
            ),
            (
                lambda master: master["maps"][0]["regions"][0]["comparison"][
                    "climateInfluence"
                ].update(sourceIDs=["missing_source"]),
                "unknown source IDs",
            ),
            (
                lambda master: master["maps"][0]["regions"][0]["comparison"][
                    "climateInfluence"
                ].update(checkedAt="2026/07/19"),
                "ISO 8601 calendar date",
            ),
            (
                lambda master: master["maps"][0]["regions"][0]["comparison"][
                    "climateInfluence"
                ].update(effectiveDate="2026-7-19"),
                "ISO 8601 calendar date",
            ),
        )
        for mutate, message in mutations:
            master = self._master()
            mutate(master)
            with self.subTest(message=message), self.assertRaisesRegex(
                RegionMapPackError, message
            ):
                self._build_mutated(master)

    def test_sources_must_be_https_and_referenced(self) -> None:
        master = self._master()
        master["sources"][1]["url"] = "http://example.com"
        with self.assertRaisesRegex(RegionMapPackError, "must use HTTPS"):
            self._build_mutated(master)

    def test_published_map_requires_human_review_bound_to_current_content(self) -> None:
        master = self._master()
        master["review"].update(
            status="published",
            reviewer="External reviewer",
            reviewedAt="2026-07-19",
            reviewedContentHash="0" * 64,
            scopes={scope: True for scope in REVIEW_SCOPES},
        )
        with self.assertRaisesRegex(RegionMapPackError, "missing or stale"):
            self._build_mutated(master)

        master["review"]["reviewedContentHash"] = self.payload["reviewTargetHash"]
        self._build_mutated(master)

        master["review"]["scopes"][REVIEW_SCOPES[0]] = False
        with self.assertRaisesRegex(RegionMapPackError, "incomplete review scopes"):
            self._build_mutated(master)

        master = self._master()
        master["sources"].append(
            {
                "id": "unused_source",
                "name": "未使用",
                "url": None,
                "license": "参照のみ",
                "checkedAt": "2026-07-19",
                "note": "テスト",
            }
        )
        with self.assertRaisesRegex(RegionMapPackError, "not referenced"):
            self._build_mutated(master)

    def test_vector_asset_is_generated_with_preservation_metadata(self) -> None:
        self.assertIn("map_france", self.assets)
        files = self.assets["map_france"]
        self.assertIn(b"<svg", files["france.svg"])
        contents = json.loads(files["Contents.json"])
        self.assertTrue(contents["properties"]["preserves-vector-representation"])

    def test_normalizer_aliases_match_runtime_contract(self) -> None:
        self.assertEqual(
            canonical_geography("ヴァレ・ドゥ・ラ・マルヌ"),
            "ヴァレ・ド・ラ・マルヌ",
        )
        self.assertEqual(
            canonical_geography("ミュスカ・ドゥ・ボーム・ドゥ・ヴニーズ"),
            "ミュスカ・ド・ボーム・ド・ヴニーズ",
        )
        self.assertEqual(canonical_geography(" サン・テミリオン "), "サンテミリオン")

    def test_pack_and_source_hash_are_deterministic_and_checkable(self) -> None:
        rebuilt, rebuilt_assets = build_pack()
        self.assertEqual(self.payload, rebuilt)
        self.assertEqual(self.assets, rebuilt_assets)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "region_map_pack.json"
            catalog = root / "RegionMaps"
            write_pack_and_assets(self.payload, self.assets, output, catalog)
            check_existing_pack(
                DEFAULT_INPUT,
                DEFAULT_QUESTION_PACK,
                DEFAULT_REFERENCE_PACK,
                DEFAULT_ASSET_SOURCE_DIR,
                output,
                catalog,
            )

    def test_source_hash_changes_when_svg_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset_dir = Path(directory)
            source = (DEFAULT_ASSET_SOURCE_DIR / "france.svg").read_bytes()
            (asset_dir / "france.svg").write_bytes(
                source.replace(b"</svg>", b"<!-- hash test -->\n</svg>")
            )

            changed, _ = build_pack(asset_source_dir=asset_dir)

        self.assertNotEqual(self.payload["sourceHash"], changed["sourceHash"])

    def test_aspect_ratio_must_match_svg_view_box(self) -> None:
        master = self._master()
        master["maps"][0]["aspectRatio"] += 0.01
        with self.assertRaisesRegex(RegionMapPackError, "does not match SVG"):
            self._build_mutated(master)

    def test_invalid_coordinates_are_rejected(self) -> None:
        master = self._master()
        master["maps"][0]["regions"][0]["position"]["x"] = 1.01
        with self.assertRaisesRegex(RegionMapPackError, "between 0 and 1"):
            self._build_mutated(master)

    def test_unknown_focus_term_and_child_map_references_are_rejected(self) -> None:
        for key, value, message in (
            ("focusValues", ["存在しない産地"], "do not resolve"),
            ("termIDs", ["term-does-not-exist"], "unknown term IDs"),
            ("childMapID", "missing_map", "unknown childMapID"),
        ):
            master = self._master()
            master["maps"][0]["regions"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                RegionMapPackError, message
            ):
                self._build_mutated(master)

    def test_duplicate_ids_and_normalized_focus_values_are_rejected(self) -> None:
        master = self._master()
        master["maps"][0]["regions"][1]["id"] = master["maps"][0]["regions"][0]["id"]
        with self.assertRaisesRegex(RegionMapPackError, "duplicate ids"):
            self._build_mutated(master)

        master = self._master()
        values = master["maps"][0]["regions"][0]["focusValues"]
        values.append(values[0])
        with self.assertRaisesRegex(RegionMapPackError, "duplicate normalized"):
            self._build_mutated(master)

    @staticmethod
    def _master() -> dict[str, Any]:
        return json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))

    @staticmethod
    def _build_mutated(master: dict[str, Any]) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "master.json"
            path.write_text(json.dumps(master, ensure_ascii=False), encoding="utf-8")
            build_pack(path)


if __name__ == "__main__":
    unittest.main()
