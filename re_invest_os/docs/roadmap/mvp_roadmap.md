# MVP Roadmap — re_invest_os

作成日: 2026-05-12
ベース: blueprint_v0_1.md §17, product_requirements.md, README.md
スコープ: 青写真26章フル + 周辺機能
期間: 12週 (Phase 0完了後、2026-05-12 起算)

---

## 0. 現状 (2026-05-12 時点)

### Phase 0 完了
- ✅ リポジトリ骨格 (monorepo: apps/, packages/, infra/, docs/, tests/)
- ✅ Phase 0ドキュメント (PRD, calculation_engine_spec, ai_document_extraction_spec, design_principles, data_schema, technical_architecture, legal_risk_checklist, mvp_roadmap)
- ✅ デザイン方向確定 (Bloomberg基調) + 5案モックアップ保存
- ✅ `packages/financial-engine` 全機能 (loan/cashflow/tax/exit/irr/score/max_offer/sensitivity/cross_asset) + 84テスト
- ✅ `apps/api` FastAPI雛形 + 7エンドポイント + 10テスト
- ✅ `apps/web` Next.js (Bloomberg基調) + API取得ライブ表示

### Phase 0 残
- Supabase プロジェクト作成 (ユーザー判断)
- API キー取得 (Anthropic / OpenAI / MLIT / e-Stat) (ユーザー判断)
- ロゴ / プロダクト名最終決定 (ユーザー判断)
- 法務文書の専門家レビュー (外部依頼)

---

## 1. Week 1-2: 認証・DB・基盤

### ゴール
ログインできてユーザー固有のデータが保存される。

### 成果物
- Supabase プロジェクト (dev / staging / prod)
- マイグレーション v1: users, user_profiles, user_investment_criteria, subscriptions
- マイグレーション v2: properties, property_listing_prices, uploaded_documents
- マイグレーション v3: analysis_runs + 子テーブル群
- Next.js: 認証 (`/login`, `/signup`, `/auth/callback`)
- Next.js: ダッシュボード骨格 (Bloomberg風レイアウト確立)
- FastAPI: JWT 検証ミドルウェア
- FastAPI: `/me`, `/criteria` エンドポイント (CRUD)
- E2E: ログイン → 投資基準保存 → 取得

### リスク
- Supabase Auth の Google ログインで callback URL の設定漏れ
- RLS ポリシー設定漏れで他人のデータが見えてしまう
- 本番Supabase切り替え時にマイグレーション順序

### KPI
- 認証成功率 99%
- DB クエリ p95 < 100ms

---

## 2. Week 3-4: 資料解析v0 (販売図面 + URL)

### ゴール
URL or PDF を投入すると物件データが構造化されて表示される。

### 成果物
- `packages/document-schemas`: classification + property_brochure スキーマ (Pydantic + zod)
- `apps/api`: `/api/documents/upload` (multipart, Supabase Storage 保存)
- `apps/api`: `/api/documents/{id}/classify`
- `apps/api`: `/api/documents/{id}/extract`
- `apps/api`: `/api/listings/from-url` (allowlist: rakumachi / suumo)
- Worker: BackgroundTasks (FastAPI) で非同期実行
- Anthropic Claude Haiku で抽出
- PII マスク (氏名・電話・メール regex)
- Next.js: アップロード UI (drag&drop)
- Next.js: 抽出結果確認画面 (項目別 confidence表示、編集可)
- Sentry連携
- fixtures: 楽待 / SUUMO サンプル各3件、販売図面PDF 5件

### リスク
- Anthropic API のレート制限・トークン上限
- HTML構造の変更 (楽待・SUUMOは頻繁に変わる)
- PDF抽出精度 (スキャンPDFはOCR必要)
- 個人情報がLLMに送られる事故

### KPI
- URL抽出成功率 80%
- 販売図面PDF 主要項目抽出率 80%
- 平均処理時間 < 30秒

---

## 3. Week 5-6: 分析パイプライン統合

### ゴール
抽出済み物件 → 投資シミュレーション → 結果画面まで一気通貫。

