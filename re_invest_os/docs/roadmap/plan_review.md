# Plan Review — 現プランの精査と代替案

作成日: 2026-05-12
レビュー対象: `docs/product/product_requirements.md`, `docs/roadmap/mvp_roadmap.md`, `docs/architecture/technical_architecture.md`

---

## 0. 結論サマリー

**現プランはおおむね正しい方向だが、3つの構造的リスクがある。**

| リスク | 重大度 | 対処方向 |
|---|---|---|
| **スコープ過大** (MVPに25機能/12週) | 🔴 高 | MVP機能を半減 → 8週で出す |
| **抽出パイプライン後回し** (最大の差別化リスクがWeek 3-4埋没) | 🔴 高 | 抽出を Phase 2 に前倒し |
| **PoC資産の死蔵** (1.5年分の公示地価データ未使用) | 🟡 中 | PoC データを ETL で取り込む |

スタック (Next.js + FastAPI + Supabase) は **維持推奨**。理由は §5.1。

推奨改訂は §7。

---

## 1. 現プランの強み (保持すべき)

### 1.1 計算とAIの分離 ✅
仕様の中心思想「AI=読む/分類/説明、Engine=純粋関数」が `financial-engine` (84テスト) でしっかり実装されている。これは正しい。

### 1.2 Bloomberg基調デザイン ✅
営業ポータルとの視覚的差別化が明確。LP・結果画面とも一貫した思想。

### 1.3 法務リスク認識 ✅
`legal_risk_checklist.md` の NG/OK 表現リスト、PII マスク、業者送客禁止の技術的担保 — 個人開発で軽視されがちな部分を最初から押さえている。

### 1.4 デザイントークンの早期確立 ✅
shadcn/ui に行く前に CSS 変数で固めた。後の画面追加が速い。

### 1.5 OpenAPI からの型生成 ✅
Pydantic ↔ TypeScript の手書き同期を回避。Phase 0 で入れて正解。

---

## 2. 現プランの弱み

### 2.1 🔴 MVP スコープが過大

PRD の P0 機能だけで 14個 + P1 11個 = **25機能を12週**。
ソロ開発 (週20-25時間) で250-300時間しかない。1機能あたり12時間以下。
**現実的でない。**

実装済みは `financial-engine` + UI 骨格で **約30時間** (1週相当)。残り11週で25機能をフル品質で作るのは無理。

→ Phase毎の品質が落ちるか、リリースが遅延する。

### 2.2 🔴 「最大の差別化」が後回し

差別化の核は **資料抽出精度** (URL → 構造化、PDF → 構造化)。これが80%以上の精度で動くかは、技術的に最大の不確実性。

しかし現プランでは:
- Week 1-2: 認証・DB (確実に動く既知技術)
- **Week 3-4: 資料解析v0** ← ここで初めて検証
- Week 5+: その後の機能

もし Week 3-4 で抽出精度が出なかった場合、Week 1-2 の認証・DB投資が宙に浮く。

**リスクの順序が逆。** 不確実性が高いものを先にやるべき (de-risk first)。

### 2.3 🟡 PoC データの死蔵

`/home/kazumasa/projects/land_price_api_app/` には以下が既に存在:
- 1.5年分の MLIT XPT002 (公示地価ポイント) DuckDB
- 1.5年分の MLIT XIT001 (取引価格) DuckDB
- e-Stat 賃料相場テーブル
- 国土地理院ジオコーダー連携
- 47都道府県のポイント分布

これは Score の `market_cap_rate` `market_rent_per_sqm_yen` に直接使える教師データ。これなしで Score を実装すると「市場情報未投入 (満点扱い)」のフォールバックが常時発火し、**Score の意味が薄れる**。

「完全に新規実装」と決めた判断は、データ収集のコスト感を軽視している。

### 2.4 🟡 二言語スタックの保守負荷

Python (FastAPI + financial-engine) + TypeScript (Next.js) = 2 言語。
ソロ開発で:
- 型同期 (openapi-typescript で緩和、しかしゼロでない)
- 二つのテストランナー
- 二つの依存関係管理
- 二つのデプロイ先

総コストは「Next.js 単体」の **1.5-2倍**。

### 2.5 🟡 Next.js 16 / Tailwind v4 の先端度

Next.js 16 は 2026年4月リリース、Tailwind v4 も最近。文書化されていないバグに当たる確率が、安定版 (Next 15, Tailwind v3) より高い。
すでに `pnpm-workspace.yaml` 周りで何度かトラブル発生済み。

