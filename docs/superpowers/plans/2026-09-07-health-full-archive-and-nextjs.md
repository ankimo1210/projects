# Health Full Archive and Next.js Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Google Health の取得可能な本人データを元の粒度で全量保存し、取得不能を明示したうえで既存7画面を Next.js へ移す。

**Architecture:** Python が OAuth、原本保存、取得範囲の台帳、typed projection、静的 export を所有する。受信ページは解析前に可逆圧縮して保存し、取得の完了と表示用変換の完了を分ける。Next.js は同じ export generation の JSON を読むローカル静的 UI とする。

**Tech Stack:** Python >=3.12 / requests / DuckDB / pandas / scipy / stdlib gzip, hashlib, argparse, http.server。Next.js 16 系のサポート対象 patch / TypeScript / Tailwind CSS v4 / shadcn/ui / Recharts / npm。Vitest は dev dependency。

**Spec:** `docs/superpowers/specs/2026-09-06-health-full-archive-and-nextjs-design.md`

## Global constraints

- 全データを元の粒度で保存する。容量を理由とする削除・間引き・保持期間の切り詰めは禁止。
- Python >=3.12。既存の auth/client/store/sync/analytics の有用な契約とテストを維持する。
- OAuth・同期・Web データの書き出しは Python CLI。Next.js は読み取り専用。
- 単一ユーザー、ローカル専用。公開・クラウド保存・リモートデプロイは含めない。
- UI は日本語。コード、識別子、commit message は英語。
- 実データ・token・認可コード・probe 結果は git に追加しない。自動テストは架空 fixture と fake HTTP のみ。
- 新しい型すべての typed parser、新規の健康分析、E2E テスト基盤は今回の対象外。
- readonly API で取得不能な対象は失敗/未確認として残す。他の取得と UI 作業を止めず、全件完了を装わない。
- 日時と範囲の semantics、source identity、未知の JSON 属性を生保存時に変えない。

## Execution context and gates

作業場所は `/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs`、branch は `codex/health-full-archive-nextjs`、基準 commit は `6cb0a94d`。元の checkout の branch を切り替えない。ここには実 DB/token/.env をコピーしていない。

2026-09-07 の基準確認:

```bash
# original workspace root から既存 venv を使った基準テスト
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src uv run --no-sync pytest /home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/tests -q
# 258 passed in 77.34s
```

実装時は選択した worktree の repo root から uv を実行する。依存同期は `uv sync --package health`。テストと fixture に実 DB の path を渡さない。live 運用時だけ `--data-dir /home/kazumasa/projects/health/data --env-file /home/kazumasa/projects/health/.env` を明示する。

この計画は単一 spec の依存する4段階を扱う。P1/P2/P3/P4 は別々に検証・commit できるが、型の公開状況やアカウント権限の失敗だけで後続段階を止めない。実アカウントの成功確認と、fake HTTP での機能検証を別々に報告する。

## Verified references and unresolved live evidence

