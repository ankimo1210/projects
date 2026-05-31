# re_invest_os MVP Redefinition — Design Spec

- Status: Approved (Section A approved; Spec 1 detail approved via /goal autonomous directive)
- Date: 2026-05-30
- Owner: kikeuchi（個人開発）
- Supersedes (defers): `docs/design/2026-05-30-market-grounding-v1-design.md` → Later
- Related: `docs/architecture/calculation_engine_spec.md`, `CLAUDE.md`

## 0. 一行サマリー

re_invest_os を「買付前DD Webアプリ（B2C高度分析サブスク）」から、
**「不動産投資の営業資料を金融プロ水準で検証する中立DDエンジン」** に再定義する。
B2Cは集客装置、収益化はB2B/OEM・レポート課金へ寄せる。提供価値は「買いか？」では
なく **前提の甘さ / ストレス耐性 / 収支耐性価格帯 / 仲介確認事項**。

## 1. 戦略リフレーム（確定）

### 1.1 事業定義
- B2C向け高度分析サブスク単体での正面突破は困難（分析ツール単体課金が成立しにくい /
  楽待・健美家等の無料代替 / 低LTV高チャーン / 送客寄せはブランド毀損）。
- 本命収益化は **B2B/OEM・レポート課金・教育/FP/融資相談/管理会社向けツール**。
- B2Cの役割は直接収益ではなく、ユーザー接点・診断事例・信用・コンテンツ素材・B2B販売実績。

### 1.2 提供価値
「この物件は買いか？」ではなく:
- この営業資料・販売図面・URLの前提はどこが甘いか
- どの条件をストレスすると収支が崩れるか
- いくら以下なら収支耐性が残るか
- 仲介に何を確認すべきか

### 1.3 送客の線引き（精密化）
- 物件販売会社・ワンルーム販売会社には送客しない / リードを売らない / 検討履歴を渡さない。
- 税理士・FP・融資相談・保険・管理会社等の周辺連携は、透明性担保を条件に検討可能。

## 2. 法務・表現ルール（最重要）

投資助言・宅建業・金融商品販売に見える表現を、UI・レポート・AI出力・**テストデータ**から排除する。

### 2.1 禁止表現
買い / 見送り推奨 / おすすめ / 推奨買付価格 / 割安 / 購入すべき / 儲かる / 確実 /
保証 / この物件は良い / この物件は悪い / 健全（物件評価ラベルとして） / 要警戒 ほか。

### 2.2 使用可能表現
ユーザー入力条件に基づく試算 / 収支耐性 / 前提リスク / 確認未了項目 /
ストレス条件下で成立する価格帯 / 売出価格と収支耐性価格の差額 / 参考値 / 検証結果 / 感応度分析。

### 2.3 買付レンジの扱い
「推奨買付価格」ではなく **「条件を満たす価格帯の検証」** として表現する。
> ユーザー入力条件とストレス条件に基づくと、DSCR 1.25以上・税後IRR 8%以上を満たす価格帯は3,300万円以下です。

## 3. 技術原則（固定）

1. 計算をLLMに任せない。LLMはPDF/URL読解・分類・説明文整形に限定。
2. NOI/DSCR/税後CF/IRR/Equity Multiple/Payback/価格帯/感応度/甘さスコアは **deterministic engine（純粋関数）** で計算。
3. `engine_version` / `prompt_versions` / `input_snapshot_json` / `normalized_property_json` を保存し、全分析を再現可能にする。
4. NG表現チェックを **テストで担保** する。
5. レポート生成と分析ロジックを分離（将来のB2B/OEM展開）。

## 4. 既存資産との擦り合わせ

| 新MVP要素 | 既存コード | 方針 |
|---|---|---|
| 甘さスコア | `apps/api/src/api/services/risk_engine.py`（confidence/risk 完備、既にレポート「ASSUMPTION CRITIQUE 前提甘さ検出」に接続） | **中核に昇格・強化** |
| 物件健全性スコア | `packages/financial-engine/src/re_engine/score.py`（100点→健全/中立/要警戒） | **撤去**（価値判断ラベルを排除） |
| 収支耐性価格帯 | `re_engine/bid_ranges.py` + `re_engine/max_offer.py`（最大買付価格） | **改名・再フレーミング**（Spec 2） |
| ストレス | `re_engine/sensitivity.py` | 固定7シナリオ表示へ整理（Spec 2） |
| NG表現チェック | `apps/api/src/api/services/ng_filter.py`（LLM出力専用） | **拡張**（語彙＋UI/レポート/テストデータ＋テスト担保） |
| 市場データ連携 | Market Grounding v1 設計＋プラン | **Laterへ棚上げ**（confidence A 昇格の任意ブースター） |

