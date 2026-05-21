from __future__ import annotations
import csv
import sqlite3
from contextlib import closing
from pathlib import Path

from .line_detector import classify
from .models import ColumnInfo, TableInfo
from .safety import confirm_output_dir, redact_text
from .utils import get_logger

logger = get_logger(__name__)


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cur.fetchall()]


def _get_columns(conn: sqlite3.Connection, table: str) -> list[ColumnInfo]:
    with closing(conn.cursor()) as cur:
        cur.execute(f'PRAGMA table_info("{table}")')
        return [
            ColumnInfo(name=row["name"], type=row["type"], is_pk=bool(row["pk"]))
            for row in cur.fetchall()
        ]


def _get_row_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            row = cur.fetchone()
            return row[0] if row else None
    except sqlite3.OperationalError as e:
        logger.warning("COUNT(*) failed for table %r: %s", table, e)
        return None


def _get_sample_rows(conn: sqlite3.Connection, table: str, limit: int) -> list[tuple]:
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(f'SELECT * FROM "{table}" LIMIT {limit}')
            return [tuple(row) for row in cur.fetchall()]
    except sqlite3.OperationalError as e:
        logger.warning("Sample query failed for table %r: %s", table, e)
        return []


def inspect(db_path: Path, out_dir: Path, sample_rows: int = 5) -> list[TableInfo]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    samples_dir = confirm_output_dir(out_dir / "table_samples")

    with closing(_open_readonly(db_path)) as conn:
        table_names = _get_tables(conn)
        tables: list[TableInfo] = []

        for name in table_names:
            columns = _get_columns(conn, name)
            row_count = _get_row_count(conn, name)
            samples = _get_sample_rows(conn, name, sample_rows)

            ti = TableInfo(name=name, columns=columns, row_count=row_count, sample_rows=samples)
            tables.append(ti)

            # Write sample CSV (raw values, no redaction)
            if samples and columns:
                sample_csv = samples_dir / f"{name}.csv"
                with sample_csv.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([c.name for c in columns])
                    writer.writerows(samples)

    candidates = classify(tables)
    _write_report(db_path, tables, candidates, out_dir)

    return tables


def _write_report(
    db_path: Path,
    tables: list[TableInfo],
    candidates,
    out_dir: Path,
) -> None:
    report_path = out_dir / "db_schema_report.md"

    lines: list[str] = [
        f"# DB Schema Report\n",
        f"**Source:** `{db_path}`\n",
        f"**Tables:** {len(tables)}\n",
        "",
    ]

    # Candidate summary
    lines.append("## Estimated Table Candidates\n")
    for label, names in [
        ("Message table candidates", candidates.messages),
        ("Chat/room table candidates", candidates.rooms),
        ("Contact/member table candidates", candidates.contacts),
        ("Attachment/media table candidates", candidates.attachments),
    ]:
        joined = ", ".join(f"`{n}`" for n in names) if names else "*(none)*"
        lines.append(f"- **{label}:** {joined}")
    lines.append("")

    # Per-table details
    lines.append("## Table Details\n")
    for ti in tables:
        row_cnt = str(ti.row_count) if ti.row_count is not None else "unknown"
        lines.append(f"### `{ti.name}` — {row_cnt} rows\n")

        # Column table
        lines.append("| Column | Type | PK |")
        lines.append("|--------|------|----|")
        for col in ti.columns:
            pk_mark = "✓" if col.is_pk else ""
            lines.append(f"| `{col.name}` | {col.type} | {pk_mark} |")
        lines.append("")

        # Sample rows (with redaction for display)
        if ti.sample_rows and ti.columns:
            lines.append("**Sample rows (truncated to 80 chars):**\n")
            col_names = [c.name for c in ti.columns]
            lines.append("| " + " | ".join(col_names) + " |")
            lines.append("|" + "|".join("---" for _ in col_names) + "|")
            for row in ti.sample_rows:
                cells = [redact_text(v, 80) for v in row]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")

    with report_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Schema report written to %s", report_path)
