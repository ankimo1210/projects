# re_invest_os 新機能 Top7 実装指示書

作成日: 2026-05-23
対象: re_invest_os / 不動産買付前 DD Web アプリ
目的: 既存の分析エンジン・AI抽出・比較ボードを活かし、買付前判断に直結する新機能 Top7 を実装する。

---

## 0. 実装方針

この実装では、Top7 をバラバラの機能として追加しない。
`Deal Workspace` という 1 つの買付前 DD 画面に統合する。

ユーザー体験は以下を目指す。

```text
物件URLまたは販売図面PDFを入れる
  ↓
収支・税後CF・IRR・DSCRを計算
  ↓
いくらなら買えるか分かる
  ↓
どの前提が危ないか分かる
  ↓
仲介に何を確認すべきか分かる
  ↓
自分用の投資メモとして保存できる
  ↓
複数物件を比較・ウォッチできる
```

---

## 1. 固定原則

以下は絶対に守る。

1. 計算を LLM に任せない
   - LLM は読む、分類する、説明文を整える用途に限定する。
   - NOI、DSCR、IRR、税後CF、最大買付、感応度はすべて deterministic engine で計算する。

2. 分析結果は再現可能にする
   - `engine_version`
   - `prompt_versions`
   - `input_snapshot_json`
   - `normalized_property_json`
   を必ず保存する。

3. 投資助言に見える表現を避ける
   - NG: 買い、見送り推奨、おすすめ、割安、購入すべき
   - OK: ユーザー入力条件に基づく試算、収支耐性、前提リスク、確認未了項目、買付価格レンジ

4. 「業者送客しない」前提を崩さない
   - 仲介会社への送客導線は作らない。
   - 物件問い合わせ代行も作らない。
   - ユーザーの検討履歴を業者に渡さない。

5. 既存機能を最大限再利用する
   - 既存の URL/PDF 抽出
   - cashflow engine
   - sensitivity engine
   - max bid engine
   - AI Insight
   - SQLite 永続化
   - 比較ボード
   を前提に実装する。

---

## 2. 実装対象 Top7

優先順位は以下。

1. 買付価格レンジ
2. 前提リスクスコア
3. 仲介確認チェックリスト
4. 投資委員会メモ
5. ウォッチリスト
6. PDF/URL 差分比較
7. 反証カード

初期 MVP では 1〜4 を最優先。
5〜7 は MVP 後半または Phase 2 でよい。

---

# Part A. データモデル

## A1. deals

物件検討単位。

```sql
CREATE TABLE deals (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    property_type TEXT,
    status TEXT NOT NULL DEFAULT 'analyzing',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

`status` 候補:

```text
analyzing
waiting_for_broker
ready_to_bid
bid_submitted
rejected
passed
archived
```

---

## A2. analysis_runs

分析実行単位。
同じ deal に対して複数回分析できるようにする。

```sql
CREATE TABLE analysis_runs (
    id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    prompt_versions JSON,
    input_snapshot_json JSON NOT NULL,
    normalized_property_json JSON NOT NULL,
    metrics_json JSON NOT NULL,
    sensitivity_json JSON,
    max_bid_json JSON,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);