既存の純粋エンジン入力契約（`Assumptions`）と出所追跡（`re_engine/normalized.py`:
`NormalizedProperty` / `FieldSource` / `Source→Confidence` マップ）は **そのまま活用**。
甘さスコアの confidence A–D は既に `normalized.py` の定義と完全一致している。

## 5. スコープ分割（実装プラン単位）

MVP（Must-Have 6機能・4週間）は1本の実装プランには大きすぎるため、3つに分割する。

- **Spec 1 — 分析コア再定義（Week 1–2）**【本ドキュメントで詳細化】
  エンジン安定化＋甘さスコア昇格・強化＋NG表現エンフォースメント土台＋健全性スコアUI撤去。
- **Spec 2 — ストレス＆収支耐性価格（Week 3）**【✅ 実装済 2026-05-31。plan: `docs/superpowers/plans/2026-05-31-reio-mvp-spec2-stress-resilience.md`】
  固定7ストレスの崩れ方表示（ΔDSCR付）＋`bid_ranges` ポリシーを current_case/base_stress/conservative_stress に改名し Resilience Price Range として提示。UI で「最大買付価格」表記を撤去（NG走査で担保）。
- **Spec 3 — 出力＆コンテンツ（Week 4）**【概要のみ。別スペックで詳細化】
  匿名診断テンプレ生成＋PDFレポート土台＋Phase 0サンプル格納。

各 Spec は spec → plan → implementation の独立サイクルを持つ。

---

# Spec 1 — 分析コア再定義（詳細）

## S1.1 ゴール / 非ゴール

### ゴール
1. 税後CF/IRR/DSCR エンジンの出力を安定化し、デッドクロス年を追加、schema/version を凍結。
2. 甘さスコアを分析の中核に昇格し、集約・カップリング・カテゴリを強化する。
3. 物件健全性スコア（100点・健全/要警戒）を撤去し、価値判断ラベルを排除する。
4. NG表現チェックを UI/レポート/テストデータへ拡張し、テストで担保する基盤を作る。

### 非ゴール（Spec 2/3 または Later）
- 固定7ストレス表示・収支耐性価格帯の改名（Spec 2）。
- 匿名診断テンプレ・PDFレポート（Spec 3）。
- 市場データ連携による confidence A 自動昇格（Later / Market Grounding v1）。

## S1.2 エンジン安定化

### デッドクロス年
- `KPI` に `dead_cross_year: int | None` を追加。
- 定義: `yearly_cashflows` を年順に走査し、初めて `depreciation_yen < principal_payment_yen`
  となる `year`。減価償却（非現金の損金）が元金返済（現金流出・非損金）を下回る転換点
  ＝帳簿黒字でも課税所得が膨らみキャッシュが痩せる「黒字倒産」リスクの起点。
- 発生しなければ `None`。`re_engine/analyze.py` で純粋導出。
  `YearlyCashflow` は既に `depreciation_yen` と `principal_payment_yen` を持つため追加I/Oなし。

### schema/version 凍結
- `engine_version`: `0.1.0 → 0.2.0`（KPIフィールド追加・後方互換のためminor）。
- ラウンドトリップテスト: `AnalysisResult.model_validate(result.model_dump(by_alias=True))` が不変。
- 再現性（原則3）: 分析保存時に `analyses` 行へ `input_snapshot_json`（=`Assumptions` 全体）と
  `normalized_property_json`（=`NormalizedProperty`）を **nullable 追加カラム** として永続化。
  既存行は NULL のまま（`CLAUDE.md` gotcha: 既存行を黙って書き換えない）。

## S1.3 甘さスコア 昇格・強化（中核）

### 集約ラッパー（§7.2 のJSON形に一致）
`risk_engine.py` に追加:
```python
class AssumptionScore(BaseModel):
    overall_risk: RiskLevel       # low / medium / high / unknown
    summary: str
    items: list[AssumptionRisk]
    model_config = ConfigDict(extra="forbid")

def assess_assumption_score(
    assumptions, result, normalized=None, market=None
) -> AssumptionScore:
    items = assess_assumption_risks(assumptions, result, normalized, market)
    items = _apply_dscr_coupling(result, items)   # S1.3 カップリング
    overall = _aggregate_overall_risk(items)
    return AssumptionScore(overall_risk=overall, summary=summarize_risks(items), items=items)
```
- `overall_risk` 集約: `high` が1つでもあれば `high`、なければ `medium` が1つでもあれば
  `medium`、いずれも無く全項目 `unknown` なら `unknown`、それ以外 `low`。

