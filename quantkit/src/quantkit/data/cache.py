"""Local parquet cache for raw and normalized data.

Layout (under the data root, see utils.paths):
    raw/<source>/<key>.parquet         # exactly as downloaded (auditable)
    processed/<source>/<key>.parquet   # normalized to the common schema

Caching is explicit and inspectable; nothing is hidden. TTL lets a caller treat
a cache entry as stale and re-download.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from ..utils import paths


class CacheManager:
    def __init__(self, root: Path | None = None):
        # root overrides the data dir (tests pass a tmp dir); else utils.paths.
        self._root = Path(root) if root is not None else None

    def _base(self, kind: str) -> Path:
        if self._root is not None:
            return self._root / kind
        return {"raw": paths.raw_dir(), "processed": paths.processed_dir()}.get(
            kind, paths.data_root() / kind
        )

    def path(self, kind: str, source: str, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "_")
        return self._base(kind) / source / f"{safe}.parquet"

    def exists(self, kind: str, source: str, key: str) -> bool:
        return self.path(kind, source, key).exists()

    def age_seconds(self, kind: str, source: str, key: str) -> float | None:
        p = self.path(kind, source, key)
        return (time.time() - p.stat().st_mtime) if p.exists() else None

    def is_fresh(self, kind: str, source: str, key: str, ttl_seconds: float | None) -> bool:
        age = self.age_seconds(kind, source, key)
        if age is None:
            return False
        return True if ttl_seconds is None else age <= ttl_seconds

    def read(self, kind: str, source: str, key: str) -> pd.DataFrame:
        return pd.read_parquet(self.path(kind, source, key))

    def write(self, kind: str, source: str, key: str, frame: pd.DataFrame) -> Path:
        p = self.path(kind, source, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        # reset_index so a DatetimeIndex round-trips cleanly through parquet
        frame.to_parquet(p)
        return p
