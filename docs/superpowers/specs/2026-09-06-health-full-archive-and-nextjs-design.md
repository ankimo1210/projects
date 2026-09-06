# Health: Full Google Archive + Next.js Frontend — Design

**Date:** 2026-09-06
**Status:** Approved in brainstorming; implementation plan pending
**Project:** `health/`
**Related:** `docs/superpowers/specs/2026-07-20-health-google-health-api-migration-design.md`

## Why

要件が2つ、同時に立った。

1. **アーカイブ要件（bare minimum）** — Google が持っている自分のデータを **literally 全部**ローカルへ落として保存する。表示のためのダウンサンプルは許容するが、取得段階で捨てるのは不可。
2. **UI 刷新** — Streamlit の既定 chrome をやめ、[21st.dev](https://21st.dev/) 系の shadcn/ui デザインへ寄せる。

調査の結果、**(1) は現状まったく満たされていない**ことが判明した。`build_inventory()` を実走したところ、Google Health が公開する **35 データ型のうち実装済みは 13、22 型が未実装**。しかも未実装側に `heart-rate-variability`（生サンプル）や `oxygen-saturation`（生サンプル）が含まれる — 実装済みの `hrv_rmssd` / `spo2_avg` は**その元データの日次要約でしかない**。

したがって優先順位は「取得 → 表示」であり、フロントエンドを先に作り替えても穴は塞がらない。本 spec は両方を1つの設計として扱い、フェーズに分けて実装する。

## Goal

- Google Health が公開する **35 データ型すべて**について、API レスポンスを verbatim でローカルへ保存する。
- 同期と認可を **Streamlit なしで**（CLI から）実行できる。
- ダッシュボードを **Next.js + shadcn/ui** の read-only 静的サイトへ移行し、Streamlit を廃止する。
- 既存の Python core（`src/health/`、258 tests）と CVD 安全パレットを維持する。

## Non-goals

- 生データの再解釈・新規分析の追加（アーカイブが揃った後の話）。
- マルチユーザー、リモートデプロイ、クラウド保存。ローカル単一ユーザー専用のまま。
- 未実装 22 型すべての typed parser 実装（下記 D-1 参照）。
- E2E テスト基盤の導入。

## Current state (measured 2026-09-06)

すべて本セッションで実測した値。

### Data volume

| Table | Rows | 備考 |
|---|---|---|
| `daily_series` | 11,791 | 17 系列 × 2024-03-06〜2026-09-06 |
| `sleep_sessions` | 897 | |
| `intraday` | 701,036 | `hr` 693,855 / `steps` 7,181 |
| `raw_json` | 1,475 | `health.duckdb` 151MB の大半 |

`intraday.hr` のサンプリング間隔は **1〜3秒**（3s: 342,827 / 2s: 241,132 / 1s: 109,755）、**約 36,500 点/日**。現行 `heart_view.py` は「分単位ビューア」と称しつつ、その日の全点を間引かずに Plotly へ渡している。

### Coverage gap

- 公開 35 型中 **実装 13 / 未実装 22**。
- 未実装のうち影響が大きいもの: `heart-rate-variability`(sample), `oxygen-saturation`(sample), `exercise`, `daily-heart-rate-zones`, `time-in-heart-rate-zone`, `active-energy-burned`, `basal-energy-burned`, `activity-level`, `sedentary-period`, `floors`, `altitude`, `active-zone-minutes`, `vo2-max` 系 3 型, `respiratory-rate-sleep-summary`, `core-body-temperature`, `height`。
- 手入力/専用デバイス依存で空の可能性が高いもの: `blood-glucose`, `nutrition-log`, `hydration-log`, `swim-lengths-data`。
- `intraday` は `full_history=False` / `INTRADAY_LOOKBACK_DAYS = 30` により **直近 30 日より前へ遡らない**。これはアプリ側の定数であり、API 側の制限かは**未確認**。

### Code shape

| | LOC |
|---|---|
| `src/health/`（core） | 2,421 |
| `app/`（Streamlit view） | 1,025 |

`redirect_uri` の結合は `auth.py:41` のデフォルト引数 1 箇所のみ（他は test 1 行・README 1 行）。`health/.gitignore` は `/data/` のみ。

### Existing archival foundation

```sql
CREATE TABLE raw_json(
    metric VARCHAR, range_start DATE, range_end DATE, page_index INTEGER,
    fetched_at TIMESTAMP, payload JSON,
    PRIMARY KEY(metric, range_start, range_end, page_index));
```

**API レスポンスを verbatim で保持しており、`daily_series` / `sleep_sessions` / `intraday` はそこからの派生**。アーカイブ要件に対して既に正しい形をしている。

## Key decision: raw-first archive

**D-1.** `Metric.parse_pages` は `Callable[[Sequence[dict]], ParsedRows]`。**空の `ParsedRows()` を返す no-op parser を渡せる**ため、「取得してアーカイブするだけの型」を**同期エンジン無改造で** `CATALOG` へ追加できる。

したがって取得完全性は「22 本の parser を書く」問題ではなく、「22 型の request shape を確定して CATALOG に載せる」問題に縮む。typed parser は**表示したくなった型にだけ後追いで**書く。

検討した代替案:

| 案 | 判定 |
|---|---|
| 22 型すべて typed parser まで実装 | 却下。データが空の型はパーサを検証できず、無駄になる |
| probe でデータがある型だけ実装 | **却下。要件に反する** — 空と判断した型が後日埋まっても取得されない |
| **raw-first アーカイブ（採用）** | 生データは全部残り、解釈は後からいつでもやり直せる |

## Decisions

| # | Topic | Decision |
|---|---|---|
| D-1 | 未実装 22 型 | no-op parser で `CATALOG` に追加。raw のみ保存 |
| D-2 | write 面（OAuth・同期） | **Python CLI へ降ろす**。`health auth`（loopback OAuth）/ `health sync`。Next.js は完全 read-only |
| D-3 | データ転送 | **静的エクスポート**。常駐 API を置かない |
| D-4 | intraday の配信 | **フル解像度のまま日別ファイル**。間引きは描画時にブラウザ側で行う |
| D-5 | 間引きアルゴリズム | **min/max バケット法**（約 2,000 点）。平均では HR の短時間スパイクが消えるため |
| D-6 | チャートライブラリ | **Recharts 一本**（shadcn/ui 準拠）。uPlot は Recharts が詰まった場合の予備で今は入れない |
| D-7 | 系列色 | **`app/theme.py` の CVD 安全パレットを CSS 変数へ移植**。テンプレート由来のチャート色は採用しない |
| D-8 | テンプレートの扱い | **丸ごと clone しない**。`create-next-app` + `shadcn/ui` に、MIT の Studio Admin からシェルと必要コンポーネントのみ移植 |
| D-9 | toolchain | **npm**（`make sde-check` の前例に合わせる。pnpm は PATH にない） |
| D-10 | 公開 API 追加 | `[project.scripts] health = "health.cli:main"` |

## Phase 1 — Establish facts (spike)

**目的:** 22 型の request shape と、実際にデータが存在するかを最小コストで確定する。

`scripts/probe_datatypes.py` を 35 型へ拡張して 1 回実走する。probe は狭い期間で各型を独立に叩き、DuckDB へは書かず `data/probe/<metric>/` へ JSON を保存する既存の仕組み。

確定させるもの:

- 各型の `method`（`dailyRollUp` / `reconcile`）
- `reconcile` 型の `filter_path`
- `max_range_days` の実効上限
- **データの有無**（空でも CATALOG には載せる。D-1 の方針は変えない）
- **`intraday` が 30 日より深く取れるか** — 取れるなら `INTRADAY_LOOKBACK_DAYS` を見直す

**契約の正本:** `health/CLAUDE.md` は `.superpowers/sdd/health-google-api-contracts.md` を参照しているが、**このファイルはリポジトリに存在しない**（`find` で確認済み）。代わりに移行 spec が挙げる Google 公式ドキュメントを正とする。

- [Data types](https://developers.google.com/health/data-types)
- [`dailyRollUp`](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp)
- [`reconcile`](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile)
- [`list` filter syntax](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list)
- [Quotas and rate limits](https://developers.google.com/health/rate-limits)

**成果物:** 型ごとの request shape 表。CLAUDE.md の壊れた参照もこの機会に直す。

**Exit criteria:** 35 型それぞれについて method / shape / データ有無が表に埋まっている。

## Phase 2 — Acquisition completeness

**2-1. CATALOG 拡張**

P1 の表に従って 22 型を `CATALOG` へ追加。parser は `lambda pages: ParsedRows()`（型ごとに名前付き関数として定義し、後から実装へ差し替えられるようにする）。

**2-2. リクエスト予算**

メトリクスが 14 → 35 で約 2.5 倍。現行 `MAX_REQUESTS_PER_RUN = 200` のままだと 1 run で forward pass すら終わらない可能性がある。対応:

- UI の 200/500/1000 の選択肢を CLI 引数へ移す
- forward pass が全メトリクスの `RECENT_WINDOW_DAYS` を確実に踏めるだけの下限を計算し、それを下回る cap を拒否する

**2-3. intraday floor**

P1 の実測結果に従って `full_history` / `INTRADAY_LOOKBACK_DAYS` を決定する。深く取れるなら backfill 対象へ格上げする。

**2-4. CLI 新設**

```
health auth     # loopback OAuth。固定ポートで一時サーバを立て code を受ける
health sync     # ヘッドレス同期。進捗は stderr、cap は引数
health export-web   # Phase 3
```

`auth.py` の `redirect_uri` デフォルトを CLI のポートへ変更する。**Google Cloud Console 側で新しい redirect URI を完全一致登録する手作業が発生する**（README に手順を追記）。

これにより **Streamlit の「接続」リンクは P2 の時点で機能しなくなる**（8501 で待ち受けていないため）。以後、認可は CLI が単独で所有する。Streamlit は `tokens.json` を読むだけなので、**閲覧用としては P4 まで動き続ける**。

なお現行の `load_tokens()` は失効判定をせず、期限切れ `tokens.json` でも「接続済み」と扱う。そのため Streamlit 側には再接続導線が同期ページ最下部にしか無く、実際に本セッションで詰まった。CLI 化でこの問題は解消する。

**Exit criteria:** Streamlit を起動せずに認可と同期が完走する。35 型すべてについて同期が試行され、`sync_state` に結果（成功 / 空 / 失敗理由）が残る。空レスポンスの型が `raw_json` にどう記録されるかは P1 の probe で確認し、必要なら「試行したが空」を区別できるようにする。

## Phase 3 — Export layer

`health export-web` が `health/web/public/data/` へ静的 JSON を書く。**`analytics` の計算結果も Python 側で確定させ**、単一の真実源を保つ。

| File | 中身 | 概算 |
|---|---|---|
| `daily.json` | 全系列を列指向（`{dates: [...], series: {steps: [...]}}`） | ~200KB / gzip 40KB |
| `sleep.json` | 全セッション | ~150KB |
| `intraday/<metric>/<YYYY-MM-DD>.json` | **フル解像度** | ~700KB / gzip 150KB |
| `intraday/<metric>/index.json` | 存在する日の一覧 | 極小 |
| `analytics.json` | rolling z / lagged correlation / coverage calendar / social jetlag の事前計算結果 | 小 |
| `inventory.json` | 35 型テーブル + 保存系列統計 | 小 |
| `meta.json` | 生成時刻・同期 watermark・各系列の範囲 | 極小 |

**`health/.gitignore` へ `/web/public/data/` を追加する**（実データのため。現状 `/data/` しか無い）。

**Exit criteria:** 生成物だけでフロントが動く。DuckDB へ触れない。

## Phase 4 — Next.js frontend

`health/web/`。`create-next-app` + `shadcn/ui`、Studio Admin（MIT）からシェルとコンポーネントのみ移植。

**ページ（7枚）:** 概要 / 気づき / 睡眠 / 活動 / 心拍 / 身体 / データ棚卸し。**同期ページは CLI へ移るため消える。**

**データ取得:** `public/data/**` を fetch するのみ。API ルートなし・認証なし・サーバ側データ取得なし。

**チャート:** Recharts。intraday は取得後にクライアントで min/max バケット間引き（D-4/D-5）。

**配色:** `app/theme.py` の `LIGHT` / `DARK` を CSS 変数へ移植する。`categorical` のスロット順序と `line_safe`（細線でコントラスト 3:1 を切るスロットを避ける集合）を**そのまま維持**する。テンプレート由来のプリセットは shell（背景・枠・角丸・フォント・サイドバー）にのみ適用する。

**Exit criteria:** 7 ページが実データで動く。light/dark 双方で描画確認済み。Streamlit を削除できる。

## Testing

現行 **258 tests**。うち **8 件が Streamlit `app/` に結合**している（`test_app_smoke.py` 3 / `test_insights_view.py` 2 / `test_sync_view.py` 3）。P4 で `app/` を削除するとこの 8 件も消え、**core 250 tests が残る**。`test_insights_view.py` が検証している判断ロジックのうち残す価値があるものは、削除前に `src/health/analytics.py` 側のテストへ移す。

| 層 | 方針 |
|---|---|
| Python core | 既存 250 core tests を維持。CATALOG 拡張分は fixture ベースの契約テストを追加 |
| CLI | fake HTTP で `auth` / `sync` / `export-web` を通す。**live API は自動テストで呼ばない**（既存方針を踏襲） |
| Export | 生成 JSON のスキーマと決定性を検証 |
| Frontend | `tsc --noEmit` + lint + **Vitest（間引き関数とデータローダのみ）**。E2E は入れない |
| Workspace | Makefile へ `health-web-check` を `sde-check` と同形で追加 |

`probe_datatypes.py` の出力は**実データ**であり、共有・commit しない（既存方針）。

## Risks & open questions

| # | 内容 | 扱い |
|---|---|---|
| R-1 | 22 型の request shape が公式ドキュメントから確定しない | P1 の probe で実測。それでも不明な型は「未確定」として表に残し、CATALOG 追加を保留する |
| R-2 | intraday が 30 日より深く取れない可能性 | P1 で実測。取れないなら**それが上流の限界**であり、要件は「取れる範囲すべて」と解釈する。README に明記する |
| R-3 | 35 型同期のリクエスト量が rate limit に当たる | 既存の 429 ハンドリング（run 全体を停止）がそのまま効く。cap 設計で緩和 |
| R-4 | Google Cloud Console の redirect URI 追加が手作業 | 避けられない。README に手順を書く |
| R-5 | Recharts が 2,000 点で重い | uPlot への差し替えを予備案として持つ（D-6） |
| R-6 | `health.duckdb` が raw 増加で肥大 | 現在 151MB。35 型化で数倍を見込む。上限を超えたら raw をファイルへ外出しする案を別途検討 |

## Out of scope

- 未実装 22 型の typed parser（必要になった型だけ後から）。
- intraday の事前 1 分版生成（多日 intraday 一覧が欲しくなった時点で追加）。
- Streamlit の段階的併存。P4 完了時に削除する。
