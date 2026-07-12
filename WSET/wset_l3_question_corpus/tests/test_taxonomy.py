import pytest

from wset_corpus.taxonomy import classify, load_taxonomy, validate_labels


def test_comparison_classification() -> None:
    result = classify("Compare traditional method and tank method sparkling wines.")
    assert result["question_format"] == "comparison"
    assert result["topic_primary"] == "sparkling_wines"
    validate_labels(result, load_taxonomy())


def test_invalid_taxonomy_label_fails() -> None:
    result = classify("Explain fermentation.")
    result["topic_primary"] = "not_a_topic"
    with pytest.raises(ValueError):
        validate_labels(result)
