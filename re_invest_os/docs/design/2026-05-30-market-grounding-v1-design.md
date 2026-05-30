# Market Grounding v1 — Design Spec

> **⚠️ SUPERSEDED / DEFERRED (2026-05-30):** MVP再定義により本機能は "Later" へ棚上げ。
> 市場データ連携は甘さスコアの confidence A 自動昇格の任意ブースターとして将来再開する。
> 現行の優先計画は `docs/design/2026-05-30-mvp-redefinition-design.md` を参照。

- Status: Deferred (superseded by MVP redefinition)
- Date: 2026-05-30
- Scope: re_invest_os 分析の高度化 / 軸A「マーケット・グラウンディング」
- Owner: kikeuchi（個人開発）
- Related: `docs/architecture/calculation_engine_spec.md` (§5.6 score, §5.8 sensitivity)

## 1. 背景と問題

re_invest_os は「過度に楽観的な前提を critique する買い手側 DD ツール」を価値提案とする。
しかし現状、分析エンジンは精密だが **市場の真実が一滴も流れていない**:

- `apps/api/src/api/services/market_context.py` は **stub**。常に `None` を返す。
- `packages/financial-engine/src/re_engine/score.py`:
  - `_rent_score` は市場賃料が無いと **満点** を返す（"賃料相場情報未投入 (満点扱い)"）。
  - `_price_score` は市場 cap が無いと絶対 cap の閾値フォールバック。
- `apps/api/src/api/services/risk_engine.py` は `MarketBenchmark` が無いと **相場乖離判定をスキップ**。

結果として、市場データ未投入のとき **「データが無いほど高得点」** になりうる。これは
buy-side / critique-over-optimism という製品の約束に正面から反する。

加えて市場構造体が 3 つに分裂している:
- `re_engine/score.py::MarketContext` (Pydantic)
- `apps/api/services/risk_engine.py::MarketBenchmark` (Pydantic)
- `apps/api/services/market_context.py::MarketContext` (dataclass, stub)

## 2. ゴール / 非ゴール

### ゴール (v1)
1. score / risk を **実際の市場データ** で駆動する。
2. 市場データの **供給経路をハイブリッド化**:
   - 公式 API（国交省 不動産情報ライブラリ）= 地価・取引価格（再現性◎）
   - 自律 Web リサーチ = 賃料相場・空室率（カバレッジ）
3. 取得値に **出所・取得時刻・サンプル数・confidence** を付与し、分析に **スナップショット凍結**（再現性）。
4. 「市場未投入＝満点」を **coverage 調整** に是正する（§6）。
5. レポートに **Market Context パネル** を追加し、根拠を可視化する。

### 非ゴール (v1 では後回し)
- `bid_ranges` のショックを市場分位点に連動させる。
- 近傍 comps の一覧 UI。
- スケジュールバッチによる事前計算更新（オンデマンド + キャッシュで開始）。
- `apps/worker` への取得処理移管。
- cap 相場の自律取得（v1 は公式取引価格からの proxy のみ）。
- 確率的分析（軸B）・CF リアリズム（軸C）。別スペック。

## 3. 制約（既存コードの規約）

- **`re_engine` は純粋関数**。I/O・LLM・グローバル状態を持たない。市場データ取得は
  すべて `apps/api/src/api/services/` 側に置き、エンジンには Pydantic 構造体を **入力** として渡す。
- **再現性**: `AnalysisResult.engine_version` と同思想で、市場スナップショットに
  `provider_versions` と `fetched_at` を記録する。
- **計算を LLM に任せない**: 自律リサーチの LLM は「読む / 分類 / 集計」まで。最終 KPI・
  NOI・cap の計算はエンジンの純粋関数が行う。LLM 出力は Pydantic 検証 + sanity bounds を通す。
- **PII**: 本機能はエリア単位の公開データのみ扱い、物件固有 PII を外部送信しない
  （既存 `services/pii.py` の対象外だが、リサーチクエリに物件住所の番地以下を含めない）。

## 4. アーキテクチャ

選定: **案1 プロバイダ・レジストリ**（ブレインストーミングで承認済み）。

```
[analysis request]
  → MarketDataService.get_snapshot(area_key, geo) -> MarketSnapshot
        ├─ cache lookup (area-keyed, TTL)
        ├─ on miss → provider registry gather():
        │     OfficialLandPriceProvider   (同期, 国交省API)
        │     RentResearchProvider        (低速, WebSearch/WebFetch; background 可)
        ├─ merge → MarketSnapshot (metric ごとに出所/confidence)
        └─ persist cache + (分析確定時) analyses 行へ凍結
  → score.total_score(result, to_market_context(snapshot), data_quality)
  → risk_engine.assess_assumption_risks(..., to_market_benchmark(snapshot))
  → response: KPI + score(+coverage) + risks + MarketSnapshot(provenance)
```

