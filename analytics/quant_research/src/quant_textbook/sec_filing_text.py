"""Point-in-time SEC filing provenance and primary-document retrieval.

The M6 panel remains immutable.  This module reconstructs the exact filing
behind each panel row into a separate sidecar, then downloads only the
``previous_accession`` primary document.  Raw documents and manifests belong
in an explicit external cache, never in the repository.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from .sec_panel import PANEL_COLUMNS, _cache_dirs, _vintages_for_cache

SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
PROVENANCE_KEY = ("cik", "previous_period_end", "target_period_end")
_SAFE_DOCUMENT_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RETRYABLE_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})


def _manifest_digest(manifest: Mapping[str, Any]) -> str:
    return sha256(
        (json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class FilingProvenanceQuality:
    """Integrity result for the row-preserving filing sidecar."""

    panel_row_count: int
    sidecar_row_count: int
    unique_previous_document_count: int
    duplicate_keys: int
    missing_primary_document_rows: int
    target_accession_leakage_rows: int
    accepted: bool


@dataclass(frozen=True)
class PreviousFilingSidecar:
    """Row-aligned provenance without modifying the locked M6 panel."""

    rows: tuple[dict[str, Any], ...]
    quality: FilingProvenanceQuality


@dataclass(frozen=True)
class RetrievalAudit:
    """Raw-document coverage and leakage diagnostics before text modeling."""

    requested_row_count: int
    covered_row_count: int
    row_coverage: float
    unique_document_count: int
    successful_document_count: int
    duplicate_family_count: int
    cross_partition_duplicate_family_count: int
    target_accession_leakage_rows: int
    manifest_integrity_errors: tuple[str, ...]
    accepted: bool


@dataclass(frozen=True)
class NormalizedTextAudit:
    """Coverage and duplicate diagnostics for visible normalized text."""

    requested_row_count: int
    covered_row_count: int
    row_coverage: float
    successful_document_count: int
    empty_document_count: int
    duplicate_family_count: int
    cross_partition_duplicate_family_count: int
    target_accession_leakage_rows: int
    manifest_integrity_errors: tuple[str, ...]
    accepted: bool


class _VisibleTextExtractor(HTMLParser):
    """Conservative visible-body extractor for SEC HTML and inline XBRL."""

    _SKIPPED_TAGS = frozenset({"script", "style", "template", "noscript", "ix:hidden"})
    _BLOCK_TAGS = frozenset(
        {
            "article",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "li",
            "main",
            "p",
            "section",
            "table",
            "tbody",
            "td",
            "tfoot",
            "th",
            "thead",
            "tr",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    @staticmethod
    def _hidden(attributes: list[tuple[str, str | None]]) -> bool:
        values = {name.lower(): "" if value is None else value for name, value in attributes}
        style = values.get("style", "").replace(" ", "").lower()
        return (
            "hidden" in values
            or values.get("aria-hidden", "").lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if self._skip_depth:
            self._skip_depth += 1
            return
        if normalized in self._SKIPPED_TAGS or self._hidden(attrs):
            self._skip_depth = 1
            return
        if normalized in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._skip_depth and tag.lower() in self._BLOCK_TAGS and not self._hidden(attrs):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag.lower() in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = []
        for raw in "".join(self._parts).splitlines():
            line = " ".join(raw.split())
            if line:
                lines.append(line)
        return "\n".join(lines)


def _iso_date(value: Any, *, name: str) -> str:
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a valid date") from error
    if pd.isna(parsed):
        raise ValueError(f"{name} must be a valid date")
    return parsed.date().isoformat()


def _panel_rows(panel: pd.DataFrame | Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(panel, pd.DataFrame):
        missing = [column for column in PANEL_COLUMNS if column not in panel]
        if missing:
            raise ValueError(f"panel is missing columns: {missing}")
        rows = panel.to_dict(orient="records")
    else:
        rows = [dict(row) for row in panel]
    if not rows:
        raise ValueError("panel must contain at least one row")
    normalized: list[dict[str, Any]] = []
    keys: set[tuple[int, str, str]] = set()
    for row in rows:
        try:
            cik = int(row["cik"])
            previous_period = _iso_date(row["previous_period_end"], name="previous_period_end")
            target_period = _iso_date(row["target_period_end"], name="target_period_end")
        except KeyError as error:
            raise ValueError(f"panel row is missing {error.args[0]}") from error
        key = (cik, previous_period, target_period)
        if key in keys:
            raise ValueError(f"panel grain is duplicated: {key}")
        keys.add(key)
        normalized.append(
            {
                **row,
                "cik": cik,
                "previous_period_end": previous_period,
                "target_period_end": target_period,
            }
        )
    return normalized


def build_previous_filing_sidecar(
    panel: pd.DataFrame | Iterable[Mapping[str, Any]],
    cache_root: Path,
    *,
    holiday_dates: tuple[date, ...] | None = None,
) -> PreviousFilingSidecar:
    """Reconstruct exact previous filing metadata for every locked panel row.

    The function verifies values and availability dates on both sides of each
    pair.  A stale or ambiguous cache therefore cannot silently relabel the M6
    target rows.
    """

    panel_rows = _panel_rows(panel)
    requested_ciks = {int(row["cik"]) for row in panel_rows}
    cache_dirs, _ = _cache_dirs(cache_root)
    by_period: dict[tuple[int, str], dict[str, Any]] = {}
    for cache_dir in cache_dirs:
        cik = int(cache_dir.name.removeprefix("CIK"))
        if cik not in requested_ciks:
            continue
        for vintage in _vintages_for_cache(cache_dir, holiday_dates=holiday_dates):
            key = (cik, _iso_date(vintage["end"], name="vintage period end"))
            if key in by_period:
                raise ValueError(f"duplicate first-reported Assets vintage: {key}")
            by_period[key] = vintage

    output: list[dict[str, Any]] = []
    missing_primary = 0
    leakage = 0
    for row in panel_rows:
        cik = int(row["cik"])
        previous_key = (cik, row["previous_period_end"])
        target_key = (cik, row["target_period_end"])
        previous = by_period.get(previous_key)
        target = by_period.get(target_key)
        if previous is None or target is None:
            raise ValueError(
                f"cannot resolve both panel vintages for {previous_key} -> {target_key}"
            )

        comparisons = (
            (float(previous["value"]), float(row["previous_assets_usd"]), "previous Assets"),
            (float(target["value"]), float(row["target_assets_usd"]), "target Assets"),
        )
        for rebuilt, locked, label in comparisons:
            if not math.isclose(rebuilt, locked, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"{label} differs from the locked panel for {previous_key}")
        previous_available = _iso_date(previous["availability_date"], name="previous availability")
        target_available = _iso_date(target["availability_date"], name="target availability")
        if previous_available != _iso_date(
            row["previous_available_date"], name="locked previous availability"
        ):
            raise ValueError(
                f"previous availability differs from the locked panel for {previous_key}"
            )
        if target_available != _iso_date(
            row["target_available_date"], name="locked target availability"
        ):
            raise ValueError(f"target availability differs from the locked panel for {target_key}")
        primary_document = previous.get("primary_document")
        if not isinstance(primary_document, str) or not primary_document.strip():
            missing_primary += 1
            primary_document = None
        previous_accession = str(previous["accn"])
        target_accession = str(target["accn"])
        if previous_accession == target_accession:
            leakage += 1
        output.append(
            {
                "cik": cik,
                "previous_period_end": row["previous_period_end"],
                "target_period_end": row["target_period_end"],
                "target_available_date": target_available,
                "previous_accession": previous_accession,
                "previous_form": str(previous["form"]),
                "previous_filing_date": str(previous["filed"]),
                "previous_acceptance_datetime": str(previous["acceptance_datetime"]),
                "previous_available_date": previous_available,
                "previous_primary_document": primary_document,
                "previous_document_sha256": None,
                "target_accession": target_accession,
            }
        )

    output.sort(
        key=lambda row: (row["target_available_date"], row["cik"], row["target_period_end"])
    )
    duplicate_keys = len(output) - len(
        {(row["cik"], row["previous_period_end"], row["target_period_end"]) for row in output}
    )
    unique_documents = {
        (row["cik"], row["previous_accession"], row["previous_primary_document"])
        for row in output
        if row["previous_primary_document"] is not None
    }
    accepted = bool(
        len(output) == len(panel_rows)
        and duplicate_keys == 0
        and missing_primary == 0
        and leakage == 0
    )
    return PreviousFilingSidecar(
        rows=tuple(output),
        quality=FilingProvenanceQuality(
            panel_row_count=len(panel_rows),
            sidecar_row_count=len(output),
            unique_previous_document_count=len(unique_documents),
            duplicate_keys=duplicate_keys,
            missing_primary_document_rows=missing_primary,
            target_accession_leakage_rows=leakage,
            accepted=accepted,
        ),
    )


def primary_document_url(cik: int, accession: str, primary_document: str) -> str:
    """Return the canonical SEC Archives URL for one primary document."""

    if isinstance(cik, bool) or int(cik) <= 0:
        raise ValueError("cik must be a positive integer")
    accession_digits = accession.replace("-", "")
    if len(accession_digits) != 18 or not accession_digits.isdigit():
        raise ValueError("accession must contain exactly 18 digits")
    document_path = PurePosixPath(primary_document) if isinstance(primary_document, str) else None
    if (
        document_path is None
        or document_path.is_absolute()
        or ".." in document_path.parts
        or "\\" in primary_document
        or not document_path.parts
        or not all(_SAFE_DOCUMENT_PART.fullmatch(part) for part in document_path.parts)
    ):
        raise ValueError("primary_document must be a safe SEC-relative path")
    return f"{SEC_ARCHIVES_BASE_URL}/{int(cik)}/{accession_digits}/{primary_document}"


def validate_sec_user_agent(value: str) -> str:
    """Require a descriptive User-Agent with a contact email, without persisting it."""

    text = value.strip()
    if len(text) < 12 or "@" not in text or any(character in text for character in "\r\n"):
        raise ValueError("user_agent must include a descriptive name and contact email")
    return text


def _retry_after_seconds(error: HTTPError, *, maximum: float) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers is not None else None
    if raw is None:
        return None
    try:
        return min(maximum, max(0.0, float(raw)))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(raw)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return min(maximum, max(0.0, (retry_at - datetime.now(UTC)).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            return None


def fetch_primary_document(
    url: str,
    *,
    user_agent: str,
    timeout_seconds: float = 60.0,
    maximum_attempts: int = 4,
    initial_backoff_seconds: float = 1.0,
    maximum_backoff_seconds: float = 30.0,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bytes, int, int]:
    """Fetch bytes with bounded retry for transient SEC/network failures."""

    agent = validate_sec_user_agent(user_agent)
    if timeout_seconds <= 0 or maximum_attempts < 1:
        raise ValueError("timeout_seconds and maximum_attempts must be positive")
    if initial_backoff_seconds < 0 or maximum_backoff_seconds < 0:
        raise ValueError("backoff values must be non-negative")
    request = Request(
        url, headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": agent}
    )
    for attempt in range(1, maximum_attempts + 1):
        try:
            with opener(request, timeout=timeout_seconds) as response:
                payload = response.read()
                status = int(getattr(response, "status", 200))
            if not payload:
                raise ValueError("SEC primary document response was empty")
            return payload, attempt, status
        except HTTPError as error:
            if error.code not in _RETRYABLE_HTTP_STATUS or attempt == maximum_attempts:
                raise
            retry_after = _retry_after_seconds(error, maximum=maximum_backoff_seconds)
            delay = (
                retry_after
                if retry_after is not None
                else min(maximum_backoff_seconds, initial_backoff_seconds * (2 ** (attempt - 1)))
            )
        except (URLError, TimeoutError):
            if attempt == maximum_attempts:
                raise
            delay = min(maximum_backoff_seconds, initial_backoff_seconds * (2 ** (attempt - 1)))
        sleep(delay)
    raise RuntimeError("unreachable retry state")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def normalize_visible_filing_text(payload: bytes) -> str:
    """Extract visible ordered text and apply deterministic Unicode/space normalization."""

    if not payload:
        raise ValueError("filing document payload must be non-empty")
    decoded = payload.decode("utf-8", errors="replace")
    parser = _VisibleTextExtractor()
    parser.feed(decoded)
    parser.close()
    text = unicodedata.normalize("NFKC", parser.text())
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def normalize_retrieved_documents(
    retrieval_manifest: Mapping[str, Any],
    document_root: Path,
    normalized_root: Path,
) -> dict[str, Any]:
    """Normalize every hash-verified raw document into a separate external cache."""

    documents = retrieval_manifest.get("documents")
    if retrieval_manifest.get("schema_version") != "b9-sec-primary-documents-v1" or not isinstance(
        documents, list
    ):
        raise ValueError("retrieval manifest has an unsupported schema")
    raw_root = document_root.expanduser().resolve()
    output_root = normalized_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for entry in documents:
        if not isinstance(entry, Mapping):
            raise ValueError("retrieval manifest entries must be objects")
        relative = Path(str(entry["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("retrieval manifest contains an unsafe raw path")
        raw_path = (raw_root / relative).resolve()
        if not raw_path.is_relative_to(raw_root) or not raw_path.is_file():
            raise ValueError(f"raw filing document is missing: {relative}")
        payload = raw_path.read_bytes()
        if sha256(payload).hexdigest() != entry.get("raw_sha256") or len(payload) != entry.get(
            "byte_count"
        ):
            raise ValueError(f"raw filing document differs from its manifest: {relative}")
        normalized = normalize_visible_filing_text(payload)
        normalized_payload = (normalized + "\n").encode("utf-8") if normalized else b""
        normalized_relative = Path(f"{relative.as_posix()}.txt")
        _atomic_write(output_root / normalized_relative, normalized_payload)
        entries.append(
            {
                "cik": int(entry["cik"]),
                "accession": str(entry["accession"]),
                "form": str(entry["form"]),
                "filing_date": str(entry["filing_date"]),
                "acceptance_datetime": str(entry["acceptance_datetime"]),
                "availability_date": str(entry["availability_date"]),
                "primary_document": str(entry["primary_document"]),
                "retrieved_at_utc": str(entry["retrieved_at_utc"]),
                "raw_sha256": str(entry["raw_sha256"]),
                "normalized_text_sha256": sha256(normalized_payload).hexdigest(),
                "byte_count": int(entry["byte_count"]),
                "normalized_byte_count": len(normalized_payload),
                "token_count": len(re.findall(r"\S+", normalized)),
                "path": normalized_relative.as_posix(),
            }
        )
    manifest = {
        "schema_version": "b9-sec-normalized-text-v1",
        "source_retrieval_manifest_sha256": _manifest_digest(retrieval_manifest),
        "document_count": len(entries),
        "documents": entries,
    }
    _atomic_write(
        output_root / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def download_previous_filing_documents(
    sidecar_rows: Iterable[Mapping[str, Any]],
    output_root: Path,
    *,
    provenance_sha256: str,
    user_agent: str,
    timeout_seconds: float = 60.0,
    maximum_attempts: int = 4,
    sleep_seconds: float = 0.2,
    refresh: bool = False,
    fetcher: Callable[..., tuple[bytes, int, int]] = fetch_primary_document,
) -> dict[str, Any]:
    """Download each unique previous primary document and atomically publish a manifest."""

    agent = validate_sec_user_agent(user_agent)
    if not re.fullmatch(r"[0-9a-f]{64}", provenance_sha256):
        raise ValueError("provenance_sha256 must be a lowercase SHA-256 digest")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be non-negative")
    root = output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    requests: dict[tuple[int, str, str], dict[str, Any]] = {}
    for raw in sidecar_rows:
        row = dict(raw)
        cik = int(row["cik"])
        accession = str(row["previous_accession"])
        document = row.get("previous_primary_document")
        if not isinstance(document, str):
            raise ValueError(f"previous_primary_document is missing for {accession}")
        key = (cik, accession, document)
        request_record = {
            "cik": cik,
            "accession": accession,
            "form": str(row["previous_form"]),
            "filing_date": str(row["previous_filing_date"]),
            "acceptance_datetime": str(row["previous_acceptance_datetime"]),
            "availability_date": str(row["previous_available_date"]),
            "primary_document": document,
            "url": primary_document_url(cik, accession, document),
        }
        existing = requests.get(key)
        if existing is not None and existing != request_record:
            raise ValueError(f"conflicting provenance for previous accession {accession}")
        requests[key] = request_record
    if not requests:
        raise ValueError("at least one previous filing document is required")

    entries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for key in sorted(requests):
        record = requests[key]
        relative = (
            Path(f"CIK{record['cik']:010d}")
            / record["accession"].replace("-", "")
            / PurePosixPath(record["primary_document"])
        )
        destination = root / relative
        try:
            if destination.exists() and not refresh:
                payload = destination.read_bytes()
                attempts = 0
                status = 200
                source = "cache"
            else:
                payload, attempts, status = fetcher(
                    record["url"],
                    user_agent=agent,
                    timeout_seconds=timeout_seconds,
                    maximum_attempts=maximum_attempts,
                )
                _atomic_write(destination, payload)
                source = "network"
                if sleep_seconds:
                    time.sleep(sleep_seconds)
            entries.append(
                {
                    **record,
                    "path": relative.as_posix(),
                    "retrieved_at_utc": datetime.now(UTC).isoformat(),
                    "raw_sha256": sha256(payload).hexdigest(),
                    "byte_count": len(payload),
                    "attempt_count": attempts,
                    "http_status": status,
                    "source": source,
                }
            )
        except Exception as error:
            failures.append(
                {
                    "cik": record["cik"],
                    "accession": record["accession"],
                    "primary_document": record["primary_document"],
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )

    manifest = {
        "schema_version": "b9-sec-primary-documents-v1",
        "source_provenance_sha256": provenance_sha256,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "user_agent_policy": "contact-bearing User-Agent supplied but not persisted",
        "requested_document_count": len(requests),
        "success_count": len(entries),
        "failure_count": len(failures),
        "documents": entries,
        "failures": failures,
    }
    _atomic_write(
        root / "manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def audit_filing_retrieval(
    sidecar_rows: Iterable[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    document_root: Path,
    *,
    provenance_sha256: str,
    outer_time_cutoff: date,
    company_modulus: int,
    company_remainder: int,
    minimum_row_coverage: float = 0.9,
) -> RetrievalAudit:
    """Audit raw coverage, exact duplicates, partitions, and target exclusion."""

    rows = [dict(row) for row in sidecar_rows]
    if not rows:
        raise ValueError("sidecar must contain at least one row")
    if not 0.0 <= minimum_row_coverage <= 1.0:
        raise ValueError("minimum_row_coverage must lie in [0, 1]")
    if company_modulus <= 0 or not 0 <= company_remainder < company_modulus:
        raise ValueError("company split parameters are invalid")
    documents = manifest.get("documents")
    if manifest.get("schema_version") != "b9-sec-primary-documents-v1" or not isinstance(
        documents, list
    ):
        raise ValueError("retrieval manifest has an unsupported schema")
    root = document_root.expanduser().resolve()
    errors: list[str] = []
    if manifest.get("source_provenance_sha256") != provenance_sha256:
        errors.append("retrieval manifest is not linked to the filing provenance sidecar")
    by_request: dict[tuple[int, str, str], Mapping[str, Any]] = {}
    sha_to_requests: dict[str, set[tuple[int, str, str]]] = defaultdict(set)
    for entry in documents:
        if not isinstance(entry, Mapping):
            errors.append("document manifest entry must be an object")
            continue
        try:
            key = (int(entry["cik"]), str(entry["accession"]), str(entry["primary_document"]))
            relative = Path(str(entry["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsafe document path")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("document file is missing")
            payload = path.read_bytes()
            digest = sha256(payload).hexdigest()
            if digest != entry.get("raw_sha256") or len(payload) != entry.get("byte_count"):
                raise ValueError("document hash or byte count differs from manifest")
            if key in by_request:
                raise ValueError("duplicate document request in manifest")
            by_request[key] = entry
            sha_to_requests[digest].add(key)
        except (KeyError, TypeError, ValueError) as error:
            errors.append(str(error))

    covered = 0
    leakage = 0
    sha_partitions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        cik = int(row["cik"])
        previous_accession = str(row["previous_accession"])
        target_accession = str(row["target_accession"])
        document = str(row["previous_primary_document"])
        if previous_accession == target_accession:
            leakage += 1
        key = (cik, previous_accession, document)
        entry = by_request.get(key)
        if entry is None:
            continue
        covered += 1
        after_cutoff = (
            date.fromisoformat(str(row["target_available_date"])[:10]) >= outer_time_cutoff
        )
        held_company = cik % company_modulus == company_remainder
        partition = (
            "outer"
            if after_cutoff and held_company
            else "time_only"
            if after_cutoff
            else "company_only"
            if held_company
            else "development"
        )
        sha_partitions[str(entry["raw_sha256"])].add(partition)
    duplicate_families = sum(len(keys) > 1 for keys in sha_to_requests.values())
    cross_partition = sum(len(partitions) > 1 for partitions in sha_partitions.values())
    coverage = covered / len(rows)
    accepted = bool(
        coverage >= minimum_row_coverage
        and leakage == 0
        and cross_partition == 0
        and not errors
        and int(manifest.get("success_count", -1)) == len(by_request)
        and int(manifest.get("failure_count", -1)) == len(manifest.get("failures", []))
    )
    return RetrievalAudit(
        requested_row_count=len(rows),
        covered_row_count=covered,
        row_coverage=coverage,
        unique_document_count=len(
            {
                (
                    int(row["cik"]),
                    str(row["previous_accession"]),
                    str(row["previous_primary_document"]),
                )
                for row in rows
            }
        ),
        successful_document_count=len(by_request),
        duplicate_family_count=duplicate_families,
        cross_partition_duplicate_family_count=cross_partition,
        target_accession_leakage_rows=leakage,
        manifest_integrity_errors=tuple(errors),
        accepted=accepted,
    )


def audit_normalized_filing_text(
    sidecar_rows: Iterable[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    normalized_root: Path,
    *,
    retrieval_manifest: Mapping[str, Any],
    outer_time_cutoff: date,
    company_modulus: int,
    company_remainder: int,
    minimum_row_coverage: float = 0.9,
) -> NormalizedTextAudit:
    """Audit normalized-text integrity, coverage, duplicates, and target exclusion."""

    rows = [dict(row) for row in sidecar_rows]
    if not rows:
        raise ValueError("sidecar must contain at least one row")
    if not 0.0 <= minimum_row_coverage <= 1.0:
        raise ValueError("minimum_row_coverage must lie in [0, 1]")
    if company_modulus <= 0 or not 0 <= company_remainder < company_modulus:
        raise ValueError("company split parameters are invalid")
    documents = manifest.get("documents")
    if manifest.get("schema_version") != "b9-sec-normalized-text-v1" or not isinstance(
        documents, list
    ):
        raise ValueError("normalized-text manifest has an unsupported schema")
    root = normalized_root.expanduser().resolve()
    errors: list[str] = []
    raw_documents = retrieval_manifest.get("documents")
    if retrieval_manifest.get("schema_version") != "b9-sec-primary-documents-v1" or not isinstance(
        raw_documents, list
    ):
        raise ValueError("source retrieval manifest has an unsupported schema")
    if manifest.get("source_retrieval_manifest_sha256") != _manifest_digest(retrieval_manifest):
        errors.append("normalized-text manifest is not linked to the source retrieval manifest")
    raw_by_request: dict[tuple[int, str, str], Mapping[str, Any]] = {}
    for entry in raw_documents:
        if not isinstance(entry, Mapping):
            errors.append("source retrieval manifest entry must be an object")
            continue
        try:
            key = (
                int(entry["cik"]),
                str(entry["accession"]),
                str(entry["primary_document"]),
            )
            if key in raw_by_request:
                raise ValueError("duplicate source document request")
            raw_by_request[key] = entry
        except (KeyError, TypeError, ValueError) as error:
            errors.append(str(error))
    by_request: dict[tuple[int, str, str], Mapping[str, Any]] = {}
    digest_to_requests: dict[str, set[tuple[int, str, str]]] = defaultdict(set)
    empty_documents = 0
    for entry in documents:
        if not isinstance(entry, Mapping):
            errors.append("normalized-text manifest entry must be an object")
            continue
        try:
            key = (
                int(entry["cik"]),
                str(entry["accession"]),
                str(entry["primary_document"]),
            )
            relative = Path(str(entry["path"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsafe normalized-text path")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("normalized-text file is missing")
            payload = path.read_bytes()
            digest = sha256(payload).hexdigest()
            if digest != entry.get("normalized_text_sha256") or len(payload) != entry.get(
                "normalized_byte_count"
            ):
                raise ValueError("normalized-text hash or byte count differs from manifest")
            token_count = len(re.findall(r"\S+", payload.decode("utf-8")))
            if token_count != entry.get("token_count"):
                raise ValueError("normalized-text token count differs from manifest")
            source = raw_by_request.get(key)
            if source is None or source.get("raw_sha256") != entry.get("raw_sha256"):
                raise ValueError("normalized text is not linked to the matching raw document")
            if key in by_request:
                raise ValueError("duplicate normalized document request in manifest")
            by_request[key] = entry
            digest_to_requests[digest].add(key)
            if token_count == 0:
                empty_documents += 1
        except (KeyError, TypeError, UnicodeDecodeError, ValueError) as error:
            errors.append(str(error))

    covered = 0
    leakage = 0
    digest_partitions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        cik = int(row["cik"])
        previous_accession = str(row["previous_accession"])
        if previous_accession == str(row["target_accession"]):
            leakage += 1
        key = (cik, previous_accession, str(row["previous_primary_document"]))
        entry = by_request.get(key)
        if entry is None or int(entry.get("token_count", 0)) == 0:
            continue
        covered += 1
        after_cutoff = (
            date.fromisoformat(str(row["target_available_date"])[:10]) >= outer_time_cutoff
        )
        held_company = cik % company_modulus == company_remainder
        partition = (
            "outer"
            if after_cutoff and held_company
            else "time_only"
            if after_cutoff
            else "company_only"
            if held_company
            else "development"
        )
        digest_partitions[str(entry["normalized_text_sha256"])].add(partition)
    duplicate_families = sum(len(keys) > 1 for keys in digest_to_requests.values())
    cross_partition = sum(len(partitions) > 1 for partitions in digest_partitions.values())
    coverage = covered / len(rows)
    accepted = bool(
        coverage >= minimum_row_coverage
        and empty_documents == 0
        and leakage == 0
        and cross_partition == 0
        and not errors
        and int(manifest.get("document_count", -1)) == len(by_request)
    )
    return NormalizedTextAudit(
        requested_row_count=len(rows),
        covered_row_count=covered,
        row_coverage=coverage,
        successful_document_count=len(by_request),
        empty_document_count=empty_documents,
        duplicate_family_count=duplicate_families,
        cross_partition_duplicate_family_count=cross_partition,
        target_accession_leakage_rows=leakage,
        manifest_integrity_errors=tuple(errors),
        accepted=accepted,
    )


__all__ = [
    "FilingProvenanceQuality",
    "NormalizedTextAudit",
    "PreviousFilingSidecar",
    "RetrievalAudit",
    "audit_filing_retrieval",
    "audit_normalized_filing_text",
    "build_previous_filing_sidecar",
    "download_previous_filing_documents",
    "fetch_primary_document",
    "normalize_retrieved_documents",
    "normalize_visible_filing_text",
    "primary_document_url",
    "validate_sec_user_agent",
]
