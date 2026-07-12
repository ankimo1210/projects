from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.build_reference_pack import (
    DEFAULT_INPUT,
    DEFAULT_QUESTION_PACK,
    EXPECTED_CLASSIFICATION_COUNT,
    EXPECTED_TERM_COUNT,
    build_pack,
    check_existing_pack,
    write_pack,
)


class ReferencePackBuilderTests(unittest.TestCase):
    payload: dict[str, Any]
    terms: dict[str, dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_pack(
            DEFAULT_INPUT,
            DEFAULT_QUESTION_PACK,
            generated_at="2026-07-12T00:00:00Z",
        )
        cls.terms = {term["nameJapanese"]: term for term in cls.payload["terms"]}

    def test_pack_has_expected_counts_and_unique_ids(self) -> None:
        self.assertEqual(self.payload["schemaVersion"], 1)
        self.assertEqual(self.payload["termCount"], EXPECTED_TERM_COUNT)
        self.assertEqual(
            self.payload["classificationEntryCount"], EXPECTED_CLASSIFICATION_COUNT
        )
        self.assertEqual(
            len({term["id"] for term in self.payload["terms"]}), EXPECTED_TERM_COUNT
        )

    def test_original_language_annotations_are_preserved(self) -> None:
        term = self.terms["マロラクティック発酵"]
        self.assertEqual(term["nameEnglish"], "malolactic fermentation")
        self.assertEqual(term["nameFrench"], "fermentation malolactique")
        self.assertIn("MLF", term["aliases"])
        self.assertTrue(term["questionIDs"])

    def test_structured_question_tags_create_reverse_links(self) -> None:
        self.assertGreater(len(self.terms["ボルドー"]["questionIDs"]), 0)
        self.assertGreater(len(self.terms["カベルネ・ソーヴィニヨン"]["questionIDs"]), 0)
        valid_question_ids = {
            question["id"]
            for question in json.loads(DEFAULT_QUESTION_PACK.read_text(encoding="utf-8"))[
                "questions"
            ]
        }
        for term in self.payload["terms"]:
            self.assertLessEqual(set(term["questionIDs"]), valid_question_ids)

    def test_classification_systems_are_kept_separate(self) -> None:
        counts = Counter(
            entry["systemID"] for entry in self.payload["classificationEntries"]
        )
        self.assertEqual(counts["bordeaux_1855_medoc"], 61)
        self.assertEqual(counts["bordeaux_1855_sauternes"], 27)
        self.assertEqual(counts["bordeaux_graves"], 14)
        self.assertEqual(counts["bordeaux_saint_emilion_2022"], 85)
        self.assertEqual(counts["burgundy_grand_cru"], 33)
        self.assertEqual(counts["champagne_cru_2025"], 59)

    def test_region_specific_classification_semantics_are_preserved(self) -> None:
        entries = self.payload["classificationEntries"]
        mouton = next(entry for entry in entries if entry["nameOriginal"] == "Château Mouton Rothschild")
        self.assertEqual(mouton["tier"], "第1級")
        montrachet = next(entry for entry in entries if entry["nameOriginal"] == "Montrachet")
        self.assertEqual(montrachet["entryType"], "畑・AOC")
        self.assertIn("Puligny-Montrachet", montrachet["village"])
        champagne_counts = Counter(
            entry["tier"]
            for entry in entries
            if entry["systemID"] == "champagne_cru_2025"
        )
        self.assertEqual(champagne_counts, {"Grand Cru": 17, "Premier Cru": 42})

    def test_pack_is_deterministic_and_checkable(self) -> None:
        rebuilt = build_pack(
            DEFAULT_INPUT,
            DEFAULT_QUESTION_PACK,
            generated_at="different-time",
        )
        self.assertEqual(self.payload["sourceHash"], rebuilt["sourceHash"])
        self.assertEqual(self.payload["terms"], rebuilt["terms"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reference_pack.json"
            write_pack(self.payload, output)
            check_existing_pack(DEFAULT_INPUT, DEFAULT_QUESTION_PACK, output)


if __name__ == "__main__":
    unittest.main()
