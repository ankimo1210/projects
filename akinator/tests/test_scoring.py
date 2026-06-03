from app.inference.scoring import MatchResult, expected_match
from app.models import Answer, Entity, Question


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


from app.inference.scoring import update_log_score


def test_yes_raises_match_lowers_mismatch():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    female = _entity({"gender": "female"})
    assert update_log_score(0.0, male, q, Answer.YES) > 0.0
    assert update_log_score(0.0, female, q, Answer.YES) < 0.0


def test_no_is_mirror_of_yes():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    assert update_log_score(0.0, male, q, Answer.NO) < 0.0


def test_unknown_is_noop():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    assert update_log_score(1.23, male, q, Answer.UNKNOWN) == 1.23


def test_missing_feature_soft_penalty_not_elimination():
    q = Question("q", "?", "gender", "male", "equals")
    nofeat = _entity({})
    delta = update_log_score(0.0, nofeat, q, Answer.YES)
    # small negative, strictly greater than a full mismatch
    mismatch = update_log_score(0.0, _entity({"gender": "female"}), q, Answer.YES)
    assert mismatch < delta < 0.0


def test_probably_yes_is_weaker_than_yes():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    strong = update_log_score(0.0, male, q, Answer.YES)
    weak = update_log_score(0.0, male, q, Answer.PROBABLY_YES)
    assert 0.0 < weak < strong
