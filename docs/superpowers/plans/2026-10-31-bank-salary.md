# Bank Salary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 3社の NY 州を含む公開求人を収集し、出典と変更履歴を持つローカル給与データベースと更新コードを提供する。

**Architecture:** 公開採用システムのページ送りと詳細取得を会社別 adapter に分離し、給与原文を保守的に抽出する。SQLite に観測と run ごとの一覧を保存し、最新 run の CSV と検証結果を出す。

**Tech Stack:** Python 3.12+ standard library, SQLite, unittest; production dependencies = 0.

**Spec:** `docs/superpowers/specs/2026-10-31-bank-salary-design.md` (user approved 2026-10-31)

## Global Constraints

- 新しい本番依存を追加しない。
- 実データは `/home/kazumasa/projects/_data/bank-salary/`。コードは `bank-salary/` のみ。
- 未記載単位は `unspecified`。年換算や賞与推定は行わない。
- 同じ求人の異なる地域のレンジを合成しない。
- 不完全な取得で募集終了と判定しない。公開・外部送信・自動スケジュール設定はしない。

## Review Focus

1. 単位なしの小額給与を年俸と断定しない（Task 1）。
2. AUM や売上のドル額を給与と誤認しない（Task 1）。
3. API の別名と実サイト番号を取り違えない（Task 3）。
4. ページの重複、結果件数の変動、詳細失敗で完全取得と主張しない（Task 3）。
5. 同じ run の履歴・変更前データ・取得失敗求人が CSV で混在しない（Task 2/3）。

## File Structure

`bank_salary/parsing.py`: HTML 本文と給与抽出。`sources.py`: HTTP、公開サイト発見、検索と詳細、正規化。`storage.py`: SQLite 履歴・CSV・品質検証。`cli.py`: collect/export/validate。`collect.py`: 入口。`tests/`: 原文と障害を使うテスト。`README.md` と `docs/STATUS.md`: 操作方法と検証証拠。

### Task 1: Conservative salary parsing

**Files:** Create `bank-salary/bank_salary/{__init__,parsing}.py`, `bank-salary/tests/test_parsing.py`.

**Interfaces:** `text_from_html(html: str) -> str`; `extract_salary(company: str, description: str, fields: list[dict]) -> list[dict]`. Each range carries min/max, currency, period, region, evidence and parse_status.

- [x] Write and run failing tests: MS `$150,000 and $225,000 per year`, fixed amounts, hourly pay, GS region-specific base salary, JPM semicolon-separated ranges, unspecified unit, AUM false positives, inverted ranges.
- [x] Implement extraction; preserve raw evidence and unknown units. Run `PYTHONPATH=bank-salary python3 -m unittest discover -s bank-salary/tests -p test_parsing.py -v`; expected all pass.

### Task 2: Auditable SQLite history and exports

**Files:** Create `bank-salary/bank_salary/storage.py`, `bank-salary/tests/test_storage.py`.

**Interfaces:** `Store(path)`; `start_run(config) -> int`; `save(run_id, job, payload) -> int`; `record_listing(run_id, company, ids, complete)`; `finish_run(run_id, status, report)`; `export(run_id, directory)`; `validate(run_id) -> dict`.

- [x] Write/run failing tests proving unchanged content reuses observations, changed salaries preserve old observations, failed details remain visible, missing listings are only marked absent after a complete comparable scan, and export matches this run.
- [x] Implement normalized observations, compressed source JSON, source hashes, listing membership, salary children and export. Run project unittest suite; expected all pass.

### Task 3: Official collectors and CLI

**Files:** Create `bank-salary/bank_salary/{sources,cli}.py`, `bank-salary/collect.py`, `bank-salary/tests/test_sources.py`, documentation.

**Interfaces:** `HttpClient.request(url, data=None) -> dict`; `WorkdaySource.list_jobs()/detail(item)`; `OracleSource.list_jobs()/detail(item)`; `EightfoldSource.list_jobs()/detail(item)`. Listing includes expected/unique counts, errors and verification count.

- [x] Test multi-page iteration with duplicate/missing pages and changed counts using a bounded fake HTTP source; verify site discovery uses active metadata numbers rather than aliases.
- [x] Implement bounded retries, per-host throttling, source reconciliation, streaming observations and progress output. Oracle scans active Lateral/Campus or JPMC/Chase/Alumni; Workday is MS primary, Eightfold supplies a separately labelled cross-check and any verified NY supplements.
- [x] Run `python3 bank-salary/collect.py --help` and complete unittest suite; expected success.
- [x] Run initial collect for all 3 companies; save source-specific coverage and limitations. Estimate <200 MB disk, <300 MB memory; measure actual `du -sh`.
- [x] Validate SQLite integrity, run membership, salary evidence, CSV counts and amounts, official samples, and idempotent offline re-export. Expected successful checks; unresolved source coverage stays explicitly qualified.
- [x] Request one independent code review; address important findings with regression tests, then update README/STATUS and completion evidence.

## Execution decisions

- The user approved implementation and initial collection; routine planning choices do not introduce another approval round. Execute inline.
- Work is confined to a new project directory; do not modify unrelated files or make commits/pushes as part of this task. Progress is kept in `bank-salary/docs/STATUS.md`, following workspace policy rather than a separate append-only skill diary.
