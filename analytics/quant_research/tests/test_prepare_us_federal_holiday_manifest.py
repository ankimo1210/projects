from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
from types import ModuleType


def _load_tool() -> ModuleType:
    path = Path(__file__).parents[1] / "tools" / "prepare_us_federal_holiday_manifest.py"
    spec = importlib.util.spec_from_file_location("prepare_us_federal_holiday_manifest", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load holiday manifest tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_holiday_manifest_has_a_post_end_buffer_for_next_business_day(tmp_path: Path) -> None:
    module = _load_tool()
    output = tmp_path / "holidays.json"

    manifest = module.prepare_us_federal_holiday_manifest(
        start=date(2021, 12, 20),
        end=date(2021, 12, 31),
        output=output,
    )

    assert manifest["schema_version"] == "b9-us-federal-holidays-v1"
    assert manifest["requested_end"] == "2021-12-31"
    assert manifest["end"] == "2022-01-14"
    assert "2021-12-31" in manifest["holiday_dates"]
    assert manifest["holiday_dates"] == sorted(set(manifest["holiday_dates"]))
    assert json.loads(output.read_text(encoding="utf-8")) == manifest
