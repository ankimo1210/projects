from __future__ import annotations

import logging
import mimetypes
import re
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import httpx

from jhrmbs.config import AppConfig, SourceConfig
from jhrmbs.exceptions import DownloadError
from jhrmbs.paths import DataPaths
from jhrmbs.util import (
    atomic_write_bytes,
    atomic_write_json,
    read_json,
    sha256_bytes,
    sha256_file,
    timestamp_id,
    utc_now,
)

LOGGER = logging.getLogger("jhrmbs.ingest")
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


@dataclass(frozen=True)
class DownloadRecord:
    source_id: str
    role: str
    source_url: str
    final_url: str
    retrieved_at: str
    original_filename: str
    sha256: str
    byte_size: int
    media_type: str
    object_path: str
    coverage: str
    data_definition: str
    transformation_history: tuple[str, ...]
    cache_status: str
    etag: str | None = None
    last_modified: str | None = None
    link_text: str | None = None


class RawDownloader:
    def __init__(
        self,
        config: AppConfig,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self.paths = DataPaths(config.data_root)
        self.paths.ensure()
        self.index_path = self.paths.raw / "url_index.json"
        index = read_json(self.index_path, {})
        self.url_index: dict[str, dict[str, Any]] = index if isinstance(index, dict) else {}
        self.client = httpx.Client(
            timeout=config.http.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": config.http.user_agent, "Accept-Encoding": "gzip"},
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> RawDownloader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _validate_url(url: str, source: SourceConfig) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in source.allowed_hosts:
            raise DownloadError(f"許可されていない取得先です: {url}")

    @staticmethod
    def _filename(url: str, configured: str | None, media_type: str, source_id: str) -> str:
        candidate = configured or Path(unquote(urlparse(url).path)).name
        candidate = Path(candidate).name
        if candidate and "." in candidate:
            return candidate
        suffix = mimetypes.guess_extension(media_type.partition(";")[0].strip()) or ".bin"
        if media_type.startswith("text/html"):
            suffix = ".html"
        elif "csv" in media_type:
            suffix = ".csv"
        return f"{candidate or source_id}{suffix}"

    def _cached_record(
        self,
        *,
        source: SourceConfig,
        role: str,
        url: str,
        link_text: str | None,
    ) -> DownloadRecord | None:
        cached = self.url_index.get(url)
        if not cached:
            return None
        object_path = self.config.data_root / str(cached.get("object_path", ""))
        if not object_path.is_file():
            return None
        return DownloadRecord(
            source_id=source.id,
            role=role,
            source_url=url,
            final_url=str(cached.get("final_url", url)),
            retrieved_at=utc_now().isoformat(),
            original_filename=str(cached["original_filename"]),
            sha256=str(cached["sha256"]),
            byte_size=int(cached["byte_size"]),
            media_type=str(cached.get("media_type", "application/octet-stream")),
            object_path=str(cached["object_path"]),
            coverage=source.coverage,
            data_definition=source.data_definition,
            transformation_history=("HTTP 304; reused byte-identical cached object",),
            cache_status="not_modified",
            etag=str(cached["etag"]) if cached.get("etag") else None,
            last_modified=str(cached["last_modified"]) if cached.get("last_modified") else None,
            link_text=link_text,
        )

    def fetch(
        self,
        source: SourceConfig,
        url: str,
        *,
        role: str,
        configured_filename: str | None = None,
        link_text: str | None = None,
    ) -> DownloadRecord:
        self._validate_url(url, source)
        cached = self.url_index.get(url, {})
        conditional_headers: dict[str, str] = {}
        if cached.get("etag"):
            conditional_headers["If-None-Match"] = str(cached["etag"])
        if cached.get("last_modified"):
            conditional_headers["If-Modified-Since"] = str(cached["last_modified"])

        last_error: Exception | None = None
        for attempt in range(self.config.http.retries + 1):
            try:
                with self.client.stream("GET", url, headers=conditional_headers) as response:
                    self._validate_url(str(response.url), source)
                    if response.status_code == 304:
                        cached_record = self._cached_record(
                            source=source, role=role, url=url, link_text=link_text
                        )
                        if cached_record is not None:
                            LOGGER.info("cache hit %s", url)
                            return cached_record
                        conditional_headers.clear()
                        raise DownloadError(f"304 response has no valid local object: {url}")
                    if response.status_code in RETRYABLE_STATUS:
                        raise httpx.HTTPStatusError(
                            f"retryable status {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    response.raise_for_status()
                    limit = self.config.http.max_download_mb * 1024 * 1024
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > limit:
                            raise DownloadError(f"download exceeds {limit} bytes: {url}")
                        chunks.append(chunk)
                    data = b"".join(chunks)
                    media_type = response.headers.get("content-type", "application/octet-stream")
                    filename = self._filename(
                        str(response.url), configured_filename, media_type, source.id
                    )
                    digest = sha256_bytes(data)
                    suffix = Path(filename).suffix.lower() or ".bin"
                    relative_object = Path("raw") / "objects" / digest[:2] / f"{digest}{suffix}"
                    object_path = self.config.data_root / relative_object
                    if not object_path.exists():
                        atomic_write_bytes(object_path, data)
                        cache_status = "downloaded"
                    else:
                        cache_status = "content_reused"
                    record = DownloadRecord(
                        source_id=source.id,
                        role=role,
                        source_url=url,
                        final_url=str(response.url),
                        retrieved_at=utc_now().isoformat(),
                        original_filename=filename,
                        sha256=digest,
                        byte_size=size,
                        media_type=media_type,
                        object_path=str(relative_object),
                        coverage=source.coverage,
                        data_definition=source.data_definition,
                        transformation_history=("downloaded byte-for-byte; no transformation",),
                        cache_status=cache_status,
                        etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"),
                        link_text=link_text,
                    )
                    self.url_index[url] = {
                        "final_url": record.final_url,
                        "original_filename": filename,
                        "sha256": digest,
                        "byte_size": size,
                        "media_type": media_type,
                        "object_path": str(relative_object),
                        "etag": record.etag,
                        "last_modified": record.last_modified,
                    }
                    LOGGER.info("%s %s (%d bytes)", cache_status, url, size)
                    return record
            except (httpx.HTTPError, DownloadError) as exc:
                last_error = exc
                if attempt >= self.config.http.retries:
                    break
                delay = min(self.config.http.backoff_seconds * (2**attempt), 10.0)
                LOGGER.warning(
                    "retry %d/%d for %s: %s", attempt + 1, self.config.http.retries, url, exc
                )
                time.sleep(delay)
        raise DownloadError(f"取得に失敗しました: {url}: {last_error}") from last_error

    def save_index(self) -> None:
        atomic_write_json(self.index_path, self.url_index)


def _discover_collection(
    downloader: RawDownloader,
    source: SourceConfig,
) -> list[DownloadRecord]:
    index_record = downloader.fetch(
        source,
        source.url,
        role="index",
        configured_filename=f"{source.id}_index.html",
    )
    index_bytes = (downloader.config.data_root / index_record.object_path).read_bytes()
    for encoding in ("utf-8", "cp932", "euc_jp"):
        try:
            html = index_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = index_bytes.decode("utf-8", errors="replace")
    extractor = LinkExtractor()
    extractor.feed(html)
    pattern = re.compile(source.link_pattern or r".*")
    discovered: dict[str, str] = {}
    for href, text in extractor.links:
        absolute_url = urljoin(source.url, href)
        if pattern.search(absolute_url):
            discovered[absolute_url] = text
    if not discovered:
        raise DownloadError(f"リンクを1件も検出できませんでした: {source.url}")
    records = [index_record]
    for url, text in sorted(discovered.items()):
        records.append(downloader.fetch(source, url, role="data", link_text=text))
    return records


def _carried_forward_records(
    data_root: Path,
    selected_source_ids: set[str],
    configured_source_ids: set[str],
) -> tuple[list[dict[str, Any]], str | None]:
    pointer = read_json(DataPaths(data_root).raw / "latest_manifest.json", {})
    if not isinstance(pointer, dict) or not pointer.get("manifest_path"):
        return [], None
    manifest_path = data_root / str(pointer["manifest_path"])
    if not manifest_path.is_file():
        return [], None
    previous = load_manifest(manifest_path)
    carried = [
        dict(record)
        for record in previous["records"]
        if record.get("source_id") in configured_source_ids
        and record.get("source_id") not in selected_source_ids
    ]
    snapshot_id = previous.get("snapshot_id")
    return carried, str(snapshot_id) if snapshot_id else None


def ingest(config: AppConfig, source_ids: set[str] | None = None) -> Path:
    paths = DataPaths(config.data_root)
    paths.ensure()
    selected = [source for source in config.sources if not source_ids or source.id in source_ids]
    unknown = (source_ids or set()) - {source.id for source in config.sources}
    if unknown:
        raise DownloadError(f"unknown source ids: {', '.join(sorted(unknown))}")
    carried: list[dict[str, Any]] = []
    carried_from: str | None = None
    if source_ids:
        carried, carried_from = _carried_forward_records(
            config.data_root,
            source_ids,
            {source.id for source in config.sources},
        )
    snapshot = timestamp_id()
    records: list[DownloadRecord] = []
    with RawDownloader(config) as downloader:
        for source in selected:
            LOGGER.info("ingesting %s", source.id)
            if source.kind == "link_collection":
                records.extend(_discover_collection(downloader, source))
            elif source.kind == "file":
                records.append(
                    downloader.fetch(
                        source,
                        source.url,
                        role="data",
                        configured_filename=source.filename,
                    )
                )
            else:
                raise DownloadError(f"unsupported source kind: {source.kind}")
        downloader.save_index()

    manifest = {
        "schema_version": 1,
        "snapshot_id": snapshot,
        "retrieved_at": utc_now().isoformat(),
        "config_path": str(config.config_path) if config.config_path else None,
        "config_sha256": (
            sha256_file(config.config_path)
            if config.config_path is not None and config.config_path.is_file()
            else None
        ),
        "carried_forward_from_snapshot": carried_from,
        "records": [*carried, *(asdict(record) for record in records)],
    }
    manifest_path = paths.raw_manifests / f"{snapshot}.json"
    atomic_write_json(manifest_path, manifest)
    atomic_write_json(
        paths.raw / "latest_manifest.json",
        {
            "snapshot_id": snapshot,
            "manifest_path": str(manifest_path.relative_to(config.data_root)),
        },
    )
    LOGGER.info("manifest %s", manifest_path)
    return manifest_path


def latest_manifest_path(data_root: Path) -> Path:
    pointer = read_json(DataPaths(data_root).raw / "latest_manifest.json", {})
    if not isinstance(pointer, dict) or not pointer.get("manifest_path"):
        raise DownloadError("Raw manifest がありません。先に jhrmbs ingest を実行してください。")
    path = data_root / str(pointer["manifest_path"])
    if not path.is_file():
        raise DownloadError(f"Raw manifest が見つかりません: {path}")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise DownloadError(f"invalid raw manifest: {path}")
    return payload


def historical_records(data_root: Path, source_id: str) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(DataPaths(data_root).raw_manifests.glob("*.json")):
        manifest = load_manifest(manifest_path)
        for record in manifest["records"]:
            if record.get("source_id") == source_id and record.get("role") == "data":
                unique[str(record["sha256"])] = record
    return list(unique.values())
