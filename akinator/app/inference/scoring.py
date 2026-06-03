"""Probabilistic scoring for akinator candidates.

`expected_match` classifies an entity against a question. `update_log_score`
applies a Bayesian-style log-likelihood update keyed on the user's answer,
with missing attributes treated as neutral + a soft penalty (so sparse Wikidata
entities are not eliminated)."""
from __future__ import annotations

import math
from enum import Enum

from app.models import Answer, Entity, Question


class MatchResult(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"


def expected_match(entity: Entity, question: Question) -> MatchResult:
    if not entity.has_feature(question.feature_key):
        return MatchResult.MISSING
    value = entity.feature(question.feature_key)
    mt = question.match_type
    if mt == "list_contains":
        return MatchResult.MATCH if question.expected_value in value else MatchResult.MISMATCH
    # equals / numeric
    return MatchResult.MATCH if value == question.expected_value else MatchResult.MISMATCH


# Log-likelihood magnitudes. Tunable in one place.
STRONG = math.log(0.9 / 0.1)          # decisive evidence
WEAK_MISSING = math.log(0.6 / 0.4)    # soft penalty for missing attribute
_PROBABLY_SCALE = 0.5                  # "probably_*" is half as confident


def _signed_delta(result: MatchResult, asked_positive: bool) -> float:
    """Delta for a definite yes/no answer. asked_positive=True means the user
    said the property holds (YES); False means it does not (NO)."""
    if result is MatchResult.MISSING:
        return -WEAK_MISSING
    agrees = (result is MatchResult.MATCH) == asked_positive
    return STRONG if agrees else -STRONG


def update_log_score(
    log_score: float, entity: Entity, question: Question, answer: Answer
) -> float:
    if answer is Answer.UNKNOWN:
        return log_score
    result = expected_match(entity, question)
    if answer in (Answer.YES, Answer.NO):
        return log_score + _signed_delta(result, answer is Answer.YES)
    # probably_yes / probably_no — same direction, scaled down
    asked_positive = answer is Answer.PROBABLY_YES
    return log_score + _PROBABLY_SCALE * _signed_delta(result, asked_positive)
