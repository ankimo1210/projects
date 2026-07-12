import io

from pypdf import PdfWriter

from wset_corpus.parsers import (
    detect_language,
    detect_question_candidates,
    extract_html,
    extract_pdf,
    extract_structured_questions,
    parse_mark_allocation,
)


def test_html_extraction_ignores_navigation() -> None:
    document = extract_html(
        b"<html><head><title>Synthetic</title></head><body><nav>Menu</nav>"
        b"<main><h1>Study</h1><p>Explain how climate affects wine style? (5 marks)</p></main>"
        b"</body></html>"
    )
    assert document.title == "Synthetic"
    assert "Explain how climate" in document.text
    assert "Menu" not in document.text


def test_pdf_extraction_accepts_small_synthetic_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = io.BytesIO()
    writer.write(buffer)
    document = extract_pdf(buffer.getvalue())
    assert document.extraction_method == "pdf_pypdf"


def test_japanese_question_detection_and_marks() -> None:
    text = "説明\n比較しなさい。冷涼地と温暖地の栽培条件を比較しなさい。（8点）"
    candidates = detect_question_candidates(text)
    assert len(candidates) == 1
    assert parse_mark_allocation(candidates[0][1]) == 8
    assert detect_language(candidates[0][1]) == "ja"


def test_english_mark_allocation() -> None:
    assert parse_mark_allocation("Explain the effect. (2.5 marks)") == 2.5


def test_embedded_quiz_json_extraction(tmp_path) -> None:
    path = tmp_path / "quiz.html"
    path.write_text(
        '<div data-quiz=\'{"questions":[{"question":"Which wine?",'
        '"choices":["A","B"],"answer":1,"explanation":"Because."}]}\'></div>'
    )
    questions = extract_structured_questions(path)
    assert len(questions) == 1
    assert questions[0].raw_text == "Which wine?"
    assert questions[0].answer_text == "B"
    assert questions[0].explanation_text == "Because."


def test_supplemental_public_json_extraction(tmp_path) -> None:
    html = tmp_path / "page.html"
    html.write_text("<main>Quiz</main>")
    payload = tmp_path / "dynamic_questions.json"
    payload.write_text(
        '[{"question":"What happens?","options":["A","B"],'
        '"correct_index":0,"explanation":"Reason"}]'
    )
    questions = extract_structured_questions(html, [payload])
    assert questions[0].answer_text == "A"
    assert questions[0].explanation_text == "Reason"


def test_supplemental_bundle_question_and_flashcard_extraction(tmp_path) -> None:
    html = tmp_path / "page.html"
    html.write_text("<main>Study</main>")
    questions_payload = tmp_path / "questions.json"
    questions_payload.write_text(
        '[{"question":"Which wine?","options":["A","B"],"correctAnswer":1}]'
    )
    flashcards_payload = tmp_path / "flashcards.json"
    flashcards_payload.write_text('[{"front":"Define flor.","back":"A film of yeast."}]')
    questions = extract_structured_questions(html, [questions_payload, flashcards_payload])
    assert questions[0].answer_text == "B"
    assert questions[0].answer_choices == ("A", "B")
    assert questions[0].correct_answer_index == 1
    assert questions[1].question_format == "identification"
    assert questions[1].answer_text == "A film of yeast."


def test_japanese_imperative_question_detection() -> None:
    candidates = detect_question_candidates("このワインのスタイルを描写しなさい。")
    assert len(candidates) == 1