### 成果物
- Next.js: 「分析実行」ボタン → POST /analyze → 結果画面
- 結果画面 (Bloomberg基調): PROPERTY / KPI / SCORE / CASHFLOW / EXIT / SCORE BREAKDOWN
- 前提条件確認 expander (LTV, 金利, 保有年数, 出口Cap, 空室率, 修繕等)
- 最大買付価格セクション
- 感応度分析テーブル
- analysis_runs / 関連テーブルへの保存
- 「保存する」「比較に追加」ボタン
- /analyses (履歴一覧)
- 既存サンプル (西新宿) を実 DB データに移行

### リスク
- 入力フォームの設計 (どこまで露出するか、初心者向けレベル感)
- engine_version 変更時の過去分析の再現性
- 大量保存時の DB パフォーマンス

### KPI
- 分析処理成功率 90%
- フォーム→結果表示まで < 5秒
- 結果画面の再分析率 20%

---

## 4. Week 7-8: AIサマリー・確認質問・前提甘さチェック

### ゴール
分析結果に AI による「読み物」が乗り、業者への質問が自動生成される。

### 成果物
- `apps/api`: `/api/analyze/{id}/summary` (3行サマリー生成、Claude Haiku)
- `apps/api`: `/api/analyze/{id}/inquiry-questions` (確認質問リスト生成)
- `apps/api`: warning_flags (前提甘さ検出ルール群)
- Next.js: 3行サマリーパネル、warning_flags 表示
- Next.js: 確認質問リスト (チェックボックス付き、コピー機能)
- prompt versioning (`docs/prompts/summary_3line_v1.md` 等)
- ユーザー修正履歴 (`extraction_corrections`) を分類してプロンプト改善
- レントロール抽出 (PDF / Excel) を追加

### リスク
- LLM の「買い推奨」表現混入リスク → プロンプトで強く禁止 + 出力後 regex フィルタ
- レントロール (特に手書き) の精度
- 法務表現の安全性レビュー

### KPI
- AIサマリー生成成功率 95%
- 「買うべき」等の禁止表現出現率 0%
- ユーザー満足度 (フィードバック) 70%+

---

## 5. Week 9-10: 課金・保存・比較ボード

### ゴール
有料プランへのアップグレードが動作し、複数物件の比較ができる。

### 成果物
- Stripe Checkout (Free → Pro)
- Stripe Webhook (subscription.created / updated / deleted)
- `apps/api`: `/api/billing/portal` (Stripe Customer Portal)
- 機能ゲート: Pro限定機能 (詳細感応度, PDF出力, 最大買付価格 等)
- Free プラン: 月10分析の制限
- Next.js: 比較ボード (横並びテーブル、TanStack Table)
- Next.js: 保存物件・ウォッチリスト
- 投げ銭フォーム (Stripe Payment Intent, 任意金額)
- 退会・データ削除フロー (削除 → 30日後物理削除)
- 利用規約・プライバシー・特商法ページ
- PostHog 主要イベント計測
- raw file 30日削除ジョブ (cron)

### リスク
- Stripe webhook 重複処理 (idempotency)
- 退会後の Stripe customer 残存
- 課金境界の機能ゲートが甘いと FreeでProが使える
- 特商法表記の不備

### KPI
- Stripe 決済成功率 99%
- Free → Pro 転換率 (β中で計測開始)
- ユーザー削除APIが正常動作

---

## 6. Week 11-12: β公開・KPI測定

### ゴール
友人βから始めて、3か月後 KPI 目標達成に向かう。

### 成果物
- ドメイン取得 (Cloudflare) + DNS設定
- 本番デプロイ (Vercel + Fly.io + Supabase prod)
- LP公開
- 友人/知人 5-10人にβ招待
- 抽出失敗例の収集・分類
- Sentry エラー対応
- KPI ダッシュボード (PostHog 内)
- 法務・税務スポット相談 (弁護士・税理士)
- LP改善 (A/B)
- Twitter/X 開発ログ発信開始

### リスク
- 本番Supabase の RLS / マイグレーション事故
- 友人βで「PII漏れ」「業者送客」誤解
- LP コピーが投資助言と誤認される
- 検索流入が来ないと友人ユーザーだけで停滞

### KPI (3か月目標、青写真§4 と一致)
- 月間分析数 1,000件
- 登録ユーザー 100人 (友人以外 20人以上)
- 有料ユーザー 5人以上
- 週次継続 20人
- URL/資料抽出成功率 80%+
- 分析処理成功率 90%+
- 平均処理時間 30秒前後
- 再分析率 20%+

---

## 7. 週次マイルストーン (Week 1-12 一覧)