### 2.6 🟢 Web側のテスト未整備

`apps/web` にテストがゼロ。リファクタリング時の安全網がない。
Playwright E2E を MVP に組み込む計画は Phase 4 まで遅延。

### 2.7 🟢 スクレイピング先の集中リスク

楽待・SUUMO・健美家は HTML が頻繁に変わる。MVP がここに依存すると、リリース後の保守コストが恒常的に発生。

### 2.8 🟢 課金プランの過剰設計

PRD には Free / Light / Pro / Heavy / Supporter の5プラン。
MVP β段階で「Pro と Light の境界」を決める根拠データがない。

---

## 3. 代替案の検討

### 3.1 Alt-A: "Bare bones MVP" — 4週でリリース

**スコープ削減版**:
- 認証なし (匿名利用)、保存なし、課金なし、AI抽出なし
- 楽待URL貼り付け → 計算 → スコアのみ
- 月 1,000分析 → 全部Free, 投げ銭のみ

| 評価軸 | 評価 |
|---|---|
| ✅ 時間 | 4週 |
| ✅ 学習速度 | 早い (実ユーザー触る) |
| ❌ 収益 | ゼロ |
| ❌ データ蓄積 | できない (匿名・非保存) |
| ❌ ブランド形成 | 弱い (お試しツール感) |

**判定**: 採用しない。データの蓄積 (`extraction_corrections`) は将来のFT教師データとして資産価値が高い。

### 3.2 Alt-B: "Local-first MVP" — ブラウザ完結

すべてクライアントサイドで動かす:
- 計算エンジンを TypeScript ポート (or Pyodide WASM)
- データは IndexedDB (端末保存)
- Supabase / FastAPI 不要
- 認証も不要 (ブランドアカウントだけ)

| 評価軸 | 評価 |
|---|---|
| ✅ プライバシー訴求 | 最強 ("業者送客しない"を技術的に完璧に担保) |
| ✅ インフラコスト | ゼロ |
| ❌ デバイス間同期 | 不可 |
| ❌ FTデータ蓄積 | 不可 (匿名統計取れない) |
| ❌ 課金モデル | 困難 (機能ゲート不可能、ローカルなので) |
| ❌ AI抽出 | API キーが端末側にバレる |

**判定**: 部分的に魅力的だが、AI抽出が成立しない (キー露出)。**ただし将来オプションとして残す価値あり** (Pro Plus 機能で「ローカルモード」)。

### 3.3 Alt-C: "API-first / B2B" — 開発者向けAPI

計算エンジンを SaaS API として販売。
- 月 $99 で 10k 呼び出し
- 他社の物件管理アプリに組み込んでもらう

**判定**: コンセプト (個人投資家中立) と乖離。ピボットしすぎ。除外。

### 3.4 Alt-D: "Newsletter + Calc" — コンテンツ先行

- 計算ツールを無料公開 (今の状態)
- 週次ニュースレターで実例分析を発信
- メールリストを資産化、後から課金導入

**判定**: 補完的に**併走させるべき**。Twitter/X 発信 + 月次レポートは β以降の戦略として追加。

### 3.5 Alt-E: "TypeScript統一" — 単一言語化

financial-engine を TypeScript に移植 → FastAPI 削除 → すべて Next.js。

| 評価軸 | 評価 |
|---|---|
| ✅ 保守負荷 | 半減 |
| ✅ デプロイ単純化 | Vercel 一本 |
| ❌ 移植コスト | 2-3週 (84テストを書き直す必要) |
| ❌ PDF/Excel 解析 | TS ライブラリは Python より弱い |
| ❌ 数値計算精度 | numpy_financial の IRR ↔ JS の IRR で微差 |

**判定**: 既に書いた financial-engine を捨てるコストが大きい。**FastAPI は維持、Next.js Route Handler は薄いプロキシ層のみ**にする。

### 3.6 Alt-F: "PoC データ統合" — 既存資産を活かす

`land_price_api_app` の DuckDB データを Supabase Postgres へ ETL 移植 (一回限り):
- `mlit_land_prices_public_notice` テーブル (point_id, year, lat, lon, price)
- `mlit_trade_prices` テーブル
- `rent_market` テーブル

これで Score の `market_cap_rate` が最初から動く → スコアの意味が出る。

