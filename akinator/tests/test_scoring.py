from app.inference.scoring import MatchResult, expected_match
from app.models import Entity, Question


def _entity(features):
    return Entity(id="Q", name="n", aliases=[], description="", image_url=None,
                  features=features)


def test_equals_match_and_mismatch():
    q = Question("q", "?", "gender", "male", "equals")
    assert expected_match(_entity({"gender": "male"}), q) == MatchResult.MATCH
    assert expected_match(_entity({"gender": "female"}), q) == MatchResult.MISMATCH


def test_missing_feature_is_missing():
    q = Question("q", "?", "gender", "male", "equals")
    assert expected_match(_entity({}), q) == MatchResult.MISSING


def test_list_contains():
    q = Question("q", "?", "occupation", "actor", "list_contains")
    assert expected_match(_entity({"occupation": ["actor", "singer"]}), q) == MatchResult.MATCH
    assert expected_match(_entity({"occupation": ["singer"]}), q) == MatchResult.MISMATCH
    assert expected_match(_entity({"occupation": []}), q) == MatchResult.MISSING


def test_numeric_equals():
    q = Question("q", "?", "birth_century", 20, "numeric")
    assert expected_match(_entity({"birth_century": 20}), q) == MatchResult.MATCH
    assert expected_match(_entity({"birth_century": 19}), q) == MatchResult.MISMATCH
