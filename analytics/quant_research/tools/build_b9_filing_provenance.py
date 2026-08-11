"""Build a row-preserving previous-filing sidecar for the locked B9 M6 panel."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from quant_textbook.sec_filing_text import build_previous_filing_sidecar


def _read_object(path: Path, *, label: str) -> tuple[bytes, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    payload = resolved.read_bytes()
    decoded = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload, decoded


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(f".{resolved.name}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(resolved)
    finally:
        temporary.unlink(missing_ok=True)


def build_artifact(
    panel_artifact: Path,
    cache_root: Path,
    holiday_manifest: Path,
    preanalysis_contract: Path,
) -> dict[str, Any]:
    panel_bytes, panel = _read_object(panel_artifact, label="panel artifact")
    if panel.get("schema_version") != "b9-sec-panel-v1":
        raise ValueError("panel artifact has an unsupported schema")
    contract_bytes, contract = _read_object(preanalysis_contract, label="pre-analysis contract")
    if contract.get("schema_version") != "b9-preanalysis-v1":
        raise ValueError("pre-analysis contract has an unsupported schema")
    expected_sha = contract.get("parent_data", {}).get("derived_panel_sha256")
    panel_sha = sha256(panel_bytes).hexdigest()
    if panel_sha != expected_sha:
        raise ValueError("panel artifact SHA-256 differs from the pre-analysis contract")
    rows = panel.get("panel", {}).get("rows")
    if not isinstance(rows, list):
        raise ValueError("panel artifact lacks panel.rows")
    if len(rows) != contract.get("parent_data", {}).get("expected_panel_rows"):
        raise ValueError("panel row count differs from the pre-analysis contract")

    holiday_bytes, holiday = _read_object(holiday_manifest, label="holiday manifest")
    if holiday.get("schema_version") != "b9-us-federal-holidays-v1":
        raise ValueError("holiday manifest has an unsupported schema")
    raw_dates = holiday.get("holiday_dates")
    if not isinstance(raw_dates, list):
        raise ValueError("holiday manifest lacks holiday_dates")
    holiday_dates = tuple(date.fromisoformat(str(value)) for value in raw_dates)

    sidecar = build_previous_filing_sidecar(
        rows,
        cache_root,
        holiday_dates=holiday_dates,
    )
    if not sidecar.quality.accepted:
        raise ValueError(f"filing provenance sidecar failed: {asdict(sidecar.quality)}")
    return {
        "schema_version": "b9-previous-filing-provenance-v1",
        "network_access": False,
        "input_provenance": {
            "panel_artifact": {
                "path": str(panel_artifact.expanduser().resolve()),
                "sha256": panel_sha,
            },
            "holiday_manifest": {
                "path": str(holiday_manifest.expanduser().resolve()),
                "sha256": sha256(holiday_bytes).hexdigest(),
            },
            "preanalysis_contract": {
                "path": str(preanalysis_contract.expanduser().resolve()),
                "sha256": sha256(contract_bytes).hexdigest(),
            },
        },
        "quality": asdict(sidecar.quality),
        "rows": list(sidecar.rows),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-artifact", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--holiday-manifest", required=True, type=Path)
    parser.add_argument("--preanalysis-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    artifact = build_artifact(
        args.panel_artifact,
        args.cache_root,
        args.holiday_manifest,
        args.preanalysis_contract,
    )
    _atomic_json(args.output, artifact)
    print(
        json.dumps(
            {
                "output": str(args.output.expanduser().resolve()),
                "rows": artifact["quality"]["sidecar_row_count"],
                "unique_documents": artifact["quality"]["unique_previous_document_count"],
                "accepted": artifact["quality"]["accepted"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
