# Health: Full Google Archive + Next.js Frontend — Design

**Date:** 2026-09-06
**Updated:** 2026-09-07
**Status:** Requirements confirmed; implementation plan prepared; implementation pending
**Project:** `health/`
**Plan:** `docs/superpowers/plans/2026-09-07-health-full-archive-and-nextjs.md`
**Related:** `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md`

## Goal and confirmed requirements

Google Health の本人データを、公開された正式な取得手段で取得可能な範囲すべて、元の粒度でローカル保存する。その保存層を保ち、既存ダッシュボードを Studio Admin を基にした Next.js + shadcn/ui のローカル閲覧画面へ移す。

2026-09-07 にユーザーが確認した方針:

1. 現在の取得元は **Google Health 公開 API（本人の OAuth 認可が必要）**。Google Takeout の ZIP や一般公開された個人データを読んでいるわけではない。取れないものは型・期間ごとに失敗や未確認として目立つ形で示し、それだけで全工程を停止しない。別のエクスポートサービスの自動操作は今回追加しない。
2. **全データを元の粒度で保存する。容量を理由とする削除・間引き・保持期間の切り詰めは禁止。** 可逆圧縮・保存先の分割は許容する。表示のためのダウンサンプルは許容する。
3. 新しい型も保存対象とするが、専用の表・グラフへの変換は必要に応じて追加する。既存の表示・分析機能は移行する。保存済みと表示対応済みを区別する。

アプリの完成と、特定アカウントの取得完全性は別に判定する。未取得があれば利用を継続できても「全データ取得完了」とは表示しない。

## Constraints and non-goals

- Python >=3.12。既存の auth/client/store/sync/analytics の有用な契約とテストを維持する。
- OAuth・同期・Web データの書き出しは Python CLI。Next.js は読み取り専用。
- Next.js + TypeScript + Tailwind CSS + shadcn/ui + Recharts、npm を使用する。
- 単一ユーザー、ローカル専用。公開・クラウド保存・リモートデプロイは含めない。
- UI は日本語。コード、識別子、commit message は英語。
- 実データ・token・認可コード・probe 結果は git に追加しない。自動テストは架空 fixture と fake HTTP のみ。
- 新しい型すべての typed parser、新規の健康分析、E2E テスト基盤は今回の対象外。

## Evidence and corrections

2026-09-06 の既存 DB 計測は日次 11,791 行、睡眠 897 行、intraday 701,036 行、raw_json 1,475 ページ。過去の計測値であり、完成後の容量見積もりではない。HR は主に 1〜3 秒間隔だった。