| 評価軸 | 評価 |
|---|---|
| ✅ Score の意味 | 大幅向上 |
| ✅ 初期データ | 47都道府県 × 1.5年 が即利用可能 |
| ✅ 実装コスト | DuckDB → Postgres COPY で1日 |
| ✅ 公示地価更新 | PoC の `sync_public_notice.py` を Celery タスク化 |
| ❌ ない | 特になし |

**判定**: **強く推奨**。やらない理由がない。

### 3.7 Alt-G: "Extraction-first" — 抽出の de-risk 優先

Phase 2 を「Supabase 認証」ではなく「抽出パイプライン」にする:

```
Week 1: Anthropic キー取得・classify_document + property_brochure 抽出
Week 2: 楽待URL → 抽出 → 計算 → スコアの完全フロー (認証なし)
Week 3: 抽出精度評価 (20サンプル)、プロンプト調整
Week 4-5: 認証・DB (抽出が動くと確定したあと)
Week 6+: その他
```

| 評価軸 | 評価 |
|---|---|
| ✅ リスク順序 | 正しい (不確実性高いものを先に) |
| ✅ Anthropic コスト | 早期計測できる |
| ✅ デモ可能性 | Week 2 で実物が動く |
| ❌ 投資 | Anthropic キー必要 (月 $10-30) |
| ❌ 友人βはまだ | 認証・保存が後回し |

**判定**: **強く推奨**。これが本来の順序。

---

## 4. PoC との関係再評価

`/home/kazumasa/projects/land_price_api_app/` の扱いは以前「完全に新規実装」と決定したが、**精査の結果これは部分的に間違い**。

### 4.1 完全に新規実装すべきもの
- UI 全部 (Streamlit → Next.js)
- DB スキーマ (DuckDB → Postgres、設計は new で正しい)
- 計算エンジン (sim_engine.py → financial-engine、より厳密に)

### 4.2 移植すべきもの (新規実装の労力を削減できる)

| PoC 資産 | 移植先 | 価値 |
|---|---|---|
| `sync_public_notice.py` (MLIT API クライアント) | `apps/worker` の定期ジョブ | 公示地価データ取り込みコード |
| `sync_trade_prices.py` (XIT001) | 同上 | 取引価格データ取り込み |
| `sync_rent_market.py` (e-Stat) | 同上 | 賃料相場データ取り込み |
| `geocoder.py` (国土地理院) | `apps/api/services/` | ジオコーディング |
| `analytics.py:find_nearby_points` | `apps/api/services/` | 近傍検索ロジック |
| **DuckDB データ実体 (1.5年分)** | **Postgres へ ETL** | 即利用可能なマーケット情報 |
| `property_scraper.py` の regex-first + LLM補完アーキ | `apps/worker/extractors/` の参照実装 | 抽出ストラテジ |
| 楽待・健美家のサイトスキーマ (`data/site_schemas/`) | `docs/prompts/property_brochure_v1.md` の examples 充実 | プロンプト用サンプル |

これだけで **2-3週分の作業を圧縮**できる。

### 4.3 並行運用方針

land_price_api_app は **データソース＋検証用 Streamlit ツール** として残す。
re_invest_os が本番サービス。
両者の DB は将来統合する可能性あり (現在は別物として並行)。

---

## 5. スタック判断の再確認

### 5.1 FastAPI vs 廃止

廃止案 (Alt-E TypeScript 統一) の試算:
- 移植コスト: 2-3週
- 削減できる継続コスト: 月 5-10時間 (型同期・FastAPI デプロイ・二重テスト)
- 損益分岐点: **15-25週** (3-6ヶ月)

MVP 12週では損益分岐前。**維持推奨**。
ただし、長期 (6ヶ月+) では再評価の余地。

### 5.2 Supabase vs 代替

| 候補 | DB | Auth | Storage | ロックイン | 月額 (β想定) |
|---|---|---|---|---|---|
| **Supabase** | Postgres | ✓ | ✓ | 中 (RLS) | $0-25 |
| Neon + Auth.js + R2 | Postgres | 別 | 別 | 低 | $0-19 |
| Firebase | Firestore | ✓ | ✓ | 高 | 従量 |
| 自前 (Hetzner VPS) | Postgres | 自前 | MinIO | 低 | $5-15 |

**判定**: Supabase 維持。代替案は運用負荷が増えてソロ向きでない。RLS は強い。

### 5.3 Stripe vs 国内決済

