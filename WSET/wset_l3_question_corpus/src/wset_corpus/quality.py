from __future__ import annotations

from dataclasses import dataclass

from .models import QuestionRecord


@dataclass(frozen=True)
class QualityResult:
    score: float
    category: str
    penalties: tuple[str, ...]


def category(score: float) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "usable_after_review"
    if score >= 40:
        return "weak"
    return "reject"


def score_question(question: QuestionRecord) -> QualityResult:
    """Transparent heuristic review aid; never an objective truth score."""
    text = question.normalized_text or ""
    score = 0.0
    score += 20 if question.topic_primary else 8
    score += 15 if 15 <= len(text) <= 500 else 5
    score += 10 if question.command_verb else 5
    reasoning_skills = {"causal_reasoning", "comparison", "evaluation"}
    score += 15 if question.cognitive_skill in reasoning_skills else 5
    style_terms = ("style", "quality", "price", "スタイル", "品質", "価格")
    score += 15 if any(word in text.casefold() for word in style_terms) else 4
    score += 10 if question.answer_text else 2
    score += 5 if question.mark_allocation is not None else 2
    score += 5 if question.difficulty else 2
    score += 5 if question.source_id.startswith("wset_official") else 2
    penalties: list[str] = []
    if len(text.split()) < 4 and question.language == "en":
        penalties.append("trivia_or_fragment")
        score -= 10
    if question.extraction_confidence < 0.75:
        penalties.append("low_extraction_confidence")
        score -= 10
    if not question.answer_text:
        penalties.append("no_answer_basis")
    score = max(0.0, min(100.0, score))
    return QualityResult(score, category(score), tuple(penalties))
