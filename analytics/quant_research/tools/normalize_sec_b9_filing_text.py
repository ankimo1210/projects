"""Extract deterministic visible text from hash-verified B9 filing documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_textbook.sec_filing_text import normalize_retrieved_documents


def _read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("retrieval manifest must be a JSON object")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document-root", required=True, type=Path)
    parser.add_argument("--normalized-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest = normalize_retrieved_documents(
        _read_manifest(args.document_root / "manifest.json"),
        args.document_root,
        args.normalized_root,
    )
    print(
        json.dumps(
            {
                "normalized_root": str(args.normalized_root.expanduser().resolve()),
                "document_count": manifest["document_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
