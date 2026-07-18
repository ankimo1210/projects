#!/usr/bin/env python3
"""Fail closed when a commercial Release still contains unresolved gates.

Daily development checks intentionally stay green while authoring content is under
review. This command is the separate, stricter gate that must pass before an App
Store archive is created.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.build_content_review_packet import ContentReviewError, validate_issue_log
except ModuleNotFoundError:  # Direct execution: python3 scripts/this_file.py
    from build_content_review_packet import (  # type: ignore[no-redef]
        ContentReviewError,
        validate_issue_log,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTION_PACK = ROOT / "WSET" / "QuestionData" / "question_pack.json"
DEFAULT_WRITTEN_PACK = ROOT / "WSET" / "QuestionData" / "written_question_pack.json"
DEFAULT_MAP_PACK = ROOT / "WSET" / "MapData" / "region_map_pack.json"
DEFAULT_CHECKLIST = ROOT / "docs" / "app-store-release-checklist.md"
DEFAULT_PRIVACY_POLICY = ROOT / "docs" / "privacy-policy-ja.md"
DEFAULT_XCODE_PROJECT = ROOT / "WSET.xcodeproj" / "project.pbxproj"
DEFAULT_REVIEW_ISSUES = ROOT / "ContentReviews" / "review_issues.json"

EXPECTED_MCQ_COUNT = 1100
MINIMUM_WRITTEN_COUNT = 4
_CHECKBOX = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.+?)\s*$")


class ReleaseReadinessError(ValueError):
    """Raised when readiness inputs cannot be read or have an invalid shape."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseReadinessError(f"{path}: 読み込めません: {error}") from error
    if not isinstance(payload, dict):
        raise ReleaseReadinessError(f"{path}: JSONルートはobjectである必要があります")
    return payload


def _items(payload: dict[str, Any], key: str, path: Path) -> list[dict[str, Any]]:
    values = payload.get(key)
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise ReleaseReadinessError(f"{path}: {key}はobject配列である必要があります")
    return values


def _review_summary(questions: list[dict[str, Any]]) -> str:
    counts = Counter(str(question.get("reviewStatus") or "missing") for question in questions)
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _content_blockers(
    question_pack_path: Path,
    written_pack_path: Path,
    *,
    expected_mcq_count: int,
    minimum_written_count: int,
) -> list[str]:
    blockers: list[str] = []
    question_pack = _load_object(question_pack_path)
    questions = _items(question_pack, "questions", question_pack_path)
    if question_pack.get("questionCount") != len(questions):
        blockers.append("四択パックのquestionCountが実データ件数と一致していません")
    if len(questions) != expected_mcq_count:
        blockers.append(
            f"四択の公開候補が{len(questions)}問です（必要件数: {expected_mcq_count}問）"
        )
    if question_pack.get("distributionStatus") != "release":
        blockers.append(
            "四択パックがRelease配布状態ではありません "
            f"(distributionStatus={question_pack.get('distributionStatus')!r})"
        )
    unpublished_mcq = [
        question
        for question in questions
        if question.get("reviewStatus") != "published"
        or question.get("needsReview") is not False
        or not str(question.get("reviewer") or "").strip()
        or not str(question.get("reviewedAt") or "").strip()
        or not str(question.get("reviewComment") or "").strip()
        or question.get("reviewTargetHash") != question.get("reviewedContentHash")
    ]
    if unpublished_mcq:
        blockers.append(
            f"四択{len(unpublished_mcq)}問が公開レビュー未完了です "
            f"({_review_summary(questions)})"
        )

    written_pack = _load_object(written_pack_path)
    written_questions = _items(written_pack, "questions", written_pack_path)
    if written_pack.get("questionCount") != len(written_questions):
        blockers.append("記述式パックのquestionCountが実データ件数と一致していません")
    if len(written_questions) < minimum_written_count:
        blockers.append(
            f"公開済み記述式が{len(written_questions)}問です"
            f"（理論模試に最低{minimum_written_count}問必要）"
        )
    if written_pack.get("distributionStatus") != "release":
        blockers.append(
            "記述式パックがRelease配布状態ではありません "
            f"(distributionStatus={written_pack.get('distributionStatus')!r})"
        )
    unpublished_written = [
        question
        for question in written_questions
        if question.get("reviewStatus") != "published"
        or not str(question.get("reviewer") or "").strip()
        or not str(question.get("reviewedAt") or "").strip()
        or question.get("needsReview") is not False
        or question.get("reviewTargetHash") != question.get("reviewedContentHash")
    ]
    if unpublished_written:
        blockers.append(
            f"記述式{len(unpublished_written)}問に公開状態・担当者・確認日の不足があります "
            f"({_review_summary(written_questions)})"
        )
    return blockers


def _map_blockers(map_pack_path: Path) -> list[str]:
    payload = _load_object(map_pack_path)
    maps = _items(payload, "maps", map_pack_path)
    sources = _items(payload, "sources", map_pack_path)
    blockers: list[str] = []
    if not maps:
        blockers.append("Release用の産地マップがありません")
    invalid_sources = [
        source.get("id", "unknown")
        for source in sources
        if not str(source.get("name") or "").strip()
        or not str(source.get("license") or "").strip()
        or not str(source.get("checkedAt") or "").strip()
    ]
    if not sources or invalid_sources:
        blockers.append(
            "地図出典の名称・利用条件・確認日が不足しています"
            + (f" ({', '.join(map(str, invalid_sources))})" if invalid_sources else "")
        )
    review = payload.get("review")
    valid_review = (
        isinstance(review, dict)
        and review.get("status") == "published"
        and bool(str(review.get("reviewer") or "").strip())
        and bool(str(review.get("reviewedAt") or "").strip())
        and review.get("reviewedContentHash") == payload.get("reviewTargetHash")
        and isinstance(review.get("scopes"), dict)
        and bool(review["scopes"])
        and all(value is True for value in review["scopes"].values())
    )
    if not valid_review:
        blockers.append(
            "地図の産地名・位置・比較内容・利用条件・商標・SVGの人手レビュー証跡が未完了です"
        )
    return blockers


