from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.build_question_pack import (
    DEFAULT_INPUT,
    EXPECTED_CORRECT_ANSWER_COUNTS,
    EXPECTED_LO_COUNTS,
    QuestionPackError,
    build_pack,
    check_existing_pack,
    pack_question,
    read_question_rows,
    write_pack,
)


class QuestionPackBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = read_question_rows(DEFAULT_INPUT)
        cls.payload = build_pack(DEFAULT_INPUT, generated_at="2026-07-11T00:00:00Z")

    def test_workbook_contains_the_expected_balanced_1100_questions(self) -> None:
        self.assertEqual(len(self.rows), 1100)
        self.assertEqual(Counter(row["LO"] for row in self.rows), EXPECTED_LO_COUNTS)
        self.assertEqual(
            Counter(row["正答"] for row in self.rows),
            EXPECTED_CORRECT_ANSWER_COUNTS,
        )
        self.assertEqual(len({row["問題ID"] for row in self.rows}), 1100)
        self.assertEqual(
            {row["問題ID"] for row in self.rows},
            {
                f"LO{learning_outcome}-{number:03d}"
                for learning_outcome in range(1, 6)
                for number in range(1, 381 if learning_outcome == 2 else 181)
            },
        )
        self.assertEqual(len({row["問題文"].strip() for row in self.rows}), 1100)

    def test_first_question_is_mapped_to_schema_v4_without_translation_fields(self) -> None:
        question = self.payload["questions"][0]
        self.assertEqual(self.payload["schemaVersion"], 4)
        self.assertEqual(question["id"], "LO1-001")
        self.assertEqual(question["language"], "ja")
        self.assertEqual(question["learningOutcome"], "u1_lo1")
        self.assertEqual(
            question["learningOutcomeName"], "ブドウ畑・ワイナリーの自然要因と人的要因"
        )
        self.assertEqual(question["category"], "自然要因")
        self.assertEqual(question["topic"], "気候と成熟")
        self.assertEqual(question["difficulty"], "D1")
        self.assertEqual(question["geography"], question["countries"] + question["regions"])
        self.assertEqual(len(question["choices"]), 4)
        self.assertEqual(len(question["choiceExplanations"]), 4)
        self.assertEqual(question["answer"], question["choices"][question["correctAnswerIndex"]])
        self.assertNotIn("translations", question)
        self.assertNotIn("translationStatus", question)
        self.assertNotIn("translationModel", question)

    def test_existing_900_questions_are_unchanged(self) -> None:
        previous_input = DEFAULT_INPUT.with_name(
            "wset_level3_original_questions_900_v5.xlsx"
        )
        previous_rows = read_question_rows(previous_input)
        combined_by_id = {row["問題ID"]: row for row in self.rows}

        self.assertEqual(len(previous_rows), 900)
        for previous in previous_rows:
            identifier = previous["問題ID"]
            current = combined_by_id[identifier]
            with self.subTest(question_id=identifier):
                self.assertEqual(
                    {key: value for key, value in current.items() if key != "__excel_row__"},
                    {key: value for key, value in previous.items() if key != "__excel_row__"},
                )

    def test_metadata_and_review_flags_are_preserved(self) -> None:
        questions = self.payload["questions"]
        self.assertEqual(sum(question["needsReview"] for question in questions), 130)
        self.assertTrue(all(question["sourceID"] for question in questions))
        self.assertTrue(all(question["creationType"] == "オリジナル" for question in questions))
        self.assertTrue(all(question["misconceptionTags"] for question in questions))
        self.assertTrue(
            all(
                question["reviewStatus"] == "ai_reviewed_pending_expert"
                for question in questions
            )
        )
        self.assertEqual(
            self.payload["source"]["file"],
            "QuestionSources/wset_level3_original_questions_1100_v6.xlsx",
        )
        self.assertEqual(self.payload["source"]["sheet"], "問題集")
        geographic = next(
            question for question in questions if question["countries"] and question["regions"]
        )
        self.assertEqual(
            geographic["geography"],
            list(dict.fromkeys([*geographic["countries"], *geographic["regions"]])),
        )

    def test_visible_question_text_excludes_retired_english_labels(self) -> None:
        blocked_terms = (
            "private",
            "crossing",
            "hybrid",
            "replacement cane pruning",
            "out of condition",
        )
        for question in self.payload["questions"]:
            visible_values = [
                question["prompt"],
                question["answer"],
                question["explanation"],
                *question["choices"],
                *question["choiceExplanations"],
            ]
            visible_text = "\n".join(value for value in visible_values if value).lower()
            with self.subTest(question_id=question["id"]):
                for term in blocked_terms:
                    self.assertNotIn(term, visible_text)

    def test_source_hash_is_deterministic_for_question_content(self) -> None:
        rebuilt = build_pack(DEFAULT_INPUT, generated_at="different-timestamp")
        self.assertEqual(self.payload["sourceHash"], rebuilt["sourceHash"])
        self.assertEqual(self.payload["questions"], rebuilt["questions"])

    def test_correct_answer_text_mismatch_is_rejected(self) -> None:
        invalid = dict(self.rows[0])
        invalid["正答本文"] = "一致しない回答"
        with self.assertRaisesRegex(QuestionPackError, "正答本文"):
            pack_question(invalid)

    def test_workbook_review_states_are_supported(self) -> None:
        approved = dict(self.rows[0])
        approved["レビュー状態"] = "承認"
        self.assertEqual(pack_question(approved)["reviewStatus"], "approved")

    def test_written_pack_can_be_checked_against_the_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "question_pack.json"
            write_pack(self.payload, output)
            check_existing_pack(DEFAULT_INPUT, output)
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded["questionCount"], 1100)


if __name__ == "__main__":
    unittest.main()
