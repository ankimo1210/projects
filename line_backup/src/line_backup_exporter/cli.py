from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _cmd_list_backups(args: argparse.Namespace) -> None:
    from .backup_locator import list_backups
    from .utils import print_table

    backups = list_backups()
    if not backups:
        print("No iPhone backups found in default locations.")
        print("Use iTunes / Apple Devices to create a local backup first.")
        return

    headers = ["backup_id", "updated_at", "manifest_db", "manifest_plist", "encrypted", "path"]
    rows = [
        [
            b.backup_id,
            b.updated_at,
            "✓" if b.has_manifest_db else "✗",
            "✓" if b.has_manifest_plist else "✗",
            "YES ⚠" if b.likely_encrypted else "no",
            str(b.path),
        ]
        for b in backups
    ]
    print_table(headers, rows)


def _cmd_scan_line(args: argparse.Namespace) -> None:
    from .manifest import scan_line_files, check_encrypted
    from .safety import confirm_output_dir

    backup_dir = Path(args.backup_dir).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())

    if check_encrypted(backup_dir):
        print(
            "[ERROR] This backup is encrypted.\n"
            "Encrypted backups are not supported. Disable encryption in iTunes/Finder "
            "and create a new backup.",
            file=sys.stderr,
        )
        sys.exit(2)

    ranked = scan_line_files(backup_dir, out_dir)
    if not ranked:
        print("No LINE-related files found.")
        return

    print(f"\nFound {len(ranked)} LINE-related file(s). Showing top 50:\n")
    print(f"{'#':<4} {'domain':<40} {'relative_path':<60} {'file_id'}")
    print("-" * 120)
    for i, e in enumerate(ranked[:50], 1):
        rp = e.relative_path[:58] + ".." if len(e.relative_path) > 60 else e.relative_path
        dom = e.domain[:38] + ".." if len(e.domain) > 40 else e.domain
        print(f"{i:<4} {dom:<40} {rp:<60} {e.file_id}")

    print(f"\nCSV: {out_dir / 'manifest_line_files.csv'}")
    print(f"JSON: {out_dir / 'manifest_line_files.json'}")


def _cmd_extract_candidates(args: argparse.Namespace) -> None:
    from .extractor import extract_candidates
    from .safety import confirm_output_dir

    backup_dir = Path(args.backup_dir).resolve()
    manifest_csv = Path(args.manifest_csv).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())

    index = extract_candidates(backup_dir, manifest_csv, out_dir)
    print(f"\nExtracted {len(index)} file(s) to {out_dir / 'extracted'}/")
    for item in index:
        print(f"  {item['original_relative_path']} → {item['copied_to']}")
    print(f"\nIndex: {out_dir / 'extracted_index.csv'}")


def _cmd_inspect_db(args: argparse.Namespace) -> None:
    from .sqlite_inspector import inspect
    from .safety import confirm_output_dir

    db_path = Path(args.db).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())
    sample_rows = args.sample_rows

    tables = inspect(db_path, out_dir, sample_rows)
    print(f"\nInspected {len(tables)} table(s) in {db_path.name}")
    print(f"{'Table':<40} {'Rows':>10}  Columns")
    print("-" * 70)
    for ti in tables:
        row_cnt = str(ti.row_count) if ti.row_count is not None else "?"
        cols = ", ".join(c.name for c in ti.columns[:6])
        if len(ti.columns) > 6:
            cols += f" ... (+{len(ti.columns)-6})"
        print(f"{ti.name:<40} {row_cnt:>10}  {cols}")

    print(f"\nReport: {out_dir / 'db_schema_report.md'}")
    print(f"Samples: {out_dir / 'table_samples'}/")


def _cmd_export_raw_table(args: argparse.Namespace) -> None:
    from .exporter import export_raw_table
    from .safety import confirm_output_dir

    db_path = Path(args.db).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())
    limit = args.limit

    out_path = export_raw_table(db_path, args.table, out_dir, limit)
    print(f"Exported → {out_path}")