### DSCRカップリング
- 後段パス `_apply_dscr_coupling`: `result.kpi.dscr_min` が `1.00 <= x <= 1.15` のとき、
  `rent` / `interest_rate` / `opex` の `risk_level` を最低 `medium` に底上げ
  （既に `high` なら据え置き）。理由文に「DSCR最小 {x:.2f} の薄い返済余力下では
  これらの前提悪化が直ちに返済を圧迫する」を付記。

### 出口依存ルール
- `_exit_price_risk` に純粋指標を追加: `exit_share = net_proceeds / (Σ atcf + net_proceeds)`。
  `exit_share > 0.60` で `exit_price` を `high`（理由「投資リターンの過半が売却時手取りに依存」）。
  再計算不要・`AnalysisResult` のみで算出（純粋性維持）。

### カテゴリ追加（7 → 9）
- `Category` に `sale_year` と `acquisition_cost` を追加。
  - `_sale_year_risk`: `exit.hold_period_years` が confidence D（デフォルト）かつ
    `exit_share > 0.5` のとき `medium`。理由「保有年数の前提が出口依存度に影響」。
  - `_acquisition_cost_risk`: `acquisition.acquisition_cost_rate` が confidence D のとき
    `medium`。理由「諸費用率がデフォルト仮定。過小評価で初期投下資本を見誤る」。
- `assess_assumption_risks` の戻り値に2件追加。

### confidence A 昇格フック
- A は `NormalizedProperty.has_rent_roll` 等の一次資料フラグがある項目のみ。
  市場照合による A 昇格は Later（Market Grounding v1）。

## S1.4 物件健全性スコア 撤去

- `packages/financial-engine/src/re_engine/score.py` と `tests/test_score.py` を **削除**。
  `score.py` 専用の `MarketContext` / `DataQuality` も同時削除（他に利用箇所なし。
  `risk_engine` は独自 `MarketBenchmark` を保持）。
- 接続除去:
  - `apps/api/src/api/main.py`: `/analyze` レスポンスの `score: ScoreResult` を
    `assumption_score: AssumptionScore` に置換。`from re_engine.score import ...` を削除。
  - `apps/api/src/api/routers/deals.py:293` の `total_score(analysis)` を除去し
    `assess_assumption_score(...)` に置換。
  - フロント: `apps/web/src/components/deal/DealSummaryCard.tsx` の "SCORE" /
    `evaluation` セルを撤去。`apps/web/src/components/report-panels.tsx` の100点パネル
    （components マップ・「分析上の健全性スコア」文言）を撤去。
- 甘さスコアパネル（ASSUMPTION CRITIQUE）を主役に昇格し、見出しを
  「前提リスク検証 / ASSUMPTION RISK」へ再フレーミング（「健全/要警戒」を出さない）。
- API スキーマ変更のため `apps/web/src/types/api.ts`（型）を再生成/更新。

## S1.5 NG表現エンフォースメント土台

### 語彙拡張（`ng_filter.py`）
- 追加: `推奨買付価格` / `購入すべき` / `この物件は良い` / `この物件は悪い` / `見送り推奨` /
  `買いです` / `買いだ` / `買いと判断` / `割安` / `儲かる` / `確実` / `保証` ほか §2.1 準拠。
- ⚠️ 裸の「買い」はトークン登録しない（`買付` / `買い手` / `買い増し` / `買付前` は正当）。
  句として登録し誤検出を避ける。

### テストで担保
- `apps/api/tests/test_ng_expressions.py`（新規）:
  指定グロブを走査し全テキストに対し `has_ng(content) == False` を assert。
  - 走査対象: `apps/web/src/**/*.tsx`（表示ラベル）・`docs/prompts/**/*.md`・
    分析系テスト fixture（`apps/api/tests/fixtures/**`）。
  - ⚠️ 免責文 allowlist: 免責文は「…購入…を推奨するものではありません」のように
    禁止語を正当に含む。免責文を単一 `DISCLAIMERS` 定数（新規 `apps/api/src/api/constants.py`
    を作成し1箇所に集約）に置き、走査対象から除外する。
- 既存のLLM出力ランタイムチェック（summarizer等）は維持。

