from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

PARSER_VERSION = "0.1.0"
QUESTION_START = re.compile(
    r"^(?:\d+[.)]\s*)?(?:explain|describe|compare|identify|state|outline|what\b|why\b|how\b|"
    r"discuss|give reasons|define|select|which of the following|次のうち|説明しなさい|述べなさい|"
    r"比較しなさい|挙げなさい|理由を説明しなさい|どのような影響を与えるか)",
    re.IGNORECASE,
)
QUESTION_END = re.compile(r"[?？]\s*$")
JAPANESE_COMMAND_END = re.compile(r"(?:しなさい|答えなさい)[。.]?\s*$")
MARKS = re.compile(r"[（(]?\s*(\d+(?:\.5)?)\s*(?:marks?|点)\s*[）)]?", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedDocument:
    title: str | None
    text: str
    language: str
    extraction_method: str


@dataclass(frozen=True)
class StructuredQuestion:
    raw_text: str
    answer_text: str | None
    question_format: str
    position: int
    extraction_method: str
    answer_choices: tuple[str, ...] = ()
    correct_answer_index: int | None = None
    explanation_text: str | None = None


def detect_language(text: str) -> str:
    japanese = sum(
        1 for char in text if "\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff"
    )
    letters = sum(1 for char in text if char.isalpha())
    return "ja" if letters and japanese / letters >= 0.15 else "en"


def extract_html(content: bytes) -> ExtractedDocument:
    decoded = content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(decoded, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    for element in soup(["script", "style", "nav", "footer", "noscript"]):
        element.decompose()
    cleaned_html = str(soup)
    main_text = trafilatura.extract(cleaned_html, include_links=False, include_tables=True)
    text = main_text or soup.get_text("\n", strip=True)
    return ExtractedDocument(title, text, detect_language(text), "html_trafilatura")


def extract_pdf(content: bytes) -> ExtractedDocument:
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    title = reader.metadata.title if reader.metadata else None
    return ExtractedDocument(title, text, detect_language(text), "pdf_pypdf")


def extract_document(path: Path) -> ExtractedDocument:
    content = path.read_bytes()
    if path.suffix.lower() == ".pdf":
        return extract_pdf(content)
    return extract_html(content)


def _quiz_rows_to_questions(
    rows: list[dict[str, object]], method: str
) -> list[StructuredQuestion]:
    questions: list[StructuredQuestion] = []
    for position, row in enumerate(rows):
        raw_text = str(row.get("question") or row.get("front") or "").strip()
        if row.get("front") and row.get("back") and raw_text:
            questions.append(
                StructuredQuestion(
                    raw_text=raw_text,
                    answer_text=str(row["back"]).strip() or None,
                    question_format="identification",
                    position=position,
                    extraction_method="public_bundle_flashcards",
                )
            )
            continue
        choices_value = row.get("choices", row.get("options", []))
        if not raw_text or not isinstance(choices_value, list):
            continue
        choices = tuple(str(choice).strip() for choice in choices_value)
        answer_index = row.get(
            "answer", row.get("correct_index", row.get("correctAnswer"))
        )
        correct_choice: str | None = None
        if isinstance(answer_index, int) and 0 <= answer_index < len(choices):
            correct_choice = str(choices[answer_index])
        explanation = str(row.get("explanation") or "").strip()
        questions.append(
            StructuredQuestion(
                raw_text=raw_text,
                answer_text=correct_choice,
                question_format="multiple_choice",
                position=position,
                extraction_method=method,
                answer_choices=choices,
                correct_answer_index=answer_index if isinstance(answer_index, int) else None,
                explanation_text=explanation or None,
            )
        )
    return questions


def extract_structured_questions(
    content_path: Path, supplemental_paths: list[Path] | None = None
) -> list[StructuredQuestion]:
    questions: list[StructuredQuestion] = []
    if content_path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(content_path.read_bytes(), "lxml")
        for element in soup.select("[data-quiz]"):
            raw_payload = element.get("data-quiz")
            if not isinstance(raw_payload, str):
                continue
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                continue
            rows = payload.get("questions", []) if isinstance(payload, dict) else []
            if isinstance(rows, list):
                typed_rows = [row for row in rows if isinstance(row, dict)]
                questions.extend(_quiz_rows_to_questions(typed_rows, "html_embedded_quiz_json"))
        for position, wrapper in enumerate(soup.select(".qsm-question-wrapper")):
            question_element = wrapper.select_one(".mlw_qmn_new_question")
            if question_element is None:
                continue
            raw_text = question_element.get_text(" ", strip=True)
            if raw_text:
                questions.append(
                    StructuredQuestion(
                        raw_text=raw_text,
                        answer_text=None,
                        question_format="multiple_choice",
                        position=position,
                        extraction_method="html_quiz_markup",
                    )
                )
    for path in supplemental_paths or []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows = payload if isinstance(payload, list) else payload.get("questions", [])
        if isinstance(rows, list):
            typed_rows = [row for row in rows if isinstance(row, dict)]
            method = (
                "public_bundle_flashcards"
                if typed_rows and "front" in typed_rows[0]
                else "public_frontend_json"
            )
            questions.extend(_quiz_rows_to_questions(typed_rows, method))
    return questions


def parse_mark_allocation(text: str) -> float | None:
    match = MARKS.search(text)
    return float(match.group(1)) if match else None


def detect_question_candidates(text: str) -> list[tuple[int, str, float]]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    candidates: list[tuple[int, str, float]] = []
    for position, line in enumerate(lines):
        if len(line) < 8 or len(line) > 1200:
            continue
        starts = bool(QUESTION_START.search(line))
        ends = bool(QUESTION_END.search(line) or JAPANESE_COMMAND_END.search(line))
        has_marks = parse_mark_allocation(line) is not None
        confidence = 0.95 if starts and (ends or has_marks) else 0.82 if starts else 0.7
        if starts or ends:
            candidates.append((position, line, confidence))
    return candidates
