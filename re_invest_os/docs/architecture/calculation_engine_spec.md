# Calculation Engine Spec — re_invest_os

作成日: 2026-05-11
パッケージ: `packages/financial-engine/`
言語: Python 3.12+ (pydantic v2)
方針: **すべての計算は純粋関数 / I/O・LLM呼び出しは含まない / 単体テスト先行**

---

## 1. 設計原則

1. **純粋関数中心**: 引数 = `Assumptions`、戻り値 = `AnalysisResult`。グローバル状態、I/O、時刻取得を含まない
2. **数値はDecimalまたはfloatで一貫**: 金額は円 (int) を基本。利率・面積はfloat
3. **すべての結果は再現可能**: input + version で同じ output が得られる (`engine_version` を結果に含める)
4. **AIに計算させない**: LLMは数値抽出と説明のみ。CF/IRR/税はすべてこのエンジン
5. **NumPy/SciPyを限定使用**: IRR・最適化以外は標準ライブラリで済ませる
6. **テスト先行 (TDD)**: 主要関数は最初にfixtureベースのテストを書く

---

## 2. モジュール構成

```
packages/financial-engine/
  src/
    re_engine/
      __init__.py
      models.py            # Pydantic: Assumptions, AnalysisResult 等
      cashflow.py          # GPI/EGI/NOI/BTCF/ATCF
      loan.py              # 元利均等/元金均等、返済表、残債
      tax.py               # 減価償却、課税所得、譲渡税
      exit.py              # 売却価格、売却諸費用、手残り
      irr.py               # IRR、Equity Multiple、Payback Period
      score.py             # 100点スコア
      max_offer.py         # 最大買付価格 (制約付き最適化)
      sensitivity.py       # 感応度シナリオ
      cross_asset.py       # クロスアセット比較
      constants.py         # 法定耐用年数、構造区分、税率テーブル
      validation.py        # 入力バリデーション
  tests/
    test_loan.py
    test_cashflow.py
    test_tax.py
    test_exit.py
    test_irr.py
    test_score.py
    test_max_offer.py
    test_sensitivity.py
    fixtures/
      kuubun_tokyo.json    # 区分マンション例
      ittou_chiba.json     # 一棟アパート例
  pyproject.toml
```

---

## 3. 入力モデル (Assumptions)

```python
class PropertyAssumptions(BaseModel):
    property_type: Literal["kuubun", "ittou_apt", "ittou_mansion", "kodate", "land"]
    purchase_price_yen: int
    land_value_yen: int                  # 土地価格
    building_value_yen: int              # 建物価格
    structure: Literal["wood", "steel", "rc", "src"]
    building_completion_ym: str          # "YYYY-MM"
    building_area_sqm: float
    land_area_sqm: float | None
    num_units: int | None                # 一棟用
    location_pref: str                   # "13" 等
    location_city: str | None

class IncomeAssumptions(BaseModel):
    gpi_monthly_yen: int                 # 満室想定月額賃料
    other_income_monthly_yen: int = 0    # 駐車場・自販機等
    vacancy_rate: float = 0.05           # 0.0〜1.0
    rent_growth_rate: float = -0.005     # 年率、デフォルト微減
    bad_debt_rate: float = 0.0

class OpexAssumptions(BaseModel):
    management_fee_rate: float = 0.05    # GPI比
    repair_reserve_monthly_yen: int = 0
    fixed_property_tax_yen: int = 0      # 固都税年額
    insurance_yen: int = 0               # 年額
    building_mgmt_yen: int = 0           # 区分の管理費・修繕積立金 (年額)
    other_opex_yen: int = 0
    opex_growth_rate: float = 0.005

class LoanAssumptions(BaseModel):
    loan_amount_yen: int
    interest_rate: float                 # 年率 0.020 等
    term_years: int
    repayment_type: Literal["amortized", "principal_equal"] = "amortized"
    grace_period_months: int = 0

class TaxAssumptions(BaseModel):
    income_tax_rate: float = 0.20        # 所得税
    resident_tax_rate: float = 0.10      # 住民税
    business_tax_rate: float = 0.0       # 事業税 (個人投資家は通常0)
    capital_gain_short_rate: float = 0.39  # 短期譲渡
    capital_gain_long_rate: float = 0.20   # 長期譲渡 (5年超)

class ExitAssumptions(BaseModel):
    hold_period_years: int = 10
    exit_cap_rate: float = 0.060
    selling_cost_rate: float = 0.04      # 仲介・登記等

class AcquisitionAssumptions(BaseModel):
    equity_yen: int                      # 自己資金
    acquisition_cost_rate: float = 0.07  # 取得諸費用率

class Assumptions(BaseModel):
    engine_version: str = "0.1.0"
    property: PropertyAssumptions
    income: IncomeAssumptions
    opex: OpexAssumptions
    loan: LoanAssumptions
    tax: TaxAssumptions
    exit: ExitAssumptions
    acquisition: AcquisitionAssumptions
```

