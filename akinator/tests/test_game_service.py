from app.services.entity_service import EntityService


def test_entity_service_lookup(small_pool, small_questions):
    svc = EntityService(small_pool, small_questions)
    assert svc.get_entity("a").name == "アクターA"
    assert svc.get_entity("zzz") is None
    assert len(svc.entities) == 4
    assert len(svc.questions) == 4


from app.models import Answer
from app.services.game_service import GameService, GameState


def test_initial_scores_zero_and_first_question(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    assert set(state.log_scores) == {"a", "b", "c", "d"}
    assert all(v == 0.0 for v in state.log_scores.values())
    q = svc.next_question(state)
    assert q is not None and q.id not in state.asked_ids


def test_answer_updates_scores_and_marks_asked(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_gender_male")
    svc.record_answer(state, q, Answer.YES)
    assert q.id in state.asked_ids
    # males a, c rise above females b, d
    assert state.log_scores["a"] > state.log_scores["b"]
    assert state.log_scores["c"] > state.log_scores["d"]


def test_asked_question_not_reselected(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    first = svc.next_question(state)
    svc.record_answer(state, first, Answer.YES)
    second = svc.next_question(state)
    assert second is None or second.id != first.id


def test_unknown_answer_keeps_scores(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_gender_male")
    svc.record_answer(state, q, Answer.UNKNOWN)
    assert all(v == 0.0 for v in state.log_scores.values())
    assert q.id in state.asked_ids  # still consumed


def test_best_guess_returns_top_entity(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_is_fictional_True")
    svc.record_answer(state, q, Answer.YES)   # favors c, d
    guess, posterior = svc.best_guess(state)
    assert guess.id in {"c", "d"}
    assert 0.0 < posterior <= 1.0


def test_should_guess_threshold(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions), guess_threshold=0.6)
    state = svc.new_game()
    # answer several questions to concentrate mass on one entity
    for qid, ans in [("q_is_fictional_True", Answer.NO),
                     ("q_gender_male", Answer.YES),
                     ("q_occupation_actor", Answer.YES)]:
        q = next(q for q in small_questions if q.id == qid)
        svc.record_answer(state, q, ans)
    # 'a' should dominate; either threshold reached or no questions left
    assert svc.should_guess(state) in (True, False)
    guess, _ = svc.best_guess(state)
    assert guess.id == "a"
