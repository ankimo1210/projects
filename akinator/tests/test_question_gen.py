from app.question_gen import generate_questions
from app.models import Entity


def _pool():
    return [
        Entity("a", "A", [], "", None, {"is_fictional": False, "gender": "male",
                                        "occupation": ["actor"], "birth_century": 20}),
        Entity("b", "B", [], "", None, {"is_fictional": False, "gender": "female",
                                        "occupation": ["singer"], "birth_century": 20}),
        Entity("c", "C", [], "", None, {"is_fictional": True, "gender": "male",
                                        "occupation": ["actor"], "in_anime": True}),
        Entity("d", "D", [], "", None, {"is_fictional": True, "gender": "female",
                                        "in_anime": True}),
    ]


def test_generates_questions_from_attribute_values():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    keys = {(q.feature_key, q.expected_value) for q in qs}
    # boolean is_fictional split 2/2 -> kept
    assert ("is_fictional", True) in keys
    # gender male appears 2/4 -> kept
    assert ("gender", "male") in keys
    # occupation actor appears 2/4 (list_contains) -> kept
    assert ("occupation", "actor") in keys


def test_questions_have_japanese_text_and_match_type():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    q_male = next(q for q in qs if (q.feature_key, q.expected_value) == ("gender", "male"))
    assert q_male.match_type == "equals"
    assert "男" in q_male.text and q_male.text.endswith("？")
    q_actor = next(q for q in qs if (q.feature_key, q.expected_value) == ("occupation", "actor"))
    assert q_actor.match_type == "list_contains"


def test_drops_non_discriminative_values():
    # every entity is_fictional True -> useless, must be dropped
    pool = [Entity(str(i), str(i), [], "", None, {"is_fictional": True}) for i in range(4)]
    qs = generate_questions(pool, min_fraction=0.1, max_fraction=0.9)
    assert all(q.feature_key != "is_fictional" for q in qs)


def test_question_ids_unique_and_stable():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    ids = [q.id for q in qs]
    assert len(ids) == len(set(ids))


def test_in_anime_is_positive_only_no_duplicate_text():
    # in_anime has no natural negative phrasing, so only the True question is
    # emitted — otherwise two questions read identically with inverted semantics.
    pool = [
        Entity("a", "A", [], "", None, {"is_fictional": True, "in_anime": True}),
        Entity("b", "B", [], "", None, {"is_fictional": True, "in_anime": True}),
        Entity("c", "C", [], "", None, {"is_fictional": False, "in_anime": False}),
        Entity("d", "D", [], "", None, {"is_fictional": False, "in_anime": False}),
    ]
    qs = generate_questions(pool, min_fraction=0.1, max_fraction=0.9)
    anime_qs = [q for q in qs if q.feature_key == "in_anime"]
    assert len(anime_qs) == 1
    assert anime_qs[0].expected_value is True
    # no two questions share the same display text
    texts = [q.text for q in qs]
    assert len(texts) == len(set(texts))
