from wset_corpus.normalization import normalize_text, normalized_language, question_id


def test_normalization_preserves_content_and_normalizes_punctuation() -> None:
    assert normalize_text("  Explain  “oak” — briefly.  ") == 'Explain "oak" - briefly.'


def test_question_id_uses_position() -> None:
    text = "Explain climate."
    assert question_id("source", text, 1) != question_id("source", text, 2)


def test_language_detection() -> None:
    assert normalized_language("理由を説明しなさい。") == "ja"
    assert normalized_language("Explain the reason.") == "en"
