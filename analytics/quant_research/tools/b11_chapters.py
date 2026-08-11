"""Deterministic cell definitions for the B11 Treasury forecast-to-decision notebooks."""

from __future__ import annotations

from nbkit import code, md
from stage2_nb import setup_cell, treasury_curve_cell

TREASURY_SOURCES = """
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology)
- [U.S. Treasury Daily Treasury Par Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve)
"""

FINRA_SOURCES = """
- [FINRA Treasury Daily Aggregate Statistics](https://www.finra.org/finra-data/browse-catalog/about-treasury)
- [FINRA Treasury Daily File](https://www.finra.org/finra-data/browse-catalog/about-treasury/daily-file)
- [FINRA Query API](https://developer.finra.org/products/query-api)
- [FINRA Fixed Income Data Specific Terms](https://developer.finra.org/specific-terms-fixed-income-data)
"""

METHOD_SOURCES = """
- [Fama and MacBeth (1973), Risk, Return, and Equilibrium](https://www.jstor.org/stable/1831028)
- [Hansen (1982), Large Sample Properties of GMM Estimators](https://doi.org/10.2307/1912775)
- [Duffie and Kan (1996), A Yield-Factor Model of Interest Rates](https://doi.org/10.1016/0304-405X(95)00881-6)
- [Boyd and Vandenberghe, Convex Optimization](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf)
"""


def _header(title: str, goals: str, prerequisites: str) -> object:
    return md(
        f"""
# {title}

## 学習目標

{goals}

## 前提知識

{prerequisites}
"""
    )


def overview_cells():
    return [
        _header(
            "60. B11 — Treasury Curve Forecast-to-Decision",
            """
- Treasuryの公表par yieldを予測対象として定義し、取引価格・zero curve・PnLと混同しない。
- formation lag、information timestamp、baseline、multiple-testingの順序を先に固定する。
- 観測できるFINRA aggregateと、観測できないquote/trade-level execution quantityを分離する。
- forecast evidence、pricing/control、portfolio exposureを別のdecision boundaryとして書く。
""",
            """
- B5–B10のTreasury snapshot、時系列validation、PIT、実験lineage
- B1のcurve representationとB4のquadratic optimization
- B3のestimand、claim boundary、不確実性の基礎
""",
        ),
        setup_cell(60),
        treasury_curve_cell(),
        md(
            r"""
## 1. B11のデータ契約

| 層 | この版で観測するもの | 言ってよいこと | 言ってはいけないこと |
|---|---|---|---|
| Treasury | 3m/2y/5y/10y/30yの日次par yield | 公表観測日先のyield-change forecast | transaction return、executable quote、zero rate |
| FINRA aggregate | trade count、par volume、channel、on/off-the-run、一部VWAP | API gate後のactivity composition | bid–ask、queue、Kyle lambda、impact |
| trade fixture | bid/ask/trade/future mid | spread identityの単位検証 | 実市場の流動性推定 |

Treasuryの公式系列はindicative quotationから作るpar curveであり、zero-coupon curveでも取引約定でもない。B11の最終artifactはno_model_selectedやno_tradability_claimを正当な結果として保持する。
"""
        ),
        code(
            """
source_table = pd.DataFrame(
    [
        {"source": "Treasury daily par yield", "status": "core", "rows": len(rates), "claim": "forecast evidence"},
        {"source": "FINRA Treasury aggregate", "status": "conditional API gate", "rows": 0, "claim": "not enabled"},
        {"source": "trade-level quote fixture", "status": "method validation", "rows": 4, "claim": "identity only"},
    ]
)
display(source_table)
fig = go.Figure()
for index, tenor in enumerate(qt.DEFAULT_TENORS):
    fig.add_scatter(x=curve_dates, y=curve_yields[:, index], mode="lines", name=tenor)
fig.update_layout(
    title="Official Treasury par yields used as forecast observations",
    xaxis_title="Publication date",
    yaxis_title="Par yield (%)",
    template="plotly_white",
)
fig.show()
"""
        ),
        md(
            r"""
## 2. Week 41–44のevidence chain

| Week | Core | 主な実データ | 境界 |
|---:|---|---|---|
| 41 | signal research、formation lag、multiple testing | Treasury curve | forecast evidenceでありP&Lではない |
| 42 | observable activityとexecution identities | FINRAはAPI gate後、現在はfixture-only | aggregateからspreadを逆算しない |
| 43 | par/zero/forward、pricing measure、finite control | Treasury + mathematical fixture | daily par yieldをzero rateと呼ばない |
| 44 | covariance shrinkage、turnover、risk budget | Treasury yield changes | weightsはyield exposureでありcash portfolioではない |

## 3. 失敗モード

- forecast errorを取引収益、causal effect、executable priceと呼ぶ。
- FINRAのWeb画面をscrapeし、認証・利用条件を飛ばす。
- aggregate volumeからspread、slippage、Kyle lambdaを推定する。
- outer testや将来のavailabilityをformation signalへ混ぜる。
- model winnerを先に決め、primary metricや候補数を後付けする。

## 4. 段階別演習

### 基礎

1. par yield、discount factor、zero rate、forward rateの観測方程式を表にせよ。
2. trade-level fixtureのspreadを単位付きで再計算せよ。

### 標準

3. signal familyとfalsificationを事前登録せよ。
4. yield-change exposureにturnover penaltyを加え、共分散shrinkageを比較せよ。

### 研究

5. FINRA API access後のsnapshot hash、terms、列定義、欠損処理をpre-analysisへ追加せよ。

## 5. Exit Criteria

- [ ] Treasury par yieldとzero/transaction quantityを分離した
- [ ] signalのinformation timestampとformation lagを固定した
- [ ] FINRAの未承認状態を実データ主張へ混ぜていない
- [ ] exposure allocationとcash security/PnLを区別した
- [ ] no-model-selected / no-tradability-claimを失敗条件として残した

## 6. 出典
"""
            + TREASURY_SOURCES
            + FINRA_SOURCES
        ),
    ]