---

## 4. 出力モデル (AnalysisResult)

```python
class YearlyCashflow(BaseModel):
    year: int
    gpi_yen: int
    vacancy_loss_yen: int
    bad_debt_yen: int
    egi_yen: int
    opex_yen: int
    noi_yen: int
    debt_service_yen: int
    btcf_yen: int                # 税前CF
    depreciation_yen: int
    interest_expense_yen: int
    principal_payment_yen: int
    taxable_income_yen: int
    tax_yen: int
    atcf_yen: int                # 税後CF
    loan_balance_end_yen: int

class LoanScheduleRow(BaseModel):
    period_month: int
    payment_yen: int
    interest_yen: int
    principal_yen: int
    balance_yen: int

class ExitResult(BaseModel):
    sale_price_yen: int
    selling_costs_yen: int
    remaining_loan_yen: int
    book_value_yen: int
    capital_gain_yen: int
    capital_gain_tax_yen: int
    net_proceeds_yen: int        # 税引後手残り

class KPI(BaseModel):
    cap_rate: float              # NOI / 価格
    cash_on_cash: float          # 初年度BTCF / 自己資金
    dscr_min: float              # 期間中最低DSCR
    dscr_year1: float
    ltv: float
    equity_irr: float            # 自己資金IRR
    equity_multiple: float
    payback_years: float | None  # 自己資金回収年数
    btcf_first_year_yen: int
    atcf_first_year_yen: int
    dead_cross_year: int | None  # 減価償却 < 元金返済 となる初年度 (engine 0.2.0+)

class AnalysisResult(BaseModel):
    engine_version: str
    assumptions: Assumptions
    yearly_cashflows: list[YearlyCashflow]
    loan_schedule: list[LoanScheduleRow]
    exit: ExitResult
    kpi: KPI
```

---

## 5. 主要関数仕様

### 5.1 ローン返済 (loan.py)

```python
def amortized_schedule(
    principal: int, annual_rate: float, term_years: int
) -> list[LoanScheduleRow]
```

- 元利均等: monthly_payment = P * r / (1 - (1+r)^(-n))
- 端数: 各回は整数円に丸め、最終回で残債吸収
- `interest_rate=0` のときは線形分割 (ZeroDivision防止)
- `grace_period_months > 0` のときは元金据置 (利息のみ)

```python
def loan_balance_at_month(schedule: list[LoanScheduleRow], month: int) -> int
def annual_debt_service(schedule, year: int) -> int          # 12回合計
def annual_interest(schedule, year: int) -> int
def annual_principal(schedule, year: int) -> int
```

### 5.2 キャッシュフロー (cashflow.py)

```python
def project_cashflows(assumptions: Assumptions, schedule: list[LoanScheduleRow]) -> list[YearlyCashflow]
```

公式 (各年):
- GPI = `gpi_monthly_yen * 12 * (1 + rent_growth_rate)^(year-1)` + 同様にother_income
- Vacancy = GPI * vacancy_rate
- BadDebt = (GPI - Vacancy) * bad_debt_rate
- EGI = GPI - Vacancy - BadDebt
- OPEX = (管理費=GPI*management_fee_rate) + 修繕積立 + 固都税 + 保険 + 区分管理費 + その他 (それぞれ growth考慮)
- NOI = EGI - OPEX
- DebtService = `annual_debt_service(schedule, year)`
- BTCF = NOI - DebtService
- TaxableIncome = NOI - Interest - Depreciation
- Tax = max(0, TaxableIncome) * (income_tax_rate + resident_tax_rate)
- ATCF = BTCF - Tax

### 5.3 減価償却・税務 (tax.py)

```python
def annual_depreciation(building_value_yen: int, structure: str, completion_ym: str, evaluation_year: int) -> int
```

法定耐用年数 (constants.py):
- wood: 22
- steel (3mm以下): 19
- steel (3-4mm): 27
- steel (4mm超): 34
- rc/src: 47