| 候補 | 手数料 | 国内特化 | サブスク |
|---|---|---|---|
| **Stripe** | 3.6% | ❌ (US寄り) | ✓ 強い |
| Pay.JP | 3.6% | ✓ | ✓ |
| Komoju | 2.9-3.6% | ✓ | ✓ |
| Stripe Atlas (法人化込み) | 3.6% + 法人費 | ❌ | ✓ |

**判定**: 国内開始なら Pay.JP / Komoju も真剣に検討すべき (手数料同等 + 国内サポート)。
ただし MVP は Stripe テストモードで開発、本番化前に再決定でも遅くない。

### 5.4 Worker 設計

現状: FastAPI BackgroundTasks → Phase 4 で Celery 化。

**代替**: 最初から軽量サーバレス使う
- **Inngest**: イベント駆動関数、TypeScript、無料枠
- **Trigger.dev**: 同上
- **Cloudflare Workers + Queues**: 安価、ベンダーロック

ただし Python ジョブが主体 (LLM 呼び出し・PDF解析) なのでサーバレス TS とは相性悪い。
**判定**: FastAPI BackgroundTasks → Celery のままで進む。Phase 5 で再評価。

---

## 6. MVP スコープ削減案

PRD の P0 (14個) + P1 (11個) = 25 機能を **半減** する。

### 6.1 MVP コア (8週で出す、9機能)

| # | 機能 | 理由 |
|---|---|---|
| 1 | URL貼り付け (楽待のみ) | 入口、最も使われる |
| 2 | PDF販売図面アップロード | 補助入口、レントロールは後 |
| 3 | AI抽出 + 確認画面 | 差別化の核 |
| 4 | 手動入力 (現状) | フォールバック |
| 5 | CF/IRR/DSCR 計算 (engine) | できている |
| 6 | 100点スコア (engine) | できている |
| 7 | 3行AIサマリー | 価値感が伝わる |
| 8 | Supabase 認証 + 履歴保存 | リテンション |
| 9 | Stripe Free/Pro 2段階 | 収益化 |

**実装済み: 5/9** (engine + 計算 + 手動入力)
**残: 4機能 × 平均1-2週 = 4-8週**

### 6.2 v0.5 (β後、追加開発)

- レントロール抽出 (戸数の多い物件)
- SUUMO / 健美家 URL対応
- 比較ボード
- 最大買付価格 UI (engine はある)
- 感応度 UI (engine はある)
- 確認質問リスト UI

### 6.3 v1 以降

- リテラシーテスト
- クロスアセット比較 UI
- ウォッチリスト + 価格アラート
- PDF/HTML レポート出力
- Light / Heavy / Strong Supporter プラン
- 投げ銭

### 6.4 削減効果

| 項目 | 現プラン | 改訂案 |
|---|---:|---:|
| MVP機能数 | 25 | 9 |
| 期間 | 12週 | 8週 |
| 必要時間 | 300時間 | 200時間 |
| β品質 | 不安 | 余裕 |

---

## 7. 推奨改訂プラン

### 7.1 改訂後のフェーズ

| 旧Phase | 新Phase | 期間 | 内容 |
|---|---|---|---|
| Phase 0 (済) | Phase 0 (済) | — | 設計・基盤・骨格 |
| **新2** | **抽出 de-risk** | Week 1-2 | Anthropic キー、classify + brochure 抽出、楽待URL対応、20サンプルで精度検証 |
| 旧2 | 認証・DB | Week 3 | Supabase セットアップ、マイグレーション、認証画面 |
| **新3** | **PoCデータ統合** | Week 4 | land_price_api_app の DuckDB → Postgres ETL、Score の market_cap_rate を活性化 |
| 旧3-4 | 分析パイプライン統合 | Week 5-6 | 抽出 → 確認 → 計算 → 結果 → 保存 のフロー、3行サマリー、履歴一覧 |
| 旧5-6 | 課金 + β | Week 7-8 | Stripe Free/Pro、本番デプロイ、友人β |

合計: **8週 (旧12週から短縮)**

### 7.2 何が変わったか

| 変更点 | 理由 |
|---|---|
| 抽出 de-risk を最優先 | リスクの順序 (§2.2) |
| PoCデータ取り込み追加 (Week 4) | Score の意味確保 (§2.3, §4) |
| MVP機能を 25→9 に削減 | スコープ現実化 (§2.1, §6) |
| 比較ボード・確認質問・感応度UI・最大買付価格UIを v0.5 へ | 同上 |
| レントロール抽出を v0.5 へ | 手書きレントロール精度問題、販売図面で代替可 |
| SUUMO/健美家 を v0.5 へ | 楽待だけで MVP 価値検証は可能 |

