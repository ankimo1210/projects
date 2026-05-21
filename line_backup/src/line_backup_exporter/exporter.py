from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .line_detector import guess_message_columns
from .safety import confirm_output_dir
from .utils import get_logger, write_csv

logger = get_logger(__name__)

# Mac absolute time epoch: 2001-01-01 00:00:00 UTC
_MAC_EPOCH = datetime(2001, 1, 1, tzinfo=UTC).timestamp()
# Plausible range for "seconds since Mac epoch" (2001-01-01 ~ 2050-01-01)
_MAC_TS_MIN = 0
_MAC_TS_MAX = 1_546_300_800  # roughly 2050 from Mac epoch

# Unix seconds: 2000-01-01 to 2050-01-01
_UNIX_S_MIN = 946_684_800
_UNIX_S_MAX = 2_524_608_000

# Unix milliseconds: same range * 1000
_UNIX_MS_MIN = _UNIX_S_MIN * 1000
_UNIX_MS_MAX = _UNIX_S_MAX * 1000


def guess_timestamp(raw: Any) -> str:
    """Convert a raw timestamp value to ISO-8601 string. Returns '' on failure."""
    if raw is None:
        return ""
    # String ISO attempt
    if isinstance(raw, str):
        raw_str = raw.strip()
        if not raw_str:
            return ""
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw_str, fmt).isoformat()
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(raw_str).isoformat()
        except ValueError:
            pass
        # Maybe it's a numeric string
        try:
            raw = float(raw_str)
        except ValueError:
            return ""

    if not isinstance(raw, (int, float)):
        return ""

    val = float(raw)

    # Unix milliseconds
    if _UNIX_MS_MIN <= val <= _UNIX_MS_MAX:
        try:
            return datetime.fromtimestamp(val / 1000, tz=UTC).isoformat()
        except (OSError, OverflowError):
            pass

    # Unix seconds
    if _UNIX_S_MIN <= val <= _UNIX_S_MAX:
        try:
            return datetime.fromtimestamp(val, tz=UTC).isoformat()
        except (OSError, OverflowError):
            pass

    # Mac absolute time (seconds since 2001-01-01)
    if _MAC_TS_MIN <= val <= _MAC_TS_MAX:
        try:
            return datetime.fromtimestamp(val + _MAC_EPOCH, tz=UTC).isoformat()
        except (OSError, OverflowError):
            pass

    return ""


def _allowed_tables(conn: sqlite3.Connection) -> set[str]:
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row[0] for row in cur.fetchall()}


def export_raw_table(
    db_path: Path,
    table: str,
    out_dir: Path,
    limit: int | None = None,
) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    raw_dir = confirm_output_dir(out_dir / "raw_tables")
    out_path = raw_dir / f"{table}.csv"

    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        allowed = _allowed_tables(conn)
        if table not in allowed:
            raise ValueError(f"Table {table!r} not found. Available: {sorted(allowed)}")

        sql = f'SELECT * FROM "{table}"'
        if limit is not None:
            sql += f" LIMIT {limit}"

        with closing(conn.cursor()) as cur:
            cur.execute(sql)
            col_names = [d[0] for d in cur.description]
            rows = cur.fetchall()

    write_csv(out_path, rows, col_names)
    logger.info("Exported %d rows from %r to %s", len(rows), table, out_path)
    return out_path


def export_normalized(
    db_path: Path,
    message_table: str,
    out_dir: Path,
    col_overrides: dict[str, str | None] | None = None,
) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    out_path = out_dir / "line_messages_normalized.csv"
    source_db = db_path.name

    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row

        allowed = _allowed_tables(conn)
        if message_table not in allowed:
            raise ValueError(f"Table {message_table!r} not found. Available: {sorted(allowed)}")

        with closing(conn.cursor()) as cur:
            cur.execute(f'PRAGMA table_info("{message_table}")')
            col_names = [row["name"] for row in cur.fetchall()]

        guessed = guess_message_columns(col_names)
        if col_overrides:
            guessed.update(col_overrides)

        logger.info("Column mapping: %s", guessed)

        sql = f'SELECT * FROM "{message_table}"'
        with closing(conn.cursor()) as cur:
            cur.execute(sql)
            raw_rows = cur.fetchall()

    headers = [
        "source_db",
        "message_id",
        "chat_id",
        "sender_id",
        "timestamp_raw",
        "timestamp_iso_guess",
        "message_type",
        "text",
    ]

    def _get(row, col_key: str) -> Any:
        col = guessed.get(col_key)
        if col and col in row.keys():
            return row[col]
        return None

    out_rows: list[list] = []
    for row in raw_rows:
        ts_raw = _get(row, "timestamp")
        out_rows.append(
            [
                source_db,
                _get(row, "message_id"),
                _get(row, "chat_id"),
                _get(row, "sender_id"),
                ts_raw,
                guess_timestamp(ts_raw),
                _get(row, "type"),
                _get(row, "text"),
            ]
        )

    write_csv(out_path, out_rows, headers)
    logger.info("Exported %d normalized messages to %s", len(out_rows), out_path)
    print(f"Exported {len(out_rows)} rows → {out_path}")
    return out_path