def week41_cells():
    return [
        _header(
            "61. Week 41 — Signal research without alpha inflation",
            """
- forecast target、formation lag、candidate count、primary metricを計算前に固定する。
- Treasuryの5公表日先10年yield changeを、zero-changeを残したまま記述的に評価する。
- signal correlationやdirectional accuracyをP&L、causality、tradabilityと呼ばない。
""",
            """
- B5/B7のchronological validationとpublication horizon
- B3のmultiple testing、estimand、falsification
""",
        ),
        setup_cell(61),
        treasury_curve_cell(),
        md(
            r"""
## 1. Pre-analysis contract

ここでは候補を3個に固定し、5 Treasury publication observations先の10y changeをtargetにする。候補の順位やP&Lは計算後に選ばない。SignalResearchProtocolは主張の境界をデータとして保存する。

$$
y_{t+5}=100(r_{10y,t+5}-r_{10y,t})\quad\text{(basis points)}
$$
"""
        ),
        code(
            """
protocol = qt.SignalResearchProtocol(
    economic_hypothesis="published curve shape may contain descriptive information about a later 10y change",
    information_timestamp="after the official Treasury publication date",
    target="five-publication-observation 10y par-yield change in bp",
    universe="official 3m/2y/5y/10y/30y par yields",
    holding_period="five Treasury publication observations",
    rebalancing_rule="descriptive signal evaluated at every eligible origin",
    neutralization="none; no asset-pricing portfolio is formed",
    transaction_cost_model="not identified from Treasury par yields",
    primary_metric="correlation and directional accuracy; no P&L claim",
    falsification_test="reverse-time and zero-change baseline remain reported",
    data_source="U.S. Treasury daily par-yield snapshot",
)
horizon = 5
ten_year = curve_yields[:, 3]
target_series = np.zeros(ten_year.size)
target_series[horizon:] = (ten_year[horizon:] - ten_year[:-horizon]) * 100.0
slope_level = (curve_yields[:, 3] - curve_yields[:, 1]) * 100.0
momentum = np.zeros(ten_year.size)
momentum[5:] = (ten_year[5:] - ten_year[:-5]) * 100.0
signals = {
    "zero_change": np.zeros(ten_year.size),
    "10y_minus_2y_level": slope_level,
    "five_observation_momentum": momentum,
}
assert len(signals) == 3
assert protocol.target.startswith("five-publication")
"""
        ),
        code(
            """
rows = []
for name, signal in signals.items():
    audit = qt.audit_forecast_signal(signal, target_series, formation_lag=horizon, target_unit="bp")
    aligned_target = target_series[horizon:]
    rows.append(
        {
            "candidate": name,
            "observations": audit.observation_count,
            "correlation": audit.correlation,
            "directional_accuracy": audit.directional_accuracy,
            "mean_signed_target_bp": audit.mean_signed_target,
            "pnl_allowed": audit.pnl_interpretation_allowed,
            "falsification_family_size": len(signals),
            "zero_change_rmse_bp": float(np.sqrt(np.mean(aligned_target**2))),
        }
    )
signal_table = pd.DataFrame(rows)
assert signal_table["pnl_allowed"].eq(False).all()
display(signal_table)
fig = go.Figure()
fig.add_bar(x=signal_table["candidate"], y=signal_table["correlation"], name="correlation")
fig.add_bar(x=signal_table["candidate"], y=signal_table["directional_accuracy"], name="directional accuracy")
fig.update_layout(
    title="Pre-registered descriptive signal diagnostics",
    xaxis_title="Candidate (none selected after seeing the result)",
    yaxis_title="Diagnostic value",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""
        ),
        md(
            r"""
## 2. 失敗モード

- signalをtargetと同じ時点へずらす。
- 3候補を試して最良だけをprimaryへ書き換える。
- mean_signed_target_bpをstrategy returnと呼ぶ。
- Treasury par yieldからexecution costやcausal effectを作る。

## 3. 段階別演習

### 基礎

1. target_seriesのindexを図で確認し、5観測先の情報集合を説明せよ。

### 標準

2. reverse-time falsificationを追加し、候補数を増やしたときのselection riskを書け。

### 研究

3. Fama–MacBethをcross-sectional exposureへ拡張する場合の必要なasset return dataとclustered inferenceを定義せよ。

## 4. Exit Criteria

- [ ] signal計算前に候補数とprimary metricを固定した
- [ ] formation lagがtargetを未来へ置いた
- [ ] zero-change baselineを残した
- [ ] descriptive diagnosticsとP&L claimを分けた
- [ ] falsificationとmultiple-testingの対象を記録した

## 5. 出典
"""
            + TREASURY_SOURCES
            + METHOD_SOURCES
        ),
    ]


def week42_cells():
    return [
        _header(
            "62. Week 42 — Observable liquidity and execution boundaries",
            """
- trade-level quoteからquoted/effective/realized spreadを単位付きで計算する。
- FINRA Treasury Daily Aggregateの意味を、個別quote・queue・impactと分けて読む。
- API access/terms gate未通過時に、fixtureの計算を実データ分析へ昇格させない。
""",
            """
- bid/ask、midpoint、signed tradeの定義
- B11 feasibility noteと、SEC/B9のsource・license・provenance契約
""",
        ),
        setup_cell(62),
        md(
            r"""
## 1. FINRA access gate

FINRAのDaily Fileは2023-02-13以降の集計を公開しているが、Query APIは認証を要求する。Web画面をscrapeせず、credentials・利用条件・snapshot hash・列定義を先に固定する。現時点の教材はapi_access_granted=Falseであり、Week 42のCore実証は開始しない。

集計に含まれるtrade count、par volume、channel、on/off-the-run、一部VWAPからbid–askやKyle lambdaを逆算してはならない。
"""
        ),
        code(
            """
api_gate = {
    "api_access_granted": False,
    "terms_reviewed": False,
    "snapshot_sha256": None,
    "real_finra_rows_used": 0,
    "fallback": "trade-level fixture for unit identities only",
}
assert api_gate["real_finra_rows_used"] == 0
aggregate_fields = pd.DataFrame(
    [
        {"field": "dealerCustomerCount", "observable": True, "unit": "trades", "spread_identified": False},
        {"field": "dealerCustomerVolume", "observable": True, "unit": "par value", "spread_identified": False},
        {"field": "volumeWeightedAveragePrice", "observable": True, "unit": "price", "spread_identified": False},
        {"field": "bid_ask_quote", "observable": False, "unit": "not in aggregate", "spread_identified": False},
        {"field": "queue_position", "observable": False, "unit": "not in aggregate", "spread_identified": False},
    ]
)
display(aggregate_fields)
"""
        ),
        code(
            """
bid = np.array([99.90, 99.90, 100.00, 100.00])
ask = np.array([100.10, 100.10, 100.20, 100.20])
trade = np.array([100.10, 99.90, 100.20, 100.00])
future_mid = np.array([100.05, 99.95, 100.10, 100.05])
side = np.array([1.0, -1.0, 1.0, -1.0])
measurements = qt.measure_trade_costs(bid, ask, trade, future_mid, side)
trade_table = pd.DataFrame(
    {
        "quoted_spread": measurements.quoted_spread,
        "effective_spread": measurements.effective_spread,
        "realized_spread": measurements.realized_spread,
        "adverse_selection": measurements.adverse_selection,
    }
)
assert np.all(trade_table["quoted_spread"] >= 0.0)
display(trade_table)
fig = go.Figure()
for column in trade_table.columns:
    fig.add_bar(x=np.arange(len(trade_table)), y=trade_table[column], name=column)
fig.update_layout(
    title="Trade-level identity fixture; not FINRA aggregate evidence",
    xaxis_title="Fixture trade",
    yaxis_title="Price units",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""
        ),
        md(
            r"""
## 2. Scenario-only cost

ExecutionCostScenarioはhalf spread、temporary/permanent impact、delay、fundingを明示的な仮定として加算する。これはaggregate dataから推定した値ではない。

## 3. 失敗モード

- FINRA APIを持たないまま公開ページを自動取得する。
- par volumeをspreadへ変換する。
- fixtureのspread identityを実市場の平均costと呼ぶ。
- terms、snapshot、raw columnのprovenanceを残さない。

## 4. 段階別演習

### 基礎

1. buyer/sellerそれぞれでeffective spreadの符号を再計算せよ。

### 標準

2. temporary/permanent impactを別scenarioとしてsensitivity表にせよ。

### 研究

3. API access後のdownload、hash、列schema、利用規約、再配布制限をpre-analysisへ追加せよ。

## 5. Exit Criteria

- [ ] aggregate fieldとtrade-level quoteを分けた
- [ ] spread identityをfixtureで検算した
- [ ] scenario costを推定値と呼ばなかった
- [ ] API/terms gate未通過をreal-data claimへ混ぜなかった

## 6. 出典
"""
            + FINRA_SOURCES
        ),
    ]


def week43_cells():
    return [
        _header(
            "63. Week 43 — Fixed-income measure and control boundary",
            """
- par yield、zero rate、discount factor、forward rateの変換を観測方程式と分ける。
- Treasury daily par yieldをzero-coupon curveとして扱わない。
- finite-horizon dynamic programmingをCoreとし、HJM calibrationやRLをAdvancedへ置く。
""",
            """
- B1のcash-flow discountingとB2のconditional expectation
- B7のdynamic term-structure、B4のfinite-horizon optimization
""",
        ),
        setup_cell(63),
        treasury_curve_cell(),
        md(
            r"""
## 1. Measure vocabulary

Treasury snapshotのpar_yieldはcoupon cash flowを同一yieldで価格付けするpar quoteである。以下のzero/forwardは、変換の既知の形を検査するための数学fixtureであり、Treasury par quoteをzero rateへ読み替えたものではない。

$$
D(t)=e^{-t z(t)},\qquad f(t_i,t_{i+1})=-\frac{t_{i+1}z(t_{i+1})-t_i z(t_i)}{t_{i+1}-t_i}
$$
"""
        ),
        code(
            """
fixture_times = np.array([0.25, 1.0, 2.0, 5.0, 10.0])
fixture_zero = np.array([0.045, 0.043, 0.041, 0.039, 0.040])
discount = np.exp(-fixture_times * fixture_zero)
forward = -np.diff(fixture_times * fixture_zero) / np.diff(fixture_times)
measure_table = pd.DataFrame(
    {
        "maturity_years": fixture_times,
        "illustrative_zero_rate": fixture_zero,
        "discount_factor": discount,
        "treasury_latest_par_yield": np.interp(fixture_times, maturity_years, curve_yields[-1]),
    }
)
display(measure_table)
assert np.all((discount > 0.0) & (discount <= 1.0))
fig = go.Figure()
fig.add_scatter(x=fixture_times, y=100.0 * fixture_zero, mode="lines+markers", name="zero fixture")
fig.add_scatter(x=fixture_times[1:], y=100.0 * forward, mode="lines+markers", name="forward fixture")
fig.add_scatter(x=maturity_years, y=curve_yields[-1], mode="lines+markers", name="Treasury par quote")
fig.update_layout(title="Par quote versus illustrative zero/forward measures", xaxis_title="Years", yaxis_title="Percent", template="plotly_white")
fig.show()
"""
        ),
        code(
            """
transition = np.array(
    [
        [[0.80, 0.20], [0.25, 0.75]],
        [[0.55, 0.45], [0.10, 0.90]],
    ]
)
stage_cost = np.array([[0.20, 0.45], [0.55, 0.10]])
terminal_cost = np.array([0.30, 0.80])
control = qt.finite_horizon_control(transition, stage_cost, terminal_cost, horizon=5)
assert control.values.shape == (6, 2)
control_table = pd.DataFrame(control.values, columns=["state_0_value", "state_1_value"])
display(control_table)
fig = go.Figure()
fig.add_scatter(x=np.arange(control.values.shape[0]), y=control.values[:, 0], mode="lines+markers", name="state 0")
fig.add_scatter(x=np.arange(control.values.shape[0]), y=control.values[:, 1], mode="lines+markers", name="state 1")
fig.update_layout(title="Finite-horizon backward induction values", xaxis_title="Remaining stage index", yaxis_title="Expected cost", template="plotly_white")
fig.show()
"""
        ),
        md(
            r"""
## 2. 失敗モード

- par yieldをdiscount factorへ直接代入する。
- forward curveの符号規約を定義しない。
- solver successをno-arbitrage証明と呼ぶ。
- HJMのno-arbitrage restrictionと実証calibrationを一つのfitへ混ぜる。

## 3. 段階別演習

### 基礎

1. coupon cash flowからpar quoteがどのdiscount factor制約を満たすか導出せよ。

### 標準

2. fixture zeroを変え、discount monotonicityとnegative-rateケースを比較せよ。

### 研究

3. HJM drift restrictionを仮定とデータ要件に分解し、Coreへ入れない理由を書け。

## 4. Exit Criteria

- [ ] par/zero/discount/forwardを定義した
- [ ] Treasury par quoteをzero rateへ変換していない
- [ ] finite-horizon recursionを解析的に検算した
- [ ] pricing measureとforecasting measureを区別した

## 5. 出典
"""
            + TREASURY_SOURCES
            + METHOD_SOURCES
        ),
    ]


def week44_cells():
    return [
        _header(
            "64. Week 44 — Portfolio decision under estimation and cost uncertainty",
            """
- Treasury yield-change covarianceをcurve exposure allocationへ接続する。
- shrinkage、turnover penalty、risk budget、scenario sensitivityを同時に診断する。
- weightsをyield exposureと定義し、cash security portfolioやrealized PnLと呼ばない。
""",
            """
- B1のcurve tenors、B4のquadratic allocation、B5–B7のchronological split
- covariance、ridge/shrinkage、turnover penaltyの基礎
""",
        ),
        setup_cell(64),
        treasury_curve_cell(),
        md(
            r"""
## 1. Exposure allocation contract

ここでのweightは5つのTreasury par-yield changeへの線形exposureである。目的関数の単位はbpとbp²であり、債券notional、duration、cash return、execution PnLを含まない。

$$
\max_w\ \mu^\top w-\frac{\gamma}{2}w^\top\Sigma w-\tau\lVert w-w_{prev}\rVert_2^2,\qquad \mathbf{1}^\top w=0
$$
"""
        ),
        code(
            """
changes_bp = curve_changes_bp
train_end = int(0.70 * changes_bp.shape[0])
training_changes = changes_bp[:train_end]
expected_change = training_changes.mean(axis=0)
sample_covariance = np.cov(training_changes, rowvar=False, ddof=1)
shrinkage_intensity = 0.25
diagonal_target = np.diag(np.diag(sample_covariance))
covariance = (1.0 - shrinkage_intensity) * sample_covariance + shrinkage_intensity * diagonal_target
allocation = qt.mean_variance_allocation(
    expected_change,
    covariance,
    risk_aversion=5.0,
    previous_weights=np.zeros(curve_yields.shape[1]),
    turnover_penalty=0.50,
    net_exposure=0.0,
)
assert allocation.budget_residual < 1e-10
allocation_table = pd.DataFrame(
    {
        "tenor": qt.DEFAULT_TENORS,
        "expected_change_bp": expected_change,
        "exposure_weight": allocation.weights,
    }
)
display(allocation_table)
print("training rows:", training_changes.shape[0], "stationarity residual:", allocation.stationarity_residual)
"""
        ),
        code(
            """
sensitivity_rows = []
for penalty in (0.0, 0.10, 0.50, 2.0):
    result = qt.mean_variance_allocation(
        expected_change,
        covariance,
        risk_aversion=5.0,
        previous_weights=np.zeros(curve_yields.shape[1]),
        turnover_penalty=penalty,
        net_exposure=0.0,
    )
    for tenor, weight in zip(qt.DEFAULT_TENORS, result.weights, strict=True):
        sensitivity_rows.append({"turnover_penalty": penalty, "tenor": tenor, "weight": weight})
sensitivity_table = pd.DataFrame(sensitivity_rows)
fig = go.Figure()
for tenor in qt.DEFAULT_TENORS:
    subset = sensitivity_table[sensitivity_table["tenor"] == tenor]
    fig.add_scatter(x=subset["turnover_penalty"], y=subset["weight"], mode="lines+markers", name=tenor)
fig.update_layout(title="Exposure sensitivity to turnover penalty", xaxis_title="Turnover penalty", yaxis_title="Yield-change exposure weight", template="plotly_white")
fig.show()
"""
        ),
        md(
            r"""
## 2. 失敗モード

- 全期間の平均・共分散で過去のdecision originを汚染する。
- covariance shrinkageをvalidation後に選ぶ。
- weightをsecurity holding、PnL、hedge ratioと呼ぶ。
- turnover penaltyをspreadの推定値として扱う。

## 3. 段階別演習

### 基礎

1. net_exposure=0がcurve exposureで何を意味するか説明せよ。

### 標準

2. shrinkage intensityをtrainingだけで比較し、testへ再選択しない表を作れ。

### 研究

3. funding、capacity、crowdingを加えるために必要な観測と、現データで許されるscenarioを分けよ。

## 4. Exit Criteria

- [ ] covariance fitがtraining partitionだけである
- [ ] shrinkageとturnover sensitivityを保存した
- [ ] exposure unitをbp変化として明記した
- [ ] cash portfolio/PnL claimをしていない

## 5. 出典
"""
            + TREASURY_SOURCES
            + METHOD_SOURCES
        ),
    ]


def project_cells():
    return [
        _header(
            "65. B11 Project — Treasury Curve Forecast-to-Decision Specification",
            """
- economic hypothesis、information timestamp、target、baseline、cost、primary metricを1つの仕様へfreezeする。
- source・availability・methodology break・未識別のliquidity量を監査表へ残す。
- forecast、measure/control、exposure allocationを別artifactにし、winnerやproduction strategyを選ばない。
""",
            """
- Week 41–44のCoreとB5–B10のreproducibility contract
- claim boundary、PIT、locked evaluation、quadratic allocation
""",
        ),
        setup_cell(65),
        treasury_curve_cell(),
        md(
            r"""
## 1. Final specification

Projectの成果物はmodel winnerではなく、次の7点を凍結したdecision specificationである。

1. economic hypothesisとinformation timestamp
2. official source、availability、methodology break
3. forecast targetとzero-change baseline
4. decision mappingとcurve exposure unit
5. observable liquidity fieldsとscenario-only costs
6. primary metric、candidate count、falsification
7. 不足するcapacity・crowding・funding・quote data

FINRA API access/terms gateが通らない限り、Week 42のreal-data claimはblockedであり、fixtureのidentity検算だけを提出する。
"""
        ),
        code(
            """
spec_rows = [
    {"item": "hypothesis/timestamp", "status": "frozen", "evidence": "Week 41 protocol"},
    {"item": "Treasury source/method break", "status": "frozen", "evidence": treasury.metadata.snapshot_sha256},
    {"item": "forecast target/baseline", "status": "frozen", "evidence": "5 publication observations / zero-change"},
    {"item": "FINRA aggregate", "status": "conditional", "evidence": "API access and terms gate not passed"},
    {"item": "quote-level execution cost", "status": "fixture-only", "evidence": "trade identity test"},
    {"item": "exposure allocation", "status": "frozen", "evidence": "yield-change units, no cash PnL"},
    {"item": "model selection", "status": "no_model_selected", "evidence": "specification project"},
]
spec_table = pd.DataFrame(spec_rows)
display(spec_table)
assert (spec_table.loc[spec_table["item"] == "model selection", "status"] == "no_model_selected").all()
assert (spec_table.loc[spec_table["item"] == "FINRA aggregate", "status"] == "conditional").all()
"""
        ),
        code(
            """
evidence_order = ["source", "timestamp", "target", "baseline", "cost", "metric", "claim boundary"]
evidence_status = np.array([1, 1, 1, 1, 0, 1, 1], dtype=int)
evidence_frame = pd.DataFrame({"artifact": evidence_order, "frozen_or_available": evidence_status})
fig = go.Figure()
fig.add_bar(x=evidence_frame["artifact"], y=evidence_frame["frozen_or_available"], name="evidence")
fig.update_layout(title="B11 specification gate: unavailable cost data stays visible", xaxis_title="Artifact", yaxis_title="1=frozen / 0=conditional", template="plotly_white")
fig.show()
print("locked outer Treasury rows opened: False")
print("tradability claim allowed: False")
"""
        ),
        md(
            r"""
## 2. 失敗モード

- Projectで最良モデルを選ぶことを成果物にする。
- FINRA未承認のaggregateやfixtureを実約定データと呼ぶ。
- Treasury par yieldからzero curve、cash PnL、execution qualityを作る。
- 不足データを合成して、実証結果のように報告する。

## 3. 段階別演習

### 基礎

1. 7項目のspecificationを2ページのtechnical memoへ変換せよ。

### 標準

2. API access後に初めて開けるgateと、accessがなくても検証できるfixtureを分けよ。

### 研究

3. no-model-selectedを含むreplication packageのmanifest、hash、claim auditを設計せよ。

## 4. Exit Criteria

- [ ] 7つの仕様項目をfreezeした
- [ ] source、availability、methodology breakを記録した
- [ ] FINRAの条件付き状態を残した
- [ ] forecast/control/exposureの単位を分離した
- [ ] no-model-selectedとno-tradability-claimを明記した

## 5. 出典
"""
            + TREASURY_SOURCES
            + FINRA_SOURCES
            + METHOD_SOURCES
        ),
    ]


__all__ = [
    "overview_cells",
    "project_cells",
    "week41_cells",
    "week42_cells",
    "week43_cells",
    "week44_cells",
]