- [Google data types](https://developers.google.com/health/data-types): 2026-09-07 に43行を観測。既存ローカル35型を全体と扱わない。取得 method がない型もある。
- [list](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list): 元 data point の取得、filter/pagination。sleep/ECG には専用の時間条件がある。
- [reconcile](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile): source を統合する値。元 source 全量の代用にしない。
- [dailyRollUp](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp)、[quotas](https://developers.google.com/health/rate-limits)、[setup](https://developers.google.com/health/setup): 実装時の request limit / scope / OAuth の契約確認先。
- [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard): MIT の shell を採用。取得 commit と license を保存。
- [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports): output export を使用。API route と request 時の server 処理を持ち込まない。

この計画作成では live Health API を呼んでいない。個人データの有無、filter 省略時の全履歴性、最古の日付、各型の request 範囲上限は P1 の証拠で分類する。未確認を推測で埋めない。

## File map

| Files | Responsibility |
|---|---|
| `health/src/health/source_catalog.py`, `source_catalog.json` | 公開取得対象、method/filter/scope/検証根拠。型と stream を区別 |
| `health/docs/google-health-source-contracts.md` | 公式 URL・確認日・取得方式の表。個人データを記載しない |
| `health/src/health/archive.py` | 圧縮 object の private atomic write と復元 |
| `health/src/health/archive_index.py` | 同じ Store connection を使う attempt/page/work/coverage 台帳 |
| `health/src/health/archive_sync.py` | 全量列挙、ページ再開、公平な scheduler、失敗分類 |
| `health/src/health/client.py`, `probe.py` | 生レスポンス観測、取得 method と probe の拡張 |
| `health/src/health/endpoints.py`, `store.py`, `sync.py` | projection 保存先と履歴方針の分離、既存 typed 同期の互換性 |
| `health/src/health/cli.py`, `oauth_loopback.py` | auth/sync/export-web の入口と callback |
| `health/src/health/web_analytics.py`, `web_export.py` | 期間付き分析契約と一貫した export generation |
| `health/web/src/lib/{data,downsample}.ts` | JSON contract/loader と描画用間引き |
| `health/web/src/components/` | shell、期間選択、チャート、データ状態表示 |
| `health/web/src/app/{page,layout}.tsx` と各 route | 日本語7画面。feature 固有コードは route に併置 |
| `health/web/THIRD_PARTY_NOTICES.md` | テンプレートの出典・commit・MIT notice |
| `health/tests/test_{source_catalog,archive,archive_index,archive_sync,cli,oauth_loopback,web_analytics,web_export}.py` | 取得完全性・保存・CLI・export の意味のある回帰検証 |
| `health/web/src/lib/{data,downsample}.test.ts` | loader の失敗/整合性と間引きの不変条件 |
| `health/README.md`, `health/AGENTS.md`, `health/CLAUDE.md`, `health/.gitignore`, `health/pyproject.toml`, `Makefile` | 運用・契約・依存・チェックの統合 |

AGENTS.md と CLAUDE.md の symlink/同一実体を確認して二重編集を避ける。root の unrelated project を変更しない。

## P1 — Catalog and transport

### Task 1: Enumerate supported and unavailable sources

**Files:** Create source_catalog.py/json, google-health-source-contracts.md, test_source_catalog.py. Modify endpoints.py の KNOWN_DATA_TYPES と inventory.py の型一覧生成。

**Interfaces:** `load_sources() -> tuple[SourceSpec, ...]`; `SourceSpec` は下記。`methods` は公式 method 名、`preferred_method=None` は取得不能/未確認。URL から自動的に method を推測しない。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SourceSpec:
    key: str                         # type + method + source/detail kind の一意 key
    data_type: str
    label: str
    path: str                        # 固定の公式 v4 resource path
    methods: tuple[str, ...]
    preferred_method: str | None
    readonly_scopes: tuple[str, ...]
    filter_kind: str                  # none/civil_interval/civil_sample/daily/sleep_end/ecg_start
    filter_field: str | None
    page_size: int
    max_range_days: int | None        # 未確認は None; 当て推量で送信しない
    unbounded_verified: bool
    representation: str              # source/reconciled/aggregate/reference/metadata
    availability: str                # candidate/unsupported/unverified
    evidence_url: str
    checked_at: str
```

- [ ] 公式型一覧と既存 KNOWN_DATA_TYPES の和集合を表にする。新しい型、既存のみの型、write-only 型を消さない。公開一覧の固定件数をテストに埋め込まない。
- [ ] list/get/reconcile/rollup の違い、source detail の有無、profile/paired devices 等の本人 resource、共有 food reference を個別に分類する。get が詳細を補うものは別 stream として登録する。
- [ ] fixture JSON から load_sources を検証する。readonly scope 以外を要求する定義を拒否し、取得不能型も結果に残す。

```python
from health.source_catalog import load_sources

def test_archive_catalog_keeps_unavailable_types_visible():
    sources = load_sources()
    assert len({s.key for s in sources}) == len(sources)
    assert any(s.data_type == "heart-rate" and s.preferred_method == "list" for s in sources)
    assert any(s.availability != "candidate" for s in sources)
    assert all(scope.endswith(".readonly") for s in sources for scope in s.readonly_scopes)
    assert all(s.evidence_url.startswith("https://developers.google.com/") for s in sources)
```

- [ ] `uv run --no-sync pytest health/tests/test_source_catalog.py -q` を先に実行して未実装を確認し、JSON loader と型検証を実装して通す。
- [ ] 続けて既存 `test_endpoints.py test_inventory.py` を実行する。KNOWN_DATA_TYPES の scope は既存3種限定ではなくなる。未確認状態を「表示対応済み」にしない。
- [ ] 対象ファイルだけ commit: `feat(health): catalog official archive sources and limitations`。

### Task 2: Add a lossless private response store

**Files:** Create archive.py, test_archive.py. Reuse privacy.py の ensure_private_dir。

**Interfaces:** `Archive(root: Path)`, `put(body: bytes) -> ObjectRef`, `read(ref: ObjectRef) -> bytes`; `ObjectRef(sha256: str, relative_path: str, byte_count: int)`。root は data/archive。

- [ ] 以下の byte roundtrip、未知属性、同一時刻の複数 source をそのまま保持するテストを書く。

```python
from health.archive import Archive

def test_archive_preserves_body_bytes_and_observed_versions(tmp_path):
    archive = Archive(tmp_path / "archive")
    first = b'{"dataPoints":[{"source":"a","ts":1},{"source":"b","ts":1}],"unknown":1.00}\n'
    second = b'{"dataPoints":[],"unknown":2}\n'
    old = archive.put(first)
    new = archive.put(second)
    assert old.sha256 != new.sha256
    assert archive.read(old) == first
    assert archive.read(new) == second
    assert archive.put(first) == old
```

- [ ] 対象テストを実行して未実装を確認する。
- [ ] sha256(body)、gzip.compress(body, mtime=0)、同じ filesystem 内の0600 temp file、fsync、rename、directory fsync を実装する。既存 object は内容 hash を検証し、黙って上書きしない。

```python
# serialization core; directory/atomicity/permissions は put が所有する
import gzip
import hashlib

def encode_body(body: bytes) -> tuple[str, bytes]:
    return hashlib.sha256(body).hexdigest(), gzip.compress(body, mtime=0)
```

- [ ] filesystem write の ENOSPC と rename 直前の失敗を注入し、旧 object が残る・新 object が完成扱いにならない・temp も private であることを確認する。compression/hash のみを模倣するテストで終えない。
- [ ] `uv run --no-sync pytest health/tests/test_archive.py health/tests/test_privacy.py -q` を通し、`feat(health): retain original response bodies losslessly` を commit。

### Task 3: Add archival attempts and precise coverage

**Files:** Create archive_index.py, test_archive_index.py. Modify store.py は必要な初期化/呼出しだけ。

**Interfaces:** `ArchiveIndex(con)` は Store.con を借りる。`start(stream_id, request, representation) -> str` は attempt ID、`record_page(attempt_id, page_seq, ref, status_code, point_count)`、`save_cursor(stream_id, request, token, attempt_id)`、`finish(attempt_id, status, reason=None)`、`coverage() -> list[dict]`。request は Task 4 の RequestSpec を JSON にしたもの。coverage と cursor は成功した範囲だけ更新する。

- [ ] 追加 schema を単一 transaction で作る。version を記録し、再実行可能にする。

```sql
CREATE TABLE IF NOT EXISTS archive_attempts (
  id VARCHAR PRIMARY KEY, stream_id VARCHAR, request_json JSON,
  representation VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
  status VARCHAR, reason VARCHAR
);
CREATE TABLE IF NOT EXISTS archive_pages (
  attempt_id VARCHAR, page_seq INTEGER, sha256 VARCHAR, object_path VARCHAR,
  byte_count BIGINT, http_status INTEGER, point_count BIGINT,
  PRIMARY KEY(attempt_id, page_seq)
);
CREATE TABLE IF NOT EXISTS archive_work (
  stream_id VARCHAR PRIMARY KEY, request_json JSON, page_token VARCHAR,
  attempt_id VARCHAR, next_visit BIGINT, state VARCHAR
);
```

- [ ] coverage は attempt の範囲・成功/空/未完了から導く。単なる min/max 日付の間をすべて取得済みと扱わない。過去の成功と最新失敗は両方表示する。
- [ ] 2ページ目が失敗する架空ケースを作り、1ページ目の object が残る・coverage は partial・前回成功範囲が残ることを検証する。
- [ ] 既存 raw_json は stream を legacy として非破壊で取り込む。`json.dumps` の保存であり wire bytes ではないと representation に記録する。空の既存 DB と複数回実行の migration を検証する。
- [ ] schema 変更を実 DB に適用する前に writer を閉じ、checkpoint 後に0600 backup を作成する。backup 不成功なら migration を始めない。DuckDB を開いた別プロセスを強制終了しない。
- [ ] `uv run --no-sync pytest health/tests/test_archive_index.py health/tests/test_store.py -q` を通し、`feat(health): track archival attempts and incomplete coverage` を commit。

### Task 4: Capture raw pages before parsing and probe every source

**Files:** Modify client.py, probe.py, scripts/probe_datatypes.py, tests/fakes.py, test_client.py, test_probe_datatypes.py. Add test_source_probe.py。

**Interfaces:** `RequestSpec(method: str, path: str, params: dict, body: dict | None)` は source_catalog.py に定義。`HealthClient.request_page(request, budget, *, capture=None) -> dict`、capture は `Callable[[bytes, int], None]`。既存 daily_rollup/iter_reconciled の返値は維持。HealthClient に既定の `response_observer(RequestSpec, bytes, status_code)` を追加して既存 projection も捕捉する。`run_source_probe(client, output_dir, sources, today, max_requests) -> dict` を probe.py に追加。

- [ ] FakeResponse に requests.Response.content 相当を追加し、JSON fixture を json.dumps で body にする。指定した bytes がある場合はそれを優先する。
- [ ] request_page は同じ _dispatch/pace/401 retry/budget を使う。各 Health response を capture/observer に渡してから _parse する。OAuth token endpoint は対象外。header 全体を保存しない。

```python
# _request 内の1レスポンスを扱う順序
response = self._dispatch(request.method, url, budget, **kwargs)
if capture is not None:
    capture(response.content, response.status_code)
# 401 refresh/retry でも各 response の capture を先に実行する
# JSON decode と API error の変換は既存 _parse の責務
```

- [ ] malformed JSON の200、403、page1成功/page2失敗、401再試行を検証する。取得原本が必ず残り、typed parse へ渡すのは成功データだけであること、物理sendがcapに含まれることを確認する。
- [ ] `--all-sources --max-requests 200` を既存 probe script に追加する。1型の通常エラーは継続、429/cap/auth失効は停止し未訪問を pending として manifest に残す。
- [ ] live probe は直近の狭い期間、30日より前、5年より前の独立した範囲を確認する。空はその query に限る。unbounded の意味や date boundary が確認不能なら unknown_history。公開文書と一致しない request を自動的に成功扱いしない。
- [ ] `uv run --no-sync pytest health/tests/test_client.py health/tests/test_probe_datatypes.py health/tests/test_source_probe.py -q` を通す。live probe は認可が利用可能な場合にだけ操作テストとして実行し、私有 manifest の要約状態だけ報告する。
- [ ] `feat(health): capture source responses and audit retrieval contracts` を commit。

## P2 — History, CLI, and existing projections

### Task 5: Implement resumable all-history acquisition

**Files:** Create archive_sync.py, test_archive_sync.py. Consume SourceSpec、Archive、ArchiveIndex、HealthClient。

**Interfaces:** `ArchiveEngine(client, archive, index, sources, today)`、`sync(budget: RequestBudget, *, rescan: bool = False) -> ArchiveReport`。ArchiveReport は `requests_made: int`, `remaining: int`, `failures: list[dict]`, `stopped_reason: str | None`。各 failure は stream_id/status/reason/request 範囲を持つ。

- [ ] 2ページある list endpoint で cap=1、再起動後cap=1というテストを作る。最初はpartial、2回目で初めてcompleteになり、2つのsourceが同時刻でも原本に残るようにする。
- [ ] list を持つ対象は source list、reconcile/rollup のみはその方式で query を作る。detail get は親 list の resource ID から queue に追加する。write-only/unverified は理由を記録して続ける。
- [ ] 全履歴の起点は確認済み unbounded request、または証拠のある下限から始める。どちらもなければ確認できる recent を取得し、古い範囲は unknown_history。30日/5年の自動打ち切りを再利用しない。
- [ ] scheduler は1ページごとに stream を交替し、next_visit と token を永続化する。query の基本条件は continuation 中に変えない。

```python
# queue order は archive_work.next_visit で再起動後も引き継ぐ
for work in ready_work:
    page = client.request_page(work.request, budget, capture=work.capture)
    # capture が object と page row を保存済みであることが前提
    token = page.get("nextPageToken")
    if token:
        index.save_cursor(work.stream_id, work.request, token, work.attempt_id)
    else:
        index.finish(work.attempt_id, "empty" if work.total_points == 0 else "complete")
```

`work` は archive_sync.py 内部の dataclass とし、stream_id/request/attempt_id/total_points/capture を持たせる。JSON envelope の dataPoints は list であることを検証する。未知の属性を削らず保存する。malformed envelope は failed。

- [ ] token の反復、無効 token、cap、429、403、disk full、途中再起動を追加検証する。反復 token は failed で止め無限送信しない。無効 token は新しい attempt で同じ query を次の run に再走査する。
- [ ] 通常runは recent の変更を再取得し、保存済み履歴を消さない。`rescan=True` は履歴の成功済み仕事も新しいattemptで再走査する。正当な上流削除があっても古い原本は残る。
- [ ] `uv run --no-sync pytest health/tests/test_archive_sync.py -q` を通し、`feat(health): resume complete history downloads across bounded runs` を commit。

### Task 6: Decouple projection storage from history policy

**Files:** Modify endpoints.py, store.py, sync.py, test_endpoints.py, test_store.py, test_sync.py。

**Why:** 現在 Store.replace_chunk は `full_history` で daily_series / intraday の DELETE 先まで選ぶ。履歴取得を広げるため false→true だけに変えると別テーブルを更新する危険がある。

**Interfaces:** Metric に必須 keyword-only field `storage_tables: tuple[str, ...] = field(kw_only=True)` を追加し、既存 CATALOG と test helper で明示する。sleep は `(daily_series, sleep_sessions)`、intraday は `(intraday,)`、raw-only は空。履歴境界は `SyncEngine(..., history_floors: Mapping[str, date] | None = None)` で別に受け取る。

- [ ] intraday と日次が同じ series名 steps を持つ fixture を作る。intraday の履歴範囲を広げて空で置換しても daily steps が残ることを先にテストする。
- [ ] DELETE は明示した storage_tables のみ、範囲は必ず covered_start/covered_end。raw-only に空の SQL IN を生成しない。

```python
if "intraday" in metric.storage_tables:
    con.execute(
        "DELETE FROM intraday WHERE metric IN (" + series_ph + ") "
        "AND CAST(ts AS DATE) BETWEEN ? AND ?",
        [*series, covered_start, covered_end],
    )
```

- [ ] CLI が取得台帳で確認できた最古期間を history_floors に渡して既存 typed metric を必要な範囲へ拡張する。全履歴性不明なら不明を表示する。legacy app の未指定時の挙動は切替まで保つ。
- [ ] archive と projection のrequest予算を合わせてcap内に収める。既存 SyncEngine に共有 RequestBudget を任意で渡せるようにし、既定200を維持する。run単位のrequests_madeは開始時との差分で計算する。
- [ ] parser failure の原本は Task4 observer で保存済み、旧 projection/watermark は変更されないことを確認する。source raw と表示用reconciledの件数を同じ指標として扱わない。
- [ ] `uv run --no-sync pytest health/tests/test_endpoints.py health/tests/test_store.py health/tests/test_sync.py -q` を通し、`refactor(health): separate projection tables from history bounds` を commit。

### Task 7: Ship CLI OAuth, sync, and failure reporting

**Files:** Create cli.py, oauth_loopback.py, test_cli.py, test_oauth_loopback.py. Modify auth.py, pyproject.toml, README.md。

**Interfaces:** `main(argv: Sequence[str] | None = None) -> int`、`authorize(auth, *, open_browser: bool = True, timeout_s: int = 600) -> None`。CLI は auth/sync/export-web を subcommand として持つ。export-web の実装は Task9。

- [ ] argparse で `--data-dir`, `--env-file`、sync の `--max-requests`（正の整数、既定200）, `--rescan` を実装する。値は argv/environment から読むが stdout に credential を出さない。
- [ ] OAuth listener を loopback の8501に bind してから begin_auth とブラウザ起動を行う。既存 redirect URI は変更しない。認可code/stateの照合・token保存は既存 complete_auth に委譲する。
- [ ] callback path の許可以外（favicon等）は認可完了としない。log_message を無効化し query をログに残さない。success/error/timeout/Ctrl-C で server を閉じる。port 使用中は具体的な説明で失敗し他processをkillしない。
- [ ] readonly scope は SourceSpec から求め、必要な未付与scopeを表示する。CLI auth は明示された認可操作。通常sync中に権限を勝手に追加したことにしない。
- [ ] sync は Store を一つだけ開く。ArchiveEngine と projection を進める予算割当を永続run番号で交替し、少額capでも一方が永久に飢餓しないようにする。各割当と残予算の合計がcapを超えないテストを書く。
- [ ] stdout は機械可読の短いJSON summary、stderr は進捗。raw/token/任意のAPI error bodyを出さず、理由はstatusと安全な説明に限定する。終了コードは0=完走、2=失敗/未確認/残件あり、1=設定/認可/storage等のrun停止。

```python
# CLI status mapping は pure helper としてテストする
from health.cli import exit_status

def test_partial_is_not_success():
    assert exit_status(stopped=False, incomplete=True) == 2
    assert exit_status(stopped=False, incomplete=False) == 0
    assert exit_status(stopped=True, incomplete=True) == 1
```

- [ ] fake OAuth callback と fake HTTP で成功、state mismatch、拒否、timeout、port conflict、403を含む同期を検証する。環境変数から実credentialを拾わない。
- [ ] `uv run --no-sync pytest health/tests/test_cli.py health/tests/test_oauth_loopback.py health/tests/test_auth.py -q` を通す。
- [ ] `[project.scripts]` とREADMEのCLI手順、失敗理由の読み方、容量不足時の再開を追加し、`feat(health): manage authorization and archival sync from CLI` を commit。

## P3 — Export contracts

### Task 8: Move view-independent analytics into a reusable export contract

**Files:** Create web_analytics.py, test_web_analytics.py. Modify app/views/insights_view.py と test_insights_view.py は削除前の共通化のみ。既存 analytics.py を使用。

**Interfaces:** `build_analytics(daily: pd.DataFrame, sleep: pd.DataFrame) -> dict`。`clip_calendar(frame, days, *, end, date_col="date") -> pd.DataFrame` は同じファイルの純粋関数。`PERIODS=(30,90,180,365,None)`、JSON key は `30/90/180/365/all`。

- [ ] baseline は全履歴を先に計算してから期間を絞る。以下を回帰テストにする。

```python
import pandas as pd
from health.analytics import rolling_baseline_z
from health.web_analytics import build_analytics

def test_export_baseline_uses_history_before_visible_period():
    frame = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=80),
        "resting_hr": [60 + i % 7 for i in range(80)],
    })
    result = build_analytics(frame, pd.DataFrame())
    expected = rolling_baseline_z(frame, "resting_hr")
    rows = result["baselines"]["resting_hr"]
    assert rows[-1]["z"] == expected.iloc[-1]["z"]
    assert rows[0]["date"] == "2025-01-01"
