"""Core data shapes for akinator. Dataclasses + enum only — no logic beyond
trivial feature access."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Answer(str, Enum):
    YES = "yes"
    NO = "no"
    PROBABLY_YES = "probably_yes"
    PROBABLY_NO = "probably_no"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    id: str
    name: str
    aliases: list[str]
    description: str
    image_url: str | None
    features: dict[str, Any] = field(default_factory=dict)

    def feature(self, key: str) -> Any:
        return self.features.get(key)

    def has_feature(self, key: str) -> bool:
        return key in self.features and self.features[key] not in (None, [], "")


@dataclass
class Question:
    id: str
    text: str
    feature_key: str
    expected_value: Any
    match_type: str  # "equals" | "list_contains" | "numeric"
