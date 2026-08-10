"""Recompute the Stage 2 Treasury and SEC feasibility findings from a raw cache.

The script is intentionally read-only.  It expects annual ``treasury_YYYY.xml``
files and the bounded SEC JSON responses described in the Stage 2 feasibility
follow-up note.  Large source files remain outside the repository; the output is
a compact, deterministic JSON audit that can be retained with a content hash.
"""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np

_ATOM = "http://www.w3.org/2005/Atom"
_METADATA = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
_CORE_TENORS = ("BC_3MONTH", "BC_2YEAR", "BC_5YEAR", "BC_10YEAR", "BC_30YEAR")
_TENOR_FIELDS = (
    "BC_20YEAR",
    "BC_1MONTH",
    "BC_2MONTH",
    "BC_4MONTH",
    "BC_1_5MONTH",
)
_SEC_FILES = (
    "sec_aapl_sub.json",
    "sec_aapl_facts.json",
    "sec_frame.json",
    "sec_frame_2017.json",
    "sec_tickers.json",
)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_treasury_rows(raw_dir: Path) -> tuple[list[dict[str, str | None]], dict[str, Any]]:
    paths = sorted(raw_dir.glob("treasury_*.xml"))
    if not paths:
        raise FileNotFoundError(f"no treasury_*.xml files found below {raw_dir}")
    rows: list[dict[str, str | None]] = []
    manifest_lines: list[str] = []
    namespaces = {"atom": _ATOM, "metadata": _METADATA}
    for path in paths:
        manifest_lines.append(f"{path.name}:{_digest(path)}")
        root = ET.parse(path).getroot()
        for entry in root.findall("atom:entry", namespaces):
            properties = entry.find(".//metadata:properties", namespaces)
            if properties is None:
                continue
            rows.append({element.tag.rsplit("}", 1)[-1]: element.text for element in properties})
    manifest_payload = "\n".join(manifest_lines) + "\n"
    provenance = {
        "annual_file_count": len(paths),
        "annual_manifest_sha256": sha256(manifest_payload.encode()).hexdigest(),
    }
    return rows, provenance


def _treasury_profile(raw_dir: Path) -> dict[str, Any]:
    rows, provenance = _load_treasury_rows(raw_dir)
    dated = sorted(rows, key=lambda row: str(row["NEW_DATE"]))
    first_seen = {
        field: min(str(row["NEW_DATE"])[:10] for row in dated if row.get(field) not in (None, ""))
        for field in _TENOR_FIELDS
    }
    valid_30y = [
        str(row["NEW_DATE"])[:10] for row in dated if row.get("BC_30YEAR") not in (None, "")
    ]
    gap_before = max(date for date in valid_30y if date < "2003-01-01")
    gap_after = min(date for date in valid_30y if date > "2006-01-01")
    phantom = [
        row
        for row in dated
        if all(row.get(field) in (None, "") for field in _CORE_TENORS)
        and row.get("BC_30YEARDISPLAY") not in (None, "")
    ]
    missing_3m_december_2008 = [
        str(row["NEW_DATE"])[:10]
        for row in dated
        if str(row["NEW_DATE"]).startswith("2008-12") and row.get("BC_3MONTH") in (None, "")
    ]
    complete = [
        row
        for row in dated
        if str(row["NEW_DATE"])[:10] >= "2007-01-01"
        and all(row.get(field) not in (None, "") for field in _CORE_TENORS)
    ]
    dates = np.asarray([str(row["NEW_DATE"])[:10] for row in complete])
    ten_year = np.asarray([float(row["BC_10YEAR"]) for row in complete])
    previous = ten_year[:-1]
    target = ten_year[1:]
    target_dates = dates[1:]
    split = int(0.7 * target.size)
    train_design = np.column_stack([np.ones(split), previous[:split]])
    coefficients = np.linalg.lstsq(train_design, target[:split], rcond=None)[0]
    ar_prediction = coefficients[0] + coefficients[1] * previous[split:]
    no_change_prediction = previous[split:]
    no_change_rmse = math.sqrt(
        float(np.mean((100.0 * (target[split:] - no_change_prediction)) ** 2))
    )
    ar_rmse = math.sqrt(float(np.mean((100.0 * (target[split:] - ar_prediction)) ** 2)))
    return {
        **provenance,
        "entry_count": len(dated),
        "start_date": str(dated[0]["NEW_DATE"])[:10],
        "end_date": str(dated[-1]["NEW_DATE"])[:10],
        "tenor_first_seen": first_seen,
        "thirty_year_gap": {"last_before_gap": gap_before, "first_after_gap": gap_after},
        "display_only_phantom_dates": [str(row["NEW_DATE"])[:10] for row in phantom],
        "missing_3m_december_2008": missing_3m_december_2008,
        "complete_core_panel": {
            "row_count": len(complete),
            "start_date": dates[0],
            "end_date": dates[-1],
        },
        "baseline": {
            "test_rows": int(target.size - split),
            "test_start": target_dates[split],
            "test_end": target_dates[-1],
            "no_change_rmse_bp": no_change_rmse,
            "ar1_rmse_bp": ar_rmse,
            "ar1_relative_rmse_change_percent": 100.0 * (ar_rmse / no_change_rmse - 1.0),
        },
    }


