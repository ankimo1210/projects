from app.inference.question_selection import select_question, split_score
from app.models import Entity, Question


def _e(eid, features):
    return Entity(id=eid, name=eid, aliases=[], description="", image_url=None,
                  features=features)


def _make_pool():
    # 4 entities: 2 male, 2 female; 1 actor, 3 not
    return [
        _e("a", {"gender": "male", "occupation": ["actor"]}),
        _e("b", {"gender": "male", "occupation": ["singer"]}),
        _e("c", {"gender": "female", "occupation": ["singer"]}),
        _e("d", {"gender": "female", "occupation": ["singer"]}),
    ]


def test_split_score_prefers_even_split():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q_gender = Question("qg", "?", "gender", "male", "equals")     # 2/2 even
    q_actor = Question("qa", "?", "occupation", "actor", "list_contains")  # 1/3 skewed
    # lower split_score = more balanced = better
    assert split_score(q_gender, pool, weights) < split_score(q_actor, pool, weights)


def test_select_question_picks_most_balanced_and_skips_asked():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q_gender = Question("qg", "?", "gender", "male", "equals")
    q_actor = Question("qa", "?", "occupation", "actor", "list_contains")
    chosen = select_question([q_gender, q_actor], pool, weights, asked_ids=set())
    assert chosen.id == "qg"
    # if gender already asked, must fall back to actor
    chosen2 = select_question([q_gender, q_actor], pool, weights, asked_ids={"qg"})
    assert chosen2.id == "qa"


def test_select_question_returns_none_when_all_asked():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q = Question("qg", "?", "gender", "male", "equals")
    assert select_question([q], pool, weights, asked_ids={"qg"}) is None
