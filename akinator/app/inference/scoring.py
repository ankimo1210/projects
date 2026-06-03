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