既存 `KNOWN_DATA_TYPES` は 35 型、`CATALOG` は 14 metric / 13 型。**35 は公式 API 全体の固定件数ではない。** 2026-09-07 に[公式型一覧](https://developers.google.com/health/data-types)を再照合すると 43 行あり、読み取り手段のない型も含まれていた。公式資料とローカル一覧の和集合を監査し、新規・廃止・不明を区別する。型数、取得 stream 数、表示系列数を混同しない。

[list](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list) は元の data point、[reconcile](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile) は複数 source を統合した値を返す。**日次 rollup や reconcile の JSON だけでは、元データ全量の保存と同じではない。** method・scope・filter・pagination を型ごとに確認する。

既存 `raw_json` は JSON をデコードして再直列化し、再同期時に同じ chunk のページを置換する。HTTP body の byte-for-byte 保存ではない。`SyncEngine._fetch_chunk()` は parser 成功後に保存する。**no-op parser の追加だけで全量アーカイブが完成するという旧案は修正する。**

## Acquisition and storage

### Source inventory

取得用 `SOURCE_CATALOG` は公式の型・リソース・method・scope と検証状況を管理する。既存 `CATALOG` は表示用の typed projection を管理する。`KNOWN_DATA_TYPES` は取得側から導出し、二重管理を避ける。

- list が提供される型は元 data point を全ページ保存する。reconcile/rollup しかない型は提供形態と制約を記録する。
- 既存の表示用 rollup/reconcile も維持し、そのレスポンスも保存する。
- get が list より詳細な本人データを返す場合は ID ごとの詳細も取得する。profile/paired devices など本人に関係する読み取り resource も監査する。共有参照データと本人の記録を区別する。
- 読み取り不可の型に write API を呼ばない。必要な readonly scope のみを扱い、未付与は permission_denied として表示する。

### History, pages, and resume

- 全量取得に独自の「直近30日」「既定5年」の打ち切りを使わない。
- filter 省略で全履歴を列挙できることが確認できた endpoint は最終ページまで取得する。省略時の既定期間を検証する。
- 期間指定が必須なら根拠のある開始境界から区間を分割する。開始境界不明は unknown_history とし、成功期間だけ記録する。空の狭い期間から「過去もすべて空」と推定しない。
- 型ごとの filter を使用する。sleep と ECG など、指定可能な時刻条件が異なる型を一律に扱わない。
- ページごとに保存・再開位置を記録する。最後の nextPageToken がなくなる前に complete/empty にしない。
- cap/429 は partial/rate_limited、未訪問は pending。token 失効・反復は理由を記録し安全に再走査する。保存済みページは残す。
- recent と history、型間を公平に進め、大きな1型の履歴が後続を毎回未訪問にしない。通常の再取得と全件再走査を区別する。

### Lossless archive

`health/data/archive/objects/<sha256>.json.gz` に受信した health API response body を可逆圧縮して保存する。OAuth token endpoint は含めない。同一内容の共有は許可するが、観測した異なる内容を上書きしない。

DuckDB に page/attempt/coverage/cursor の索引を追加する。object を確実に書き終えてから索引を commit する。取得状態と typed projection 状態を別に管理する。

- 全フィールド、source ID、単位、timestamp、UTC offset、未知の属性を残す。同時刻の異なる source を生保存時に統合しない。
- parser error・後続ページの失敗でも受信済み body は残す。typed projection と既存 watermark は失敗によって変更しない。
- 旧 raw_json は非破壊で取り込み、再直列化された JSON であることと実取得範囲が不明な可能性を記録する。旧 checkpoint から source-level 全履歴完了を捏造しない。
- DB は writer 停止・checkpoint・backup 後、追加 schema で移行する。旧データを削除しない。
- object は0600、アプリ所有 directory は0700。atomic write と fsync を使用する。
- disk full は storage_error として取得を停止し、容量確保後に再開する。原本の自動削除・間引きは行わない。

### Coverage and failure reporting

各対象に型/resource、method、取得形態、要求範囲、実確認範囲、最終試行時刻、page/point 件数、状態、HTTP status、伏せ字処理した理由、再開可能性を残す。

状態は `pending`, `complete`, `empty`, `partial`, `permission_denied`, `unsupported`, `failed`, `rate_limited`, `unknown_history`, `storage_error`。empty/complete は成功確認した範囲に限る。complete は Google 内部の非公開データも保有しているという意味ではない。過去の成功範囲は後の失敗で消さない。

CLI と棚卸し画面に、失敗・未確認の型と期間を示す。cap や権限不足を「データなし」にしない。型単位の失敗で他の型や UI 作業を止めない。認可失効・429・storage error は run を止め状態を保存する。

## CLI and local operation

`[project.scripts] health = "health.cli:main"` を追加する。

| Command | Behavior |
|---|---|
| health auth | loopback OAuth。本人の同意で readonly token を保存 |
| health sync | 全対象と既存 projection を進める。cap・再開・全量再走査に対応 |
| health export-web | 一貫した DB/索引 snapshot から Web 用 JSON を生成 |

`--data-dir` と `--env-file` を明示可能にして worktree から実アカウントを扱う際の保存先を確定する。秘密値はログに出さない。

OAuth callback は既に登録されている `http://localhost:8501/` を CLI の一時 server で受ける。port 使用中は説明して停止する。デフォルト URI を別 port へ変更して不要な Console 操作や移行中の互換性破壊を起こさない。readonly scope の追加同意は本人がブラウザで行う。

CLI は一つの writer として Store を所有する。DB lock を無視した別 process の強制終了はしない。

## Export layer

Web データは派生物。原本 archive は配信 directory に置かない。`health export-web --out-dir <target>` の標準 target は `health/web/public/data/`。build 後の更新には `health/web/out/data/` を指定できる。

`generations/<generation_id>/` を完成させ、最後に meta.json を atomic に切り替える。ブラウザは同じ generation のファイルだけを読む。失敗時は直前の正常 generation を残す。export は live API を呼ばない。

| File in generation | Content |
|---|---|
| daily.json | 全保存期間の表示系列。dates と同じ長さの列、欠損 null、単位 |
| sleep.json | 全保存 session。主睡眠・昼寝と stage 不明の区別 |
| intraday/<metric>/<date>.json | typed series の日別フル解像度。全 source 原本とは区別 |
| intraday/<metric>/index.json | 保存済み日付・点数・time basis |
| analytics.json | Python の分析結果と計算範囲・標本数 |
| inventory.json | 型・取得範囲・失敗理由・保存/表示対応状態 |

meta.json は schema version、generation、生成時刻、manifest path、同期/表示 freshness を持つ。JSON は有限数と null のみ、NaN/Infinity を出さない。civil date と timestamp を区別し、naive な既存 timestamp に UTC の Z を付けない。

表示期間は `30/90/180/365/all`。baseline z は全履歴で計算後に表示期間で絞る。lag 相関は期間別・既存3組の pair 別に事前計算し件数を含める。social jetlag の計算範囲も明示する。任意の新しい相関期間をブラウザで再計算する機能は追加しない。

`/web/public/data/`, `/web/out/`, `/web/.next/`, `/web/node_modules/` を gitignore に含める。build 成果物も実データを含み得る。静的 build 後は localhost の HTTP server で配信する。file:// 直開きは保証しない。

## Frontend

[Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard) の MIT license と採用 commit を記録し、sidebar/header/card と必要な UI 部品を移植する。Next.js の [static export](https://nextjs.org/docs/app/guides/static-exports) を使用する。認証画面・SaaS 管理機能・API route は追加しない。

| Page | Required behavior |
|---|---|
| 概要 | 歩数・睡眠・安静時心拍、値の日付、暦上前日との比較、sparkline |
| 気づき | baseline z、期間別 lag 相関と標本数、睡眠リズム、欠損 calendar |
| 睡眠 | stage 構成、classic sleep、睡眠時間/効率、就寝起床、曜日傾向 |
| 活動 | 歩数・移動平均、距離、消費エネルギー、活動時間、日内歩数 |
| 心拍 | 安静時心拍、HRV、選択日の詳細心拍とズーム |
| 身体 | 体重・体脂肪、SpO2、呼吸数、皮膚温の既存指標 |
| データ棚卸し | 保存済み/未対応/失敗/未確認、型別・期間別 coverage、既存 CSV 書き出し |

Recharts の描画時のみ min/max bucket で約2,000点に間引く。取得した日別データは全点を保持し、ズーム後は全点から再計算する。端点・局所 min/max・順序・欠損区間を保つ。表示点を原本として分析・保存しない。

`app/theme.py` の LIGHT/DARK、categorical の順序、line_safe、sequential を移植する。shell は Shadcn Neutral 系。元パレットの検証結果が異なる surface に引き継がれるとは仮定せず、実際の chart surface で確認する。

期間をページ間で共有する。loading/export 未作成/取得失敗/空/古い値を区別する。取得日時と値の日付は別表示。7ページを light/dark・広い画面・狭い画面で実描画確認してから Streamlit を外す。

## Phases and validation

| Phase | Deliverable | Exit condition |
|---|---|---|
| P1 契約と probe | 公式一覧照合と限定 live probe | 各対象に method/scope/取得形態/検証結果。不明・失敗を隠さない |
| P2 取得と CLI | lossless archive、coverage、再開、CLI | 全対象を巡回し、途中失敗・disk full でも既存原本を保持 |
| P3 Web export | generation JSON と Python 分析 | snapshot 一貫性、欠損・期間・time basis の明示 |
| P4 Next.js | 7ページと Studio Admin shell | 機能と実描画を確認後、Streamlit を削除 |

2026-09-06 の基準は258 tests、うち8件は Streamlit view に結合。有用な判断テストは削除前に Python 側へ移す。件数だけを合格条件にしない。

- 取得: 元データと集計の区別、未知フィールド、同時刻の複数 source、全ページ、空、403/401/429、cap、反復/失効 token、disk full、再起動、履歴の穴。
- 保存: bytes 復元、atomic write、旧 JSON 非破壊取り込み、parser failure 後の原本保持、covered range 内だけの typed 更新。
- Export: schema、determinism（生成 ID/時刻を除く）、NaN/null、日付/offset、generation 混在防止、期間別分析。
- Frontend: typecheck、lint、Vitest（loader と間引き）、production static build、ブラウザでの実描画。常設 E2E 基盤は導入しない。
- Makefile に health-web-check を追加し、typecheck/lint/test/build を実際に含める。
- 本人の live probe は操作テスト。認可不足は理由を残し、fake HTTP 検証と UI 作業は続ける。

## Risks and handling

| # | Risk | Handling |
|---|---|---|
| R-1 | method/scope/一覧の変化 | 公式 URL・確認日を記録。未確定型も一覧に残す |
| R-2 | 古いデータや型が取得不能 | 失敗・未確認の型と期間を強調。成功/空と偽らず他の作業を続ける |
| R-3 | API quota / cap | ページ保存、公平な再開、partial 表示。cap だけで全型完走を保証しない |
| R-4 | readonly scope 追加同意 | 必要 scope を提示。未付与型は permission_denied |
| R-5 | chart 性能 | 描画だけ間引き、ズームで再計算。悪い実測がある場合に限り方式を再検討 |
| R-6 | 容量増加 | 原本の自動削除なし。可逆圧縮・分割。disk full は保持して停止・再開 |
