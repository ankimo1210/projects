from app.normalize import normalize_binding
from app.models import Entity


def _raw_einstein():
    return {
        "id": "Q937",
        "name_ja": "アルベルト・アインシュタイン",
        "name_en": "Albert Einstein",
        "aliases": ["Einstein"],
        "description": "理論物理学者",
        "image_url": "http://commons/einstein.jpg",
        "instance_of": ["Q5"],            # human
        "gender": "Q6581097",             # male
        "occupations": ["Q169470"],       # physicist
        "countries": ["Q183", "Q30"],     # Germany, United States
        "birth_year": 1879,
        "death_year": 1955,
        "in_anime": False,
    }


def test_normalize_real_person():
    e = normalize_binding(_raw_einstein())
    assert isinstance(e, Entity)
    assert e.id == "Q937"
    assert e.name == "アルベルト・アインシュタイン"
    assert "Albert Einstein" in e.aliases
    assert e.features["is_fictional"] is False
    assert e.features["gender"] == "male"
    assert "physicist" in e.features["occupation"]
    assert e.features["birth_century"] == 19   # 1879 -> 19th century
    assert e.features["is_dead"] is True
    assert e.features["in_anime"] is False


def test_normalize_fictional_uses_en_name_when_ja_missing():
    raw = {
        "id": "Q3010",
        "name_ja": None,
        "name_en": "Goku",
        "aliases": [],
        "description": "fictional character",
        "image_url": None,
        "instance_of": ["Q15632617"],   # fictional human
        "gender": "Q6581097",
        "occupations": [],
        "countries": [],
        "birth_year": None,
        "death_year": None,
        "in_anime": True,
    }
    e = normalize_binding(raw)
    assert e.name == "Goku"
    assert e.features["is_fictional"] is True
    assert e.features["in_anime"] is True
    assert "birth_century" not in e.features   # missing stays missing
    assert "is_dead" not in e.features          # fictional death status is unknown, left unset