def _sec_profile(raw_dir: Path) -> dict[str, Any]:
    missing = [name for name in _SEC_FILES if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing SEC feasibility files: {missing}")
    submissions = json.loads((raw_dir / "sec_aapl_sub.json").read_text(encoding="utf-8"))
    recent = submissions["filings"]["recent"]
    recent_count = len(recent["filingDate"])
    date_mismatches = sum(
        accepted[:10] != filed
        for accepted, filed in zip(recent["acceptanceDateTime"], recent["filingDate"], strict=True)
    )
    facts = json.loads((raw_dir / "sec_aapl_facts.json").read_text(encoding="utf-8"))["facts"][
        "us-gaap"
    ]
    grouped: defaultdict[tuple[str, str, str | None, str | None], list[Any]] = defaultdict(list)
    fact_count = 0
    concept_unit_series = 0
    for concept, metadata in facts.items():
        for unit, items in metadata.get("units", {}).items():
            concept_unit_series += 1
            for item in items:
                fact_count += 1
                grouped[(concept, unit, item.get("start"), item.get("end"))].append(item.get("val"))
    repeated = sum(len(values) >= 2 for values in grouped.values())
    changed = sum(len(set(values)) >= 2 for values in grouped.values())
    assets_frame = json.loads((raw_dir / "sec_frame.json").read_text(encoding="utf-8"))
    payable_frame = json.loads((raw_dir / "sec_frame_2017.json").read_text(encoding="utf-8"))
    apple_payable = [row for row in payable_frame["data"] if row.get("cik") == 320193]
    return {
        "source_sha256": {name: _digest(raw_dir / name) for name in _SEC_FILES},
        "submissions": {
            "recent_count": recent_count,
            "acceptance_filing_date_mismatches": date_mismatches,
            "mismatch_rate": date_mismatches / recent_count,
            "older_history_files": submissions["filings"]["files"],
        },
        "companyfacts": {
            "us_gaap_concepts": len(facts),
            "concept_unit_series": concept_unit_series,
            "fact_count": fact_count,
            "period_groups": len(grouped),
            "repeated_period_groups": repeated,
            "value_changed_period_groups": changed,
            "value_changed_rate": changed / len(grouped),
        },
        "frames": {
            "assets_cy2023q4i_entities": len(assets_frame["data"]),
            "aapl_accounts_payable_cy2017q3i": apple_payable,
        },
        "gate_status": {
            "access": "pass",
            "semantics": "pass_with_open_availability_contract",
            "sample": "pass",
            "baseline": "incomplete",
            "teaching_fit": "pass",
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path, help="directory containing bounded raw responses")
    parser.add_argument("--json-output", type=Path, help="optional path for the compact audit JSON")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    raw_dir = args.raw_dir.expanduser().resolve()
    if not raw_dir.is_dir():
        raise SystemExit(f"raw_dir is not a directory: {raw_dir}")
    report = {
        "treasury": _treasury_profile(raw_dir),
        "sec": _sec_profile(raw_dir),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
