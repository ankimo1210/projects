"""CLI: build processed entities.json + questions.json from the raw Wikidata dump.

The pure logic lives in `app.build.build_from_raw` (unit-tested). This wrapper
just wires the default data/raw -> data/processed paths."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.build import build_from_raw  # noqa: E402


def main() -> None:
    raw_path = config.RAW_DIR / "wikidata_entities.json"
    n_ent, n_q = build_from_raw(raw_path, config.ENTITIES_PATH, config.QUESTIONS_PATH)
    print(f"wrote {n_ent} entities, {n_q} questions")


if __name__ == "__main__":
    main()
