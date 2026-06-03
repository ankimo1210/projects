from app.models import Answer, Entity, Question


def test_entity_feature_access():
    e = Entity(
        id="Q1",
        name="Test",
        aliases=["T"],
        description="d",
        image_url=None,
        features={"gender": "male", "occupation": ["actor"], "birth_century": 20},
    )
    assert e.feature("gender") == "male"
    assert e.feature("missing") is None
    assert e.has_feature("gender") is True
    assert e.has_feature("missing") is False


def test_question_fields():
    q = Question(
        id="q_gender_male",
        text="男性ですか？",
        feature_key="gender",
        expected_value="male",
        match_type="equals",
    )
    assert q.feature_key == "gender"
    assert q.match_type == "equals"


def test_answer_enum_values():
    assert Answer.YES.value == "yes"
    assert {a.value for a in Answer} == {
        "yes", "no", "probably_yes", "probably_no", "unknown",
    }


import json
from app.data_loader import (
    dump_entities, dump_questions, load_entities, load_questions,
)


def test_entities_roundtrip(tmp_path):
    entities = [
        Entity("Q1", "A", ["a"], "d", None, {"gender": "male", "occupation": ["actor"]}),
    ]
    path = tmp_path / "entities.json"
    dump_entities(entities, path)
    loaded = load_entities(path)
    assert loaded[0].id == "Q1"
    assert loaded[0].features["occupation"] == ["actor"]


def test_questions_roundtrip(tmp_path):
    qs = [Question("q1", "?", "gender", "male", "equals")]
    path = tmp_path / "questions.json"
    dump_questions(qs, path)
    loaded = load_questions(path)
    assert loaded[0].id == "q1"
    assert loaded[0].match_type == "equals"
