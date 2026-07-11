"""Small I/O helpers shared across the lab (JSON, JSONL, paths, hashing)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    """Root of the jp_llm_lab repository (…/jp_llm_lab).

    Resolved from this file's location: src/jp_llm_lab/utils/io.py → parents[3].
    Works because the package is installed editable (source stays in place).
    """
    return Path(__file__).resolve().parents[3]


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(obj: Any, path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return p


def load_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_jsonl(obj: dict, path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path | str) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
