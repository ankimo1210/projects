"""Pure build step: raw Wikidata dump -> processed entities.json + questions.json.

Lives in the package (not scripts/) so it is importable via the installed
`app` package regardless of pytest import mode. `scripts/build_questions.py` is
a thin CLI wrapper around `build_from_raw`."""
from __future__ import annotations

import json
from pathlib import Path

from app.data_loader import dump_entities, dump_questions
from app.normalize import normalize_binding
from app.question_gen import generate_questions


def build_from_raw(
    raw_path: Path,
    entities_path: Path,
    questions_path: Path,
    min_fraction: float = 0.05,
    max_fraction: float = 0.95,
) -> tuple[int, int]:
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    entities = [normalize_binding(r) for r in raw]
    questions = generate_questions(entities, min_fraction, max_fraction)
    dump_entities(entities, entities_path)
    dump_questions(questions, questions_path)
    return len(entities), len(questions)