## S1.6 テスト戦略（Definition of Done 準拠）

変更前に**失敗する**ことを確認してから実装する（TDD）:
- `dead_cross_year`: 既知入力（築古・元金均等寄り）で特定年を返す手計算ペア。発生しないケースで `None`。
- `overall_risk` 集約: high/medium/low/unknown 各分岐。
- DSCRカップリング: `dscr_min=1.05` で rent/interest_rate/opex が medium 以上に底上げされる。
- 出口依存: `exit_share>0.6` で `exit_price=high`。
- 新カテゴリ: `sale_year` / `acquisition_cost` が9カテゴリ出力に含まれる。
- NGエンフォースメント: 走査面に NG 語を仕込むとテストが落ち、免責文では落ちない。
- score撤去後: 全スイート green、`/analyze` が `assumption_score` を返す。

統合（実出力の観察）:
- サンプル物件「西新宿レジデンス504」を API 経由で分析し、`assumption_score.overall_risk`
  が出力され、レポート画面で甘さスコアが主役表示・「健全/要警戒」が消えていることを
  実画面で確認（webapp-testing）。
- 既知 (input→output) の1ペアを手計算と突合（dead_cross_year / overall_risk）。

回帰: `pytest re_invest_os/` 全体 green、`tsc --noEmit` クリーン、`ruff` クリーン。

## S1.7 段階実装の順序（plan の入力）

1. `KPI.dead_cross_year` 追加（テスト先行、`engine_version` 0.2.0、spec doc 更新）。
2. `AssumptionScore` 集約ラッパー + `overall_risk`（テスト先行）。
3. DSCRカップリング + 出口依存ルール + 新カテゴリ2件（テスト先行）。
4. `score.py` / `test_score.py` 削除 + API/フロント接続を `assumption_score` へ置換 + 型再生成。
5. NG語彙拡張 + `DISCLAIMERS` 集約 + `test_ng_expressions.py`（テスト先行）。
6. 統合検証（サンプル物件、実画面、既知 input→output 突合）、回帰グリーン。

## S1.8 前提・リスク

- `score.py` 撤去で既存の `/analyze` レスポンス形が変わる（破壊的）。フロント型再生成必須。
- `risk_engine.py` は `apps/api/services` に留置（最小差分）。純粋ロジックだが将来的に
  `packages/financial-engine` への移設余地あり（Spec外のクリーンアップ）。
- NG走査の免責文 allowlist 設計を誤ると正当な免責文で落ちる/見逃す。`DISCLAIMERS` を
  1箇所に集約することで管理する。

---

# Spec 2 / 3（概要のみ・別スペックで詳細化）

## Spec 2 — ストレス＆収支耐性価格
- 固定7ストレス: 金利+1.0% / 賃料-5% / 空室+5pt / OPEX+10% / 修繕+20% / 出口-10% / 複合。
  `sensitivity.py` を土台に「標準条件 vs 各ストレスの DSCR・税後IRR」を表で提示。
  UI文言「投資判断ではなく、入力条件に対する感応度分析」。
- 収支耐性価格帯: `bid_ranges.py` / `max_offer.py` を **Resilience Price Range** に改名・再構成。
  POLICIES（current_case / base_stress / conservative_stress）で「条件を満たす価格帯」を提示。
  「MAX OFFER 最大買付価格」パネル・`/max_offer` を改名・再フレーミング。

## Spec 3 — 出力＆コンテンツ
- 匿名診断投稿テンプレ生成（物件名/番地/URL/画像/業者名を除去、価格・面積を丸め、判断表現を入れない）。
- PDFレポート土台（物件概要/入力条件/主要指標/年次CF/ストレス/前提リスク/収支耐性価格帯/仲介確認/免責）。
  レポート生成を分析ロジックから分離（B2B/OEM 前提）。
- Phase 0 手動診断サンプル（20–30件）を格納できる仕組み。

# MVP Definition of Done（再掲）

- 税後CF/IRR/DSCR が安定出力（+デッドクロス年）。
- 甘さスコア（overall_risk + items）が出る。
- ストレス条件での崩れ方が出る（Spec 2）。
- 収支耐性価格帯が出る（Spec 2）。
- 匿名診断テンプレが生成できる（Spec 3）。
- PDFレポート構成ができている（Spec 3）。
- NG表現チェックがテストである。
- LLMが数値計算をしていない。
- 既存テストが通る / 新規テストが追加されている。
- README/docs に今回のMVP方針が記録されている。
