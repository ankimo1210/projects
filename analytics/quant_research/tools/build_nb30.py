"""Builder for notebook 30: B6 orientation and tournament contract."""

from nbkit import code, md
from stage2_nb import setup_cell, treasury_cell

cells = [
    md(r"""
# 30. B6の地図 — winnerよりfailure conditionを探す

> 同じ問題を解いていないmodelをscore順に並べても、tournamentにはならない。

## 学習目標

- B5から固定して引き継ぐdata・target・outer testを説明できる
- boosting、kernel/GP、clustering、shift evaluationの役割を区別できる
- model familyごとの計算予算を事前に固定できる
- single metric winnerを避け、no model selectedを許容できる
- B6の4成果物と75点gateを運用できる

## 前提知識

- B5の全Exit Criteriaとlocked test
- B1のPCA・regularization・conditioning
- B2のuncertainty、B3のclaim boundary、B4のruntime contract
"""),
    setup_cell(30),
    treasury_cell(),
    md(r"""
## 1. B5から変更してはいけないもの

| Contract | Locked value |
|---|---|
| Source snapshot | Treasury 2015–2025、同じhash |
| Target | next Treasury publication 10y CMT change (bp) |
| Prediction origin | official day-$t$ publication後 |
| Outer test | B5でlockしたfinal chronological 20% |
| Missing rule | complete stable-tenor rows |
| Claim | forecast accuracy、not trading utility |

B6で変更できるのはmodel familyと、inner validation内で事前宣言したsearchである。
"""),
    code("""
split = qt.chronological_split(len(forecast.regression_target), gap=1)
immutability_audit = pd.DataFrame(
    {
        "check": [
            "snapshot hash present",
            "target dates future",
            "test starts after validation",
            "test used for selection",
        ],
        "value": [
            len(treasury.metadata.snapshot_sha256) == 64,
            bool(np.all(forecast.target_dates > forecast.prediction_dates)),
            bool(split.test.min() > split.validation.max()),
            False,
        ],
    }
)
display(immutability_audit)

fig = go.Figure()
for name, indices, color in [
    ("train", split.train, "#4c78a8"),
    ("validation", split.validation, "#f58518"),
    ("locked test", split.test, "#e45756"),
]:
    fig.add_scatter(
        x=pd.to_datetime(forecast.prediction_dates[indices]),
        y=np.full(indices.size, name),
        mode="markers",
        marker={"size": 4, "color": color},
        name=name,
    )
fig.update_layout(
    title="Immutable B5/B6 temporal partitions",
    xaxis_title="Prediction date",
    yaxis_title="Partition",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. 4週間の問い

| 週 | 問い | Core evidence |
|---|---|---|
| Week 21 | treeのnonlinearityはlinear baselineを超えるか | stump、boosting trace、validation overfit |
| Week 22 | smooth kernelとGP uncertaintyは有効か | length scale、runtime、coverage |
| Week 23 | clusterはerror sliceとして安定か | seed stability、conditional error、non-causal label |
| Week 24 | shift下で性能とintervalは保たれるか | nested split、drift、coverage boundary |
| Project | 同一条件で採用可能なmodelはあるか | RMSE/MAE、stability、runtime、no-selection gate |

MLPはB9でbackpropagationを実装してからAdvancedとして追加する。B6 Coreでlibraryのblack-box MLPを先に置かない。

## 3. 4成果物と75点gate

| Category | Points | B6で必要な証拠 |
|---|---:|---|
| Mathematical understanding | 25 | split、boosting update、kernel/GP、conformal rank |
| Implementation and testing | 30 | stump、boosting、kernel、GP、k-means、drift tests |
| Experimental design | 30 | common outer test、inner budget、shift、runtime |
| Explanation and memo | 15 | model failure、assumption、no-selection conclusion |

## 4. 失敗モード

- modelごとにfeature、timestamp、missing ruleを変える
- GPだけ短い直近periodを使いながら同条件と呼ぶ
- feature importanceを因果効果と読む
- cluster labelを真のmarket regimeと呼ぶ
- standard conformalのexchangeability保証を金融時系列へ無条件に適用する
- RMSEだけでwinnerを選びruntime・stability・calibrationを無視する

## 5. 段階別演習

### 基礎

1. B5からlockされるfieldをmanifestにせよ。
2. 各model familyのfit sizeとsearch数を予算表にせよ。

### 標準

3. model selectionとouter evaluationのdata flowを図示せよ。
4. no model selectedとなるgateをscore計算前に書け。

### 研究

5. GP subsetとfull-history ridgeの比較可能性をどう説明するか書け。
6. B9後にMLPを追加する際の同一budget規約を設計せよ。

## 6. Exit Criteria

- [ ] B5から不変のdata・target・outer testを説明できる
- [ ] model familyごとのinner budgetを固定できる
- [ ] nonlinear importanceと因果説明を区別できる
- [ ] shift・runtime・intervalをRMSEと同時に評価できる
- [ ] no model selectedを正しい結論として許容できる

## 7. 出典

- [The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/) — tree、boosting、kernel、unsupervised learning
- [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/) — GPの著者公開版
- [Interpretable Machine Learning](https://christophm.github.io/interpretable-ml-book/) — predictive interpretationの境界
- [U.S. Treasury Yield Curve Methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) — data breakとpublication contract
"""),
]
