"""Auto-generate questions from the attribute values present across entities.

For each (feature_key, value) pair, count how many entities match. Keep only
values that are discriminative — present in a fraction of the pool between
min_fraction and max_fraction (neither ~all nor ~none). Question text is
composed from Japanese label templates, NOT hand-written per entity."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models import Entity, Question

# Feature handling: which match_type and how to enumerate values.
_LIST_FEATURES = {"occupation", "country", "notable_work"}
_BOOL_FEATURES = {"is_fictional", "is_dead", "in_anime"}
_SCALAR_FEATURES = {"gender", "birth_century", "species"}

# Japanese templates. {v} is the value label.
_VALUE_LABELS = {
    ("gender", "male"): "男性", ("gender", "female"): "女性",
    ("occupation", "actor"): "俳優", ("occupation", "singer"): "歌手",
    ("occupation", "physicist"): "物理学者", ("occupation", "politician"): "政治家",
    ("occupation", "writer"): "作家", ("occupation", "athlete"): "スポーツ選手",
    ("occupation", "musician"): "音楽家", ("occupation", "painter"): "画家",
    ("occupation", "mathematician"): "数学者", ("occupation", "film_director"): "映画監督",
    ("country", "Japan"): "日本", ("country", "United States"): "アメリカ",
    ("country", "Germany"): "ドイツ", ("country", "United Kingdom"): "イギリス",
    ("country", "France"): "フランス", ("country", "Italy"): "イタリア",
    ("country", "China"): "中国", ("country", "Russia"): "ロシア",
}


def _label(feature_key: str, value: Any) -> str:
    return _VALUE_LABELS.get((feature_key, value), str(value))


def _question_text(feature_key: str, value: Any) -> str:
    if feature_key == "is_fictional":
        return "架空のキャラクターですか？" if value else "実在する人物ですか？"
    if feature_key == "is_dead":
        return "すでに亡くなっていますか？" if value else "存命ですか？"
    if feature_key == "in_anime":
        return "アニメ作品に登場しますか？"
    if feature_key == "gender":
        return f"{_label(feature_key, value)}ですか？"
    if feature_key == "occupation":
        return f"{_label(feature_key, value)}ですか？"
    if feature_key == "country":
        return f"{_label(feature_key, value)}と関係がありますか？"
    if feature_key == "birth_century":
        return f"{value}世紀生まれですか？"
    if feature_key == "species":
        return f"{value}ですか？"
    return f"{feature_key} は {value} ですか？"


def _match_type(feature_key: str) -> str:
    if feature_key in _LIST_FEATURES:
        return "list_contains"
    if feature_key == "birth_century":
        return "numeric"
    return "equals"


def _question_id(feature_key: str, value: Any) -> str:
    return f"q_{feature_key}_{value}"


def generate_questions(
    entities: list[Entity], min_fraction: float = 0.05, max_fraction: float = 0.95
) -> list[Question]:
    n = len(entities)
    if n == 0:
        return []
    # count entities matching each (feature_key, value)
    counts: dict[tuple[str, Any], int] = defaultdict(int)
    considered = _LIST_FEATURES | _BOOL_FEATURES | _SCALAR_FEATURES
    for e in entities:
        for key in considered:
            if key not in e.features:
                continue
            val = e.features[key]
            if key in _LIST_FEATURES:
                for item in val:
                    counts[(key, item)] += 1
            else:
                counts[(key, val)] += 1

    questions: list[Question] = []
    for (key, val), c in sorted(counts.items(), key=lambda kv: str(kv[0])):
        frac = c / n
        if frac < min_fraction or frac > max_fraction:
            continue
        questions.append(
            Question(
                id=_question_id(key, val),
                text=_question_text(key, val),
                feature_key=key,
                expected_value=val,
                match_type=_match_type(key),
            )
        )
    return questions
