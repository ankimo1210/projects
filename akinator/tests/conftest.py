import pytest

from app.models import Entity, Question


@pytest.fixture
def small_pool():
    return [
        Entity("a", "アクターA", [], "俳優", None,
               {"is_fictional": False, "gender": "male", "occupation": ["actor"],
                "birth_century": 20, "is_dead": False}),
        Entity("b", "シンガーB", [], "歌手", None,
               {"is_fictional": False, "gender": "female", "occupation": ["singer"],
                "birth_century": 20, "is_dead": False}),
        Entity("c", "悟空", [], "キャラ", None,
               {"is_fictional": True, "gender": "male", "in_anime": True}),
        Entity("d", "セーラーD", [], "キャラ", None,
               {"is_fictional": True, "gender": "female", "in_anime": True}),
    ]


@pytest.fixture
def small_questions():
    return [
        Question("q_is_fictional_True", "架空のキャラクターですか？", "is_fictional", True, "equals"),
        Question("q_gender_male", "男性ですか？", "gender", "male", "equals"),
        Question("q_occupation_actor", "俳優ですか？", "occupation", "actor", "list_contains"),
        Question("q_in_anime_True", "アニメ作品に登場しますか？", "in_anime", True, "equals"),
    ]
