from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_content_review_packet import (
    ContentReviewError,
    build_packet,
    check_packet,
    validate_issue_log,
    write_packet,
)


class ContentReviewPacketTests(unittest.TestCase):
    def _issue_log(self, root: Path, issues: list[dict[str, object]]) -> Path:
        path = root / "review_issues.json"
        path.write_text(
            json.dumps({"schemaVersion": 1, "issues": issues}, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def test_current_sources_produce_bound_review_targets(self) -> None:
        packet = build_packet()
        self.assertEqual(packet["schemaVersion"], 1)
        self.assertEqual(packet["sources"]["mcq"]["itemCount"], 1100)
        self.assertGreaterEqual(packet["sources"]["written"]["itemCount"], 10)
        self.assertEqual(packet["sources"]["regionMap"]["itemCount"], 1)
        self.assertEqual(len(packet["sources"]["mcq"]["requestHash"]), 64)
        self.assertEqual(len(packet["sources"]["regionMap"]["requestHash"]), 64)
        self.assertEqual(packet["unresolvedIssueCount"], 0)

    def test_packet_is_deterministic_and_checkable(self) -> None:
        first = build_packet()
        second = build_packet()
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "request.json"
            write_packet(first, output)
            check_packet(output)

    def test_open_and_resolved_issues_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            open_issue = {
                "id": "CR-0001",
                "targetType": "mcq",
                "itemID": "LO1-001",
                "severity": "high",
                "status": "open",
                "finding": "正答根拠を確認する",
                "reportedBy": "External reviewer",
                "resolution": None,
                "updatedAt": "2026-07-19",
            }
            path = self._issue_log(root, [open_issue])
            self.assertEqual(validate_issue_log(path), [open_issue])

            open_issue["status"] = "resolved"
            with self.assertRaisesRegex(ContentReviewError, "requires a resolution"):
                validate_issue_log(self._issue_log(root, [open_issue]))

            open_issue["resolution"] = "正本の解説を修正し再確認した"
            self.assertEqual(validate_issue_log(self._issue_log(root, [open_issue])), [])

    def test_invalid_target_and_duplicate_issue_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            issue = {
                "id": "CR-0001",
                "targetType": "unknown",
                "itemID": "item",
                "severity": "low",
                "status": "open",
                "finding": "finding",
                "reportedBy": "External reviewer",
                "resolution": None,
                "updatedAt": "2026-07-19",
            }
            with self.assertRaisesRegex(ContentReviewError, "targetType"):
                validate_issue_log(self._issue_log(root, [issue]))

            issue["targetType"] = "region_map"
            with self.assertRaisesRegex(ContentReviewError, "Duplicate"):
                validate_issue_log(self._issue_log(root, [issue, dict(issue)]))


if __name__ == "__main__":
    unittest.main()