中古資産の耐用年数 (簡便法):
- 法定耐用年数を全部経過: `legal_life * 0.2` (切り捨て、最低2年)
- 一部経過: `(legal_life - elapsed) + elapsed * 0.2`

償却方法: 定額法。償却率 = 1 / 耐用年数 (小数3位まで四捨五入)。

```python
def taxable_income(noi: int, interest: int, depreciation: int) -> int
def income_tax(taxable: int, rates: TaxAssumptions) -> int
```

不動産所得が赤字でも、給与所得との損益通算は土地利息部分を除外する規定 (措置法41-4) を考慮。
- `disallowed_land_interest = interest * land_value / purchase_price` を赤字から差し戻す

### 5.4 出口 (exit.py)

```python
def compute_exit(assumptions: Assumptions, cashflows: list[YearlyCashflow], schedule: list[LoanScheduleRow]) -> ExitResult
```

- 売却時NOI = 保有期間末年のNOI
- 売却価格 = NOI / exit_cap_rate
- 売却諸費用 = 売却価格 * selling_cost_rate
- 残債 = `loan_balance_at_month(schedule, hold_period_years * 12)`
- 簿価 = 取得価額 - 累計減価償却
- 譲渡所得 = 売却価格 - 売却諸費用 - 簿価
- 譲渡税率: 保有5年超 = 20%、5年以下 = 39%
- 税引後手残り = 売却価格 - 売却諸費用 - 残債 - 譲渡税

### 5.5 IRR・複合指標 (irr.py)

```python
def equity_irr(equity_invested: int, atcfs: list[int], net_proceeds: int) -> float
```

- 自己資金 = ダウンペイ + 取得諸費用
- キャッシュフロー = [-equity, ATCF_1, ..., ATCF_n-1, ATCF_n + net_proceeds]
- numpy_financial.irr または scipy.optimize.brentq
- 解が見つからないときは None

```python
def equity_multiple(equity_invested: int, total_distributions: int) -> float
def payback_years(equity_invested: int, atcfs: list[int]) -> float | None
def dscr(noi: int, debt_service: int) -> float
def cap_rate(noi: int, purchase_price: int) -> float
def cash_on_cash(btcf_year1: int, equity: int) -> float
```

### 5.6 100点スコア (score.py) — ❌ 撤去済み (2026-05-30 MVP再定義)

> **REMOVED:** `score.py`（100点・健全/中立/要警戒）は MVP 再定義で撤去された。
> 価値判断ラベル（健全/要警戒）は新方針（中立DDエンジン）に反するため。
> 代わりに **甘さスコア**（`apps/api/src/api/services/risk_engine.py` の
> `assess_assumption_score` → `AssumptionScore{overall_risk, summary, items}`）を中核に据える。
> 甘さスコアは物件評価ではなく、項目別の前提 confidence(A–D) と risk_level(low/medium/high/unknown)。
> 詳細: `docs/design/2026-05-30-mvp-redefinition-design.md` (Spec 1)。
> 以下の旧配点表は履歴として残す。

配点 (青写真8.1, 旧仕様):

| 項目 | 配点 | 計算ロジック |
|---|---:|---|
| 価格妥当性 | 20 | NOI Cap / 市場Cap の乖離 + 積算価格との乖離 |
| 賃料妥当性 | 15 | 物件㎡賃料 / 近傍賃料相場の乖離 |
| 税前/税後CF | 20 | 初年度ATCF > 0 で満点、線形減点 |
| 融資耐性 | 15 | DSCR_min, 金利+1%時のDSCR |
| 出口耐性 | 15 | 売却net proceeds, IRR, 出口Cap +0.5% 耐性 |
| 修繕・CAPEX耐性 | 10 | 修繕費1.5倍時のATCFが正か |
| データ信頼度 | 5 | 資料充足率 + 抽出信頼度 |

合計100点。70+ = 健全、50-70 = 中立、50- = 要警戒。
**買い推奨ではなく分析上の健全性スコア。**

```python
def total_score(result: AnalysisResult, market_context: MarketContext, data_quality: DataQuality) -> ScoreResult
```

### 5.7 最大買付価格 (max_offer.py)

```python
def max_offer_price(
    base: Assumptions,
    targets: InvestorTargets,
    search_range: tuple[int, int] | None = None,
) -> MaxOfferResult
```

`InvestorTargets`:
- min_dscr: float = 1.25
- min_irr: float = 0.08
- min_first_year_atcf_yen: int = 0
- max_equity_yen: int | None = None
- stress_interest_rate: float = base.loan.interest_rate + 0.01

