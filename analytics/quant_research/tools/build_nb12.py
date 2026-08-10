"""Builder for notebook 12: B3 orientation and honest-inference contract."""

from nbkit import code, md

cells = [
    md(r"""
# 12. B3の地図 — estimandから主張の境界まで

> fitできたモデルではなく、何を推定し、どの仮定の下で、どこまで主張できるかを成果物にする。

## 学習目標

- Week 9–12の依存関係と、B3 Projectへ集約する証拠を説明できる
- estimand、estimator、estimate、identificationを区別できる
- 効果量、sampling uncertainty、model misspecification、selectionを別々に診断できる
- 関連、市場反応、因果効果のclaim classを識別仮定から選べる
- B3の4成果物、配点、必須Exit Criteriaを満たす実行計画を作れる

## 前提知識

- B1のleast squares、conditioning、optimization診断
- B2の条件付き期待値、CLT、Monte Carlo coverage、時系列の情報集合
- NumPy、SciPy、pandas、Plotlyの基本操作

B3はplacement-outしない。事前知識があっても、4週間を通して同じpre-specification、有限標本検証、頑健性監査を完成させる。
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 12
TASK_IDS = {
    "selection_audit": 1,
}


def task_rng(task_name, *coordinates):
    entropy = [
        RANDOM_SEED,
        NOTEBOOK_ID,
        TASK_IDS[task_name],
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. 4週間の問い

| 週 | 中心となる問い | Coreの証拠 | Advancedの境界 |
|---|---|---|---|
| Week 9 | estimandとlikelihoodを先に固定できるか | score、Hessian、finite-sample coverage | profile likelihood、quasi-likelihood |
| Week 10 | 選択と多重性を含めて検定を監査できるか | effect size、CI、power、FWER、FDR | block bootstrap、selective inference |
| Week 11 | 依存構造に合うcovarianceを選べるか | HC、HAC、cluster coverage | multi-way cluster、wild bootstrap |
| Week 12 | 市場反応と因果効果を区別できるか | estimand、timestamp、placebo、pre-trend | staggered DiD、sensitivity analysis |
| Project | BOJ発表周辺で何が観測されたか | pre-specified announcement response | 追加識別を伴うcausal extension |

**Core**では、推定対象、観測単位、情報時点、標準誤差、finite-sample挙動、失敗条件を一つのevidence chainとして残す。

**Advanced**はCoreのExit Criteriaを満たした後に追加する。高度な推定量を使っても、windowを結果確認後に選んだり、counterfactualを定義しなかったりすれば主張は強くならない。
"""),
    md(r"""
## 2. 成果物と採点契約

B3も他blockと同じ4成果物で評価する。合計点だけでなく、4成果物の提出と必須Exit Criteriaの達成が必要である。

| 成果物 | 必須内容 | 主な採点軸 |
|---|---|---|
| 導出ノート | estimand、仮定、score/Hessian、識別 | 数学的理解 |
| 実装とtest | library任せにしない最小実装、edge case、数値照合 | 実装・test |
| 実験 | baseline、finite-sample coverage、頑健性、失敗例 | 実験設計 |
| 技術メモ | 問い、方法、結果、failure mode、結論 | 説明 |

配点は数学25、実装・test 30、実験設計30、説明15で、合格点は75点である。2〜4ページの技術メモだけを整えても、実行済みNotebookと検証証拠がなければ修了ではない。
"""),
    code("""
rubric = pd.DataFrame(
    {
        "category": [
            "Mathematical understanding",
            "Implementation and testing",
            "Experimental design",
            "Explanation and memo",
        ],
        "points": [25, 30, 30, 15],
    }
)

fig = go.Figure()
for row in rubric.itertuples(index=False):
    fig.add_bar(
        y=["B3 assessment"],
        x=[row.points],
        name=row.category,
        orientation="h",
        text=[row.points],
        textposition="inside",
    )
fig.add_vline(
    x=75,
    line_dash="dash",
    annotation_text="Pass mark",
)
fig.update_layout(
    title="B3 assessment weights",
    xaxis_title="Total points",
    xaxis_range=[0, 105],
    barmode="stack",
    template="plotly_white",
)
fig.show()

print("rubric total:", int(rubric["points"].sum()))
print("pass mark:", 75)
"""),
    md(r"""
図の75点線は各categoryの閾値ではなく、総合点の合格点を可視化した参照線である。数学だけ、またはcodeだけで75点を得る設計ではない。artifact completenessとExit Criteriaは点数とは別のgateとして扱う。
"""),
    md(r"""
## 3. estimandをdataより先に書く

研究の最初に、少なくとも次の5項目を固定する。

1. **Population:** どの事象・銘柄・時点へ一般化するか
2. **Sampling unit:** 独立性を考える単位はevent、日、銘柄、観測行のどれか
3. **Treatment / exposure:** 何を比較するか。単なるlabelか介入か
4. **Outcome and time basis:** 単位、timezone、集計window、利用可能な情報
5. **Estimand:** population distributionのどのfunctionalを求めるか

例えば発表eventを $i=1,\ldots,m$ とし、事前指定windowのreturnを $R_i$ とする。Coreの発表反応estimandの一例は

$$
\theta_{\mathrm{response}}=\mathbb{E}[R_i]
$$

である。これは「発表がなかった同じ時点の反実仮想との差」ではない。したがって、追加のcontrol designやsurprise measureなしに政策の因果効果とは呼ばない。

| 語 | 役割 |
|---|---|
| estimand | population distributionについて知りたい量 |
| estimator | sampleからestimandを近似する規則 |
| estimate | 実際のsampleから得た値 |
| identification | 観測分布と仮定からestimandを一意に表せること |

optimizerの成功はestimateを返せたという計算上の事実であり、identification、model validity、coverageを保証しない。
"""),
    md(r"""
## 4. evidence chainとclaim class

B3では主張を次の順序で強くする。後段へ進むには追加の証拠が必要である。

```text
descriptive pattern
    -> adjusted association
        -> pre-specified announcement response
            -> causal effect under explicit identification
```

各段階で残す証拠は次の通りである。

| 層 | 必須の問い |
|---|---|
| Design | estimand、sampling unit、primary analysisをdata確認前に固定したか |
| Estimation | algorithm、gradient、Hessian、convergenceを検査したか |
| Uncertainty | covarianceがheteroskedasticity・serial・cluster依存に対応するか |
| Validation | bias、coverage、type-I error、powerをMonte Carlo誤差付きで測ったか |
| Robustness | placebo、negative control、alternative specificationをprimaryと分けたか |
| Claim | 結論の語が識別仮定を超えていないか |

`p < 0.05` はこのchainの一要素にすぎない。effect size、interval、経済的単位、欠測、流動性、同時ニュースを伴わない二値判定は技術メモの結論にしない。
"""),
    md(r"""
## 5. なぜpre-specificationが必要か — 選択の最小反例

真の効果がすべて0でも、多数の候補から最も大きい絶対値だけを報告すると、通常の95% intervalはselectionを考慮していない。

次のsimulationでは、各research runで80個のnull signalを独立に推定する。`primary` はdataを見る前に先頭のsignalを選び、`selected` はdataを見た後で絶対値最大を選ぶ。両方に同じnaive intervalを付ける。
"""),
    code("""
selection_rng = task_rng("selection_audit")
replications = 2_000
family_size = 80
sample_size = 60
standard_error = 1.0 / np.sqrt(sample_size)

null_estimates = selection_rng.normal(
    scale=standard_error,
    size=(replications, family_size),
)
primary_estimates = null_estimates[:, 0]
selected_indices = np.argmax(np.abs(null_estimates), axis=1)
selected_estimates = null_estimates[
    np.arange(replications),
    selected_indices,
]

primary_coverage = np.mean(np.abs(primary_estimates) <= 1.96 * standard_error)
selected_coverage = np.mean(np.abs(selected_estimates) <= 1.96 * standard_error)
primary_mc_se = np.sqrt(primary_coverage * (1.0 - primary_coverage) / replications)
selected_mc_se = np.sqrt(selected_coverage * (1.0 - selected_coverage) / replications)

selection_summary = pd.DataFrame(
    [
        {
            "rule": "pre-specified primary",
            "mean_absolute_estimate": np.mean(np.abs(primary_estimates)),
            "naive_coverage": primary_coverage,
            "coverage_mc_se": primary_mc_se,
        },
        {
            "rule": "largest after looking",
            "mean_absolute_estimate": np.mean(np.abs(selected_estimates)),
            "naive_coverage": selected_coverage,
            "coverage_mc_se": selected_mc_se,
        },
    ]
)
display(selection_summary.round(4))
"""),
    code("""
histogram_edges = np.linspace(0.0, np.max(np.abs(selected_estimates)), 32)
primary_counts, _ = np.histogram(np.abs(primary_estimates), bins=histogram_edges)
selected_counts, _ = np.histogram(np.abs(selected_estimates), bins=histogram_edges)
histogram_centers = 0.5 * (histogram_edges[:-1] + histogram_edges[1:])

fig = go.Figure()
fig.add_bar(
    x=histogram_centers,
    y=primary_counts / replications,
    name="Pre-specified primary",
    opacity=0.65,
)
fig.add_bar(
    x=histogram_centers,
    y=selected_counts / replications,
    name="Selected maximum",
    opacity=0.65,
)
fig.add_vline(
    x=1.96 * standard_error,
    line_dash="dash",
    annotation_text="Naive 95% half-width",
)
fig.update_layout(
    title="Looking across a family changes the reported-estimate distribution",
    xaxis_title="Absolute estimate",
    yaxis_title="Fraction of research runs",
    barmode="overlay",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
primaryのcoverageはMonte Carlo errorの範囲で95%に近い。一方、selectedのintervalは「候補を選ぶ前に1つ固定した」というsampling mechanismを暗黙に仮定するため、選択後のcoverageを維持しない。Week 10ではfamily size、selection rule、FWER、FDR、powerを同時に報告する。

この反例は「多重補正をすれば好きな分析をすべてprimaryにできる」という意味ではない。primary analysisを事前指定し、探索分析と感度分析をlabelで分離することが先である。
"""),
    md(r"""
## 6. B3 Projectのpre-analysis specification

BOJ Announcement StudyのCoreは、実データ取得前にも検証できる合成データ版から始める。最終仕様には次を含める。

- official document URLまたはevent source
- publication timestamp、timezone、timestamp precision
- primary anticipation windowとresponse window
- outcomeの単位とreturn convention
- expectationまたはsurpriseの定義
- overlapping eventとsimultaneous-newsの除外・保持規則
- intraday seasonality adjustment
- eventまたは日を単位とするdependence-aware uncertainty
- placebo dates、negative-control outcome
- hypothesis familyとmultiple-testing correction
- alternative windowはsecondary sensitivityと明記

### 再現可能性の最小metadata

```yaml
estimand: mean announcement-window log return
claim_class: observed announcement response
primary_window: pre-specified before outcome inspection
sampling_unit: announcement event
timezone: Asia/Tokyo
seed_tree: root seed plus named task identifiers
uncertainty: matched to event and time dependence
```

実データadapterではtimestampとライセンスを必ず別途確認する。synthetic validationが通っても、実データのsource qualityは自動的に保証されない。
"""),
    md(r"""
## 7. 失敗モード

- estimandを書かず、利用できるcolumnからmodelを選ぶ
- optimizerが収束したのでmodel-based SEも正しいと考える
- p-valueを効果の大きさ、仮説が真である確率、再現確率として読む
- primary windowを結果確認後に選び、pre-specifiedと表現する
- heteroskedasticity、serial correlation、cluster依存をすべて同じrobust SEで処理する
- robust SEがomitted-variable biasやmeasurement errorも直すと考える
- 発表時点周辺のreturnを、counterfactualなしに政策の因果効果と呼ぶ
- sensitivity analysisの中で最も都合のよい結果だけを結論へ移す

diagnosticを増やすだけでは防げない失敗もある。primary analysisとclaim classはoutcomeを見る前に固定し、変更履歴を残す。
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. estimand、estimator、estimateを、発表window returnの例で書き分けよ。
2. sampling unitがtick、event、日である場合の独立性仮定を比較せよ。
3. 4成果物と配点を表にし、自分の不足証拠を記録せよ。

### 標準

4. 選択反例のfamily sizeを1、20、80、400へ変え、naive coverageをMonte Carlo SE付きで比較せよ。
5. BOJ課題のprimary outcome、window、exclusion ruleをoutcome確認前にYAMLへ保存せよ。
6. association、announcement response、causal effectの各claimに必要な追加仮定を書け。

### 研究

7. pre-registration変更履歴のschemaを設計し、変更理由とdata access時刻を含めよ。
8. **Advanced:** surprise measureを導入した場合でも残る識別上の脅威をDAGとtiming diagramで示せ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] B3のCoreとAdvanced、4週間の依存関係を説明できる
- [ ] population、sampling unit、time basis、estimandをdataより先に書ける
- [ ] optimizer convergence、statistical validity、causal identificationを区別できる
- [ ] effect size、interval、power、多重性を同じevidence chainへ配置できる
- [ ] 4成果物、75点、必須Exit Criteriaの三つの修了条件を説明できる
- [ ] financial announcement responseを追加識別なしにcausal effectと呼ばない
"""),
    md(r"""
## 10. 出典

- [MIT OpenCourseWare 18.650: Statistics for Applications, Lecture Notes](https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/resources/lecture-notes/) — parametric inference、MLE、hypothesis testing、regression、GLMの講義系列
- [MIT OpenCourseWare 18.650: Lectures 4–5, Maximum Likelihood Estimation](https://ocw.mit.edu/courses/18-650-statistics-for-applications-fall-2016/resources/lecture-3-maximum-likelihood-estimation/) — likelihood、score、Fisher information、asymptotic normality
- [American Statistical Association, Statement on Statistical Significance and P-Values](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) — p-valueを効果量や仮説の確率と混同しないための公式原則
- [Hernán and Robins, *Causal Inference: What If*](https://miguelhernan.org/whatifbook) — estimand、counterfactual、identificationを分ける因果推論の著者公式教材

次章では、Gaussian・logistic・Poisson likelihoodを実装し、derivative、optimizer、有限標本coverageを別々に監査する。
"""),
]
