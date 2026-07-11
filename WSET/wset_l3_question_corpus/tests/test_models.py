from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from wset_corpus.models import QuestionRecord
from wset_corpus.utils import stable_id


def make_question(**updates: object) -> QuestionRecord:
    values: dict[str, object] = {
        "question_id": "q_1",
        "source_id": "synthetic",
        "source_url": "https://example.test/source",
        "language": "en",
        "raw_text": "Explain how altitude affects wine style.",
        "normalized_text": "Explain how altitude affects wine style.",
        "question_format": "causal_explanation",
        "command_verb": "explain",
        "topic_primary": "vineyard_environment",
        "cognitive_skill": "causal_reasoning",
        "difficulty": "medium",
        "extraction_confidence": 0.9,
        "source_position": 1,
        "copyright_risk": "low",
        "created_at": datetime.now(UTC),
    }
    values.update(updates)
    return QuestionRecord.model_validate(values)


def test_stable_id_is_deterministic() -> None:
    assert stable_id("a", "b", 1) == stable_id("a", "b", 1)
    assert stable_id("a", "b", 1) != stable_id("a", "b", 2)


def test_source_lineage_is_required() -> None:
    with pytest.raises(ValidationError):
        make_question(source_url="")
