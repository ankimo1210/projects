from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from types import ModuleType


def _load_tool() -> ModuleType:
    path = Path(__file__).parents[1] / "tools" / "prepare_sec_b9_seed_cohort.py"
    spec = importlib.util.spec_from_file_location("prepare_sec_b9_seed_cohort", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load B9 seed cohort tool")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _master_index() -> str:
    return """Description: Master Index of EDGAR Dissemination Feed
CIK|Company Name|Form Type|Date Filed|Filename
--------------------------------------------------------------------------------
0000000005|Epsilon Inc|10-K|2016-02-10|edgar/data/5/a.txt
0000000001|Alpha Inc|10-K|2016-01-15|edgar/data/1/a.txt
0000000002|Beta Inc|10-K/A|2016-02-01|edgar/data/2/a.txt
0000000003|Gamma Inc|10-K|2016-03-31|edgar/data/3/a.txt
0000000001|Alpha Inc|10-K|2016-03-01|edgar/data/1/b.txt
0000000004|Delta Inc|8-K|2016-03-10|edgar/data/4/a.txt
0000000006|Zeta Inc|10-K|2016-04-01|edgar/data/6/a.txt
"""


def test_parse_and_sample_historical_master_index() -> None:
    module = _load_tool()
    records = module.parse_master_index(
        _master_index(),
        filed_start=date(2016, 1, 1),
        filed_end=date(2016, 3, 31),
    )
    assert [record.cik for record in records] == [
        "0000000001",
        "0000000001",
        "0000000003",
        "0000000005",
    ]
    unique = module.unique_cik_records(records)
    assert [record.cik for record in unique] == ["0000000001", "0000000003", "0000000005"]
    sampled = module.evenly_spaced_cik_sample(records, limit=2)
    assert [record.cik for record in sampled] == ["0000000001", "0000000005"]


def test_prepare_seed_cohort_reuses_local_master_index(tmp_path: Path) -> None:
    module = _load_tool()
    raw = tmp_path / "raw" / "master.idx"
    raw.parent.mkdir()
    raw.write_text(_master_index(), encoding="latin-1")
    cik_output = tmp_path / "derived" / "ciks.txt"
    manifest_output = tmp_path / "derived" / "seed_manifest.json"

    manifest = module.prepare_seed_cohort(
        master_index_path=raw,
        cik_output=cik_output,
        manifest_output=manifest_output,
        user_agent="quant-textbook test test@example.com",
        limit=2,
    )

    assert manifest["source"] == "cache"
    assert manifest["raw_10k_record_count"] == 4
    assert manifest["unique_cik_count"] == 3
    assert manifest["selected_cik_count"] == 2
    assert manifest["selected_cik_sha256"] == module.canonical_cik_sha256(
        ["0000000001", "0000000005"]
    )
    assert cik_output.read_text(encoding="utf-8").splitlines()[-2:] == [
        "0000000001",
        "0000000005",
    ]
    persisted = json.loads(manifest_output.read_text(encoding="utf-8"))
    assert persisted["selection_method"] == "evenly_spaced_cik_rank"
    assert [record["cik"] for record in persisted["selected_records"]] == [
        "0000000001",
        "0000000005",
    ]
