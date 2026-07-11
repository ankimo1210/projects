from tests.test_models import make_question
from wset_corpus.deduplication import find_duplicates


def test_exact_duplicate_is_clustered_not_deleted() -> None:
    left = make_question(question_id="q_left")
    right = make_question(question_id="q_right", source_id="synthetic_2")
    clusters = find_duplicates([left, right])
    assert clusters[0].match_type == "exact"
    assert len(clusters[0].members) == 2


def test_near_duplicate() -> None:
    left = make_question(
        question_id="q_left", normalized_text="Explain how altitude affects wine style"
    )
    right = make_question(
        question_id="q_right",
        normalized_text="Explain how altitude strongly affects the wine style",
    )
    clusters = find_duplicates([left, right], near_threshold=80)
    assert any(cluster.match_type == "near" for cluster in clusters)
