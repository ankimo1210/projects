"""Prepare a historical, deterministic SEC seed cohort for B9 M6.

The seed universe is the set of unique ``10-K`` filers in the static 2016 Q1
EDGAR full master index.  It is historical rather than a present-day index,
so the seed list itself does not introduce current-constituent survivorship.
The downstream fixed-anchor Assets rule remains the actual eligibility rule.

This tool writes only to caller-supplied paths.  The raw master index, CIK
list, and manifest should remain outside the repository with the SEC raw
cache.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_MASTER_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/2016/QTR1/master.idx"
_MASTER_COLUMNS = ("cik", "company_name", "form", "filing_date", "filename")
_SEPARATOR = re.compile(r"^-{10,}")


@dataclass(frozen=True)
class MasterIndexRecord:
    """One normalized 2016 Q1 EDGAR master-index record."""

    cik: str
    company_name: str
    form: str
    filing_date: date
    filename: str


def _parse_iso_date(value: str, *, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be YYYY-MM-DD") from error


def _validate_user_agent(value: str) -> str:
    user_agent = value.strip()
    if len(user_agent) < 12 or "@" not in user_agent:
        raise ValueError("user-agent must include a descriptive name and contact email")
    return user_agent


def _normalize_cik(value: str) -> str:
    digits = value.strip().lstrip("0") or "0"
    if not digits.isdigit() or not 1 <= int(digits) <= 9_999_999_999:
        raise ValueError(f"invalid CIK in master index: {value!r}")
    return digits.zfill(10)


def canonical_cik_sha256(ciks: Iterable[str]) -> str:
    """Hash a CIK cohort independently of a human-readable list header."""

    normalized = tuple(sorted({_normalize_cik(cik) for cik in ciks}))
    if not normalized:
        raise ValueError("at least one CIK is required for a cohort digest")
    payload = ("\n".join(normalized) + "\n").encode("ascii")
    return sha256(payload).hexdigest()


def parse_master_index(
    text: str,
    *,
    filed_start: date,
    filed_end: date,
    forms: Iterable[str] = ("10-K",),
) -> tuple[MasterIndexRecord, ...]:
    """Parse and filter the pipe-delimited static EDGAR master index."""

    if filed_start > filed_end:
        raise ValueError("filed_start must be on or before filed_end")
    allowed_forms = frozenset(forms)
    rows: list[MasterIndexRecord] = []
    found_separator = False
    for raw_line in text.splitlines():
        if not found_separator:
            found_separator = bool(_SEPARATOR.match(raw_line))
            continue
        if not raw_line.strip():
            continue
        fields = raw_line.split("|")
        if len(fields) != len(_MASTER_COLUMNS):
            raise ValueError(f"master index row has {len(fields)} fields, expected 5: {raw_line!r}")
        cik, company_name, form, filed, filename = (field.strip() for field in fields)
        filing_date = _parse_iso_date(filed, name="master-index filing date")
        if form not in allowed_forms or not filed_start <= filing_date <= filed_end:
            continue
        if not company_name or not filename:
            raise ValueError("master index row has an empty company name or filename")
        rows.append(
            MasterIndexRecord(
                cik=_normalize_cik(cik),
                company_name=company_name,
                form=form,
                filing_date=filing_date,
                filename=filename,
            )
        )
    if not found_separator:
        raise ValueError("master index separator was not found")
    return tuple(sorted(rows, key=lambda row: (row.cik, row.filing_date, row.filename)))


def unique_cik_records(records: Iterable[MasterIndexRecord]) -> tuple[MasterIndexRecord, ...]:
    """Keep the first index record per CIK under a stable historical order."""

    result: dict[str, MasterIndexRecord] = {}
    for record in sorted(records, key=lambda row: (row.cik, row.filing_date, row.filename)):
        result.setdefault(record.cik, record)
    return tuple(result[cik] for cik in sorted(result))


def evenly_spaced_cik_sample(
    records: Iterable[MasterIndexRecord], *, limit: int
) -> tuple[MasterIndexRecord, ...]:
    """Select a deterministic, evenly spaced CIK-rank feasibility sample."""

    candidates = unique_cik_records(records)
    if limit < 1:
        raise ValueError("limit must be positive")
    if len(candidates) <= limit:
        return candidates
    if limit == 1:
        return (candidates[0],)
    indexes = tuple((position * (len(candidates) - 1)) // (limit - 1) for position in range(limit))
    if len(set(indexes)) != limit:
        raise AssertionError("evenly spaced sample indexes must be unique")
    return tuple(candidates[index] for index in indexes)


def _download_master_index(*, url: str, user_agent: str, timeout_seconds: float) -> bytes:
    if timeout_seconds <= 0.0:
        raise ValueError("timeout_seconds must be positive")
    request = Request(
        url,
        headers={
            "Accept": "text/plain",
            "Accept-Encoding": "gzip",
            "User-Agent": _validate_user_agent(user_agent),
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            payload = gzip.decompress(payload)
    return payload


def _write_bytes(path: Path, payload: bytes) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _load_or_download_master_index(
    path: Path,
    *,
    url: str,
    user_agent: str,
    timeout_seconds: float,
    refresh: bool,
) -> tuple[bytes, str]:
    path = path.expanduser().resolve()
    if path.exists() and not refresh:
        return path.read_bytes(), "cache"
    payload = _download_master_index(
        url=url,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
    )
    _write_bytes(path, payload)
    return payload, "network"


def prepare_seed_cohort(
    *,
    master_index_path: Path,
    cik_output: Path,
    manifest_output: Path,
    user_agent: str,
    limit: int = 300,
    filed_start: date = date(2016, 1, 1),
    filed_end: date = date(2016, 3, 31),
    source_url: str = DEFAULT_MASTER_INDEX_URL,
    timeout_seconds: float = 60.0,
    refresh: bool = False,
) -> dict[str, object]:
    """Write a history-anchored, deterministic CIK list and its manifest."""

    payload, source = _load_or_download_master_index(
        master_index_path,
        url=source_url,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        refresh=refresh,
    )
    try:
        text = payload.decode("latin-1")
    except UnicodeDecodeError as error:
        raise ValueError("master index could not be decoded as latin-1") from error
    records = parse_master_index(
        text,
        filed_start=filed_start,
        filed_end=filed_end,
    )
    candidates = unique_cik_records(records)
    selected = evenly_spaced_cik_sample(candidates, limit=limit)
    ciks = tuple(record.cik for record in selected)
    cik_text = (
        "# B9 M6 historical seed: unique 10-K filers in 2016 Q1 EDGAR master index\n"
        "# deterministic evenly spaced CIK-rank feasibility sample\n" + "\n".join(ciks) + "\n"
    )
    _write_bytes(cik_output, cik_text.encode("utf-8"))
    manifest = {
        "schema_version": "b9-historical-seed-v1",
        "source_url": source_url,
        "source": source,
        "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "master_index_sha256": sha256(payload).hexdigest(),
        "master_index_path": str(master_index_path.expanduser().resolve()),
        "forms": ["10-K"],
        "filed_start": filed_start.isoformat(),
        "filed_end": filed_end.isoformat(),
        "raw_10k_record_count": len(records),
        "unique_cik_count": len(candidates),
        "selection_method": "evenly_spaced_cik_rank",
        "requested_limit": limit,
        "selected_cik_count": len(selected),
        "selected_cik_sha256": canonical_cik_sha256(ciks),
        "selected_records": [
            {
                **asdict(record),
                "filing_date": record.filing_date.isoformat(),
            }
            for record in selected
        ],
    }
    _write_bytes(
        manifest_output,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-index-path", type=Path, required=True)
    parser.add_argument("--cik-output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--filed-start", default="2016-01-01")
    parser.add_argument("--filed-end", default="2016-03-31")
    parser.add_argument("--source-url", default=DEFAULT_MASTER_INDEX_URL)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest = prepare_seed_cohort(
        master_index_path=args.master_index_path,
        cik_output=args.cik_output,
        manifest_output=args.manifest_output,
        user_agent=args.user_agent,
        limit=args.limit,
        filed_start=_parse_iso_date(args.filed_start, name="filed-start"),
        filed_end=_parse_iso_date(args.filed_end, name="filed-end"),
        source_url=args.source_url,
        timeout_seconds=args.timeout_seconds,
        refresh=args.refresh,
    )
    print(
        json.dumps(
            {
                "master_index_sha256": manifest["master_index_sha256"],
                "selected_cik_count": manifest["selected_cik_count"],
                "unique_cik_count": manifest["unique_cik_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
