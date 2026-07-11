from tests.test_models import make_question
from wset_corpus.quality import category, score_question


def test_quality_score_is_bounded_and_transparent() -> None:
    result = score_question(make_question())
    assert 0 <= result.score <= 100
    assert result.category == category(result.score)
    assert "no_answer_basis" in result.penalties
