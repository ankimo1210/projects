"""Builder for notebook 24: B5 orientation and real-data contract."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 24. B5の地図 — 予測modelより先に問いと時点を固定する

> 実データを使うことは出発点であり、正しいprediction contractを作ることが最初の成果物である。

## 学習目標

- Week 17–20の依存関係とB5 Projectのevidence chainを説明できる
- prediction time、target time、information set、loss、metricを区別できる
- no-changeを含む単純baselineを複雑なmodelより先に置ける
- 実データのsource、unit、availability、methodology breakを監査できる
- 4成果物、75点、必須Exit Criteriaを別々の修了条件として運用できる

## 前提知識

- B1のleast squares、regularization、PCA、conditioning
- B3のestimandとclaim boundary
- B4のalgorithm停止規約とtested package
- pandas、NumPy、Plotlyの基本操作
"""),
    setup_cell(24),
    md(r"""
## 1. 4週間の問い

| 週 | 中心となる問い | Coreの証拠 |
|---|---|---|
| Week 17 | いつ、何を、どの情報で予測するか | data contract、baseline、chronological split |
| Week 18 | regularizationは安定性を改善するか | coordinate solver、alpha path、scale test |
| Week 19 | 方向確率は観測頻度と整合するか | log loss、Brier、reliability diagram |
| Week 20 | pipelineは未来を見ていないか | expanding folds、purge、transform fit range |
| Project | 単純baselineを実データで上回るか | locked test、regime別error、no-selection gate |

MLPはB9でbackpropagationを学んだ後のAdvancedとする。B5はlinear・generative classifier・validationの契約を完成させる。
"""),
    md(r"""
## 2. 4成果物と75点gate

| Category | Points | B5で必要な証拠 |
|---|---:|---|
| Mathematical understanding | 25 | risk、regularization、classification lossの導出 |
| Implementation and testing | 30 | feature/target contract、elastic net、classifier、split test |
| Experimental design | 30 | baseline、temporal validation、calibration、break audit |
| Explanation and memo | 15 | 問い、結果、failure、claim boundaryを2〜4ページで説明 |

総合75点以上でも、4成果物が揃わない、またはfinal testをmodel selectionへ使った場合は未修了とする。
"""),
    treasury_cell(),
    code("""
quality_table = pd.DataFrame(
    {
        "check": [
            "row count",
            "duplicate dates",
            "missing required yields",
            "largest calendar gap",
            "methodology break in range",
            "forecast rows",
            "methodology-crossing targets retained",
        ],
        "value": [
            treasury.quality.row_count,
            treasury.quality.duplicate_dates,
            sum(treasury.quality.missing_by_tenor.values()),
            treasury.quality.maximum_calendar_gap_days,
            treasury.quality.methodology_break_present,
            len(forecast.regression_target),
            int(crosses_methodology_break.sum()),
        ],
    }
)
display(quality_table)

fig = go.Figure()
for tenor in treasury.metadata.tenors:
    fig.add_scatter(x=rates["date"], y=rates[tenor], name=tenor, mode="lines")
fig.add_vline(x="2021-12-06", line_dash="dash", annotation_text="Method break")
fig.update_layout(
    title="Official U.S. Treasury daily par yield snapshot",
    xaxis_title="Observation date",
    yaxis_title="Par yield (% per annum)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 3. Data contract

- **Grain:** Treasury trading date × constant maturity
- **Values:** percent per annum、bond-equivalent、semiannual coupon basisのpar yield
- **Inputs:** indicative bid-side quotationを使う公式curveから読んだ値
- **Availability:** 通常はday-$t$の18:00 America/New_Yorkまで。遅延し得る
- **Break:** 2021-12-06にHermite splineからmonotone-convex methodologyへ変更
- **Not included:** transaction、executable quote、bid–ask、volume、position、cost

したがって、同日中の売買、流動性、PnLをこのdataから評価しない。targetは次のTreasury公表日の10年CMT変化である。
"""),
    code("""
contract = pd.DataFrame(
    {
        "field": [
            "prediction origin",
            "target",
            "unit",
            "outer test",
            "claim",
            "terms review",
        ],
        "locked value": [
            "after official day-t publication",
            "next Treasury publication 10y CMT change",
            "basis points",
            "final chronological 20%",
            "forecast accuracy only; no trading claim",
            treasury.metadata.terms_reviewed_at,
        ],
    }
)
display(contract)
"""),
    md(r"""
## 4. 失敗モード

- par yieldをzero-coupon rateと呼ぶ
- observation dateだけを見て、18:00頃というavailabilityを無視する
- random splitで将来regimeをtrainingへ混ぜる
- final testを見てfeature、alpha、windowを変更する
- no-changeを上回らないmodelを「AIによる改善」と呼ぶ
- yield forecastを取引PnLへ変換するinstrument・price・costを持たずにSharpeを報告する

## 5. 段階別演習

### 基礎

1. source、grain、unit、availability、methodology breakを自分の言葉で書け。
2. prediction dateとtarget dateがstrictly orderedであることを検査せよ。

### 標準

3. no-change、historical mean、lag-1 modelの役割を比較せよ。
4. 4成果物へ各週のevidenceを割り当てよ。

### 研究

5. exact publication timestampが無いことによるpoint-in-time riskを設計メモへ追加せよ。
6. 実際に取引可能性を研究するなら追加で必要なdataを列挙せよ。

## 6. Exit Criteria

- [ ] loss、metric、utilityを区別できる
- [ ] prediction originとtarget horizonを明記できる
- [ ] Treasury CMTのquote conventionと禁止解釈を説明できる
- [ ] no-change baselineを全modelと同じholdoutで比較できる
- [ ] 4成果物、75点、必須Exit Criteriaを別gateとして運用できる

## 7. 出典

- [U.S. Treasury Daily Treasury Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?page=1&type=daily_treasury_yield_curve) — 公式par yield dataとCSV/XML入口
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) — input quotation、3:30 PM observation、6:00 PM availability、2021 methodology break
- [U.S. Treasury Interest Rate FAQ](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions) — CMT、par yield、zero rateとの違い
- [ISLP](https://www.statlearning.com/) — supervised learning、regularization、classification、resampling
"""),
]
