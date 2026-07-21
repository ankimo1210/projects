from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_written_question_pack import (
    DEFAULT_INPUT,
    DEFAULT_REFERENCE_PACK,
    WrittenQuestionPackError,
    build_pack,
    check_existing_pack,
    review_target_hash,
    validate_source,
    write_pack,
)


class WrittenQuestionPackBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))

    def test_release_pack_includes_all_non_rejected_questions(self) -> None:
        pack = build_pack(generated_at="2026-07-19T00:00:00Z")
        self.assertEqual(pack["schemaVersion"], 1)
        self.assertEqual(pack["distributionStatus"], "release")
        reference_pack = json.loads(DEFAULT_REFERENCE_PACK.read_text(encoding="utf-8"))
        self.assertEqual(
            pack["referencePackSourceHash"],
            reference_pack["sourceHash"],
        )
        self.assertEqual(pack["questionCount"], len(self.source["questions"]))
        self.assertGreaterEqual(pack["questionCount"], 10)
        self.assertEqual(
            pack["reviewSummary"]["pending_external_review"],
            len(self.source["questions"]),
        )

        self.assertEqual(len(pack["referencePackSourceHash"]), 64)
        for question in pack["questions"]:
            self.assertEqual(question["studyMode"], "written_answer")
            self.assertEqual(question["reviewStatus"], "pending_external_review")
            self.assertIsNone(question["reviewer"])
            self.assertIsNone(question["reviewedAt"])
            self.assertTrue(question["needsReview"])
            self.assertIsNone(question["qualityScore"])
            self.assertIn("レビュー待ち", question["reviewReason"])
            self.assertTrue(question["contentMetadata"]["externalReviewRequired"])
            self.assertEqual(question["choices"], [])
            self.assertIsNone(question["correctAnswerIndex"])
            self.assertEqual(
                sum(item["marks"] for item in question["rubricItems"]),
                question["markAllocation"],
            )
            for item in question["rubricItems"]:
                self.assertTrue(item["knowledgeTags"])
                self.assertTrue(item["relatedTermIDs"])

    def test_release_pack_excludes_rejected_questions(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"][0]["reviewStatus"] = "rejected"
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "source.json"
            input_path.write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )
            pack = build_pack(input_path, generated_at="fixed")

        self.assertEqual(pack["questionCount"], len(source["questions"]) - 1)
        self.assertNotIn(
            source["questions"][0]["id"],
            {question["id"] for question in pack["questions"]},
        )

    def test_pack_is_deterministic_and_checkable(self) -> None:
        first = build_pack(generated_at="first")
        second = build_pack(generated_at="second")
        self.assertEqual(first["sourceHash"], second["sourceHash"])
        self.assertEqual(first["questions"], second["questions"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "written_question_pack.json"
            write_pack(first, output)
            check_existing_pack(DEFAULT_INPUT, output)

    def test_rejects_duplicate_question_ids(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"].append(copy.deepcopy(source["questions"][0]))
        with self.assertRaisesRegex(WrittenQuestionPackError, "Duplicate"):
            validate_source(source)

    def test_rejects_rubric_mark_mismatch(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"][0]["rubricItems"][0]["marks"] += 1
        with self.assertRaisesRegex(WrittenQuestionPackError, "rubric marks"):
            validate_source(source)

    def test_rejects_invalid_coordinates_or_empty_text_indirectly(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"][0]["prompt"] = "  "
        with self.assertRaisesRegex(WrittenQuestionPackError, "prompt"):
            validate_source(source)

    def test_rejects_published_question_without_human_review_fields(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"][0]["reviewStatus"] = "published"
        with self.assertRaisesRegex(WrittenQuestionPackError, "require reviewer"):
            validate_source(source)

    def test_rejects_published_question_with_stale_content_hash(self) -> None:
        source = copy.deepcopy(self.source)
        question = source["questions"][0]
        question["reviewStatus"] = "published"
        question["reviewer"] = "External reviewer"
        question["reviewedAt"] = "2026-07-19T09:00:00+09:00"
        question["metadata"]["externalReviewRequired"] = False
        question["reviewedContentHash"] = "0" * 64
        with self.assertRaisesRegex(WrittenQuestionPackError, "missing or stale"):
            validate_source(source)

    def test_rejects_unknown_related_term_id(self) -> None:
        source = copy.deepcopy(self.source)
        source["questions"][0]["rubricItems"][0]["relatedTermIDs"] = [
            "term-does-not-exist"
        ]
        with self.assertRaisesRegex(WrittenQuestionPackError, "unknown relatedTermIDs"):
            validate_source(source)

    def test_rejects_missing_content_metadata(self) -> None:
        source = copy.deepcopy(self.source)
        del source["questions"][0]["metadata"]
        with self.assertRaisesRegex(WrittenQuestionPackError, "metadata"):
            validate_source(source)


if __name__ == "__main__":
    unittest.main()
