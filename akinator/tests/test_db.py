from app.db import (
    init_db, create_game, save_answer, finish_game, save_correction,
    get_game_answers,
)


def test_game_lifecycle(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    gid = create_game(db)
    assert isinstance(gid, int)
    save_answer(db, gid, "q_gender_male", "yes", 1)
    save_answer(db, gid, "q_in_anime_True", "no", 2)
    rows = get_game_answers(db, gid)
    assert [r["question_id"] for r in rows] == ["q_gender_male", "q_in_anime_True"]
    finish_game(db, gid, guessed_entity_id="a", was_correct=False)
    save_correction(db, gid, "実は別人B")
    # finishing + correction must not raise; answers still retrievable
    assert len(get_game_answers(db, gid)) == 2
