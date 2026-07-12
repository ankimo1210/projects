from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def stable_id(*parts: object, prefix: str = "") -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:20]
    return f"{prefix}{digest}"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
