from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

from .utils import ROOT

COMMANDS: list[tuple[str, str, str]] = [
    (r"\bcompare\b|比較しなさい", "compare", "comparison"),
    (r"\bexplain\b|理由を説明しなさい|説明しなさい", "explain", "causal_reasoning"),
    (r"\bdescribe\b|述べなさい", "describe", "description"),
    (r"\bidentify\b|\bstate\b|挙げなさい", "identify", "recall"),
    (r"\bdefine\b", "define", "recall"),
    (r"\bwhich of the following\b|次のうち|\bselect\b", "select", "recognition"),
    (r"\bdiscuss\b", "discuss", "evaluation"),
]

TOPICS: list[tuple[str, tuple[str, ...]]] = [
    ("sparkling_wines", ("sparkling", "champagne", "cava", "prosecco", "発泡", "スパークリング")),
    ("fortified_wines", ("fortified", "sherry", "port", "madeira", "酒精強化")),
    ("grape_growing", ("vineyard", "vine", "canopy", "yield", "ブドウ畑", "樹冠", "収量")),
    (
        "winemaking",
        ("fermentation", "pressing", "maceration", "winemaking", "発酵", "醸造", "圧搾"),
    ),
    ("maturation", ("maturation", "oak", "lees", "熟成", "樽", "澱")),
    ("tasting", ("tasting", "acidity", "tannin", "aroma", "テイスティング", "酸度", "タンニン")),
    ("laws_and_regulations", ("law", "regulation", "classification", "法律", "規制", "格付け")),
    ("business_and_price", ("price", "cost", "market", "価格", "コスト", "市場")),
    ("service", ("service", "serve", "serving", "サービス", "供出")),
    ("storage", ("storage", "store", "保管", "保存")),
]

GEOGRAPHY = [
    "France", "Italy", "Spain", "Portugal", "Germany", "Austria", "Hungary", "Greece",
    "United States", "Canada", "Chile", "Argentina", "South Africa", "Australia", "New Zealand",
    "Bordeaux", "Burgundy", "Champagne", "Loire", "Rhône", "Rioja", "Mosel", "Napa Valley",
    "Mendoza", "Marlborough", "フランス", "イタリア", "スペイン", "ドイツ", "オーストラリア",
]

GRAPES = [
    "Cabernet Sauvignon", "Merlot", "Pinot Noir", "Syrah", "Chardonnay", "Sauvignon Blanc",
    "Riesling", "Nebbiolo", "Sangiovese", "Tempranillo", "Garnacha", "Chenin Blanc",
]


class Classification(TypedDict):
    question_format: str
    command_verb: str | None
    cognitive_skill: str
    topic_primary: str
    geography: list[str]
    grape_varieties: list[str]


def load_taxonomy(path: Path | None = None) -> dict[str, Any]:
    target = path or ROOT / "config" / "taxonomy.yaml"
    payload: dict[str, Any] = yaml.safe_load(target.read_text(encoding="utf-8"))
    return payload


def classify(text: str) -> Classification:
    lowered = text.casefold()
    command_verb: str | None = None
    cognitive_skill = "recall"
    for expression, command, skill in COMMANDS:
        if re.search(expression, lowered, re.IGNORECASE):
            command_verb, cognitive_skill = command, skill
            break

    if re.search(r"\b[a-d][.)]\s", lowered) or command_verb == "select":
        question_format = "multiple_choice"
    elif command_verb == "compare":
        question_format = "comparison"
    elif command_verb == "explain":
        question_format = "causal_explanation"
    elif re.search(r"process|method|steps?|工程|製法", lowered):
        question_format = "process_description"
    else:
        question_format = "short_written_answer"

    topic = next(
        (
            name
            for name, keywords in TOPICS
            if any(keyword.casefold() in lowered for keyword in keywords)
        ),
        "still_wines",
    )
    geography = [item for item in GEOGRAPHY if item.casefold() in lowered]
    grapes = [item for item in GRAPES if item.casefold() in lowered]
    return {
        "question_format": question_format,
        "command_verb": command_verb,
        "cognitive_skill": cognitive_skill,
        "topic_primary": topic,
        "geography": geography,
        "grape_varieties": grapes,
    }


def validate_labels(
    record: Classification, taxonomy: dict[str, Any] | None = None
) -> None:
    values = taxonomy or load_taxonomy()
    formats = cast(list[str], values["question_formats"])
    skills = cast(list[str], values["cognitive_skills"])
    topics = cast(list[str], values["content_areas"])
    if record.get("question_format") not in formats:
        raise ValueError(f"invalid question format: {record.get('question_format')}")
    if record.get("cognitive_skill") not in skills:
        raise ValueError(f"invalid cognitive skill: {record.get('cognitive_skill')}")
    if record.get("topic_primary") not in topics:
        raise ValueError(f"invalid topic: {record.get('topic_primary')}")
