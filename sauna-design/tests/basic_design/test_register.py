import csv
import json
from pathlib import Path


def test_requirement_source_ids_are_resolvable():
    root = Path(__file__).resolve().parents[2]
    sources = json.loads((root / "plan/basic_design/sources.json").read_text())
    known = {r["id"] for r in sources}
    rules = list(csv.DictReader((root / "plan/basic_design/rules.csv").open(encoding="utf-8-sig")))
    assert not {r["source_id"] for r in rules} - known
