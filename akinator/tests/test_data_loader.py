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
