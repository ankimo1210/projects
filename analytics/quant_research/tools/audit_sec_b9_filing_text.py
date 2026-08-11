"""Audit B9 primary-document retrieval coverage, integrity, and leakage."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from quant_textbook.sec_filing_text import audit_filing_retrieval, audit_normalized_filing_text


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON input must be an object: {path}")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--document-root", required=True, type=Path)
    parser.add_argument("--normalized-root", type=Path)
    parser.add_argument("--outer-time-cutoff", required=True, type=date.fromisoformat)
    parser.add_argument("--company-modulus", type=int, default=3)
    parser.add_argument("--company-remainder", type=int, default=0)
    parser.add_argument("--minimum-row-coverage", type=float, default=0.9)
    parser.add_argument("--require-gate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sidecar = _read_object(args.provenance)
    if sidecar.get("schema_version") != "b9-previous-filing-provenance-v1":
        raise ValueError("provenance sidecar has an unsupported schema")
    manifest = _read_object(args.document_root / "manifest.json")
    raw_result = audit_filing_retrieval(
        sidecar.get("rows", []),
        manifest,
        args.document_root,
        outer_time_cutoff=args.outer_time_cutoff,
        company_modulus=args.company_modulus,
        company_remainder=args.company_remainder,
        minimum_row_coverage=args.minimum_row_coverage,
    )
    normalized_result = None
    if args.normalized_root is not None:
        normalized_result = audit_normalized_filing_text(
            sidecar.get("rows", []),
            _read_object(args.normalized_root / "manifest.json"),
            args.normalized_root,
            retrieval_manifest=manifest,
            outer_time_cutoff=args.outer_time_cutoff,
            company_modulus=args.company_modulus,
            company_remainder=args.company_remainder,
            minimum_row_coverage=args.minimum_row_coverage,
        )
    gate_accepted = bool(
        raw_result.accepted and normalized_result is not None and normalized_result.accepted
    )
    print(
        json.dumps(
            {
                "raw": asdict(raw_result),
                "normalized": asdict(normalized_result) if normalized_result else None,
                "text_modeling_gate_accepted": gate_accepted,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if args.require_gate and not gate_accepted else 0


if __name__ == "__main__":
    raise SystemExit(main())
