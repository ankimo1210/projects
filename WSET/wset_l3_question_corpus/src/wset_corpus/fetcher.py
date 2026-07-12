from __future__ import annotations

import json
import mimetypes
import os
import time
import urllib.robotparser
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

from .models import SourceConfig, SourceRecord
from .utils import ROOT, sha256_bytes, stable_id


class SafeFetcher:
    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or ROOT / "config" / "crawler.yaml"
        self.config = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.user_agent = os.getenv("WSET_USER_AGENT", self.config["user_agent"])
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
            timeout=self.config["timeout_seconds"],
        )
        self.last_request: dict[str, float] = {}
        self.denials: dict[str, int] = {}

    def close(self) -> None:
        self.client.close()

    def _robots_allowed(self, url: str) -> bool:
        if not self.config.get("honor_robots_txt", True):
            return True
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except OSError:
            return True
        return parser.can_fetch(self.user_agent, url)

    def _rate_limit(self, domain: str) -> None:
        delay = 60 / max(1, int(self.config["requests_per_domain_per_minute"]))
        elapsed = time.monotonic() - self.last_request.get(domain, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)

    def fetch(self, source: SourceConfig, url: str) -> SourceRecord:
        domain = urlparse(url).netloc
        if self.denials.get(domain, 0) >= self.config["stop_after_access_denials"]:
            return self._record(source, url, "stopped_after_access_denials")
        if not self._robots_allowed(url):
            return self._record(source, url, "robots_disallowed")

        source_dir = ROOT / "data" / "raw_private" / source.source_id
        url_key = stable_id(url, prefix="url_")
        target_dir = source_dir / url_key
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = target_dir / "manifest.json"
        legacy_manifest_path = source_dir / "manifest.json"
        for cached_manifest_path in (manifest_path, legacy_manifest_path):
            if not cached_manifest_path.exists():
                continue
            manifest = json.loads(cached_manifest_path.read_text(encoding="utf-8"))
            cached_dir = cached_manifest_path.parent
            requested_url = manifest.get("requested_url", manifest.get("url"))
            if requested_url == url and (cached_dir / manifest["filename"]).exists():
                return self._record(
                    source,
                    manifest.get("url", url),
                    "cached",
                    manifest.get("retrieved_at"),
                    manifest.get("sha256"),
                )

        response: httpx.Response | None = None
        error: str | None = None
        for attempt in range(int(self.config["max_retries"])):
            self._rate_limit(domain)
            try:
                response = self.client.get(url)
                self.last_request[domain] = time.monotonic()
                if response.status_code in {401, 403, 429}:
                    self.denials[domain] = self.denials.get(domain, 0) + 1
                    error = f"access_denied_{response.status_code}"
                    break
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                error = type(exc).__name__
                if attempt + 1 < int(self.config["max_retries"]):
                    time.sleep(2**attempt)

        if response is None or response.is_error:
            return self._record(source, url, error or "fetch_failed")
        if len(response.content) > int(self.config["max_response_bytes"]):
            return self._record(source, url, "response_too_large")

        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        allowed = self.config["allowed_content_types"]
        if content_type not in allowed:
            return self._record(source, url, f"unsupported_content_type:{content_type}")

        extension = mimetypes.guess_extension(content_type) or ".bin"
        extension = ".html" if extension in {".htm", ".html"} else extension
        filename = f"content{extension}"
        content_hash = sha256_bytes(response.content)
        retrieved_at = datetime.now(UTC).isoformat()
        (target_dir / filename).write_bytes(response.content)
        manifest = {
            "source_id": source.source_id,
            "url": str(response.url),
            "requested_url": url,
            "filename": filename,
            "content_type": content_type,
            "status_code": response.status_code,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"content-type", "etag", "last-modified", "content-length"}
            },
            "retrieved_at": retrieved_at,
            "sha256": content_hash,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        record = self._record(source, str(response.url), "fetched", retrieved_at, content_hash)
        snapshot = ROOT / "data" / "source_snapshots" / f"{source.source_id}_{url_key}.json"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    @staticmethod
    def _record(
        source: SourceConfig,
        url: str,
        status: str,
        retrieved_at: str | None = None,
        content_hash: str | None = None,
    ) -> SourceRecord:
        return SourceRecord(
            source_id=source.source_id,
            name=source.name,
            publisher=source.publisher,
            language=source.language,
            source_type=source.source_type,
            url=url,
            access_type=source.access_type,
            crawl_policy=source.crawl_policy,
            copyright_risk=source.copyright_risk,
            retrieved_at=datetime.fromisoformat(retrieved_at) if retrieved_at else None,
            content_hash=content_hash,
            status=status,
            notes=source.notes,
        )