### 7.3 何を維持するか

- 全体スタック (Next.js + FastAPI + Supabase + Stripe)
- Bloomberg基調デザイン
- 計算エンジン (既に84テスト緑)
- 法務リスク検討 (legal_risk_checklist)
- 「業者送客しない」中核思想

### 7.4 アクション (改訂直後の3手)

| # | アクション | 必要 | 所要 |
|---|---|---|---|
| 1 | **PoC データを Postgres ETL するスクリプトを書く** | アカウント不要 | 半日 (DuckDB読込→SQL生成) |
| 2 | **Anthropic 抽出パイプラインを `apps/api` に追加** (キー不要、スケルトンだけ) | アカウント不要 | 半日 |
| 3 | **`docs/prompts/` の examples に PoC の site_schemas を流し込む** | アカウント不要 | 1時間 |

これだけで Anthropic キー取得後 1日で抽出が動き始める。

---

## 8. 不採用とした選択肢 (理由付き)

| 案 | 不採用理由 |
|---|---|
| 完全 Bare bones MVP (Alt-A) | データ蓄積価値を捨てる |
| Local-first / WASM (Alt-B) | LLM抽出が成立しない (APIキー露出) |
| B2B API販売 (Alt-C) | コンセプトのピボット過大 |
| TypeScript 単一化 (Alt-E) | 移植コストが12週MVPで回収できない |
| FastAPI 廃止 | 同上 |
| Supabase → 自前 | ソロで運用負荷高い |
| Pay.JP 採用 | 本番化前に再決定でよい (MVPは Stripe テスト) |
| Inngest / Trigger.dev | Python タスク主体と相性悪い |
| Next.js 15 ダウングレード | すでに16で組んでしまった、戻すコスト > 利益 |

---

## 9. 残る未解決論点

ユーザーが決める必要があるもの:

1. **改訂プランを採用するか** (この文書全体への賛否)
2. **PoC データ ETL を入れるか** (Score の価値を上げるか、まっさら新規実装で行くか)
3. **抽出 de-risk を Week 1-2 に置くか、それとも認証先行か**
4. **MVP9機能で足りるか、もっと削れるか/もっと盛るか**
5. **楽待だけで β を出すか、SUUMOまで MVP に入れるか**
6. **3行サマリーは MVP に必須か、v0.5でよいか**

---

## 10. 改訂版チェックリスト (採用された場合)

### 即実行 (アカウント不要)
- [ ] `docs/roadmap/mvp_roadmap.md` を改訂版で上書き
- [ ] `docs/product/product_requirements.md` の機能スコープを9機能に絞る
- [ ] `apps/worker/etl/` 雛形を作成
- [ ] PoC データ移行スクリプト `scripts/etl_public_notice.py` を書く
- [ ] `apps/api/services/extractors/` 雛形を作成
- [ ] `docs/prompts/property_brochure_v1.md` の examples を PoC site_schemas で充実

### キー取得後
- [ ] Anthropic API キー → 抽出パイプライン実装開始
- [ ] Supabase dev プロジェクト → マイグレーション流す

### Week 1-2 終了時に評価
- [ ] 楽待URLサンプル20件で抽出精度を計測
- [ ] 80%未達なら、プロンプトv2 / モデル切替で改善
- [ ] 70%未達なら、当面 PDF アップロードのみに絞る (URL解析を後回し)

---

## 11. 改訂版のリスク

新プランにもリスクはある:

| リスク | 確率 | 影響 | 緩和 |
|---|---|---|---|
| Anthropic キー早期取得が必要 | 確実 | 低 (月$10-30) | 個人クレカで可 |
| 抽出精度80%に届かない | 中 | 中 | PDF アップロード比率を上げる、楽待スキーマ専用化 |
| PoC データ ETL に予想外に時間 | 中 | 低 | 最悪 Score の市場機能を v0.5 へ後ろ倒し |
| MVP 9機能でも回るか不明 | 低 | 高 | 友人βで仮説検証、足りなければ追加 |

---

## 12. 改訂ログ

| 日付 | 内容 |
|---|---|
| 2026-05-12 | v0.1 初版精査。抽出de-risk・PoC統合・スコープ削減を推奨 |