```

- [ ] 出力は `baselines[metric]`（date/value/baseline/sd/z）、`periods[key].correlations`（x/y/lag/n/spearman）、`socialJetlag`（hours/scope/firstDate/lastDate）、`periods[key].coverage`、`movingAverages`。
- [ ] 現行3pair `(sleep_minutes,resting_hr)`, `(sleep_minutes,hrv_rmssd)`, `(steps,sleep_minutes)` と lag 0/1/2/3 を使用する。相関の期間は日次全体の最新日を共通endとする。20組未満はnull、理由/件数を残す。
- [ ] jetlag は現行同様の全保存睡眠を入力し、scope=all_saved_sleep と記載する。主睡眠グラフはis_mainを絞る。移動平均の計算対象と欠損を0扱いしない semantics を維持する。
- [ ] 欠損日・年跨ぎ・休日不足・一定値系列の fixture を検証する。baseline/相関をブラウザで再実装しない。
- [ ] `uv run --no-sync pytest health/tests/test_web_analytics.py health/tests/test_analytics.py health/tests/test_insights_view.py -q` を通し、`feat(health): export period-aware analytics from Python` を commit。

### Task 9: Publish atomic generations of full-resolution web data

**Files:** Create web_export.py, test_web_export.py. Modify cli.py, .gitignore。Store の読み取りを使用し、必要な intraday 日付列挙を store.py に追加する。

**Interfaces:** `export_web(store: Store, out_dir: Path, *, generation_id: str | None = None, generated_at: datetime | None = None) -> Path` は meta.json の path を返す。`Store.intraday_days(metric: str) -> list[date]`。全ファイルは下記envelope。

```typescript
// Task10で data.ts に同じ契約を定義する
export type Period = "30" | "90" | "180" | "365" | "all";
export type Snapshot<T> = { schemaVersion: 1; generation: string; data: T };
export type Meta = {
  schemaVersion: 1; generation: string; generatedAt: string;
  basePath: string; // generations/<safe-id>/
  files: Record<string, string>;
  freshness: { archiveStatus: string; projectionStatus: string };
};
export type Daily = {
  dates: string[];
  series: Record<string, (number | null)[]>;
  units: Record<string, string>;
};
export type Intraday = {
  date: string; metric: string; timeBasis: "civil";
  timeUnit: "microseconds_since_local_midnight";
  points: [number, number | null][];
};
```

- [ ] empty、日付欠落、異なる系列長、不正な数値、2 source同時刻を原本とtypedで混同しないfixtureを用意する。以下の全点保持を先にテストする。

```python
import json
from datetime import datetime
from health.store import Store
from health.web_export import export_web

