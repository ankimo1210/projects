import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_free_content_manifest import (
    DEFAULT_MANIFEST,
    FreeContentManifestError,
    validate_manifest,
)


class FreeContentManifestTests(unittest.TestCase):
    def test_bundled_manifest_is_balanced_and_resolves_all_references(self) -> None:
        summary = validate_manifest()
        self.assertEqual(summary["multipleChoiceCount"], 100)
        self.assertEqual(summary["writtenCount"], 1)
        self.assertEqual(summary["glossaryCount"], 60)
        self.assertEqual(set(summary["learningOutcomeCounts"].values()), {20})
        self.assertGreaterEqual(summary["glossaryCategoryCount"], 8)

    def test_duplicate_or_dangling_ids_are_rejected(self) -> None:
        source = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        source["multipleChoiceQuestionIDs"][-1] = source["multipleChoiceQuestionIDs"][0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(FreeContentManifestError):
                validate_manifest(manifest_path=path)

        source = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        source["glossaryTermIDs"][-1] = "missing-term"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(FreeContentManifestError):
                validate_manifest(manifest_path=path)


if __name__ == "__main__":
    unittest.main()
