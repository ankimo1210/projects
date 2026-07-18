import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ai_review_fixture import (
    DEFAULT_FIXTURE,
    FixtureValidationError,
    load_and_validate,
    validate_fixture,
)


class ValidateAIReviewFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))

    def test_canonical_fixture_is_valid_and_has_bounded_scores(self) -> None:
        validated = load_and_validate()

        self.assertGreaterEqual(len(validated["cases"]), 3)
        for case in validated["cases"]:
            rubric_total = sum(item["maximumMarks"] for item in case["rubric"])
            self.assertLessEqual(case["expectedScoreRange"]["maximum"], rubric_total)

    def test_duplicate_rubric_ids_are_rejected(self) -> None:
        broken = copy.deepcopy(self.payload)
        broken["cases"][0]["rubric"][1]["id"] = broken["cases"][0]["rubric"][0]["id"]

        with self.assertRaisesRegex(FixtureValidationError, "duplicate rubric id"):
            validate_fixture(broken)

    def test_score_above_rubric_total_is_rejected(self) -> None:
        broken = copy.deepcopy(self.payload)
        broken["cases"][0]["expectedScoreRange"]["maximum"] = 99

        with self.assertRaisesRegex(FixtureValidationError, "exceeds rubric bounds"):
            validate_fixture(broken)

    def test_malformed_json_is_wrapped_as_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(FixtureValidationError, "cannot read fixture"):
                load_and_validate(path)


if __name__ == "__main__":
    unittest.main()
