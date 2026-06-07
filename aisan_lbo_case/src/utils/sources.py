from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"


def now_jst_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_yaml(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def write_json(path: Path | str, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_sources() -> dict[str, dict[str, Any]]:
    raw = load_yaml(CONFIG_DIR / "sources.yaml")
    return raw.get("sources", {})


def source_rows(extra_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    retrieved_at = now_jst_iso()
    rows: list[dict[str, Any]] = []
    for source_id, source in load_sources().items():
        rows.append(
            {
                "source_id": source_id,
                "title": source.get("title", ""),
                "publisher": source.get("publisher", ""),
                "url": source.get("url", ""),
                "source_type": source.get("source_type", ""),
                "retrieved_at": retrieved_at,
                "local_path": source.get("local_path", ""),
                "notes": source.get("notes", ""),
            }
        )
    if extra_rows:
        rows.extend(extra_rows)
    return rows


def write_sources_bibliography(
    path: Path | str = OUTPUT_DIR / "sources_bibliography.csv",
    extra_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = source_rows(extra_rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "title",
        "publisher",
        "url",
        "source_type",
        "retrieved_at",
        "local_path",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def source_url(source_id: str) -> str:
    return load_sources().get(source_id, {}).get("url", "")
