from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_release_readiness import collect_blockers


class ReleaseReadinessTests(unittest.TestCase):
    def _write(self, root: Path, name: str, value: object) -> Path:
        path = root / name
        if isinstance(value, str):
            path.write_text(value, encoding="utf-8")
        else:
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def _paths(self, root: Path, *, ready: bool) -> dict[str, Path]:
        mcq = {
            "id": "MCQ-001",
            "reviewStatus": "published" if ready else "ai_reviewed_pending_expert",
            "needsReview": not ready,
            "reviewer": "reviewer" if ready else None,
            "reviewedAt": "2026-07-19" if ready else None,
            "reviewComment": "確認済み" if ready else None,
            "reviewTargetHash": "a" * 64,
            "reviewedContentHash": "a" * 64 if ready else None,
        }
        written = {
            "id": "SAQ-001",
            "reviewStatus": "published" if ready else "pending_external_review",
            "reviewer": "reviewer" if ready else None,
            "reviewedAt": "2026-07-19" if ready else None,
            "needsReview": not ready,
            "reviewTargetHash": "b" * 64,
            "reviewedContentHash": "b" * 64 if ready else None,
        }
        return {
            "question_pack_path": self._write(
                root,
                "questions.json",
                {
                    "questionCount": 1,
                    "distributionStatus": "release" if ready else "development_only",
                    "questions": [mcq],
                },
            ),
            "written_pack_path": self._write(
                root,
                "written.json",
                {
                    "questionCount": 1,
                    "distributionStatus": "release" if ready else "development_only",
                    "questions": [written],
                },
            ),
            "map_pack_path": self._write(
                root,
                "map.json",
                {
                    "reviewTargetHash": "c" * 64,
                    "review": {
                        "status": "published" if ready else "pending_external_review",
                        "reviewer": "reviewer" if ready else None,
                        "reviewedAt": "2026-07-19" if ready else None,
                        "reviewedContentHash": "c" * 64 if ready else None,
                        "scopes": {
                            "positions": ready,
                            "content": ready,
                        },
                    },
                    "maps": [{"id": "france"}],
                    "sources": [
                        {
                            "id": "source",
                            "name": "自作",
                            "license": "プロジェクト自作",
                            "checkedAt": "2026-07-19",
                        }
                    ],
                },
            ),
            "checklist_path": self._write(
                root,
                "checklist.md",
                "- [x] StoreKit実機確認\n" if ready else "- [ ] StoreKit実機確認\n",
            ),
            "privacy_policy_path": self._write(
                root,
                "privacy.md",
                "# プライバシーポリシー\n運営者: Example\n"
                if ready
                else "# プライバシーポリシー（公開前ドラフト）\n",
            ),
            "xcode_project_path": self._write(root, "project.pbxproj", "// safe\n"),
            "review_issues_path": self._write(
                root,
                "review-issues.json",
                {"schemaVersion": 1, "issues": []},
            ),
        }

    def test_ready_fixture_has_no_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory), ready=True)
            blockers = collect_blockers(
                **paths,
                expected_mcq_count=1,
                minimum_written_count=1,
            )
        self.assertEqual(blockers, [])

    def test_pending_content_and_manual_work_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory), ready=False)
            blockers = collect_blockers(
                **paths,
                expected_mcq_count=1,
                minimum_written_count=1,
            )
        joined = "\n".join(blockers)
        self.assertIn("四択パックがRelease配布状態ではありません", joined)
        self.assertIn("四択1問が公開レビュー未完了", joined)
        self.assertIn("記述式パックがRelease配布状態ではありません", joined)
        self.assertIn("記述式1問に公開状態・担当者・確認日の不足", joined)
        self.assertIn("手動確認未完了", joined)
        self.assertIn("公開前ドラフト", joined)
        self.assertIn("地図の産地名・位置・比較内容", joined)

    def test_map_source_evidence_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._paths(root, ready=True)
            paths["map_pack_path"] = self._write(
                root,
                "invalid-map.json",
                {
                    "reviewTargetHash": "c" * 64,
                    "review": {
                        "status": "published",
                        "reviewer": "reviewer",
                        "reviewedAt": "2026-07-19",
                        "reviewedContentHash": "c" * 64,
                        "scopes": {"positions": True, "content": True},
                    },
                    "maps": [{"id": "france"}],
                    "sources": [],
                },
            )
            blockers = collect_blockers(
                **paths,
                expected_mcq_count=1,
                minimum_written_count=1,
            )
        self.assertEqual(blockers, ["地図出典の名称・利用条件・確認日が不足しています"])

    def test_open_content_review_issue_blocks_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._paths(root, ready=True)
            paths["review_issues_path"] = self._write(
                root,
                "open-issues.json",
                {
                    "schemaVersion": 1,
                    "issues": [
                        {
                            "id": "CR-0001",
                            "targetType": "written",
                            "itemID": "SAQ-001",
                            "severity": "high",
                            "status": "open",
                            "finding": "採点基準の再確認が必要",
                            "reportedBy": "External reviewer",
                            "resolution": None,
                            "updatedAt": "2026-07-19",
                        }
                    ],
                },
            )
            blockers = collect_blockers(
                **paths,
                expected_mcq_count=1,
                minimum_written_count=1,
            )
        self.assertEqual(
            blockers,
            ["未解決のコンテンツレビュー指摘が1件あります (CR-0001)"],
        )

    def test_unreviewed_online_release_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._paths(root, ready=True)
            paths["xcode_project_path"] = self._write(
                root,
                "unsafe-project.pbxproj",
                """
                INFOPLIST_KEY_WSETAIReviewProductionEnabled = YES;
                INFOPLIST_KEY_WSETAIReviewBackendEndpoint = https://example.com/review;
                CODE_SIGN_ENTITLEMENTS = WSET/WSET.entitlements;
                """,
            )
            blockers = collect_blockers(
                **paths,
                expected_mcq_count=1,
                minimum_written_count=1,
            )
        self.assertEqual(
            blockers,
            [
                "R7の本番AI添削フラグがRelease設定で有効です",
                "R7のAI添削送信先がRelease設定に含まれています",
                "R7のiCloud／CloudKit entitlementがRelease設定に含まれています",
            ],
        )


if __name__ == "__main__":
    unittest.main()
