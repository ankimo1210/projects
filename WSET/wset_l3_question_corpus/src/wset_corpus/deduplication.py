from __future__ import annotations

from collections import defaultdict

from rapidfuzz.fuzz import token_set_ratio

from .models import DuplicateCluster, DuplicateMember, QuestionRecord
from .utils import stable_id


def find_duplicates(
    questions: list[QuestionRecord], near_threshold: float = 90.0
) -> list[DuplicateCluster]:
    clusters: list[DuplicateCluster] = []
    exact: dict[str, list[QuestionRecord]] = defaultdict(list)
    for question in questions:
        key = (question.normalized_text or "").casefold()
        if key:
            exact[key].append(question)
    exact_members: set[str] = set()
    for key, matches in exact.items():
        if len(matches) < 2:
            continue
        exact_members.update(item.question_id for item in matches)
        clusters.append(
            DuplicateCluster(
                cluster_id=stable_id("exact", key, prefix="dup_"),
                match_type="exact",
                members=[
                    DuplicateMember(question_id=item.question_id, similarity=100)
                    for item in matches
                ],
                probable_original_source=matches[0].source_id,
            )
        )

    for index, left in enumerate(questions):
        if left.question_id in exact_members or not left.normalized_text:
            continue
        for right in questions[index + 1 :]:
            if right.question_id in exact_members or not right.normalized_text:
                continue
            similarity = float(token_set_ratio(left.normalized_text, right.normalized_text))
            if similarity >= near_threshold:
                clusters.append(
                    DuplicateCluster(
                        cluster_id=stable_id(left.question_id, right.question_id, prefix="dup_"),
                        match_type="near",
                        members=[
                            DuplicateMember(question_id=left.question_id, similarity=100),
                            DuplicateMember(question_id=right.question_id, similarity=similarity),
                        ],
                        probable_original_source=left.source_id,
                        language_relationship=(
                            "same_language" if left.language == right.language else "cross_language"
                        ),
                    )
                )
    return clusters
