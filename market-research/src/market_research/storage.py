"""Immutable raw evidence and transactional point-in-time rows in DuckDB."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

from .contracts import Instrument, MacroObservation, PriceBar, _utc
from .macro import as_of
from .prices import PriceView, price_view_as_of


def _json(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda x: x.isoformat(),
        allow_nan=False,
    )


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True, slots=True)
class CacheKey:
    provider: str
    dataset: str
    identity: str
    interval: str
    currency: str
    adjustment: str
    schema_version: int = 1
    request_json: str = ""

    def __post_init__(self):
        for name in ("provider", "dataset", "identity", "interval", "currency", "adjustment"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"cache key {name} must be nonempty")
        if self.schema_version != 1:
            raise ValueError("unsupported cache schema version")
        if not isinstance(self.request_json, str) or (
            self.request_json and not isinstance(json.loads(self.request_json), dict)
        ):
            raise ValueError("request_json must encode an object")

    @property
    def encoded(self) -> str:
        return _json(asdict(self))

    @property
    def digest(self) -> str:
        return _hash(self.encoded.encode())


@dataclass(frozen=True, slots=True)
class Snapshot:
    snapshot_id: str
    key: CacheKey
    observed_at: datetime
    raw_hash: str
    raw_path: Path
    complete: bool
    cursor: str | None
    stale: bool = False


class CacheUnavailableError(ValueError):
    pass


def _price_json(row: PriceBar) -> str:
    payload = asdict(row)
    payload.pop("session_date")
    return _json(payload)


def _price_decode(payload: str) -> PriceBar:
    data = json.loads(payload)
    data["instrument"] = Instrument(**data["instrument"])
    for name in ("bar_start", "bar_end", "available_at", "observed_at"):
        data[name] = datetime.fromisoformat(data[name])
    data["quality_reasons"] = tuple(data["quality_reasons"])
    return PriceBar(**data)


def _macro_decode(payload: str) -> MacroObservation:
    data = json.loads(payload)
    data["period_start"] = date.fromisoformat(data["period_start"])
    data["release_at"] = datetime.fromisoformat(data["release_at"])
    return MacroObservation(**data)


class ResearchStore:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.root / "research.duckdb"))
        self.con.execute("SET TimeZone='UTC'")
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id VARCHAR PRIMARY KEY, key_json VARCHAR NOT NULL, key_hash VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL, raw_hash VARCHAR NOT NULL,
                complete BOOLEAN NOT NULL, cursor VARCHAR, record_hash VARCHAR NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entries (
                kind VARCHAR NOT NULL, row_key VARCHAR NOT NULL, identity VARCHAR NOT NULL,
                provider VARCHAR NOT NULL, adjustment VARCHAR NOT NULL,
                available_at TIMESTAMPTZ NOT NULL, payload VARCHAR NOT NULL,
                PRIMARY KEY(kind, row_key)
            );
            CREATE TABLE IF NOT EXISTS snapshot_entries (
                snapshot_id VARCHAR NOT NULL, kind VARCHAR NOT NULL, row_key VARCHAR NOT NULL,
                PRIMARY KEY(snapshot_id, kind, row_key)
            );
        """)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.con.close()

    def _raw_path(self, digest: str) -> Path:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid raw hash")
        return self.root / "raw" / digest[:2] / digest

    def _write_raw(self, raw: bytes) -> str:
        digest = _hash(raw)
        path = self._raw_path(digest)
        if path.exists():
            if _hash(path.read_bytes()) != digest:
                raise ValueError("raw hash mismatch")
            return digest
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return digest

    def read_raw(self, snapshot: Snapshot) -> bytes:
        raw = self._raw_path(snapshot.raw_hash).read_bytes()
        if _hash(raw) != snapshot.raw_hash:
            raise ValueError("raw hash mismatch")
        return raw

    def save(
        self,
        key: CacheKey,
        raw: bytes,
        *,
        observed_at: datetime,
        prices=(),
        macro=(),
        complete: bool = True,
        cursor: str | None = None,
    ) -> Snapshot:
        observed = _utc(observed_at, "observed_at")
        if not isinstance(raw, bytes) or not raw:
            raise ValueError("raw snapshot must contain bytes")
        if not isinstance(complete, bool) or (complete and cursor is not None):
            raise ValueError("complete snapshot cannot have a pending cursor")
        records = []
        for row in prices:
            expected = (
                row.provider,
                "prices",
                row.instrument.instrument_id,
                row.interval,
                row.instrument.currency,
                row.adjustment,
            )
            if expected != (
                key.provider,
                key.dataset,
                key.identity,
                key.interval,
                key.currency,
                key.adjustment,
            ):
                raise ValueError("price does not match cache key")
            if row.observed_at > observed:
                raise ValueError("price observed after snapshot")
            records.append(
                (
                    "price",
                    _hash(_json([row.key, row.instrument.currency]).encode()),
                    key.identity,
                    row.provider,
                    row.adjustment,
                    row.available_at,
                    _price_json(row),
                )
            )
        for row in macro:
            if (row.source, "macro", row.indicator) != (key.provider, key.dataset, key.identity):
                raise ValueError("macro row does not match cache key")
            if row.release_at > observed:
                raise ValueError("macro release after snapshot")
            row_key = (row.indicator, row.period_start, row.source, row.release_at, row.vintage_id)
            records.append(
                (
                    "macro",
                    _hash(_json(row_key).encode()),
                    row.indicator,
                    row.source,
                    "none",
                    row.release_at,
                    _json(asdict(row)),
                )
            )
        raw_hash = self._write_raw(raw)
        identity = [key.encoded, observed, raw_hash, complete, cursor]
        snapshot_id = _hash(_json(identity).encode())
        record_hash = _hash(_json(sorted(records)).encode())
        self.con.execute("BEGIN TRANSACTION")
        try:
            old_snapshot = self.con.execute(
                "SELECT record_hash FROM snapshots WHERE id=?", [snapshot_id]
            ).fetchone()
            if old_snapshot and old_snapshot[0] != record_hash:
                raise ValueError("conflicting snapshot normalization")
            self.con.execute(
                "INSERT OR IGNORE INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    snapshot_id,
                    key.encoded,
                    key.digest,
                    observed,
                    raw_hash,
                    complete,
                    cursor,
                    record_hash,
                ],
            )
            for record in records:
                old = self.con.execute(
                    "SELECT payload FROM entries WHERE kind=? AND row_key=?", list(record[:2])
                ).fetchone()
                if old and old[0] != record[-1]:
                    raise ValueError("conflicting immutable row")
                self.con.execute(
                    "INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?, ?, ?)", list(record)
                )
                self.con.execute(
                    "INSERT OR IGNORE INTO snapshot_entries VALUES (?, ?, ?)",
                    [snapshot_id, *record[:2]],
                )
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        return Snapshot(
            snapshot_id, key, observed, raw_hash, self._raw_path(raw_hash), complete, cursor
        )

    def _snapshot(self, row) -> Snapshot:
        return Snapshot(
            row[0],
            CacheKey(**json.loads(row[1])),
            row[3],
            row[4],
            self._raw_path(row[4]),
            row[5],
            row[6],
        )

    def latest_snapshot(
        self, key: CacheKey, *, now: datetime, max_age: timedelta, allow_stale: bool = False
    ) -> Snapshot:
        when = _utc(now, "now")
        if max_age < timedelta(0):
            raise ValueError("max_age must be nonnegative")
        row = self.con.execute(
            "SELECT * FROM snapshots WHERE key_hash=? AND complete AND observed_at<=? ORDER BY observed_at DESC, id DESC LIMIT 1",
            [key.digest, when],
        ).fetchone()
        if row is None:
            raise CacheUnavailableError("complete cache unavailable")
        snapshot = self._snapshot(row)
        stale = when - snapshot.observed_at > max_age
        if stale and not allow_stale:
            raise CacheUnavailableError("cache is stale")
        self.read_raw(snapshot)
        return replace(snapshot, stale=stale)

    def pending_snapshot(self, key: CacheKey) -> Snapshot:
        row = self.con.execute(
            """SELECT s.* FROM snapshots s WHERE s.key_hash=? AND NOT s.complete
            AND NOT EXISTS (SELECT 1 FROM snapshots done WHERE done.key_hash=s.key_hash
                AND done.complete AND done.observed_at>=s.observed_at)
            ORDER BY s.observed_at DESC, s.id DESC LIMIT 1""",
            [key.digest],
        ).fetchone()
        if row is None:
            raise CacheUnavailableError("pending cache unavailable")
        snapshot = self._snapshot(row)
        self.read_raw(snapshot)
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Snapshot:
        row = self.con.execute("SELECT * FROM snapshots WHERE id=?", [snapshot_id]).fetchone()
        if row is None:
            raise CacheUnavailableError("snapshot unavailable")
        snapshot = self._snapshot(row)
        self.read_raw(snapshot)
        return snapshot

    def snapshots(self, limit: int = 50) -> tuple[Snapshot, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = self.con.execute(
            "SELECT * FROM snapshots ORDER BY observed_at DESC, id DESC LIMIT ?", [limit]
        ).fetchall()
        return tuple(self._snapshot(row) for row in rows)

    def snapshot_price_view(self, snapshot: Snapshot, when: datetime) -> PriceView:
        # Reload the manifest: callers cannot promote a partial snapshot via replace().
        saved = self.get_snapshot(snapshot.snapshot_id)
        if not saved.complete or saved.key.dataset != "prices":
            raise CacheUnavailableError("complete price snapshot required")
        rows = self.con.execute(
            """SELECT e.payload FROM entries e JOIN snapshot_entries se
            ON se.kind=e.kind AND se.row_key=e.row_key
            WHERE se.snapshot_id=? AND e.kind='price' ORDER BY e.available_at, e.row_key""",
            [saved.snapshot_id],
        ).fetchall()
        return price_view_as_of(
            [_price_decode(row[0]) for row in rows], when, adjustment=saved.key.adjustment
        )

    def _rows(self, kind: str, identity: str, provider: str):
        return self.con.execute(
            """
            SELECT e.payload FROM entries e
            WHERE e.kind=? AND e.identity=? AND e.provider=? AND EXISTS (
                SELECT 1 FROM snapshot_entries se JOIN snapshots s ON s.id=se.snapshot_id
                WHERE se.kind=e.kind AND se.row_key=e.row_key AND s.complete
            ) ORDER BY e.available_at, e.row_key
        """,
            [kind, identity, provider],
        ).fetchall()

    def price_view(
        self,
        instrument_id: str,
        provider: str,
        when: datetime,
        adjustment: str,
        *,
        currency: str | None = None,
    ) -> PriceView:
        rows = [_price_decode(row[0]) for row in self._rows("price", instrument_id, provider)]
        rows = [row for row in rows if row.adjustment == adjustment]
        if currency is not None:
            rows = [row for row in rows if row.instrument.currency == currency]
        if len({row.instrument.currency for row in rows}) > 1:
            raise ValueError("currency selection is required for multiple quote currencies")
        return price_view_as_of(rows, when, adjustment=adjustment)

    def macro_view(
        self, indicator: str, when: datetime, source: str
    ) -> tuple[MacroObservation, ...]:
        rows = [_macro_decode(row[0]) for row in self._rows("macro", indicator, source)]
        return as_of(rows, indicator, when, source=source)
