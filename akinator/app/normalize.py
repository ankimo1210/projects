"""Convert one raw Wikidata binding dict into a normalized Entity.

Raw QIDs/years are mapped to question-ready feature values. Missing inputs are
omitted from `features` entirely (so downstream `has_feature` is False) rather
than stored as None — except booleans we can determine with confidence."""
from __future__ import annotations

from typing import Any

from app.models import Entity

# Minimal QID lookup tables. Extend as the fetch query grows.
_GENDER = {"Q6581097": "male", "Q6581072": "female"}
# instance-of QIDs that mean "fictional"
_FICTIONAL_INSTANCE = {"Q15632617", "Q95074", "Q15773347", "Q20085850"}
# occupation QID -> english slug used in questions
_OCCUPATION = {
    "Q169470": "physicist",
    "Q33999": "actor",
    "Q177220": "singer",
    "Q82955": "politician",
    "Q36180": "writer",
    "Q937857": "athlete",
    "Q639669": "musician",
    "Q1028181": "painter",
    "Q170790": "mathematician",
    "Q2526255": "film_director",
}
_COUNTRY = {
    "Q17": "Japan", "Q183": "Germany", "Q30": "United States",
    "Q145": "United Kingdom", "Q142": "France", "Q38": "Italy",
    "Q148": "China", "Q159": "Russia",
}


def _century(year: int | None) -> int | None:
    if year is None:
        return None
    return (year - 1) // 100 + 1


def _map_list(qids: list[str], table: dict[str, str]) -> list[str]:
    return [table[q] for q in qids if q in table]


def normalize_binding(raw: dict[str, Any]) -> Entity:
    name = raw.get("name_ja") or raw.get("name_en") or raw["id"]

    is_fictional = any(q in _FICTIONAL_INSTANCE for q in raw.get("instance_of", []))

    features: dict[str, Any] = {"is_fictional": is_fictional}

    gender = _GENDER.get(raw.get("gender"))
    if gender is not None:
        features["gender"] = gender

    occupations = _map_list(raw.get("occupations", []), _OCCUPATION)
    if occupations:
        features["occupation"] = occupations

    countries = _map_list(raw.get("countries", []), _COUNTRY)
    if countries:
        features["country"] = countries

    century = _century(raw.get("birth_year"))
    if century is not None:
        features["birth_century"] = century

    # is_dead: real person with a death year is dead; real person with a birth
    # year and no death year we treat as alive. Fictional: leave unknown.
    if not is_fictional and raw.get("birth_year") is not None:
        features["is_dead"] = raw.get("death_year") is not None

    if raw.get("in_anime") is not None:
        features["in_anime"] = bool(raw.get("in_anime"))

    aliases = [a for a in raw.get("aliases", []) if a]
    if raw.get("name_en") and raw.get("name_en") != name:
        aliases = [raw["name_en"], *aliases]

    return Entity(
        id=raw["id"],
        name=name,
        aliases=aliases,
        description=raw.get("description") or "",
        image_url=raw.get("image_url"),
        features=features,
    )
