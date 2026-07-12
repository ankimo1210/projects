import json

from scripts.build_private_app_pack import (
    CURATED_PATH,
    apply_complete_translations,
    deduplicated_rows,
    pack_question,
    question_fingerprint,
)
from scripts.fetch_ankiweb_deck import select_note_fields
from scripts.translate_private_app_pack import (
    extract_direct_translation,
    normalize_wine_terms,
)


def sample(identifier: str, **updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "question_id": identifier,
        "source_id": "source",
        "source_url": "https://example.com",
        "normalized_text": "Which wine?",
        "answer_text": "B",
        "answer_choices": ["A", "B"],
        "correct_answer_index": 1,
        "question_format": "multiple_choice",
        "topic_primary": "sparkling_wines",
        "language": "en",
        "human_review_status": "machine_screened",
        "quality_score": 80,
    }
    row.update(updates)
    return row


def test_pack_question_preserves_mcq_contract() -> None:
    packed = pack_question(sample("q_1"))
    assert packed["studyMode"] == "multiple_choice"
    assert packed["correctAnswerIndex"] == 1
    assert packed["learningOutcome"] == "u1_lo3"


def test_rejected_questions_are_not_eligible() -> None:
    rows = [sample("q_1"), sample("q_2", human_review_status="rejected")]
    assert [row["question_id"] for row in deduplicated_rows(rows)] == ["q_1"]


def test_anki_three_field_model_uses_front_and_back() -> None:
    front, back = select_note_fields(
        ["Name", "Front", "Back"],
        ["Repeated question", "Repeated question", "Actual answer"],
    )
    assert front == "Repeated question"
    assert back == "Actual answer"


def test_curated_service_questions_are_valid_and_bilingual() -> None:
    questions = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    assert len(questions) >= 30
    assert {question["language"] for question in questions} == {"en", "ja"}
    assert all(question["learningOutcome"] == "u1_lo5" for question in questions)
    assert all(question["studyMode"] == "multiple_choice" for question in questions)
    assert all(
        0 <= question["correctAnswerIndex"] < len(question["choices"])
        and question["answer"] == question["choices"][question["correctAnswerIndex"]]
        for question in questions
    )


def test_complete_translation_cache_produces_bilingual_questions(
    tmp_path, monkeypatch
) -> None:
    question = {
        "id": "q_1",
        "prompt": "Which wine?",
        "answer": "Champagne",
        "explanation": None,
        "choices": [],
    }
    cache_path = tmp_path / "translations.jsonl"
    record = {
        "id": "q_1",
        "sourceFingerprint": question_fingerprint(question),
        "en": {
            "prompt": "Which wine?",
            "answer": "Champagne",
            "explanation": None,
            "choices": [],
        },
        "ja": {
            "prompt": "どのワインか？",
            "answer": "シャンパーニュ",
            "explanation": None,
            "choices": [],
        },
        "model": "test-model",
        "status": "machine_translated",
    }
    cache_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.build_private_app_pack.TRANSLATION_CACHE", cache_path
    )

    translated, complete = apply_complete_translations([question])

    assert complete is True
    assert translated[0]["translations"]["en"]["answer"] == "Champagne"
    assert translated[0]["translations"]["ja"]["answer"] == "シャンパーニュ"


def test_incomplete_translation_cache_does_not_create_mixed_schema(
    tmp_path, monkeypatch
) -> None:
    cache_path = tmp_path / "translations.jsonl"
    cache_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.build_private_app_pack.TRANSLATION_CACHE", cache_path
    )
    questions = [
        {
            "id": "q_1",
            "prompt": "Which wine?",
            "answer": "Champagne",
            "explanation": None,
            "choices": [],
        }
    ]

    untranslated, complete = apply_complete_translations(questions)

    assert complete is False
    assert untranslated == questions


def test_direct_translation_extracts_official_translategemma_envelope() -> None:
    content = json.dumps(
        [
            {
                "type": "text",
                "source_lang_code": "en",
                "target_lang_code": "ja",
                "text": "⟦0000⟧ スパークリングワイン",
            }
        ],
        ensure_ascii=False,
    )
    assert extract_direct_translation(content) == "⟦0000⟧ スパークリングワイン"


def test_wine_term_normalization_repairs_known_machine_variants() -> None:
    assert normalize_wine_terms("タニクと澱（せんでい）", "ja") == "タンニンと澱"
