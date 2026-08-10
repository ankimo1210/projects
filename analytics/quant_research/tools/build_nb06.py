"""Builder for notebook 06: B2 orientation and simulation contract."""

from nbkit import code, md

cells = [
    md(r"""
# 06. B2の地図 — 確率を「再現可能な計算」にする

> 乱数を出すことと、確率的な主張を検証することは同じではない。

## 学習目標

- Week 5–8の依存関係と、各週の成果物を説明できる
- estimand、estimator、sampling error、discretization errorを区別できる
- `numpy.random.Generator` を注入する再現可能な実験を設計できる
- B2のcoreとadvancedを切り分け、先へ進む停止条件を持てる

## 前提知識

- B1のベクトル・行列、固有値、Cholesky分解
- 平均、分散、共分散、正規分布の初歩
- NumPy配列と関数の基本操作

B1の全章を終えている必要はない。ただし、共分散行列の固有値と条件数を診断できない場合は、Week 2を先に復習する。
"""),
    code("""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
"""),
    md(r"""
## 1. 4週間の問い

| 週 | 中心となる問い | 必須成果物 |
|---|---|---|
| Week 5 | 条件を観測すると分布はどう変わるか | 条件付きGaussianの解析値とsimulation照合 |
| Week 6 | 標本数を増やせば何が、どの意味で安定するか | coverageとheavy-tail失敗実験 |
| Week 7 | 過去の情報に対して公平とは何か | Markov chainとstopping ruleの診断 |
| Week 8 | 連続時間を離散計算でどう近似するか | Brownian motion、Euler–Maruyama、誤差分解 |
| Project | Monte Carlo推定をどう監査可能にするか | RNG注入、CI、分散削減を備えた小さなlibrary |

### Coreとadvanced

**Core**は、B2プロジェクトを完成させるために必須である。条件付き期待値、収束概念、有限状態Markov chain、martingale、Brownian motion、Itôの公式、Euler–Maruyama、通常のMonte Carlo、antithetic/control variateを含む。

**Advanced**は、coreのExit Criteriaを満たした後に扱う。importance sampling、Girsanovによる測度変換、Brownian bridge、rare-event simulationを含む。高度な手法を追加しても、estimandと誤差budgetが曖昧なら研究の質は上がらない。
"""),
    code("""
units = ["W5", "W6", "W7", "W8", "Project"]
core_hours = np.array([7.0, 8.0, 7.5, 9.0, 7.0])
advanced_hours = np.array([1.5, 2.0, 2.0, 3.5, 4.0])

fig = go.Figure()
fig.add_bar(x=units, y=core_hours, name="Core")
fig.add_bar(x=units, y=advanced_hours, name="Advanced")
fig.update_layout(
    title="B2 study load by unit",
    xaxis_title="Unit",
    yaxis_title="Estimated hours",
    barmode="stack",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. B2 placement診断

次の6項目を、口頭の自己申告ではなく導出または再実行可能な数値確認で示す。

1. conditional expectationを情報集合への射影として導出する。
2. LLNとCLTが答える問いを区別する。
3. martingaleをfiltrationに対して定義する。
4. optional stoppingが成立する条件と、無条件ではない理由を説明する。
5. Itô lemmaを単純な拡散過程へ適用する。
6. Monte Carlo confidence intervalを構成し、coverageとMonte Carlo uncertaintyを診断する。

診断が強ければ確率基礎を圧縮できるが、B2 Project、4成果物、採点、Exit Criteria、再現性・検証要件は免除しない。
"""),
    md(r"""
## 3. 4成果物と75点gate

| Category | Points | B2で必要な証拠 |
|---|---:|---|
| Mathematical understanding | 25 | 条件付き分布、収束、martingale、Itôの導出 |
| Implementation and testing | 30 | RNG注入、path/payoff分離、CI、edge-case test |
| Experimental design | 30 | coverage、heavy tail、discretization、variance reduction |
| Explanation and memo | 15 | estimand、error budget、結果、失敗条件を2〜4ページで説明 |

合計75点以上、4成果物の提出、必須Exit Criteriaの達成をそれぞれ独立に確認する。
"""),
    md(r"""
## 4. 最初に固定するもの — estimand

確率変数 $Y$ の期待値

$$
\mu=\mathbb{E}[Y]
$$

を知りたいとする。独立標本 $Y_1,\ldots,Y_N$ による標本平均は

$$
\hat\mu_N=\frac{1}{N}\sum_{i=1}^{N}Y_i
$$

である。$\mu$ が **estimand**、$\hat\mu_N$ が **estimator**、実際に得た数値がestimateである。この3語を混ぜると、何を検証したか追跡できない。

連続時間過程のpayoffを計算する場合、有限path数に由来するsampling errorに加え、時間刻み $\Delta t$ に由来するdiscretization errorが入る。

$$
\hat\mu_{N,\Delta t}-\mu
=\left(\hat\mu_{N,\Delta t}-\mu_{\Delta t}\right)
+\left(\mu_{\Delta t}-\mu\right)
$$

第1項だけを減らしても第2項は消えない。したがって、path数 $N$ とstep数を別々に変える実験が必要である。
"""),
    md(r"""
## 5. 再現可能性の契約

このブロックではglobalな乱数状態を使わず、計算関数へ `numpy.random.Generator` を渡す。

- seedは実験の入口で一度だけ固定する
- 関数内で毎回同じseedからgeneratorを作り直さない
- 独立streamが必要なら `SeedSequence.spawn` を使う
- path生成とpayoff評価を分離する
- 出力には標本数、標準誤差、confidence interval、診断値を残す

同じseedはdebuggingには有用だが、結果の一般性を保証しない。主張の頑健性は複数の独立streamで確認する。
"""),
    code("""
def spawned_generators(seed, count):
    seed_sequence = np.random.SeedSequence(seed)
    return [np.random.default_rng(child) for child in seed_sequence.spawn(count)]


streams_a = spawned_generators(RANDOM_SEED, 3)
streams_b = spawned_generators(RANDOM_SEED, 3)
draws_a = np.array([stream.normal(size=4) for stream in streams_a])
draws_b = np.array([stream.normal(size=4) for stream in streams_b])

print("reproducible spawn tree:", np.array_equal(draws_a, draws_b))
print("distinct child streams:", not np.array_equal(draws_a[0], draws_a[1]))
print("sample child output:", np.round(draws_a[0], 4))
"""),
    md(r"""
`spawn` は親seedから再現可能な子streamを構成する。これは単に整数seedへ1を足す規約より、並列化の意図をコードで明確にする。ただし、子streamをどのworker・実験へ割り当てたかはmetadataとして保存する必要がある。
"""),
    md(r"""
## 6. 最小のbaseline — 標本平均と標準誤差

$\operatorname{Var}(Y)=\sigma^2<\infty$ なら、独立標本に対して

$$
\operatorname{SE}(\hat\mu_N)=\frac{\sigma}{\sqrt{N}}
$$

である。標本標準偏差 $s$ で置き換えた $s/\sqrt{N}$ を最初のbaselineとする。分散削減法は、このbaselineと同じestimand・同程度の計算costで比較する。

次の図は、標準正規の平均推定を独立streamで繰り返したRMSEである。傾き $-1/2$ は1回のきれいなpathではなく、反復実験で検証する。
"""),
    code("""
sample_sizes = np.array([32, 128, 512, 2048, 8192])
replications = 500
rmse_values = []

for index, sample_size in enumerate(sample_sizes):
    rng = np.random.default_rng(
        np.random.SeedSequence(RANDOM_SEED, spawn_key=(index,))
    )
    estimates = rng.normal(size=(replications, sample_size)).mean(axis=1)
    rmse_values.append(np.sqrt(np.mean(estimates**2)))

rmse_values = np.asarray(rmse_values)
reference = rmse_values[0] * np.sqrt(sample_sizes[0] / sample_sizes)
log_slope = np.polyfit(np.log(sample_sizes), np.log(rmse_values), 1)[0]

fig = go.Figure()
fig.add_scatter(
    x=sample_sizes,
    y=rmse_values,
    mode="lines+markers",
    name="Empirical RMSE",
)
fig.add_scatter(
    x=sample_sizes,
    y=reference,
    mode="lines",
    name="N^(-1/2) reference",
    line={"dash": "dash"},
)
fig.update_layout(
    title="Monte Carlo sampling error baseline",
    xaxis_title="Sample size N",
    yaxis_title="RMSE of sample mean",
    xaxis_type="log",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()

print("estimated log-log slope:", round(float(log_slope), 3))
"""),
    md(r"""
理論線と有限標本の線は完全には一致しない。傾きを判断するときは、反復数、標本数の範囲、乱数streamを記録する。Week 6では有限分散を持たない分布へ同じ手順を適用し、$N^{-1/2}$ を無条件に期待できないことを見る。
"""),
    md(r"""
## 7. 検証の順序

B2の数値実験は次の順序で組み立てる。

1. 解析解がある小さなcaseを選ぶ
2. 単純なestimatorをbaselineにする
3. seed、標本数、step幅、単位を固定する
4. bias、standard error、coverage、計算costを測る
5. 意図的に仮定を壊し、診断が反応するか確かめる
6. 最後にadvanced methodを追加する

「既知の答えに合う」ことは必要条件であって十分条件ではない。同じ実装上の誤りを解析式とsimulationへ重複させないため、可能ならSciPyなど独立した実装とも照合する。
"""),
    md(r"""
## 8. 失敗モード — seed固定を再現性のすべてと考える

次の実験は同じ数列を返すが、良い設計ではない。

```python
def bad_estimator(sample_size):
    rng = np.random.default_rng(7)
    return rng.normal(size=sample_size).mean()
```

関数を呼ぶたびにstreamが先頭へ戻るため、反復実験が独立にならない。さらに、次も別の失敗である。

- 1つのseedで都合のよい図を選ぶ
- 複数methodが異なる乱数を使い、差とnoiseを混同する
- confidence intervalを1本描き、coverageを確認しない
- time-step biasをMonte Carlo標準誤差に含める
- heavy-tailでも標本分散が有限母分散をよく表すと仮定する

乱数の管理は、simulationの研究設計そのものである。
"""),
    md(r"""
## 9. 段階別演習

### 基礎

1. estimand、estimator、estimateを、コイン投げの例で書き分けよ。
2. $N$ を4倍にしたとき標準誤差がどう変わるか導出せよ。
3. 同じ親seedから4つの子generatorを作り、再生成できることを確かめよ。

### 標準

4. 標準正規の実験を20個の親seedで反復し、log-log slopeの分布を描け。
5. common random numbersを使ったmethod比較と、独立乱数を使った比較の分散を調べよ。
6. simulation結果のmetadata schemaを設計せよ。最低限、seed tree、$N$、step数、estimandを含める。

### 研究

7. sampling error、discretization error、model errorを分けたerror budgetを、European optionの例で設計せよ。
8. advancedへ進む停止条件を、bias、coverage、実行時間の閾値として定義せよ。
"""),
    md(r"""
## 10. Exit Criteria

- [ ] B2のcoreとadvancedを説明し、学習順序を守れる
- [ ] estimand、estimator、estimateを区別できる
- [ ] global乱数状態を使わず `Generator` を注入する理由を説明できる
- [ ] sampling errorとdiscretization errorを別々に検証できる
- [ ] $N^{-1/2}$ baselineを反復実験で確認できる
- [ ] placement診断6項目を導出または数値確認で監査した
- [ ] 4成果物、75点、必須Exit Criteriaの三つを区別した
"""),
    md(r"""
## 11. 出典

- [NumPy Random sampling](https://numpy.org/doc/stable/reference/random/) — `Generator` を中心とする乱数APIとlegacy APIとの区別
- [NumPy `Generator.spawn`](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.spawn.html) — 独立に近い子generatorの生成
- [NumPy `SeedSequence`](https://numpy.org/doc/stable/reference/random/bit_generators/generated/numpy.random.SeedSequence.html) — seedの混合と再現可能なspawn tree
- [MIT OpenCourseWare 18.600: Probability and Random Variables, Lecture Notes](https://ocw.mit.edu/courses/18-600-probability-and-random-variables-fall-2019/pages/lecture-notes/) — 条件付き期待値、極限定理、確率過程への入口

次章では、多変量Gaussianを「相関した乱数生成」と「観測後の条件付き分布」の両側から扱う。
"""),
]