| 週 | マイルストーン |
|---:|---|
| **1** | Supabase セットアップ、DB v1, 認証実装着手 |
| **2** | 認証E2E動作、`/me` /`/criteria` 動作 |
| **3** | アップロード基盤、Claude Haiku 接続、分類動作 |
| **4** | 販売図面抽出、楽待/SUUMO URL解析、抽出確認UI |
| **5** | 結果画面 (Bloomberg) ライブデータ表示、保存 |
| **6** | 最大買付価格・感応度UI、履歴一覧、比較骨格 |
| **7** | AIサマリー、warning_flags、確認質問リスト |
| **8** | レントロール抽出、prompt versioning、コスト計測 |
| **9** | Stripe Free/Pro 動作、機能ゲート |
| **10** | 比較ボード、保存・ウォッチ、PostHog計測 |
| **11** | 本番デプロイ、ドメイン、友人β招待 |
| **12** | β改善ループ、KPI観測、LP A/B |

---

## 8. リスク & 緩和策

| リスク | 確率 | 影響 | 緩和策 |
|---|---|---|---|
| Anthropic API 価格・速度悪化 | 中 | 大 | OpenAI フォールバック実装、量子化LLM検討 |
| 楽待/SUUMO HTML構造変更 | 高 | 中 | スクレイパーのテスト fixture、weekly検証ジョブ |
| Stripe 検証通過遅延 | 中 | 中 | 早めに法人化 / 利用規約整備 |
| 法務クレーム (投資助言扱い) | 低 | 大 | 表現NG/OKリスト遵守、弁護士レビュー、免責多重表示 |
| 個人情報漏洩 (PII 含む資料の業者流出) | 低 | 致命的 | PIIマスク自動化、外部送信ログ、業者連携を技術的に禁止 |
| 友人β以外のユーザー来ない | 高 | 中 | Twitter発信、ProductHunt等のローンチ、SEO |
| LLMコスト暴騰 | 中 | 中 | 月次上限、Free制限、コスト計測の自動アラート |
| 個人事業の事業所得認定不可 | 中 | 中 (税効果) | 帳簿整備、課金導線、税理士確認 |

---

## 9. β後 (Week 13+) のロードマップ概略

| 期間 | テーマ |
|---|---|
| Month 4-5 | 抽出精度改善 (修正データ反映)、レントロール強化、固定資産税資料 |
| Month 6 | 公式ハザードデータ連携 (浸水想定区域 1都道府県) |
| Month 7-8 | リテラシーテスト、クロスアセット比較 UI、PDF レポート |
| Month 9-10 | 一棟物件特化、CAPEX診断、修繕履歴解析 |
| Month 11-12 | 価格説明モデル (ML)、匿名統計、独自LLM検討 |
| Month 13-18 | B2B版 (個人投資家思想を壊さない範囲)、法人化 |

---

## 10. 開発リソース

ソロ開発前提 (kazumasa)。Claude Code をペアとして活用。

- 平日: 2-3時間
- 週末: 6-10時間
- 想定: 週20-25時間 = MVP 12週 ≈ 250-300時間

外部リソース (発生時):
- 弁護士 (法務文書レビュー): 5-10万円 (Week 10-11)
- 税理士 (青色申告相談): 月3-5万円 (Phase 0から)
- デザイナー (ロゴ・LP意匠): 必要なら 10-30万円 (Week 6-8)
- 友人βテスター: 5-10人 (Week 11+)

---

## 11. 完了判定 (DoD)

各週のマイルストーンに対し、以下をクリアしたら完了:

- [ ] 機能が動作する (手動テスト OK)
- [ ] テストが緑 (pytest, typecheck)
- [ ] Sentry にエラーが出ていない (24h ベース)
- [ ] 該当する PostHog イベントが計測されている
- [ ] PR が main にマージ済み
- [ ] ドキュメント (README or spec) が更新済み

---

## 12. オープン論点

- ロゴ・プロダクト名 (Week 6 までに確定)
- LP のデザイン基調 (Bloomberg統一 or LPだけStripe寄り)
- ベータ招待方法 (DM / LP signup / 招待コード)
- 価格プラン Light (480円) を初期から出すか Pro 一本で行くか
- 単発レポート課金 (300-980円) の MVP 内採用
- 個別税理士監修 (法人税対応は v2 だが、それまでに監修するか)