def _review_issue_blockers(issue_log_path: Path) -> list[str]:
    try:
        unresolved = validate_issue_log(issue_log_path)
    except ContentReviewError as error:
        raise ReleaseReadinessError(
            f"{issue_log_path}: レビュー指摘ログが不正です: {error}"
        ) from error
    if not unresolved:
        return []
    identifiers = ", ".join(str(issue["id"]) for issue in unresolved[:10])
    suffix = "…" if len(unresolved) > 10 else ""
    return [
        f"未解決のコンテンツレビュー指摘が{len(unresolved)}件あります "
        f"({identifiers}{suffix})"
    ]


def _checklist_blockers(checklist_path: Path) -> list[str]:
    try:
        lines = checklist_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ReleaseReadinessError(f"{checklist_path}: 読み込めません: {error}") from error
    items = [match.groups() for line in lines if (match := _CHECKBOX.match(line))]
    if not items:
        raise ReleaseReadinessError(f"{checklist_path}: チェック項目がありません")
    return [f"手動確認未完了: {label}" for mark, label in items if mark == " "]


def _privacy_blockers(privacy_policy_path: Path) -> list[str]:
    try:
        policy = privacy_policy_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseReadinessError(
            f"{privacy_policy_path}: 読み込めません: {error}"
        ) from error
    placeholders = ("公開前ドラフト", "公開前に、運営者名")
    if any(placeholder in policy for placeholder in placeholders):
        return ["プライバシーポリシーが公開前ドラフトのままです"]
    return []


def _online_feature_blockers(xcode_project_path: Path) -> list[str]:
    """Keep optional R7 integrations non-live until their separate review is complete."""

    try:
        project = xcode_project_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseReadinessError(
            f"{xcode_project_path}: 読み込めません: {error}"
        ) from error

    blockers: list[str] = []
    if re.search(
        r"(?:INFOPLIST_KEY_)?WSETAIReviewProductionEnabled\s*=\s*YES\s*;",
        project,
        re.IGNORECASE,
    ):
        blockers.append("R7の本番AI添削フラグがRelease設定で有効です")
    if re.search(
        r"(?:INFOPLIST_KEY_)?WSETAIReviewBackendEndpoint\s*=\s*[^;\s]+\s*;",
        project,
        re.IGNORECASE,
    ):
        blockers.append("R7のAI添削送信先がRelease設定に含まれています")
    if (
        re.search(r"CODE_SIGN_ENTITLEMENTS\s*=\s*[^;\s]+\s*;", project)
        or "com.apple.developer.icloud" in project
        or "com.apple.developer.ubiquity" in project
        or "com.apple.iCloud" in project
    ):
        blockers.append("R7のiCloud／CloudKit entitlementがRelease設定に含まれています")
    return blockers


def collect_blockers(
    *,
    question_pack_path: Path = DEFAULT_QUESTION_PACK,
    written_pack_path: Path = DEFAULT_WRITTEN_PACK,
    map_pack_path: Path = DEFAULT_MAP_PACK,
    checklist_path: Path = DEFAULT_CHECKLIST,
    privacy_policy_path: Path = DEFAULT_PRIVACY_POLICY,
    xcode_project_path: Path = DEFAULT_XCODE_PROJECT,
    review_issues_path: Path = DEFAULT_REVIEW_ISSUES,
    expected_mcq_count: int = EXPECTED_MCQ_COUNT,
    minimum_written_count: int = MINIMUM_WRITTEN_COUNT,
) -> list[str]:
    """Return deterministic No-Go reasons. An empty result means the gate passes."""

    return [
        *_content_blockers(
            question_pack_path,
            written_pack_path,
            expected_mcq_count=expected_mcq_count,
            minimum_written_count=minimum_written_count,
        ),
        *_map_blockers(map_pack_path),
        *_review_issue_blockers(review_issues_path),
        *_checklist_blockers(checklist_path),
        *_privacy_blockers(privacy_policy_path),
        *_online_feature_blockers(xcode_project_path),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="App Store archive前のコンテンツ・手動確認ゲート"
    )
    parser.add_argument("--question-pack", type=Path, default=DEFAULT_QUESTION_PACK)
    parser.add_argument("--written-pack", type=Path, default=DEFAULT_WRITTEN_PACK)
    parser.add_argument("--map-pack", type=Path, default=DEFAULT_MAP_PACK)
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--privacy-policy", type=Path, default=DEFAULT_PRIVACY_POLICY)
    parser.add_argument("--xcode-project", type=Path, default=DEFAULT_XCODE_PROJECT)
    parser.add_argument("--review-issues", type=Path, default=DEFAULT_REVIEW_ISSUES)
    arguments = parser.parse_args()
    blockers = collect_blockers(
        question_pack_path=arguments.question_pack,
        written_pack_path=arguments.written_pack,
        map_pack_path=arguments.map_pack,
        checklist_path=arguments.checklist,
        privacy_policy_path=arguments.privacy_policy,
        xcode_project_path=arguments.xcode_project,
        review_issues_path=arguments.review_issues,
    )
    if blockers:
        print(f"Release判定: NO-GO（{len(blockers)}件）")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("Release判定: GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
