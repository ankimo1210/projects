"""Serialize/deserialize entities and questions to/from JSON on disk."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.models import Entity, Question


def dump_entities(entities: list[Entity], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(e) for e in entities]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_entities(path: Path) -> list[Entity]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Entity(**d) for d in data]


def dump_questions(questions: list[Question], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(q) for q in questions]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_questions(path: Path) -> list[Question]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Question(**d) for d in data]
