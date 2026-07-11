from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .deduplication import find_duplicates
from .fetcher import SafeFetcher
from .models import QuestionRecord
from .normalization import normalize_text, question_id
from .parsers import (
    detect_question_candidates,
    extract_document,
    extract_structured_questions,
    parse_mark_allocation,
)
from .quality import score_question
from .registry import approved_sources, load_sources
from .screening import screen_question
from .taxonomy import classify, validate_labels
from .utils import ROOT, read_jsonl, write_jsonl


def fetch_sources(source_id: str | None = None) -> list[dict[str, Any]]:
    fetcher = SafeFetcher()
    records = []
    try:
        for source in approved_sources(load_sources(), source_id):
            for url in source.urls:
                records.append(fetcher.fetch(source, str(url)).model_dump(mode="json"))
    finally:
        fetcher.close()
    write_jsonl(ROOT / "data" / "exports" / "fetch_log.jsonl", records)
    return records


def extract_sources(source_id: str | None = None) -> list[QuestionRecord]:
    sources = {source.source_id: source for source in load_sources()}
    questions: list[QuestionRecord] = []
    base = ROOT / "data" / "raw_private"
    directories = [base / source_id] if source_id else sorted(base.iterdir())
    for directory in directories:
        if not directory.is_dir() or directory.name not in sources:
            continue
        source = sources[directory.name]
        for manifest_path in sorted(directory.rglob("manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            content_path = manifest_path.parent / manifest["filename"]
            supplemental_paths = [
                manifest_path.parent / item["filename"]
                for item in manifest.get("supplemental_files", [])
                if isinstance(item, dict) and item.get("filename")
            ]
            document = extract_document(content_path)
            structured = extract_structured_questions(content_path, supplemental_paths)
            url_position = manifest.get("url", "")
            heuristic_candidates = (
                []
                if structured
                else detect_question_candidates(document.text)
            )
            for position, raw_text, confidence in heuristic_candidates:
                normalized = normalize_text(raw_text)
                labels = classify(normalized)
                validate_labels(labels)
                questions.append(
                    QuestionRecord.model_validate(
                        {
                            "question_id": question_id(
                                source.source_id, normalized, position, url_position
                            ),
                            "source_id": source.source_id,
                            "source_url": url_position,
                            "language": document.language,
                            "raw_text": raw_text,
                            "normalized_text": normalized,
                            "mark_allocation": parse_mark_allocation(raw_text),
                            "extraction_confidence": confidence,
                            "extraction_method": document.extraction_method,
                            "source_position": position,
                            "copyright_risk": source.copyright_risk,
                            **labels,
                        }
                    )
                )
            for item in structured:
                normalized = normalize_text(item.raw_text)
                labels = classify(normalized)
                labels["question_format"] = item.question_format
                validate_labels(labels)
                questions.append(
                    QuestionRecord.model_validate(
                        {
                            "question_id": question_id(
                                source.source_id, normalized, item.position, url_position
                            ),
                            "source_id": source.source_id,
                            "source_url": url_position,
                            "language": document.language,
                            "raw_text": item.raw_text,
                            "normalized_text": normalized,
                            "answer_text": item.answer_text,
                            "answer_choices": list(item.answer_choices),
                            "correct_answer_index": item.correct_answer_index,
                            "explanation_text": item.explanation_text,
                            "mark_allocation": parse_mark_allocation(item.raw_text),
                            "extraction_confidence": 0.98,
                            "extraction_method": item.extraction_method,
                            "source_position": item.position,
                            "copyright_risk": source.copyright_risk,
                            **labels,
                        }
                    )
                )
    write_jsonl(
        ROOT / "data" / "extracted" / "questions.jsonl",
        [question.model_dump(mode="json") for question in questions],
    )
    return questions


def load_questions() -> list[QuestionRecord]:
    path = ROOT / "data" / "normalized" / "questions.jsonl"
    if not path.exists():
        path = ROOT / "data" / "extracted" / "questions.jsonl"
    return [QuestionRecord.model_validate(row) for row in read_jsonl(path)]


def normalize_and_classify() -> list[QuestionRecord]:
    extracted_path = ROOT / "data" / "extracted" / "questions.jsonl"
    questions = [
        QuestionRecord.model_validate(row) for row in read_jsonl(extracted_path)
    ]
    normalized: list[QuestionRecord] = []
    for question in questions:
        text = normalize_text(question.raw_text or question.normalized_text or "")
        labels = classify(text)
        if question.extraction_method in {
            "html_embedded_quiz_json",
            "html_quiz_markup",
            "public_frontend_json",
        }:
            labels["question_format"] = "multiple_choice"
            labels["cognitive_skill"] = "recognition"
        elif question.extraction_method == "public_bundle_flashcards":
            labels["question_format"] = "identification"
            labels["cognitive_skill"] = "recall"
        validate_labels(labels)
        normalized.append(
            question.model_copy(
                update={
                    "normalized_text": text,
                    "question_id": question_id(
                        question.source_id, text, question.source_position, question.source_url
                    ),
                    **labels,
                }
            )
        )
    write_jsonl(
        ROOT / "data" / "normalized" / "questions.jsonl",
        [question.model_dump(mode="json") for question in normalized],
    )
    return normalized


def score_questions() -> list[QuestionRecord]:
    scored = []
    for question in load_questions():
        result = score_question(question)
        review_status, screening_note = screen_question(question)
        notes = [*result.penalties]
        if screening_note:
            notes.append(screening_note)
        scored.append(
            question.model_copy(
                update={
                    "quality_score": result.score,
                    "quality_category": result.category,
                    "human_review_status": review_status,
                    "review_notes": ";".join(notes) or None,
                }
            )
        )
    write_jsonl(
        ROOT / "data" / "reviewed" / "questions.jsonl",
        [question.model_dump(mode="json") for question in scored],
    )
    return scored


def deduplicate_questions() -> list[dict[str, Any]]:
    clusters = find_duplicates(load_questions())
    rows: list[dict[str, Any]] = []
    for cluster in clusters:
        for member in cluster.members:
            rows.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "match_type": cluster.match_type,
                    "question_id": member.question_id,
                    "similarity": member.similarity,
                    "probable_original_source": cluster.probable_original_source,
                    "language_relationship": cluster.language_relationship,
                    "human_review_status": cluster.human_review_status,
                }
            )
    _write_csv(ROOT / "data" / "exports" / "duplicate_clusters.csv", rows)
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0]) if rows else [])
    if not names:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