def test_export_does_not_downsample_intraday(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    rows = [("hr", datetime(2025, 1, 1, 0, 0, i), float(60 + i)) for i in range(60)]
    store.upsert_intraday(rows)
    manifest_path = export_web(store, tmp_path / "web", generation_id="test-generation")
    meta = json.loads(manifest_path.read_text())
    path = manifest_path.parent / meta["basePath"] / "intraday/hr/2025-01-01.json"
    snapshot = json.loads(path.read_text())
    assert len(snapshot["data"]["points"]) == 60
    assert snapshot["data"]["points"][1] == [1_000_000, 61.0]
    store.close()
```

- [ ] Store をread transaction中に読み、一つのgenerationを生成する。日内seriesは日単位で読み、全履歴全点をメモリに載せない。timestampをcivil date＋当日の整数microsecondsへlosslessに分ける。元typedがnaiveなのでoffsetを捏造しない。
- [ ] daily/sleep/intraday index/analytics/inventory を書く。NaNはnull、数値無限大はnull＋品質理由とし `json.dumps(..., allow_nan=False)` を通す。unitsを単位別パネルへ渡す。
- [ ] JSON内容をdeterministicに整列する。同じgeneration IDの上書きを拒否する。生成完了後だけroot meta.jsonをatomic replaceし、正常な既存generationを保持する。
- [ ] 中途write失敗のテストでmetaのbyte列が旧値のまま・旧generationが参照可能であることを確認する。壊れた新generationを参照させない。
- [ ] manifestにsecret、絶対的なdata/token path、raw bodyを含めない。inventoryの理由はsanitize済み。export/build/data/node_modulesをgitignoreへ追加する。
- [ ] CLI export-webを接続し、`uv run --no-sync pytest health/tests/test_web_export.py health/tests/test_web_analytics.py health/tests/test_cli.py -q` を通す。
- [ ] `feat(health): export consistent web snapshots without sampling` を commit。

## P4 — Next.js dashboard

### Task 10: Build the static Studio Admin shell and validated loader

**Files:** Create health/web のpackage/config、src/app/layout.tsx/page.tsx/globals.css、components/{dashboard-shell,period-provider,data-state}.tsx、src/lib/data.ts/data.test.ts、THIRD_PARTY_NOTICES.md。

**Interfaces:** `loadMeta(fetcher: typeof fetch = fetch) -> Promise<Meta>`、`loadSnapshot<T>(meta: Meta, name: string, validate: (v: unknown) => v is T, fetcher?: typeof fetch) -> Promise<T>`、`isDaily(v: unknown): v is Daily`。失敗は `DataLoadError(kind: "missing" | "http" | "schema" | "generation", message: string)`。daily以外にも `isIntraday`, `isSleep`, `isAnalytics`, `isInventory`, `isIntradayIndex` を同じtype-guard形式で定義する。sleepは既存Store.sleep_frameの列を持つrecord配列、analyticsはTask8の出力、inventoryはTask3のcoverage配列、intraday indexは日付/点数/timeBasisのrecord配列を検証する。

- [ ] Node/npm と公式対応versionsを確認し、Next16のサポート対象patchと互換React、Tailwind4を選ぶ。npmで取得した具体的versionとlockを記録する。テンプレートcommit/MIT noticeを残す。Marketing/Auth/RBAC画面は取り込まない。
- [ ] create-next-app と必要な shadcn 部品だけでshellを作る。設定は `output: "export"`、固定7route、fontはlocal/system fallback。配信に外部font requestを必須にしない。

```javascript
// health/web/next.config.mjs
const nextConfig = { output: "export", trailingSlash: true };
export default nextConfig;
```

- [ ] Task9の型をdata.tsへ実装し、runtime validationを行う。manifest pathは同じorigin配下、safe relative pathのみ許可し、`..` と絶対URLを拒否する。metaはcache:no-store、generation fileは不変として読む。
- [ ] 以下のloaderテストを入れる。fetcher fixtureはtest内でResponseを返し外部HTTPはしない。

```typescript
import { expect, it, vi } from "vitest";
import { isDaily, loadSnapshot, type Meta } from "./data";

it("rejects mixed export generations", async () => {
  const meta: Meta = {
    schemaVersion: 1, generation: "new", generatedAt: "2026-09-07T00:00:00Z",
    basePath: "generations/new/", files: { daily: "daily.json" },
    freshness: { archiveStatus: "partial", projectionStatus: "complete" },
  };
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    schemaVersion: 1, generation: "old", data: { dates: [], series: {}, units: {} },
  })));
  await expect(loadSnapshot(meta, "daily", isDaily, fetcher)).rejects.toMatchObject({kind: "generation"});
});
```

- [ ] 404、invalid JSON、null、系列長の不一致、NaN相当、path traversal、異なるschemaVersionを検証する。UIは取得失敗を空配列に置き換えない。日付変更中の古いfetch結果はAbortController/active request IDで破棄する。
- [ ] 日本語navigation、折りたたみsidebar、page header、期間30/90/180/365/all、light/darkを作る。必要なchart CSS variablesをtheme.pyから移植する。
- [ ] npm scripts に typecheck=`tsc --noEmit`、lint、test=`vitest run`、build=`next build` を設定し、全実行を通す。`feat(health-web): add static dashboard shell and snapshot loader` を commit。

### Task 11: Implement detail charts with reversible display sampling

**Files:** Create src/lib/downsample.ts/downsample.test.ts、components/intraday-chart.tsx、components/series-chart.tsx。

**Interfaces:** `Point={x:number,y:number|null}`、`downsampleMinMax(points: readonly Point[], target=2000): Point[]`。xはTask9の整数microseconds。nullは欠損区間境界であり、0にしない。

- [ ] 以下の保存と描画の分離を検証する。

```typescript
import { expect, it } from "vitest";
import { downsampleMinMax } from "./downsample";

