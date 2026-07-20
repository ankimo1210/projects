from __future__ import annotations

import json
import math
from pathlib import Path

from jhrmbs.util import atomic_write_json, read_json


def test_atomic_write_json_replaces_non_finite_numbers_with_null(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    atomic_write_json(
        path,
        {
            "nan": float("nan"),
            "positive_infinity": float("inf"),
            "nested": {"values": [1.5, float("-inf"), "text", None]},
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
    payload = json.loads(text)
    assert payload["nan"] is None
    assert payload["positive_infinity"] is None
    assert payload["nested"]["values"] == [1.5, None, "text", None]


def test_atomic_write_json_keeps_finite_payload_intact(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    payload = {"a": 1, "b": [1.25, "x"], "c": {"d": True, "e": None}}
    atomic_write_json(path, payload)
    assert read_json(path) == payload
    assert all(
        not isinstance(value, float) or math.isfinite(value)
        for value in json.loads(path.read_text(encoding="utf-8"))["b"]
        if value is not None
    )
