from __future__ import annotations

import re

from .models import QuestionRecord

MARKETING_PREFIXES = (
    "what you'll learn",
    "are you ready",
    "how to taste wine",
)
QUESTION_PREFIX = re.compile(
    r"^(?:\d+[.)]\s*)?(?:explain|describe|compare|identify|state|outline|discuss|"
    r"give reasons|define|select|which|what|why|how|are|can|does|do|is|次のうち|"
    r"説明しなさい|述べなさい|比較しなさい|挙げなさい)",
    re.IGNORECASE,
)


def screen_question(question: QuestionRecord) -> tuple[str, str | None]:
    if question.extraction_method in {
        "html_embedded_quiz_json",
        "html_quiz_markup",
        "public_frontend_json",
        "public_bundle_flashcards",
    }:
        return "machine_screened", None
    text = (question.normalized_text or "").strip()
    lowered = text.casefold()
    if lowered.startswith(MARKETING_PREFIXES):
        return "rejected", "marketing_or_navigation_text"
    words = text.split()
    latin_tokens = [re.sub(r"[^A-Za-z]", "", word) for word in words]
    single_letter_rate = (
        sum(len(token) == 1 for token in latin_tokens) / len(words) if words else 0
    )
    if single_letter_rate > 0.15:
        return "fact_check_required", "pdf_character_spacing_damage"
    if not QUESTION_PREFIX.search(text):
        return "rejected", "fragment_or_non_question"
    return "machine_screened", None