ロジック:
- 価格を2分探索 (purchase_price のみを変動、loan_amount = price * 同LTV を維持)
- すべての制約を満たす最大価格を返す
- 制約ごとに「どれが効いたか」を返す (`binding_constraints: list[str]`)
- 安全価格 = 最大価格 - 5% (バッファ)

### 5.8 感応度 (sensitivity.py)

```python
def sensitivity_grid(base: Assumptions, scenarios: list[Scenario]) -> SensitivityResult
```

固定シナリオセット (青写真8.4):
- rent_drop: -5%, -10%
- vacancy_up: +5pt, +10pt
- rate_up: +0.5pt, +1.0pt
- opex_up: x1.5, x2.0
- exit_cap_up: +0.25pt, +0.5pt
- exit_price_drop: -5%, -10%
- combined: rent-5% + vacancy+5pt + rate+0.5pt

各シナリオで再計算し、ATCF/IRR/DSCR_minを返す。

### 5.9 クロスアセット比較 (cross_asset.py)

```python
def cross_asset_comparison(
    equity_yen: int,
    hold_years: int,
    re_atcfs: list[int],
    re_net_proceeds: int,
    benchmarks: list[AssetBenchmark],
) -> CrossAssetResult
```

`AssetBenchmark`: 資産クラスごとの 期待年率/標準偏差/流動性/手間スコア。
**指数・資産クラスレベルのみ。個別銘柄推奨はしない。**

ベンチマーク (初期固定値、後で更新可能):

| 資産クラス | 期待年率 | 備考 |
|---|---:|---|
| 全世界株式 | 5.0% | 名目、長期 |
| 米国株式 | 6.0% | 名目、長期 |
| 日本株式 | 4.0% | 名目、長期 |
| J-REIT | 4.5% | 配当込み |
| 国内債券 | 1.0% | 10年国債周辺 |
| 米国債 | 4.0% | 為替リスク別 |
| 円定期預金 | 0.3% | |
| MMF | 0.5% | |

出力:
- 不動産税後IRR vs 各資産期待リターン
- リスクプレミアム
- 流動性・分散・手間の定性比較

---

## 6. テスト方針

### 6.1 テスト戦略

- **fixtureベース**: 入出力のスナップショットを `tests/fixtures/*.json` で保持
- **golden test**: 既知の手計算結果と完全一致を検証 (許容誤差 1円)
- **property-based test**: hypothesis で edge case (金利0%、LTV100%、保有1年など)
- **regression**: バージョン更新時にスナップショット差分を確認

### 6.2 必須テストケース

```
test_loan.py
  - 元利均等3000万円, 2%, 30年: 月返済額 110,886円
  - 金利0%: 線形分割
  - 1年経過後の残債計算
  - 元金均等

test_cashflow.py
  - GPI/Vacancy/EGI/NOI 1年分の手計算照合
  - 10年成長シミュレーション

test_tax.py
  - 木造22年新築、RC47年新築、中古減価償却
  - 土地利息損益通算除外
  - 譲渡税短期/長期

test_exit.py
  - 5年保有、10年保有のnet proceeds

test_irr.py
  - 既知IRR (Excel/numpy_financial照合)
  - 解なし (常に赤字)

test_score.py
  - 各サブスコアの上下限
  - データ信頼度50%でも他が満点なら95点

test_max_offer.py
  - DSCR制約のみ
  - 全制約
  - binding_constraints の正確性

test_sensitivity.py
  - 全シナリオが計算完了
  - rate+1% で DSCR が下がる方向
```

### 6.3 ベンチマーク

- 1分析あたり 100ms 以下 (10年シミュレーション + 全感応度)
- max_offer 2分探索: 30回程度の反復で収束

---

## 7. バージョニング

- `engine_version` (semver) を全結果に保存
- 計算ロジック変更時は minor++、互換性破壊時は major++
- migration ノートは `packages/financial-engine/CHANGELOG.md`

---

## 8. 既知の制約・将来課題

- 法人 vs 個人の税計算は v0 では個人のみ。法人は v2
- 消費税還付スキームは未対応 (法人化後)
- 元金据置・ステップ返済は v1
- 中古耐用年数の簡便法以外 (見積法) は未対応
- 借換シミュレーションは v1
- 区分マンションの長期修繕積立金値上げシナリオは sensitivity に含めず手入力
- IRR は単一解しか返さない (符号反転がある場合は注意)
- クロスアセット比較は名目リターン。インフレ調整なし
