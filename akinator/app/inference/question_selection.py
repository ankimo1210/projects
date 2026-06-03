"""Choose the next question that best splits current candidates.

MVP metric: minimize the weighted imbalance |yes_weight - no_weight| between
entities that would answer yes vs no. Missing-feature entities count as a half
to each side so they don't dominate selection. Lower score = more balanced =
better. Designed so the metric can later be swapped for entropy/info-gain
without touching callers."""
from __future__ import annotations

from app.inference.scoring import MatchResult, expected_match
from app.models import Entity, Question


def split_score(question: Question, pool: list[Entity], weights: dict[str, float]) -> float:
    yes_w = 0.0
    no_w = 0.0
    for e in pool:
        w = weights.get(e.id, 0.0)
        result = expected_match(e, question)
        if result is MatchResult.MATCH:
            yes_w += w
        elif result is MatchResult.MISMATCH:
            no_w += w
        else:  # MISSING -> split evenly
            yes_w += w / 2
            no_w += w / 2
    return abs(yes_w - no_w)


def select_question(
    questions: list[Question],
    pool: list[Entity],
    weights: dict[str, float],
    asked_ids: set[str],
) -> Question | None:
    candidates = [q for q in questions if q.id not in asked_ids]
    if not candidates:
        return None
    return min(candidates, key=lambda q: split_score(q, pool, weights))