it("preserves extrema and does not mutate source points", () => {
  const input = Array.from({length: 10_000}, (_, x) => ({x, y: x === 5011 ? 190 : 60}));
  const original = structuredClone(input);
  const sampled = downsampleMinMax(input, 2000);
  expect(input).toEqual(original);
  expect(sampled[0]).toEqual(input[0]);
  expect(sampled.at(-1)).toEqual(input.at(-1));
  expect(sampled.some(p => p.x === 5011 && p.y === 190)).toBe(true);
  expect(sampled.length).toBeLessThanOrEqual(2000);
});
```

- [ ] source配列を変更せず、端点を確保してbucketごとのmin/maxをx順に追加する。重複indexは1回だけ返す。空/単一点/全同値/不規則時刻/負値/欠損境界/逆順入力の扱いを明示しテストする。逆順はloader段階で拒否する。
- [ ] 欠損を含む連続segmentごとに処理する。segment境界保持の必要点数がtargetを超える場合は境界を優先し、targetを目安とする。既知の取得欠損や大きな時刻の飛びを連続線で埋めない。
- [ ] Rechartsのbrush/ズーム範囲で元全点をfilterし、その範囲から間引き直す。既に間引いた配列を再度入力しない。狭い範囲は全点に戻る。日付indexから保存済み最新日を既定選択する。
- [ ] tooltipの時刻・bpm/歩数・原点数/表示点数が確認できるようにする。歩数を医療上の判定に変換しない。新しい分析関数は追加しない。
- [ ] Vitestとtypecheckを通し、架空の約36,500点でズーム/戻す操作をブラウザ確認する。`feat(health-web): preserve intraday detail while sampling charts` を commit。

### Task 12: Migrate seven pages and expose archival failures

**Files:** Create/complete src/app/page.tsx、src/app/{insights,sleep,activity,heart,body,inventory}/page.tsx と各routeのcomponents。必要な共通UIはcomponentsへ置く。

**Interfaces:** Task9/10のSnapshotを読む。analyticsはPythonの期間別結果を選択するのみ。inventoryはcoverageの状態とprojection対応状況を独立表示する。

- [ ] 以下の対応表に沿って既存viewを移す。存在しない列/履歴不足/nullを静かに0表示しない。

| Page | Code reference | Acceptance example |
|---|---|---|
| 概要 | app/views/overview_view.py | 最終値が古い時に値の日付を表示。暦上前日がなければ前日比を出さない |
| 気づき | insights_view.py、web_analytics.py | 30日表示でもそれ以前の履歴でbaselineを算出。相関は対応するperiod結果とnを表示 |
| 睡眠 | sleep_view.py | classicとstage不明を区別。主睡眠、7日平均、効率、夜の区間、曜日。昼寝を原本から削除しない |
| 活動 | activity_view.py | 歩数、活動強度、距離、calories、日内歩数。単位が違う値を同一軸に混ぜない |
| 心拍 | heart_view.py | HRV平均/深睡眠、安静時心拍、index内の過去日選択と全点からの再ズーム |
| 身体 | body_view.py | 体重/体脂肪は別軸パネル、SpO2範囲、呼吸数、基準比温度 |
| 棚卸し | inventory_view.py | 403は権限不足、capは途中、未知過去は未確認。保存のみの型は「表示未対応」 |

- [ ] 棚卸しに型/resource・要求/確認期間・最終試行・保存件数・失敗理由を表示する。複数intervalのgapをmin/maxで隠さない。失敗だけを絞り込めるようにし、現行CSV書き出しを維持する。
- [ ] count>0でも最新試行がfailedになっているfixture、completeだが表示未対応のfixture、emptyとpermission_deniedが並ぶfixtureで見分けられることを実描画確認する。
- [ ] loading、export未生成、古いgeneration、schemaエラーをDataStateで表示する。未認可や取得失敗でも既存の取得済みデータは閲覧できる。
- [ ] chart surface上でline_safe等のcontrastを確認する。light/dark、1440px程度と390px程度の幅で7route、sidebar/period/日付/CSV操作を実行する。架空データで確認してから本人データをローカルで確認する。
- [ ] `npm --prefix health/web run typecheck`, `run lint`, `test`, `run build` を通す。常設E2E基盤は追加せずブラウザ確認結果を残す。
- [ ] `feat(health-web): migrate health views and show download coverage` を commit。

### Task 13: Retire Streamlit and validate local operation

**Files:** Modify README.md, AGENTS.md/CLAUDE.md, pyproject.toml, Makefile、root uv.lockはhealth依存差分のみ。Delete app/ と appだけに結合した tests は移行確認後。

- [ ] sourceレベルの利用を `rg -n 'streamlit|plotly|from common|from theme' health/src health/tests health/scripts health/app` で確認する。残すpalette/判断ロジックの参照を移してからappを削除する。テストは単に件数を減らす目的で消さない。
- [ ] test_app_smoke.py/test_insights_view.py/test_sync_view.pyの計8件を見直す。baseline等の意味は新しいPythonテストに移行済みであることを確認し、純粋な旧UI呼び出しテストだけ削除する。
- [ ] healthから未使用になったstreamlit/plotly依存を外し、説明文を更新する。他workspace memberの依存は外さない。
- [ ] Makefileに以下を追加する。

```make
health-web-check:
	npm --prefix health/web run typecheck
	npm --prefix health/web run lint
	npm --prefix health/web test
	npm --prefix health/web run build
