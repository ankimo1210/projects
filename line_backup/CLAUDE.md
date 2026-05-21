# LINE Backup Exporter — Claude Code Guide

## Purpose

Local-only CLI tool to analyze iPhone backup data for LINE messages.
**No network calls. Read-only access to backups. No destructive operations.**

## Running & Testing

```bash
# Tests (no venv needed)
PYTHONPATH=src python3 -m unittest discover tests -v

# CLI (no install)
PYTHONPATH=src python3 -m line_backup_exporter.cli <subcommand> --help

# Install (use venv)
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

## Architecture

```
src/line_backup_exporter/
  models.py          # Dataclasses only — no logic
  safety.py          # Path traversal guard, filename sanitizer, text redactor
  utils.py           # Logger factory, CSV writer, text table printer
  backup_locator.py  # Enumerate OS default backup directories → BackupInfo list
  manifest.py        # Open Manifest.db (read-only), filter LINE files, write CSV+JSON
  extractor.py       # Copy SQLite blobs from backup → output/extracted/
  sqlite_inspector.py# Table/column/sample enumeration → Markdown report
  line_detector.py   # Keyword scoring to guess message/room/contact/attachment tables
  exporter.py        # Raw table CSV export + normalized message CSV with timestamp guessing
  html_renderer.py   # XSS-safe HTML from normalized CSV, split by chat_id
  cli.py             # argparse subparsers — thin glue only, no business logic
```

## Critical Constraints — Never Violate

- Always call `safety.ensure_within_directory(backup_dir, src)` before reading any file resolved from `fileID`.
- SQLite table names must be validated against `sqlite_master` before use in queries. Never interpolate user input directly into SQL.
- Output goes to `--out DIR` only. Never write outside that directory.
- Do not read or log message content in bulk. Use `redact_text(..., 80)` for display.
- `check_encrypted()` must be called at the start of any command that opens the backup.

## Do Not Read By Default

- `output/` — contains personal data and generated artifacts
- `*.sqlite`, `*.db`, `*.csv`, `*.json`, `*.html` — user data or generated output
- Any file matching `.gitignore`

## Key Patterns

- All SQLite connections: `sqlite3.connect("file:...?mode=ro", uri=True)` wrapped in `contextlib.closing`.
- Table name quoting: `f'SELECT * FROM "{table}"'` after allow-list check.
- File copies: `shutil.copy2`, destination via `unique_path()` to avoid overwrite.
- Timestamp guessing: `exporter.guess_timestamp()` handles Unix-s, Unix-ms, Mac absolute time, ISO string.

## CLI Subcommands

| Command | Key args |
|---|---|
| `list-backups` | *(none)* |
| `scan-line` | `--backup-dir --out` |
| `extract-candidates` | `--backup-dir --manifest-csv --out` |
| `inspect-db` | `--db --out --sample-rows` |
| `export-raw-table` | `--db --table --out --limit` |
| `export-line-csv` | `--db --message-table --out [column overrides]` |
| `render-html` | `--messages-csv --out --split-by-chat` |

## Actual LINE DB Schema (verified 2026-05-09)

Backup: `00008140-000A1D881E79801C` (non-encrypted, iOS backup)
Main DB: `output/extracted/AppDomainGroup-group.com.linecorp.line__Line.sqlite`

### Key tables in Line.sqlite

| Table | Rows | Role |
|---|---|---|
| `ZMESSAGE` | 377,631 | メッセージ本体 |
| `ZCHAT` | 1,031 | チャットルーム |
| `ZUSER` | 3,886 | ユーザー/連絡先 |
| `ZGROUP` | 13 | 現在参加中グループのみ |

### ZMESSAGE 重要カラム

- `Z_PK` — message_id
- `ZTIMESTAMP` — **Unix ミリ秒**（`guess_timestamp` で正しく処理される）
- `ZCHAT` — FK → ZCHAT.Z_PK
- `ZSENDER` — FK → ZUSER.Z_PK。**NULL = 自分の発言**
- `ZTEXT` — 本文
- `ZCONTENTTYPE` — 0=テキスト, 1=画像, 2=動画, 6=通話, 7=スタンプ, 107=URL, 112=画像通知

### ZCHAT 重要カラム

- `ZTYPE` — 0=1対1, 2=グループ
- `ZMID` — ZUSER.ZMID (1対1) or ZGROUP.ZID/ZUNIFIEDGROUP.ZID (グループ) に対応

### グループ名の解決順序

1. `ZGROUP.ZID = ZCHAT.ZMID` → `ZGROUP.ZNAME`（現在参加中の13グループのみ）
2. `ZUNIFIEDGROUP.ZID = ZCHAT.ZMID` → `ZUNIFIEDGROUP.ZNAME`（UnifiedGroup.sqlite）
3. 解決不能な場合は ZMID をそのまま使う（実績: 1件のみ）

### 正規化済み出力ファイル

- `output/line_messages_with_names.csv` — 名前解決済み全377,631件
- `output/html/index.html` — バブルUIチャット別HTML（895チャット）

## Adding a New Module

1. Add dataclasses to `models.py` if new data shapes are needed.
2. Implement logic in a focused module; keep functions small.
3. Wire into `cli.py` as a new subcommand handler (`_cmd_*` pattern).
4. Add a `tests/test_<module>.py` using `unittest` and `tempfile`.
