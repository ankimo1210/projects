from pathlib import Path

from tests.test_models import make_question
from wset_corpus.exporting import _question_row
from wset_corpus.utils import ROOT


def test_public_safe_export_removes_restricted_text() -> None:
    question = make_question(redistribution_status="private_research_only")
    private = _question_row(question, "private")
    public = _question_row(question, "public-safe")
    assert private["raw_text"]
    assert public["raw_text"] is None
    assert public["normalized_text"] is None
    assert public["answer_choices"] == []
    assert public["correct_answer_index"] is None
    assert public["explanation_text"] is None


def test_raw_private_is_gitignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw_private/**" in ignore
    assert Path(ROOT / "data" / "raw_private").exists()