```

- [ ] 壊れている `.superpowers/sdd/health-google-api-contracts.md` 参照をhealth/docs/google-health-source-contracts.mdへ直す。archiveとprojectionの責務、backup、coverage、readonly scope、private生成物の扱いをREADMEに記載する。
- [ ] rootからの運用を以下で説明する。buildとデータ更新は独立。Next.jsの静的成果物out/dataへexportすれば、再buildせずデータを更新できる。

```bash
uv run --no-sync health --data-dir /home/kazumasa/projects/health/data --env-file /home/kazumasa/projects/health/.env auth
uv run --no-sync health --data-dir /home/kazumasa/projects/health/data --env-file /home/kazumasa/projects/health/.env sync --max-requests 200
npm --prefix health/web run build
uv run --no-sync health --data-dir /home/kazumasa/projects/health/data export-web --out-dir health/web/out/data
uv run --no-sync python -m http.server 3000 --bind 127.0.0.1 --directory health/web/out
```

- [ ] 本番DBのbackup→必要migration→認可済みならprobe/syncを実行する。Googleの同意が必要なら理由を報告し、その型を未取得として扱う。同期完了を偽らず、実データの失敗があってもUIとfixture検証を完了する。
- [ ] 最終検証:

```bash
uv run --no-sync pytest health/tests -q
uv run --no-sync ruff check health/src health/scripts health/tests
uv run --no-sync ruff format --check health/src health/scripts health/tests
make health-web-check
git diff --check
```

- [ ] 取得状態は各型/期間/ページ数の要約だけで確認する。health/data、public/data、out、.next、token類がgitに載らないことを確認する。push/deployは行わない。
- [ ] `refactor(health): complete local Next.js cutover and document operation` を commit。

## Acceptance matrix and completion report

| Requirement | Tasks | Evidence |
|---|---|---|
| 公式の全対象を取得/不能として列挙 | 1,4,5 | catalog＋private probe manifestの状態要約 |
| 元データと取得済みbodyを削らない | 2,3,4 | bytes復元、複数source、失敗/ENOSPCの回帰 |
| 30日/5年を取得上限にしない | 4,5,6 | query境界と確認できたcoverage、unknown_historyの表示 |
| 全ページと公平な再開 | 3,5,7 | cap=1の複数run、token/429/403/restartのテスト |
| CLIにOAuth/syncを移す | 7,13 | fake callback、port使用中、scope不足、CLIの終了コード |
| 新型は保存だけでもよい | 1,3,12 | archivedとprojection対応を別欄で表示 |
| 全点の派生データと描画だけの間引き | 9,11 | export点数一致、min/max、ズームで全点へ復帰 |
| 分析の意味を維持 | 8,12 | 全履歴baseline、期間別相関、単位/欠損の確認 |
| 7画面とStudio Admin風のshell | 10,11,12 | build、light/darkと2幅でのブラウザ確認 |
| ローカル・private・非公開 | 2,7,9,10,13 | permissions、ignore、loopback server、秘密値非出力 |
| 取得失敗でも他の作業を完了 | 4,5,7,12,13 | 明示的failure/unknown表示、取得済みデータ閲覧 |

最終報告は実装変更・検証結果・実アカウントの取得済み/未取得の範囲・ブラウザURLを分けて簡潔に書く。「コードが完成」と「全データ取得完了」を混同しない。

## Plan review (2026-09-07)

- specの各要件を上記matrixに対応付けた。
- 旧設計の固定35型、rollupを原本全量とみなす説明、no-opだけで完成する説明、容量上限での削除、古いデータ取得失敗を成功扱いする説明は置き換えた。
- 追加確認事項として、storage tableとfull_historyの結合、parser前の原本保存、scope拡張、全期間性の証拠、snapshot一貫性、静的build後のデータ更新を具体化した。
- これは実装計画。checkboxは未実行のままとし、live APIやNext.js buildを実施済みとは記載しない。
