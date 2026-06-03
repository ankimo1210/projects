"""Holds the loaded entity/question collections and id lookups. Constructed once
from JSON at app startup (see main.py) or directly in tests."""
from __future__ import annotations

from app.config import ENTITIES_PATH, QUESTIONS_PATH
from app.data_loader import load_entities, load_questions
from app.models import Entity, Question


class EntityService:
    def __init__(self, entities: list[Entity], questions: list[Question]) -> None:
        self.entities = entities
        self.questions = questions
        self._by_id = {e.id: e for e in entities}

    @classmethod
    def from_disk(cls) -> "EntityService":
        return cls(load_entities(ENTITIES_PATH), load_questions(QUESTIONS_PATH))

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._by_id.get(entity_id)