新規コードの配置:
```
apps/api/src/api/services/market/
  __init__.py
  snapshot.py        # MarketSnapshot, MetricValue, area_key, adapters
  service.py         # MarketDataService (registry, cache, merge, freeze)
  cache.py           # area-keyed cache store (reio.db / Postgres)
  providers/
    __init__.py      # registry
    base.py          # MarketDataProvider protocol
    official.py      # OfficialLandPriceProvider (国交省API + 国土地理院ジオコード)
    rent_research.py # RentResearchProvider (WebSearch/WebFetch)
```
`market_context.py` (stub) は `service.py` + adapters に置き換え、削除する（dead code を残さない）。

## 5. データモデル: `MarketSnapshot`

サービス層 (`services/market/snapshot.py`)。将来 cross-app 共有が必要になれば
`packages/shared-schemas/` に移す。

```python
Confidence = Literal["A", "B", "C", "D"]   # 既存 re_engine.normalized.Confidence と整合
Method = Literal["official_api", "web_research", "stat", "proxy"]

class MetricValue(BaseModel):
    value: float | None          # 代表値 (通常 p50)
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    unit: str                    # "yen_per_sqm" | "ratio" など
    method: Method
    source: str                  # 例 "国交省 不動産情報ライブラリ XIT002"
    source_url: str | None = None
    sample_count: int = 0
    confidence: Confidence
    fetched_at: datetime
    model_config = ConfigDict(extra="forbid")

class MarketSnapshot(BaseModel):
    area_key: str                # 例 "13-shinjuku" / 駅キー
    geo: dict | None             # {lat, lng} 任意
    land_price_per_sqm: MetricValue | None = None
    market_cap_rate: MetricValue | None = None      # 取引価格からの proxy
    rent_per_sqm_monthly: MetricValue | None = None # p25/p50/p75
    vacancy_rate: MetricValue | None = None
    provider_versions: dict[str, str]               # {"official": "1.0", "rent_research": "1.0"}
    built_at: datetime
    ttl_days: int
    model_config = ConfigDict(extra="forbid")
```

### アダプタ（純粋エンジンへの変換）
```python
def to_market_context(s: MarketSnapshot) -> re_engine.score.MarketContext: ...
def to_market_benchmark(s: MarketSnapshot) -> risk_engine.MarketBenchmark: ...
def to_data_quality(s: MarketSnapshot) -> re_engine.score.DataQuality: ...
```
これにより既存の 3 分裂構造体を `MarketSnapshot` に一本化し、エンジン側構造体は
「エンジンが必要とする最小入力」として温存する。

### area_key の決め方
- 第一候補: `prefCode-cityCode`（国交省コード体系。PoC 知見と整合）。
- 駅単位がより適切なケースは将来拡張。v1 は市区町村粒度で固定し、ambiguity を避ける。

## 6. score / risk の結線 ＋「未投入＝満点」是正

承認済み: coverage 調整を入れる。

### score.py の変更
- 市場依存コンポーネント（`price`, `rent`）に **coverage** 概念を導入:
  - 市場データ **あり** → 従来どおり相対評価。
  - 市場データ **なし** → 満点ではなく **中立配点（max の 50%）** を上限とし、`covered=False` を立てる。
- `ScoreComponent` に `covered: bool = True` を追加。
- `ScoreResult` に `market_coverage: float`（0.0–1.0、市場依存配点のうち実データで賄えた割合）を追加。
- 評価ラベル（健全/中立/要警戒）は従来閾値を維持。ただし `market_coverage < 0.5` のとき
  UI は「市場データ不足のため暫定」バッジを出す（§7）。
- これは score の挙動変更。`score.py` 冒頭の仕様コメントに `score_spec_version = "0.2.0"` を明記し、
  `docs/architecture/calculation_engine_spec.md §5.6` を更新する。

### risk_engine.py の変更
- 機能追加は不要（既に `MarketBenchmark` を受ければ相場乖離判定が動く）。
- `MarketSnapshot` → `MarketBenchmark` アダプタを通して実データを供給するのみ。

## 7. UI: Market Context パネル（Bloomberg 基調）

レポート画面（`apps/web/src/app/report/`）に新パネルを追加:
- 物件値 vs 市場 p25 / p50 / p75（賃料・cap・空室・地価）。
- 乖離表示（例: 設定賃料 +12% vs 市場 p75）。
- 各メトリックに **出所 / 取得時刻 / confidence バッジ**。
- `market_coverage` が低いときは「暫定」バッジ + 「市場データを取得」アクション（再取得トリガ）。
- API 経由（`apps/web/src/app/api/market/route.ts` プロキシ）で取得。既存 panel 群と同じ
  非同期バックグラウンド取得パターンに合わせる。

## 8. キャッシュ & 再現性