```

---

## A3. bid_ranges

買付価格レンジ。

```sql
CREATE TABLE bid_ranges (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL,
    aggressive_price INTEGER,
    base_price INTEGER,
    conservative_price INTEGER,
    explanation_json JSON,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

---

## A4. assumption_risks

前提リスク。

```sql
CREATE TABLE assumption_risks (
    id TEXT PRIMARY KEY,
    analysis_run_id TEXT NOT NULL,
    category TEXT NOT NULL,
    value_json JSON,
    confidence TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

`category` 候補:

```text
rent
vacancy
opex
repair
interest_rate
exit_price
tax
```

`confidence` 候補:

```text
A: 実データまたは一次資料で確認
B: 販売図面・URL等に明記
C: ユーザー入力のみ
D: デフォルト仮定
```

`risk_level` 候補:

```text
low
medium
high
unknown
```

---

## A5. checklist_items

仲介確認チェックリスト。

```sql
CREATE TABLE checklist_items (
    id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    question TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    answer TEXT,
    evidence_url TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

`status` 候補:

```text
open
answered
not_applicable
dismissed
```

---

## A6. market_evidence_cards

反証カード。

```sql
CREATE TABLE market_evidence_cards (
    id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT,
    card_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_json JSON,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

`card_type` 候補:

```text
rent_market
price_market
land_price
demographics
hazard
liquidity
```

---

## A7. investment_memos

投資委員会メモ。

```sql
CREATE TABLE investment_memos (
    id TEXT PRIMARY KEY,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT NOT NULL,
    memo_markdown TEXT NOT NULL,
    memo_snapshot_json JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id),
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs(id)
);
```

---

## A8. watchlist_items

ウォッチリスト。

```sql
CREATE TABLE watchlist_items (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    deal_id TEXT NOT NULL,
    watch_status TEXT NOT NULL DEFAULT 'active',
    target_bid_price INTEGER,
    latest_asking_price INTEGER,
    last_checked_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);
```

---

# Part B. Backend 実装

## B1. ディレクトリ構成

以下の構成を目安に実装する。

```text
backend/app/
  domains/
    deals/
      models.py
      schemas.py
      service.py
      routes.py

    analysis/
      engine/
        cashflow.py
        irr.py
        sensitivity.py
        max_bid.py
        bid_ranges.py
      schemas.py
      routes.py

    assumptions/
      risk_engine.py
      schemas.py
      routes.py

    checklist/
      rules.py
      llm_refine.py
      schemas.py
      routes.py

    memo/
      builder.py
      templates/
        investment_memo.md
      routes.py

    market/
      evidence_cards.py
      schemas.py
      routes.py

    watchlist/
      schemas.py
      service.py
      routes.py
```

既存構成とズレる場合は、既存構成を優先しつつ責務は分離する。

---

# Part C. 機能別仕様

---

## C1. 買付価格レンジ

### 目的

売出価格に対して、ユーザー入力条件とストレス条件に基づく買付価格レンジを出す。

### 表示する価格

```text
強気レンジ
標準レンジ
安全レンジ
```

### 計算ポリシー

```python
@dataclass(frozen=True)
class BidPolicy:
    name: str
    min_dscr: float
    min_after_tax_irr: float
    rent_shock: float
    vacancy_shock: float
    rate_shock: float
    opex_shock: float
```

初期値:

```python
BID_POLICIES = [
    BidPolicy(
        name="aggressive",
        min_dscr=1.20,
        min_after_tax_irr=0.075,
        rent_shock=0.00,
        vacancy_shock=0.00,
        rate_shock=0.00,
        opex_shock=0.00,
    ),
    BidPolicy(
        name="base",
        min_dscr=1.25,
        min_after_tax_irr=0.080,
        rent_shock=-0.03,
        vacancy_shock=0.02,
        rate_shock=0.005,
        opex_shock=0.05,
    ),
    BidPolicy(
        name="conservative",
        min_dscr=1.35,
        min_after_tax_irr=0.090,
        rent_shock=-0.07,
        vacancy_shock=0.05,
        rate_shock=0.010,
        opex_shock=0.10,
    ),
]
```

### 実装要件

- 既存の最大買付二分探索ロジックを再利用する。
- 各 `BidPolicy` ごとに最大成立価格を計算する。
- 必ず以下の関係を満たす。

```text
conservative_price <= base_price <= aggressive_price
```

- 成立価格が計算不能な場合は `null` を返す。
- LLM は使わない。

### API

```text
POST /api/analysis/{analysis_run_id}/bid-ranges
GET  /api/analysis/{analysis_run_id}/bid-ranges
```

### レスポンス例

```json
{
  "analysis_run_id": "run_123",
  "asking_price": 39800000,
  "aggressive_price": 35200000,
  "base_price": 33400000,
  "conservative_price": 30800000,
  "gap_to_base_price": -6400000,
  "gap_to_base_price_pct": -0.1608,
  "explanation": {
    "aggressive": "現状前提で DSCR 1.20、税後IRR 7.5% を満たす価格です。",
    "base": "軽いストレス条件で DSCR 1.25、税後IRR 8.0% を満たす価格です。",
    "conservative": "保守的ストレス条件で DSCR 1.35、税後IRR 9.0% を満たす価格です。"
  }
}
```

### UI

カード表示。

```text
売出価格: 3,980万円

買付価格レンジ
強気: 3,520万円
標準: 3,340万円
安全: 3,080万円

標準レンジとの差額: -640万円
```

### 禁止表現

```text
買うべき
おすすめ
割安
買い
見送り
```

---

## C2. 前提リスクスコア

### 目的

収支分析がどの前提に依存しているかを可視化する。

### 対象カテゴリ

```text
rent
vacancy
opex
repair
interest_rate
exit_price
tax
```

### 信頼度

```text
A: 実データまたは一次資料で確認
B: 販売図面・URL等に明記
C: ユーザー入力のみ
D: デフォルト仮定
```

### リスク判定ロジック例

```python
def assess_assumption_risks(normalized_property, metrics, market_data=None):
    risks = []

    if normalized_property.rent.source in ["pdf", "url"]:
        confidence = "B"
    elif normalized_property.rent.source == "user_input":
        confidence = "C"
    else:
        confidence = "D"

    if market_data and normalized_property.rent_per_sqm > market_data.rent_p75:
        risk_level = "high"
    else:
        risk_level = "medium" if confidence in ["C", "D"] else "low"

    risks.append(...)
    return risks
```

### 実装要件

- 最初は market_data がなくても動くようにする。
- market_data がある場合のみ相場乖離判定を行う。
- confidence と risk_level の根拠を必ず `reason` に保存する。
- LLM は使わない。説明文整形だけ LLM 使用可。

### API

```text
POST /api/analysis/{analysis_run_id}/assumption-risks
GET  /api/analysis/{analysis_run_id}/assumption-risks
```

### UI

```text
前提リスク

賃料: B / medium
空室率: D / high
修繕費: D / high
金利: C / medium
出口価格: C / high
```

画面上部には以下のように要約する。

```text
この分析は、修繕費・空室率・出口価格の仮定に強く依存しています。
```

---

## C3. 仲介確認チェックリスト

### 目的

ユーザーが仲介会社に確認すべき事項を、物件ごとに整理する。

### 実装方針

- ルールベースで質問候補を生成する。
- LLM は文面調整にのみ使う。
- 質問の優先度と根拠は LLM に変更させない。

### ルール例

```python
def generate_checklist(property, metrics, risks):
    items = []

    if metrics.dscr < 1.15:
        items.append(ChecklistItem(
            category="rent",
            priority="high",
            question="現賃料の開始時期と直近の更新状況を確認してください。",
            reason="DSCR が低く、賃料下振れで返済余力が悪化しやすいため。"
        ))

    if property.building_age >= 15:
        items.append(ChecklistItem(
            category="repair",
            priority="high",
            question="大規模修繕履歴と今後の修繕計画を確認してください。",
            reason="築年数的に修繕費上振れリスクがあるため。"
        ))

    if risks.exit_price.risk_level == "high":
        items.append(ChecklistItem(
            category="exit_price",
            priority="medium",
            question="近隣の直近成約事例や売却時の想定価格根拠を確認してください。",
            reason="出口価格の前提が分析結果に大きく影響しているため。"
        ))

    return deduplicate(items)
```

### 初期チェックリストルール

最低限、以下を実装する。

| 条件 | 質問 |
|---|---|
| DSCR < 1.15 | 現賃料の開始時期・更新状況 |
| 賃料信頼度 C/D | 賃料査定根拠 |
| 築15年以上 | 修繕履歴・大規模修繕計画 |
| 区分マンション | 管理組合議事録・修繕積立金値上げ予定 |
| 空室率 D | 同エリア募集期間・空室実績 |
| 出口価格リスク high | 近隣成約・売却想定根拠 |
| レントロールあり | 入居者属性・滞納履歴 |
| 借地/再建築不可/旧耐震 | 権利関係・融資可否 |

### API

```text
POST /api/deals/{deal_id}/checklist/generate
GET  /api/deals/{deal_id}/checklist
PATCH /api/checklist-items/{item_id}
```

### PATCH 例

```json
{
  "status": "answered",
  "answer": "2024年4月から入居。更新は2026年4月予定。",
  "evidence_url": null
}
```

### UI

テーブル表示。

```text
優先度 | 状態 | 確認事項 | 理由 | 回答メモ
```

---

## C4. 投資委員会メモ

### 目的

個人投資家が検討履歴を残せるようにする。
PDF出力・課金への接続点にもする。

### メモ構成

```markdown
# 投資メモ

## 1. 物件概要

## 2. 投資仮説

## 3. 主要指標

## 4. 買付価格レンジ

## 5. 前提リスク

## 6. 確認未了事項

## 7. 下振れシナリオ

## 8. 見送り条件

## 9. 次アクション
```

### 実装方針

- `memo_snapshot_json` を作る。
- LLM に snapshot を渡して Markdown に整形させる。
- LLM は数値を再計算しない。
- LLM は判断を断定しない。
- 生成後、NG表現チェックを通す。

### NG表現チェック

以下が含まれていたら生成を失敗扱いにするか、自動修正する。

```text
買い
買うべき
おすすめ
推奨
割安
見送り
儲かる
確実
保証
```

### API

```text
POST /api/deals/{deal_id}/memo
GET  /api/deals/{deal_id}/memos
GET  /api/memos/{memo_id}
```

### LLM プロンプト要件

```text
あなたは不動産投資の買付前DDメモを整形するアシスタントです。
以下のJSONに含まれる数値のみを使ってください。
数値の再計算は禁止です。
投資判断を断定しないでください。
「買い」「おすすめ」「推奨」「割安」「儲かる」「確実」などの表現は禁止です。
出力は日本語Markdownのみ。
```

---

## C5. ウォッチリスト

### 目的

検討中物件を保存・管理する。

### 実装範囲

初期版では以下のみ。

- deal をウォッチリストに追加
- ステータス変更
- 目標買付価格保存
- 最新売出価格の手動更新
- 確認未了数の表示

自動スクレイピング監視は実装しない。

### API

```text
POST   /api/deals/{deal_id}/watchlist
GET    /api/watchlist
PATCH  /api/watchlist/{watchlist_item_id}
DELETE /api/watchlist/{watchlist_item_id}
```

### UI

```text
物件名
売出価格
標準買付価格
乖離
確認未了数
ステータス
最終更新日
```

---

## C6. PDF/URL 差分比較

### 目的

複数物件を同じ軸で比較する。

### compare_vector

```python
class CompareVector(BaseModel):
    deal_id: str
    title: str
    asking_price: int | None
    gross_yield: float | None
    noi_yield: float | None
    dscr: float | None
    after_tax_irr: float | None
    equity_multiple: float | None
    payback_years: float | None
    max_bid_base: int | None
    gap_to_asking: float | None
    rent_confidence: str | None
    repair_risk: str | None
    exit_price_risk: str | None
    open_checklist_count: int
```

### API

```text
GET /api/deals/compare?deal_ids=id1,id2,id3
```

### UI

最大5件比較。
最上段に以下を出す。

```text
標準買付価格との差額
DSCR
税後IRR
前提リスク high 数
確認未了数
```

---

## C7. 反証カード

### 目的

物件資料に書かれている前提を、外部データで検証する。

### 初期版

最初は market_data が不完全でもよい。
以下のカードを作る。

1. 賃料相場カード
2. 価格相場カード
3. 公示地価カード

### API

```text
POST /api/deals/{deal_id}/evidence-cards/generate
GET  /api/deals/{deal_id}/evidence-cards
```

### 出力例

```json
{
  "card_type": "rent_market",
  "title": "賃料相場との比較",
  "summary": "現賃料は近隣推定レンジの上限付近です。",
  "confidence": "medium",
  "payload": {
    "current_rent": 145000,
    "market_rent_p25": 128000,
    "market_rent_p50": 134000,
    "market_rent_p75": 139000
  }
}
```

### 実装注意

- データがない場合は無理に推定しない。
- `unknown` として表示する。
- LLM に相場推定をさせない。

---

# Part D. Frontend 実装

## D1. Deal Workspace

ルート:

```text
/deals/[id]
```

タブまたはセクション:

```text
Summary
Bid Range
Assumption Risk
Checklist
Evidence
Memo
Compare
```

---

## D2. コンポーネント

```text
frontend/src/components/deal/
  DealHeader.tsx
  DealSummaryCard.tsx
  BidRangeCard.tsx
  AssumptionRiskPanel.tsx
  ChecklistTable.tsx
  EvidenceCards.tsx
  InvestmentMemoPanel.tsx
  CompareDrawer.tsx
  WatchlistButton.tsx
```

---

## D3. BidRangeCard

表示要件:

- 売出価格
- 強気価格
- 標準価格
- 安全価格
- 標準価格と売出価格の差額
- 各レンジの条件説明

禁止:

- 買い/見送り判定バッジ
- おすすめ表示
- 色だけに依存した判断表示

---

## D4. AssumptionRiskPanel

表示要件:

- カテゴリ
- 信頼度
- リスクレベル
- 理由
- 参照ソース

信頼度説明ツールチップ:

```text
A: 一次資料または実データ
B: 販売図面・URLに記載
C: ユーザー入力
D: デフォルト仮定
```

---

## D5. ChecklistTable

表示要件:

- 優先度
- 状態
- 質問
- 理由
- 回答メモ
- 保存ボタン

状態変更:

```text
未確認
回答済み
対象外
非表示
```

---

## D6. InvestmentMemoPanel

表示要件:

- メモ生成ボタン
- Markdown preview
- コピー
- PDF export placeholder

初期版では PDF export はダミーボタンでもよい。
ただし将来課金導線にする前提でコンポーネントを分ける。

---

## D7. Watchlist

ルート:

```text
/watchlist
```

表示:

```text
物件名
売出価格
標準買付価格
差額
確認未了数
ステータス
更新日
```

---

# Part E. API 一覧

```text
POST /api/analysis/{analysis_run_id}/bid-ranges
GET  /api/analysis/{analysis_run_id}/bid-ranges

POST /api/analysis/{analysis_run_id}/assumption-risks
GET  /api/analysis/{analysis_run_id}/assumption-risks

POST /api/deals/{deal_id}/checklist/generate
GET  /api/deals/{deal_id}/checklist
PATCH /api/checklist-items/{item_id}

POST /api/deals/{deal_id}/memo
GET  /api/deals/{deal_id}/memos
GET  /api/memos/{memo_id}

POST   /api/deals/{deal_id}/watchlist
GET    /api/watchlist
PATCH  /api/watchlist/{watchlist_item_id}
DELETE /api/watchlist/{watchlist_item_id}

GET /api/deals/compare?deal_ids=id1,id2,id3

POST /api/deals/{deal_id}/evidence-cards/generate
GET  /api/deals/{deal_id}/evidence-cards
```

---

# Part F. テスト要件

## F1. bid_ranges

必須テスト:

```text
- aggressive/base/conservative の3価格が返る
- conservative <= base <= aggressive を満たす
- 金利ショックを上げると価格が下がる
- 賃料ショックを下げると価格が下がる
- 成立不能ケースで null を返す
```

---

## F2. assumption_risks

必須テスト:

```text
- PDF/URL抽出値は confidence B
- ユーザー入力値は confidence C
- デフォルト仮定は confidence D
- 市場レンジ上限超過時に risk_level high
- market_data なしでも動く
```

---

## F3. checklist

必須テスト:

```text
- DSCR < 1.15 で賃料確認質問が出る
- 築15年以上で修繕質問が出る
- 区分マンションで管理組合質問が出る
- 重複質問が出ない
- dismissed の項目が再生成で復活しない
```

---

## F4. memo

必須テスト:

```text
- memo_snapshot_json の数値だけが使われる
- NG表現が含まれる場合に検知できる
- Markdown の必須見出しが揃っている
- analysis_run_id に紐づいて保存される
```

---

## F5. watchlist

必須テスト:

```text
- deal を watchlist に追加できる
- status を変更できる
- target_bid_price を保存できる
- 削除できる
```

---

## F6. compare

必須テスト:

```text
- 最大5件まで比較できる
- compare_vector が返る
- open_checklist_count が正しい
- analysis_run が複数ある場合は最新を使う
```

---

# Part G. 実装順序

## Week 1: Deal Workspace 基盤

実装:

```text
/deals/[id]
DealHeader
DealSummaryCard
既存 analysis_run 表示
watchlist 追加ボタンのダミー
```

完了条件:

```text
1つの deal ページで、物件概要・主要指標・既存分析結果が見られる。
```

---

## Week 2: 買付価格レンジ + 前提リスク

実装:

```text
bid_ranges.py
risk_engine.py
BidRangeCard
AssumptionRiskPanel
関連API
関連テスト
```

完了条件:

```text
物件分析後に、買付価格レンジと前提リスクが自動生成される。
```

---

## Week 3: チェックリスト + 投資メモ

実装:

```text
checklist/rules.py
checklist/llm_refine.py
ChecklistTable
memo/builder.py
InvestmentMemoPanel
関連API
関連テスト
```

完了条件:

```text
仲介確認項目を生成し、回答メモを保存し、投資メモをMarkdownで生成できる。
```

---

## Week 4: ウォッチリスト + 比較 + 反証カード初期版

実装:

```text
watchlist service
Watchlist page
compare_vector
CompareDrawer
market/evidence_cards.py
EvidenceCards
```

完了条件:

```text
複数物件を保存・比較し、簡易反証カードを表示できる。
```

---

# Part H. Definition of Done

この実装の完了条件は以下。

```text
- 既存テストがすべて通る
- 新規テストが追加されている
- 計算ロジックに LLM が使われていない
- analysis_run に engine_version と input snapshot が保存される
- 買付価格レンジが表示される
- 前提リスクが表示される
- 仲介確認チェックリストが生成・編集できる
- 投資メモがMarkdownで生成・保存できる
- ウォッチリストに追加できる
- 最大5件比較ができる
- NG表現チェックがある
- ユーザーに「買い/見送り」を断定しない
```

---

# Part I. Agent 実装プロンプト

以下を Claude Code / Copilot Agent に渡して実装する。

```text
あなたは re_invest_os の実装担当です。

このリポジトリは、個人投資家向けの不動産買付前DD Webアプリです。
既存機能として、URL/PDF抽出、正規化、NOI/DSCR/税後CF/IRR/Equity Multiple/Payback、感応度、最大買付、AI Insight、SQLite保存、比較ボードがあります。

今回の目的は、新機能 Top7 を Deal Workspace に統合することです。

最優先は以下です。

1. 買付価格レンジ
2. 前提リスクスコア
3. 仲介確認チェックリスト
4. 投資委員会メモ

その後、以下を実装してください。

5. ウォッチリスト
6. PDF/URL差分比較
7. 反証カード初期版

重要制約:
- 計算をLLMに任せないでください。
- LLMは文書抽出、分類、説明文整形だけに使ってください。
- 買い、見送り推奨、おすすめ、割安、購入すべき、儲かる、確実、保証などの表現は禁止です。
- ユーザー入力条件に基づく試算、収支耐性、前提リスク、確認未了項目という表現を使ってください。
- engine_version、prompt_versions、input_snapshot_json、normalized_property_json を保存してください。
- 既存テストを壊さず、新規テストを追加してください。

実装順:
1. 既存コード構成を調査し、既存の analysis / max_bid / sensitivity / AI insight / compare の再利用ポイントを特定してください。
2. DBモデルまたはSQLAlchemyモデルを追加してください。
3. bid_ranges.py を実装してください。
4. assumption risk engine を実装してください。
5. checklist rules を実装してください。
6. memo builder を実装してください。
7. Deal Workspace UI を作成してください。
8. watchlist / compare / evidence cards を追加してください。
9. テストを追加し、全テストを通してください。
10. 変更内容と未実装リスクを docs にまとめてください。

まずはリポジトリ構成を確認し、既存実装を壊さない最小差分の実装計画を作成してから着手してください。
```

---

# Part J. 後回しにするもの

以下は今回実装しない。

```text
- 自動スクレイピング監視
- 業者送客
- 本格ポートフォリオ管理
- 税務最適化アドバイス
- 個別物件の買い/見送り判定
- 外部ユーザーへの物件共有SNS機能
- 法人CRM
```

---

# Part K. UI 文言ガイド

## 使ってよい表現

```text
ユーザー入力条件に基づく試算
収支耐性
前提リスク
確認未了項目
買付価格レンジ
標準レンジとの差額
下振れシナリオ
分析条件
参考値
```

## 避ける表現

```text
買い
見送り推奨
おすすめ
割安
購入すべき
この物件は良い
この物件は悪い
儲かる
確実
保証
```

---

# Part L. 最終的なユーザー体験

MVP 完了時、ユーザーは以下をできる。

```text
1. 物件URLまたはPDFを投入する
2. 主要指標を見る
3. 買付価格レンジを見る
4. 前提リスクを見る
5. 仲介確認チェックリストを見る
6. 確認結果をメモする
7. 投資メモを生成する
8. ウォッチリストに保存する
9. 複数物件を比較する
```

この状態になれば、単なる収支シミュレーターではなく、買付前 DD ワークスペースとして成立する。
