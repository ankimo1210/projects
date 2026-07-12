from tests.test_models import make_question
from wset_corpus.screening import screen_question


def test_marketing_heading_is_rejected() -> None:
    question = make_question(normalized_text="What you'll learn")
    assert screen_question(question)[0] == "rejected"


def test_pdf_spacing_damage_is_flagged() -> None:
    question = make_question(normalized_text="W h a t is th e answer?")
    assert screen_question(question)[0] == "fact_check_required"


def test_clear_question_is_machine_screened() -> None:
    question = make_question(normalized_text="Explain how altitude affects wine style.")
    assert screen_question(question)[0] == "machine_screened"
