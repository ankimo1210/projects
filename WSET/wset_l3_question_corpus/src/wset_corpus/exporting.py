from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from .models import QuestionRecord
from .pipeline import _write_csv
from .registry import load_sources
from .taxonomy import load_taxonomy
from .utils import ROOT, read_jsonl, write_jsonl

ExportMode = Literal["private", "public-safe"]


def _question_row(question: QuestionRecord, mode: ExportMode) -> dict[str, Any]:
    row = question.model_dump(mode="json")
    if mode == "public-safe" and question.redistribution_status != "reusable":
        row["raw_text"] = None
        row["normalized_text"] = None
        row["answer_text"] = None
        row["answer_choices"] = []
        row["correct_answer_index"] = None
        row["explanation_text"] = None
    return row


def export_dataset(mode: ExportMode = "private") -> list[Path]:
    reviewed = ROOT / "data" / "reviewed" / "questions.jsonl"
    fallback = ROOT / "data" / "normalized" / "questions.jsonl"
    rows = read_jsonl(reviewed if reviewed.exists() else fallback)
    questions = [QuestionRecord.model_validate(row) for row in rows]
    suffix = "public_safe" if mode == "public-safe" else "private"
    jsonl_path = ROOT / "data" / "exports" / f"questions_{suffix}.jsonl"
    csv_path = ROOT / "data" / "exports" / f"questions_{suffix}.csv"
    exported = [_question_row(question, mode) for question in questions]
    write_jsonl(jsonl_path, exported)
    _write_csv(csv_path, exported, list(QuestionRecord.model_fields))
    paths = [jsonl_path, csv_path]
    if mode == "private":
        canonical_jsonl = ROOT / "data" / "exports" / "questions.jsonl"
        canonical_csv = ROOT / "data" / "exports" / "questions.csv"
        write_jsonl(canonical_jsonl, exported)
        _write_csv(canonical_csv, exported, list(QuestionRecord.model_fields))
        paths.extend([canonical_jsonl, canonical_csv])

    source_rows = []
    for source in load_sources():
        row = source.model_dump(mode="json")
        row["urls"] = " | ".join(str(url) for url in source.urls)
        row["expected_content"] = " | ".join(source.expected_content)
        source_rows.append(row)
    sources_path = ROOT / "data" / "exports" / "sources.csv"
    _write_csv(sources_path, source_rows)

    patterns_path = ROOT / "data" / "exports" / "question_patterns.jsonl"
    patterns = read_jsonl(ROOT / "data" / "reviewed" / "question_patterns.jsonl")
    write_jsonl(patterns_path, patterns)

    taxonomy = load_taxonomy()
    counts: dict[str, int] = {}
    for question in questions:
        if question.topic_primary:
            counts[question.topic_primary] = counts.get(question.topic_primary, 0) + 1
    gap_rows = [
        {
            "dimension": "content_area",
            "value": topic,
            "question_count": counts.get(topic, 0),
            "gap_status": "missing" if counts.get(topic, 0) == 0 else "covered_unreviewed",
        }
        for topic in taxonomy["content_areas"]
    ]
    gaps_path = ROOT / "data" / "exports" / "coverage_gaps.csv"
    _write_csv(gaps_path, gap_rows)

    queue = [
        row
        for row in exported
        if float(row.get("quality_score") or 0) >= 75
        and row.get("human_review_status") not in {"human_reviewed", "rejected"}
    ]
    queue_path = ROOT / "data" / "exports" / "high_quality_review_queue.csv"
    _write_csv(queue_path, queue, list(QuestionRecord.model_fields))
    return [*paths, sources_path, patterns_path, gaps_path, queue_path]
