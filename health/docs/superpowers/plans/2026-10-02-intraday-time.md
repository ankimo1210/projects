# 日内時刻の修正・復元計画

**Spec:** [日内データの実時間](../specs/2026-10-02-intraday-time.md)

## Global Constraints

health のみ変更する。WSL の専用 worktree を使用し、root の共有 venv を利用する。実データは private なローカルだけで検証する。依存追加、認可変更、HealthPlanet 同期、push は行わない。ユーザー変更を維持する。

## Review Focus

UTC と civil の食い違い、offset 欠落・非整数 offset、日跨ぎ、完全な原本の選択とページ欠落、UTC が一部不明の日、再構築失敗時の transaction、checkpoint の穴、旧形式との互換性、公開文書への個人データ混入を確認する。

### Task 1: Parser and store

**Files:** `health/src/health/endpoints.py`, `health/src/health/store.py`, `health/tests/test_intraday_time.py`

**Interfaces:** `ParsedRows.intraday` の 3 要素 tuple を維持し、整列した `intraday_times` を追加する。Store は sample_key を主キーにし、`intraday_time_frame` と typed-only `replace_intraday` を提供する。

- [ ] 同じ civil・異なる UTC を両方保存し、同じ UTC の重複を拒否するテストを書く。旧 3 列 DB の移行と再 open、原本を触らない置換も確認する。
- [ ] 新テストを実行する。Expected: 未実装の契約で失敗する。
- [ ] parser と transactional migration / bulk insert を実装する。
- [ ] Python 一式を実行する。Expected: 既存 526 件と新規テストが通る。
- [ ] `fix(health): preserve physical identity of intraday observations` を commit する。

### Task 2: Offline recovery

**Files:** `health/src/health/intraday_rebuild.py`, `health/src/health/cli.py`, `health/tests/test_intraday_rebuild.py`

**Interfaces:** Task 1 の typed-only replacement を使い、`rebuild-intraday` は保存済み raw と hash 検証済み archive だけを読む。派生 replay attempt と連続範囲の checkpoint 更新を記録する。

- [ ] 完全・不完全な archive、raw の置換、再実行、checkpoint の穴を合成データでテストする。
- [ ] 新テストを実行する。Expected: recovery module が未実装で失敗する。
- [ ] 再構築 module と CLI を実装する。
- [ ] Python 一式を実行する。Expected: 全件通る。
- [ ] `feat(health): rebuild intraday projections from saved responses` を commit する。

### Task 3: Export and display

**Files:** `health/src/health/web_export.py`, `health/web/src/lib/types.ts`, `health/web/src/lib/data.ts`, `health/web/src/lib/intraday-time.ts`, `health/web/src/components/intraday-chart.tsx`, Python/Web テスト、`health/docs/web-data-contract.md`, `health/README.md`

**Interfaces:** `timeBasis=physical`, `timeUnit=microseconds_since_unix_epoch`, `civilTimes`, `utcOffsets` を追加。civil 旧形式の互換性を維持する。

- [ ] UTC 横軸・重複 civil・旧形式・metadata 整列と formatter の回帰テストを書く。
- [ ] 新テストを実行する。Expected: 新形式の export/validation が失敗する。
- [ ] export、validator、UTC zoom / tooltip、契約文書を実装する。
- [ ] Python 一式と Web の typecheck/lint/test/build を実行する。Expected: 全件通る。
- [ ] `fix(health): display intraday data on its physical timeline` を commit する。

### Task 4: Verify and restore the local sync

**Files:** `health/docs/STATUS.md`（個人データを含めない）

**Interfaces:** Tasks 1–3 の全契約。現用 DB には修正済み現用コードだけを接続する。

- [ ] private なコピー DB で移行・replay・再実行を検証する。Expected: 原本保持、旧行保持、完全な観測だけを復元する。
- [ ] 実装全体の fresh review を依頼し、重要な指摘は RED→GREEN で修正する。
- [ ] 現用 health コードへローカル統合し、バックアップ後に本番の offline rebuild と export を行う。Expected: 欠落日が復元され、checkpoint は連続した範囲だけ進む。private JSON の件数が DB と一致する。
- [ ] 検証と残る制約を STATUS に記録して commit する。Expected: health のみ変更、個人値なし、リモート変更なし。