- `market_snapshots` テーブル（reio.db / 本番 Postgres）。PK = `area_key`、`built_at`、`ttl_days`。
  - 地価: TTL = 365 日（年次公示）。
  - 賃料・空室: TTL = 30 日。
  - メトリックごとに TTL が違うため、`MetricValue.fetched_at` 単位で鮮度判定し、
    期限切れメトリックのみ再取得する（部分更新）。
- **凍結**: 分析確定時、その時点の `MarketSnapshot` を `analyses` 行に
  `market_snapshot_json`（新カラム）として保存。再分析時はこれを復元して同一結果を再現。
  - 注意（CLAUDE.md gotcha）: 既存 `analyses` 行を黙って書き換えるマイグレーションは禁止。
    `market_snapshot_json` は nullable 追加カラムとし、既存行は NULL のまま。
- `AnalysisResult`（純粋エンジン出力）にはフィールドを足さない。スナップショットは
  永続化層・レスポンス層が保持する（エンジン純粋性を維持）。

## 9. 自律リサーチの信頼性担保

- **provenance 必須**: `source_url` + `fetched_at` + `sample_count`。欠ける値は採用しない。
- **sanity bounds**（Pydantic validator、妥当域外は破棄して confidence を下げる）:
  - 賃料: 500–20,000 円/㎡・月
  - cap rate: 0.01–0.15
  - vacancy: 0.0–0.40
  - 地価: 1,000–50,000,000 円/㎡
- **confidence 算定**: `sample_count` と ソース品質（公式 > 統計 > 集計サイト > 個別募集）で A–D。
  - official_api → A/B、stat → B、web_research(集計) → C、web_research(少数) → D。
- **コスト/レイテンシ制御**: エリアキャッシュ + cache-miss 時のみ取得。リサーチが重い場合は
  `202 Accepted` + ポーリング（フロントは「市場データ取得中」表示）。worker 移管は v1 非対象。
- **LLM 境界**: リサーチ結果の数値は構造化抽出（既存 LLM client / format="json" の知見を流用）。
  最終的な NOI / cap / score は純粋エンジンが計算する。

## 10. テスト戦略（Definition of Done 準拠）

- **engine（score）**:
  - 市場データ無し → `rent`/`price` が満点を返さない（変更前に失敗する assert）。
  - `market_coverage` が 0.0–1.0 で正しく算出される。
  - 既存 score テストの更新（満点前提のものを coverage 前提に修正）。
- **service**:
  - 各プロバイダをモック化し、snapshot 統合・merge・area cache hit/miss・部分 TTL 更新・
    sanity bounds 破棄・confidence 算定をユニットテスト。
  - HTTP（国交省 API）と Web リサーチは fixture（録画）でテスト。ネットワーク非依存。
  - 凍結: 分析保存 → 再取得で同一 `market_snapshot_json` が復元されること。
- **統合（実出力の観察）**:
  - サンプル物件（西新宿レジデンス 504 号）を API 経由で分析し、score が市場データで
    変化すること・Market Context パネルに値と出所が表示されることを実画面で確認（webapp-testing）。
  - 既知 (input → output) の 1 ペアを手計算 or 公式 API 実値と突合して検証。
- **回帰**: `pytest re_invest_os/` 全体がグリーン。`tsc --noEmit` クリーン。

## 11. 前提・リスク

- **国交省 不動産情報ライブラリ API キー** が `apps/api/.env` に必要（PoC land_price_api_app で実績あり）。
  未設定時は OfficialLandPriceProvider をスキップし confidence を下げて degrade（fail せず）。
- **公式 API パラメータ知見**（PoC で確認済み、再利用）:
  - XPT002（公示地価）: `response_format`/`z`/`x`/`y`/`year`/`priceClassification` をクエリで渡す。
  - XIT002（取引価格）: `area`（prefectureCode ではない）。
  - 価格フィールドのパース（`u_current_years_price_ja` 等）に注意。
- **賃料相場の無料一次ソースが限定的**: 推定混じりになるため confidence で明示。誇張しない。
- **自律リサーチのコスト・レート制限・出所品質**: キャッシュ + 部分更新で抑制。
- **score 挙動変更**: 既存分析のスコアが下がりうる。`score_spec_version` で追跡し、UI で説明。

## 12. 段階実装の順序（plan の入力）

1. `MarketSnapshot` / `MetricValue` / アダプタ（テスト先行）。
2. score の coverage 是正（テスト先行、`score_spec_version` 更新、spec doc 更新）。
3. `MarketDataService` + area cache + 凍結（プロバイダはモックで）。
4. `OfficialLandPriceProvider`（fixture テスト）。
5. `RentResearchProvider`（fixture テスト、sanity bounds、confidence）。
6. API 結線（score/risk に実データ供給、レスポンスに snapshot）。
7. Market Context パネル（UI wired、webapp-testing で確認）。
8. 統合検証（サンプル物件、既知 input→output 突合）、回帰グリーン。
