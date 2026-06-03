import json
from pathlib import Path

from app.build import build_from_raw
from app.data_loader import load_entities, load_questions


def test_build_from_raw_writes_processed(tmp_path):
    raw = [
        {"id": "Q1", "name_ja": "俳優A", "name_en": "ActorA", "aliases": [],
         "description": "d", "image_url": None, "instance_of": ["Q5"],
         "gender": "Q6581097", "occupations": ["Q33999"], "countries": ["Q17"],
         "birth_year": 1970, "death_year": None, "in_anime": False},
        {"id": "Q2", "name_ja": "歌手B", "name_en": "SingerB", "aliases": [],
         "description": "d", "image_url": None, "instance_of": ["Q5"],
         "gender": "Q6581072", "occupations": ["Q177220"], "countries": ["Q30"],
         "birth_year": 1985, "death_year": None, "in_anime": False},
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    ent_path = tmp_path / "entities.json"
    q_path = tmp_path / "questions.json"

    build_from_raw(raw_path, ent_path, q_path, min_fraction=0.1, max_fraction=0.95)

    entities = load_entities(ent_path)
    questions = load_questions(q_path)
    assert {e.id for e in entities} == {"Q1", "Q2"}
    assert len(questions) > 0
    # gender splits 1/1 -> a gender question should exist
    assert any(q.feature_key == "gender" for q in questions)
