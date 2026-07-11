from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wset_corpus.utils import ROOT, read_jsonl, sha256_bytes

DEFAULT_OUTPUT = ROOT / "data" / "exports" / "legacy_question_pack.json"
CURATED_PATH = ROOT / "data" / "curated" / "service_pairing_questions.json"
TRANSLATION_CACHE = (
    ROOT / "data" / "translations_private" / "question_translations.jsonl"
)
ALLOWED_STATUSES = {"machine_screened", "human_reviewed"}

TOPIC_TO_OUTCOME = {
    "grape_growing": ("unit_1", "u1_lo1", "Production factors"),
    "winemaking": ("unit_1", "u1_lo1", "Production factors"),
    "maturation": ("unit_1", "u1_lo1", "Production factors"),
    "still_wines": ("unit_1", "u1_lo2", "Still wines"),
    "laws_and_regulations": ("unit_1", "u1_lo2", "Still wines"),
    "business_and_price": ("unit_1", "u1_lo2", "Still wines"),
    "sparkling_wines": ("unit_1", "u1_lo3", "Sparkling wines"),
    "fortified_wines": ("unit_1", "u1_lo4", "Fortified wines"),
    "service": ("unit_1", "u1_lo5", "Advice and service"),
    "storage": ("unit_1", "u1_lo5", "Advice and service"),
    "tasting": ("unit_2", "u2_lo1", "Analytical tasting"),
}


class UnionFind:
    def __init__(self, identifiers: list[str]) -> None:
        self.parent = {identifier: identifier for identifier in identifiers}

    def find(self, identifier: str) -> str:
        parent = self.parent[identifier]
        if parent != identifier:
            self.parent[identifier] = self.find(parent)
        return self.parent[identifier]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def deduplicated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(row["question_id"]): row for row in rows}
    union_find = UnionFind(list(by_id))
    clusters: dict[str, list[str]] = defaultdict(list)
    path = ROOT / "data" / "exports" / "duplicate_clusters.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig") as handle:
            for member in csv.DictReader(handle):
                identifier = member["question_id"]
                if identifier in by_id:
                    clusters[member["cluster_id"]].append(identifier)
    for identifiers in clusters.values():
        for identifier in identifiers[1:]:
            union_find.union(identifiers[0], identifier)

    eligible = [row for row in rows if row.get("human_review_status") in ALLOWED_STATUSES]
    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        components[union_find.find(str(row["question_id"]))].append(row)

    def preference(row: dict[str, Any]) -> tuple[int, int, int, float]:
        choices = row.get("answer_choices") or []
        valid_mcq = (
            row.get("question_format") == "multiple_choice"
            and len(choices) >= 2
            and isinstance(row.get("correct_answer_index"), int)
        )
        return (
            int(row.get("human_review_status") == "human_reviewed"),
            int(valid_mcq),
            int(bool(row.get("answer_text"))),
            float(row.get("quality_score") or 0),
        )

    return [max(component, key=preference) for component in components.values()]


def pack_question(row: dict[str, Any]) -> dict[str, Any]:
    topic = str(row.get("topic_primary") or "still_wines")
    unit, outcome, category = TOPIC_TO_OUTCOME.get(
        topic, ("unit_1", "u1_lo2", "Still wines")
    )
    choices = [str(choice) for choice in row.get("answer_choices") or []]
    correct_index = row.get("correct_answer_index")
    valid_mcq = (
        row.get("question_format") == "multiple_choice"
        and len(choices) >= 2
        and isinstance(correct_index, int)
        and 0 <= correct_index < len(choices)
    )
    if valid_mcq:
        study_mode = "multiple_choice"
    elif row.get("question_format") == "identification":
        study_mode = "flashcard"
    else:
        study_mode = "written_answer"
    return {
        "id": row["question_id"],
        "prompt": row.get("normalized_text") or row.get("raw_text") or "",
        "answer": row.get("answer_text"),
        "explanation": row.get("explanation_text"),
        "choices": choices if valid_mcq else [],
        "correctAnswerIndex": correct_index if valid_mcq else None,
        "studyMode": study_mode,
        "originalFormat": row.get("question_format") or "unknown",
        "unit": unit,
        "learningOutcome": outcome,
        "category": category,
        "topic": topic,
        "cognitiveSkill": row.get("cognitive_skill"),
        "commandVerb": row.get("command_verb"),
        "language": row.get("language") or "en",
        "geography": row.get("geography") or [],
        "grapeVarieties": row.get("grape_varieties") or [],
        "markAllocation": row.get("mark_allocation"),
        "sourceID": row["source_id"],
        "sourceURL": row["source_url"],
        "qualityScore": row.get("quality_score"),
        "reviewStatus": row.get("human_review_status") or "unreviewed",
    }


def translatable_content(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt": question.get("prompt") or "",
        "answer": question.get("answer"),
        "explanation": question.get("explanation"),
        "choices": question.get("choices") or [],
    }


def question_fingerprint(question: dict[str, Any]) -> str:
    content = json.dumps(
        translatable_content(question),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(content)


def apply_complete_translations(
    questions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    if not TRANSLATION_CACHE.exists():
        return questions, False
    cached = {
        str(record["id"]): record for record in read_jsonl(TRANSLATION_CACHE)
    }
    translated: list[dict[str, Any]] = []
    for question in questions:
        record = cached.get(str(question["id"]))
        if (
            record is None
            or record.get("sourceFingerprint") != question_fingerprint(question)
            or not isinstance(record.get("en"), dict)
            or not isinstance(record.get("ja"), dict)
        ):
            return questions, False
        paired = dict(question)
        paired["translations"] = {"en": record["en"], "ja": record["ja"]}
        paired["translationStatus"] = record.get("status", "machine_translated")
        paired["translationModel"] = record.get("model")
        translated.append(paired)
    return translated, True


def build_pack(output: Path) -> dict[str, Any]:
    source_path = ROOT / "data" / "reviewed" / "questions.jsonl"
    rows = read_jsonl(source_path)
    questions = [pack_question(row) for row in deduplicated_rows(rows)]
    if CURATED_PATH.exists():
        curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
        if not isinstance(curated, list):
            raise ValueError(f"Curated question file must contain a list: {CURATED_PATH}")
        questions.extend(curated)
    questions = [question for question in questions if question["prompt"]]
    identifiers = [str(question["id"]) for question in questions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Question pack contains duplicate IDs")
    questions.sort(key=lambda question: str(question["id"]))
    questions, translations_complete = apply_complete_translations(questions)
    stable_content = json.dumps(
        questions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    payload = {
        "schemaVersion": 2 if translations_complete else 1,
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceHash": sha256_bytes(stable_content),
        "questionCount": len(questions),
        "questions": questions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ignored private iOS question pack")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_pack(args.output)
    print(
        f"Wrote {payload['questionCount']} deduplicated questions to {args.output} "
        f"(schema v{payload['schemaVersion']})"
    )


if __name__ == "__main__":
    main()