def _cmd_export_line_csv(args: argparse.Namespace) -> None:
    from .exporter import export_normalized
    from .safety import confirm_output_dir

    db_path = Path(args.db).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())

    overrides: dict[str, str | None] = {}
    if args.chat_id_col:
        overrides["chat_id"] = args.chat_id_col
    if args.sender_id_col:
        overrides["sender_id"] = args.sender_id_col
    if args.timestamp_col:
        overrides["timestamp"] = args.timestamp_col
    if args.text_col:
        overrides["text"] = args.text_col
    if args.type_col:
        overrides["type"] = args.type_col

    out_path = export_normalized(db_path, args.message_table, out_dir, overrides or None)
    print(f"Normalized CSV → {out_path}")


def _cmd_render_html(args: argparse.Namespace) -> None:
    from .html_renderer import render
    from .safety import confirm_output_dir

    messages_csv = Path(args.messages_csv).resolve()
    out_dir = confirm_output_dir(Path(args.out).resolve())
    split = args.split_by_chat.lower() not in ("false", "0", "no")

    index_path = render(messages_csv, out_dir, split_by_chat=split)
    print(f"HTML index → {index_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="line-backup-exporter",
        description="Local iPhone backup LINE data analyzer (read-only, offline)",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # list-backups
    sub.add_parser("list-backups", help="List iPhone backups in default locations")

    # scan-line
    p = sub.add_parser("scan-line", help="Scan Manifest.db for LINE-related files")
    p.add_argument("--backup-dir", required=True, metavar="PATH",
                   help="Path to iPhone backup directory")
    p.add_argument("--out", required=True, metavar="DIR",
                   help="Output directory")

    # extract-candidates
    p = sub.add_parser("extract-candidates", help="Copy SQLite DB candidates from backup")
    p.add_argument("--backup-dir", required=True, metavar="PATH")
    p.add_argument("--manifest-csv", required=True, metavar="PATH",
                   help="manifest_line_files.csv from scan-line")
    p.add_argument("--out", required=True, metavar="DIR")

    # inspect-db
    p = sub.add_parser("inspect-db", help="Inspect a SQLite DB schema and generate report")
    p.add_argument("--db", required=True, metavar="PATH")
    p.add_argument("--out", required=True, metavar="DIR")
    p.add_argument("--sample-rows", type=int, default=5, metavar="INT")

    # export-raw-table
    p = sub.add_parser("export-raw-table", help="Export a raw table to CSV")
    p.add_argument("--db", required=True, metavar="PATH")
    p.add_argument("--table", required=True, metavar="TABLE")
    p.add_argument("--out", required=True, metavar="DIR")
    p.add_argument("--limit", type=int, default=None, metavar="INT")

    # export-line-csv
    p = sub.add_parser("export-line-csv", help="Export normalized LINE messages CSV")
    p.add_argument("--db", required=True, metavar="PATH")
    p.add_argument("--message-table", required=True, metavar="TABLE")
    p.add_argument("--out", required=True, metavar="DIR")
    p.add_argument("--chat-id-col", default=None)
    p.add_argument("--sender-id-col", default=None)
    p.add_argument("--timestamp-col", default=None)
    p.add_argument("--text-col", default=None)
    p.add_argument("--type-col", default=None)

    # render-html
    p = sub.add_parser("render-html", help="Render normalized CSV to HTML")
    p.add_argument("--messages-csv", required=True, metavar="PATH")
    p.add_argument("--out", required=True, metavar="DIR")
    p.add_argument("--split-by-chat", default="true", metavar="BOOL")

    return parser


_COMMANDS = {
    "list-backups": _cmd_list_backups,
    "scan-line": _cmd_scan_line,
    "extract-candidates": _cmd_extract_candidates,
    "inspect-db": _cmd_inspect_db,
    "export-raw-table": _cmd_export_raw_table,
    "export-line-csv": _cmd_export_line_csv,
    "render-html": _cmd_render_html,
}


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    try:
        handler(args)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
