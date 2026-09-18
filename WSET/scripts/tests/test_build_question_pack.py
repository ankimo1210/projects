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
    _distribution_status,
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

    def test_v7_is_a_bounded_reaudit_of_v6(self) -> None:
        previous_input = DEFAULT_INPUT.with_name(
            "wset_level3_original_questions_1100_v6.xlsx"
        )
        previous_rows = read_question_rows(previous_input)
        v7_rows = read_question_rows(
            DEFAULT_INPUT.with_name("wset_level3_original_questions_1100_v7.xlsx")
        )
        current_by_id = {row["問題ID"]: row for row in v7_rows}
        previous_by_id = {row["問題ID"]: row for row in previous_rows}
        allowed_changed_fields = {
            "問題文",
            "選択肢A",
            "選択肢B",
            "選択肢C",
            "選択肢D",
            "正答本文",
            "A解説",
            "B解説",
            "C解説",
            "D解説",
            "誤概念タグ",
            "レビュアー",
            "レビュー日",
            "レビューコメント",
        }
        content_fields = allowed_changed_fields - {
            "レビュアー",
            "レビュー日",
            "レビューコメント",
        }
        choice_fields = {"選択肢A", "選択肢B", "選択肢C", "選択肢D"}
        content_changed_questions = 0
        choice_changed_questions = 0
        changed_choice_count = 0

        self.assertEqual(set(current_by_id), set(previous_by_id))
        for identifier, previous in previous_by_id.items():
            identifier = previous["問題ID"]
            current = current_by_id[identifier]
            changed_fields = {
                key
                for key in current
                if key != "__excel_row__" and current[key] != previous[key]
            }
            with self.subTest(question_id=identifier):
                self.assertLessEqual(changed_fields, allowed_changed_fields)
                self.assertEqual(current["正答"], previous["正答"])
            if changed_fields & content_fields:
                content_changed_questions += 1
            changed_choices = changed_fields & choice_fields
            if changed_choices:
                choice_changed_questions += 1
                changed_choice_count += len(changed_choices)

        self.assertEqual(content_changed_questions, 90)
        self.assertEqual(choice_changed_questions, 90)
        self.assertEqual(changed_choice_count, 325)

    def test_curated_answer_regressions_are_scored_as_correct(self) -> None:
        # These facts were previously present as distractors while false answers
        # were marked correct. Structural validation alone cannot detect that.
        # This is a curated regression set, not an automated fact checker.
        facts = {
            "LO1-116": "コルクごとに酸素透過性や密閉性",
            "LO1-127": "低い樹冠が果房へ自然な日陰",
            "LO1-135": "浸食を抑え",
            "LO1-147": "果房と葉の温度を下げ",
            "LO2-023": "北部の花崗岩質丘陵",
            "LO2-030": "南向き斜面が日射を受け",
            "LO2-040": "大西洋の影響",
            "LO2-079": "幅広い品種",
            "LO2-174": "水はけのよい",
            "LO3-042": "ハウス・スタイルを維持",
            "LO3-095": "夜間が冷涼",
            "LO3-150": "水分を保持",
            "LO4-120": "若い型は新鮮なブドウと花",
            "LO4-178": "化学反応と蒸発",
            "LO5-040": "好みや反応が人によって異なる",
            "LO5-163": "色素とタンニンが沈殿",
        }
        by_id = {question["id"]: question for question in self.payload["questions"]}
        for identifier, fact in facts.items():
            question = by_id[identifier]
            with self.subTest(question_id=identifier):
                selected = question["choices"][question["correctAnswerIndex"]]
                self.assertIn(fact, selected)
                self.assertEqual(question["answer"], selected)
                self.assertEqual(
                    question["explanation"],
                    question["choiceExplanations"][question["correctAnswerIndex"]],
                )

    def test_explanations_do_not_use_duplicate_verdicts_or_topic_only_rejections(self) -> None:
        for question in self.payload["questions"]:
            with self.subTest(question_id=question["id"]):
                for explanation in [question["explanation"], *question["choiceExplanations"]]:
                    self.assertNotIn("正しい。正しい。", explanation)
                    self.assertNotIn("誤り。誤り。", explanation)
                    self.assertNotIn("これは同じ知識領域の", explanation)

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
        self.assertEqual(self.payload["distributionStatus"], "release")
        self.assertEqual(
            self.payload["source"]["file"],
            "QuestionSources/wset_level3_original_questions_1100_v8.xlsx",
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

        target_hash = pack_question(self.rows[0])["reviewTargetHash"]
        published = dict(self.rows[0])
        published["レビュー状態"] = "公開"
        published["要レビュー"] = "N"
        published["レビュアー"] = "External reviewer"
        published["レビュー日"] = "2026-07-19"
        published["レビューコメント"] = "内容・正答・解説を確認済み"
        published["レビュー対象ハッシュ"] = target_hash
        packed = pack_question(published)
        self.assertEqual(packed["reviewStatus"], "published")
        self.assertEqual(_distribution_status([packed]), "release")

    def test_published_question_requires_human_evidence_bound_to_content(self) -> None:
        published = dict(self.rows[0])
        published["レビュー状態"] = "公開"
        published["要レビュー"] = "N"

        with self.assertRaisesRegex(QuestionPackError, "external human reviewer"):
            pack_question(published)

        published["レビュアー"] = "External reviewer"
        published["レビュー日"] = "2026-07-19"
        published["レビューコメント"] = "レビュー完了"
        published["レビュー対象ハッシュ"] = "0" * 64
        with self.assertRaisesRegex(QuestionPackError, "missing or stale"):
            pack_question(published)

    def test_release_status_is_independent_of_editorial_review_metadata(self) -> None:
        published = dict(self.payload["questions"][0])
        published["reviewStatus"] = "published"
        published["needsReview"] = False
        published["reviewer"] = "External reviewer"
        published["reviewedAt"] = "2026-07-19"
        published["reviewComment"] = "レビュー完了"
        published["reviewedContentHash"] = published["reviewTargetHash"]
        pending = dict(published)
        pending["reviewStatus"] = "ai_reviewed_pending_expert"

        self.assertEqual(_distribution_status([published]), "release")
        self.assertEqual(
            _distribution_status([published, pending]),
            "release",
        )
        published["needsReview"] = True
        self.assertEqual(_distribution_status([published]), "release")
        self.assertEqual(_distribution_status([]), "development_only")

    def test_written_pack_can_be_checked_against_the_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "question_pack.json"
            write_pack(self.payload, output)
            check_existing_pack(DEFAULT_INPUT, output)
            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded["questionCount"], 1100)


if __name__ == "__main__":
    unittest.main()
