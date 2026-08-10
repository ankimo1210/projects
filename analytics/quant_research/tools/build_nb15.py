"""Builder for notebook 15: regression and robust inference."""

from nbkit import code, md

cells = [
    md(r"""
# 15. Week 11 — 回帰と頑健推論

> robust standard errorは、同じ係数推定量の不確実性を再評価する。欠落変数でずれた係数を正しいestimandへ戻す処方ではない。

## 学習目標

- coefficient estimateとcovariance estimateを別の問題として扱う
- sampling unitと依存構造からnaive、HC、HAC、cluster covarianceを選ぶ
- sandwich estimatorをscoreの集計単位から導出し、実装を照合する
- coverage、estimator bias、Monte Carlo誤差を別々に測る
- HAC lagとcluster数に対する推論の感度を報告する
- robust SEがomitted-variable biasを直さない反例を再現する

## 前提知識

- OLS、行列積、条件付き期待値
- confidence intervalとMonte Carlo coverage
- 時系列のserial correlationとpanelのcluster
"""),
    code("""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy.stats import norm

from quant_textbook.robust import fit_ols_inference

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 15
TASK_IDS = {
    "coverage": 1,
    "manual_checks": 2,
    "hac_sensitivity": 3,
    "cluster_sensitivity": 4,
    "ovb": 5,
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
## 1. Estimand、sampling unit、covariance

線形射影の係数を

$$
\beta^*=\arg\min_b\mathbb{E}[(Y-X'b)^2]
$$

とする。OLSは標本上の二乗誤差を最小化して $\hat\beta$ を作る。covariance estimatorは、$\hat\beta$ のsampling variationをどの依存構造の下で近似するかを決める。covarianceの選択を変えても、同じdesign matrixなら $\hat\beta$ 自体は変わらない。

本章のsimulationでは推定したいslopeを $\beta^*=0.8$ とし、sampling unitを次のように固定する。

| DGP | 独立とみなす単位 | 許す依存 | 主な候補 | 誤った単位の例 |
|---|---|---|---|---|
| heteroskedastic cross-section | row | row内の分散がcovariateで変化 | HC | homoskedastic naive |
| one time series | seriesを構成する時点列 | 時点間の短期serial correlation | HAC | 各時点を独立扱い |
| grouped panel | cluster | cluster内の任意の相関 | cluster | cluster内rowを独立扱い |

cluster-robust推論ではcluster同士が独立という近似が中心になる。clusterは便利なlabelではなく、再標本化で一緒に動くsampling unitである。

GLMでは $g\{\mathbb{E}[Y\mid X]\}=X'\beta$ のfamilyとlinkがcoefficient estimandの一部になる。sandwich covarianceはscore varianceの仮定を緩めうるが、誤ったlink、欠けたinteraction、zero inflationなどで変わったestimandを自動的に修復しない。本labは線形回帰へ絞り、同じ「係数とcovarianceを分離する」原則をGLMへ持ち越す。
"""),
    md(r"""
## 2. Sandwich estimator

OLS residualを $\hat u_i=y_i-x_i'\hat\beta$、breadを $B=(X'X)^{-1}$ とする。heteroskedasticity-consistent covarianceの基本形は

$$
\widehat{\operatorname{Var}}(\hat\beta)
=B\left(\sum_i x_i x_i'\hat u_i^2\right)B.
$$

中央のmeatがscore $s_i=x_i\hat u_i$ の共分散を推定する。HC1は有限標本係数 $n/(n-k)$ を掛ける。HACはlagged score covarianceをkernelで集計し、cluster covarianceはcluster score $S_g=\sum_{i\in g}s_i$ を先に作って

$$
B\left(\sum_g S_gS_g'\right)B
$$

とする。どの観測を足してからouter productを取るかが、依存を許す範囲を表す。
"""),
    code("""
def add_intercept(values):
    values = np.asarray(values, dtype=float)
    return np.column_stack([np.ones(values.shape[0]), values])


def interval_contains(result, coefficient_index, truth, critical_value=1.96):
    center = result.coefficients[coefficient_index]
    radius = critical_value * result.standard_errors[coefficient_index]
    return (center - radius <= truth) and (truth <= center + radius)


def manual_hc1_covariance(design, residuals):
    n_observations, n_parameters = design.shape
    bread = np.linalg.inv(design.T @ design)
    scores = design * residuals[:, None]
    meat = scores.T @ scores
    return (n_observations / (n_observations - n_parameters)) * bread @ meat @ bread


def manual_cluster_covariance(design, residuals, clusters):
    n_observations, n_parameters = design.shape
    unique_clusters = np.unique(clusters)
    bread = np.linalg.inv(design.T @ design)
    meat = np.zeros((n_parameters, n_parameters))
    for cluster in unique_clusters:
        cluster_score = (design[clusters == cluster] * residuals[clusters == cluster, None]).sum(axis=0)
        meat += np.outer(cluster_score, cluster_score)
    correction = (
        len(unique_clusters) / (len(unique_clusters) - 1)
        * (n_observations - 1)
        / (n_observations - n_parameters)
    )
    return correction * bread @ meat @ bread
"""),
    md(r"""
上の関数は式を可視化する教材実装である。実務ではrank、leverage、few clusters、multi-way cluster、kernelやbandwidth、missing dataを含む追加契約が必要になる。次に共通libraryの結果と行列式を照合する。
"""),
    code("""
check_rng = task_rng("manual_checks")
n_check_clusters = 24
check_cluster_size = 10
check_clusters = np.repeat(np.arange(n_check_clusters), check_cluster_size)
check_cluster_x = check_rng.normal(size=n_check_clusters)
check_cluster_error = check_rng.normal(scale=1.2, size=n_check_clusters)
check_x = check_cluster_x[check_clusters] + check_rng.normal(size=len(check_clusters))
check_y = 0.3 + 0.8 * check_x + check_cluster_error[check_clusters] + check_rng.normal(size=len(check_clusters))
check_design = add_intercept(check_x)

check_hc1 = fit_ols_inference(check_design, check_y, covariance_type="HC1")
check_cluster = fit_ols_inference(
    check_design,
    check_y,
    covariance_type="cluster",
    clusters=check_clusters,
    small_sample=True,
)

manual_hc1 = manual_hc1_covariance(check_design, check_hc1.residuals)
manual_cluster = manual_cluster_covariance(
    check_design,
    check_cluster.residuals,
    check_clusters,
)

print("HC1 maximum covariance difference:", np.max(np.abs(check_hc1.covariance - manual_hc1)))
print("cluster maximum covariance difference:", np.max(np.abs(check_cluster.covariance - manual_cluster)))
print("coefficient equality:", np.max(np.abs(check_hc1.coefficients - check_cluster.coefficients)))
"""),
    md(r"""
covarianceが異なっても係数は一致する。行列照合はformulaとimplementationの局所検証であり、選んだ依存構造がデータに妥当であることまでは証明しない。
"""),
    md(r"""
## 3. 3種類のDGPでcoverageを測る

95% intervalのcoverageを独立replicationで測る。各DGPでは係数の真値を同じにし、誤差構造だけを変える。

- **heteroskedastic:** $\operatorname{Var}(u_i\mid x_i)$ が $|x_i|$ とともに増える
- **serial:** $x_t$ と $u_t$ がそれぞれAR(1)で動き、scoreがserially correlatedになる
- **clustered:** cluster-level componentを $x$ と $u$ が持ち、cluster内scoreが相関する

使えない方法を無理に表へ埋めない。single time seriesに任意のcluster labelを付けても、独立clusterが生まれるわけではない。
"""),
    code("""
TRUE_SLOPE = 0.8
N_REPLICATIONS = 320


def simulate_heteroskedastic(rng, n_observations=260):
    predictor = rng.normal(size=n_observations)
    error_scale = 0.35 + 0.85 * np.abs(predictor)
    outcome = 0.2 + TRUE_SLOPE * predictor + error_scale * rng.normal(size=n_observations)
    return add_intercept(predictor), outcome, None


def simulate_serial(rng, n_observations=600, predictor_rho=0.60, error_rho=0.65):
    predictor = np.empty(n_observations)
    error = np.empty(n_observations)
    predictor[0] = rng.normal()
    error[0] = rng.normal()
    for index in range(1, n_observations):
        predictor[index] = predictor_rho * predictor[index - 1] + rng.normal()
        error[index] = error_rho * error[index - 1] + rng.normal()
    outcome = 0.2 + TRUE_SLOPE * predictor + error
    return add_intercept(predictor), outcome, None


def simulate_clustered(rng, n_clusters=32, cluster_size=10):
    clusters = np.repeat(np.arange(n_clusters), cluster_size)
    cluster_predictor = rng.normal(size=n_clusters)
    cluster_error = rng.normal(scale=1.3, size=n_clusters)
    predictor = cluster_predictor[clusters] + rng.normal(size=len(clusters))
    error = cluster_error[clusters] + rng.normal(scale=0.7, size=len(clusters))
    outcome = 0.2 + TRUE_SLOPE * predictor + error
    return add_intercept(predictor), outcome, clusters


scenario_contracts = {
    "heteroskedastic": {
        "id": 1,
        "generator": simulate_heteroskedastic,
        "methods": ["naive", "HC1"],
    },
    "serial": {
        "id": 2,
        "generator": simulate_serial,
        "methods": ["naive", "HC1", "HAC"],
    },
    "clustered": {
        "id": 3,
        "generator": simulate_clustered,
        "methods": ["naive", "HC1", "cluster"],
    },
}

coverage_records = []
for scenario_name, contract in scenario_contracts.items():
    estimates = {method: [] for method in contract["methods"]}
    standard_errors = {method: [] for method in contract["methods"]}
    covered = {method: [] for method in contract["methods"]}
    for replication in range(N_REPLICATIONS):
        rng = task_rng("coverage", contract["id"], replication)
        design, outcome, clusters = contract["generator"](rng)
        for method in contract["methods"]:
            kwargs = {}
            if method == "HAC":
                kwargs["max_lag"] = 10
            if method == "cluster":
                kwargs["clusters"] = clusters
                kwargs["small_sample"] = True
            result = fit_ols_inference(
                design,
                outcome,
                covariance_type=method,
                **kwargs,
            )
            estimates[method].append(result.coefficients[1])
            standard_errors[method].append(result.standard_errors[1])
            covered[method].append(interval_contains(result, 1, TRUE_SLOPE))
    for method in contract["methods"]:
        method_estimates = np.asarray(estimates[method])
        method_standard_errors = np.asarray(standard_errors[method])
        method_coverage = np.mean(covered[method])
        coverage_records.append(
            {
                "scenario": scenario_name,
                "covariance": method,
                "estimate_bias": method_estimates.mean() - TRUE_SLOPE,
                "empirical_sd": method_estimates.std(ddof=1),
                "mean_reported_se": method_standard_errors.mean(),
                "coverage": method_coverage,
                "coverage_mcse": np.sqrt(method_coverage * (1.0 - method_coverage) / N_REPLICATIONS),
            }
        )

coverage_table = pd.DataFrame(coverage_records)
display(coverage_table.round(4))
"""),
    code("""
fig = go.Figure()
for scenario_name in scenario_contracts:
    subset = coverage_table[coverage_table["scenario"] == scenario_name]
    fig.add_bar(
        x=subset["covariance"],
        y=subset["coverage"],
        error_y={"type": "data", "array": 1.96 * subset["coverage_mcse"], "visible": True},
        name=scenario_name,
    )
fig.add_hline(y=0.95, line_dash="dash", line_color="black")
fig.update_layout(
    title="Coverage depends on matching covariance to dependence",
    xaxis_title="Covariance estimator",
    yaxis_title="Empirical 95% coverage",
    yaxis_range=[0.0, 1.02],
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
error barはcoverage推定のMonte Carlo 95% intervalであり、回帰係数のintervalではない。係数biasがほぼ同じでも、reported SEとempirical SDが合わない方法はundercoverageを起こす。有限replicationなのでcoverageがちょうど0.95になる必要はない。

HCはrowごとのheteroskedasticityには対応するが、時点間またはcluster内のcross-productを復元しない。HACとclusterは「よりrobust」という一方向の序列ではなく、異なるsampling mechanismを近似する。
"""),
    md(r"""
## 4. HAC lag sensitivity

Newey–West型HACはBartlett weight

$$
w_\ell=1-\frac{\ell}{L+1},\qquad \ell=1,\ldots,L
$$

でlagged score covarianceを足す。lag $L$ が小さすぎれば依存を落とし、大きすぎれば有限標本varianceが増える。データを見て最も都合のよいlagだけを報告せず、primary ruleと感度を先に定める。
"""),
    code("""
hac_design, hac_outcome, _ = simulate_serial(
    task_rng("hac_sensitivity"),
    n_observations=900,
    predictor_rho=0.75,
    error_rho=0.80,
)
hac_lags = [0, 1, 2, 4, 6, 8, 12, 20, 32]
hac_rows = []
for max_lag in hac_lags:
    result = fit_ols_inference(
        hac_design,
        hac_outcome,
        covariance_type="HAC",
        max_lag=max_lag,
    )
    hac_rows.append(
        {
            "max_lag": max_lag,
            "slope": result.coefficients[1],
            "standard_error": result.standard_errors[1],
            "ci_lower": result.coefficients[1] - 1.96 * result.standard_errors[1],
            "ci_upper": result.coefficients[1] + 1.96 * result.standard_errors[1],
        }
    )

hac_sensitivity = pd.DataFrame(hac_rows)
display(hac_sensitivity.round(5))

fig = go.Figure()
fig.add_scatter(
    x=hac_sensitivity["max_lag"],
    y=hac_sensitivity["standard_error"],
    mode="lines+markers",
    name="HAC standard error",
)
fig.update_layout(
    title="HAC uncertainty is sensitive to the lag rule",
    xaxis_title="Maximum lag",
    yaxis_title="Slope standard error",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
lagを変えてもslopeが変わらないことを表で確認する。動くのはcovariance estimateである。lag 0はscoreのserial cross-productを使わないため、HC型に近い診断点になる。本番分析ではsampling frequency、依存の減衰、事前規則を記録する。
"""),
    md(r"""
## 5. Cluster数とfew-cluster問題

cluster covarianceの漸近近似は通常、cluster数 $G$ が増える方向を使う。row数だけを増やしても、独立clusterが少なければ情報量を過大評価しうる。次の実験ではcluster sizeを固定し、$G$ を変える。同じnormal critical valueを使うため、few clustersでのsmall-sample limitationも結果に含まれる。
"""),
    code("""
cluster_counts = [8, 12, 20, 32, 50, 80]
cluster_repetitions = 240
cluster_sensitivity_rows = []

for n_clusters in cluster_counts:
    coverage_by_method = {"naive": [], "cluster": []}
    for replication in range(cluster_repetitions):
        rng = task_rng("cluster_sensitivity", n_clusters, replication)
        design, outcome, clusters = simulate_clustered(
            rng,
            n_clusters=n_clusters,
            cluster_size=10,
        )
        naive_result = fit_ols_inference(design, outcome, covariance_type="naive")
        cluster_result = fit_ols_inference(
            design,
            outcome,
            covariance_type="cluster",
            clusters=clusters,
            small_sample=True,
        )
        coverage_by_method["naive"].append(interval_contains(naive_result, 1, TRUE_SLOPE))
        coverage_by_method["cluster"].append(interval_contains(cluster_result, 1, TRUE_SLOPE))
    for method, indicators in coverage_by_method.items():
        coverage = np.mean(indicators)
        cluster_sensitivity_rows.append(
            {
                "n_clusters": n_clusters,
                "covariance": method,
                "coverage": coverage,
                "coverage_mcse": np.sqrt(coverage * (1.0 - coverage) / cluster_repetitions),
            }
        )

cluster_sensitivity = pd.DataFrame(cluster_sensitivity_rows)
display(cluster_sensitivity.round(4))

fig = go.Figure()
for method in ["naive", "cluster"]:
    subset = cluster_sensitivity[cluster_sensitivity["covariance"] == method]
    fig.add_scatter(
        x=subset["n_clusters"],
        y=subset["coverage"],
        error_y={"type": "data", "array": 1.96 * subset["coverage_mcse"], "visible": True},
        mode="lines+markers",
        name=method,
    )
fig.add_hline(y=0.95, line_dash="dash", line_color="black")
fig.update_layout(
    title="Rows do not substitute for independent clusters",
    xaxis_title="Number of clusters",
    yaxis_title="Empirical 95% coverage",
    yaxis_range=[0.0, 1.02],
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
small-sample correctionを使っても、少数clusterでnormal approximationが正確になる保証はない。few clustersではcluster-level leverage、$t$ critical value、wild cluster bootstrapなどを検討する。本章ではAdvancedとして位置づけ、単一の補正係数を万能解として扱わない。
"""),
    md(r"""
## 6. 反例 — robust SEはomitted-variable biasを直さない

真のモデルを

$$
Y=\alpha+\beta X+\gamma Z+\varepsilon,
\qquad \operatorname{Cov}(X,Z)\ne0
$$

とする。$Z$ を落としたshort regressionのslopeは一般に $\beta$ ではない。HC covarianceを使っても、score varianceの推定が変わるだけで欠落した $Z$ はdesign matrixへ戻らない。
"""),
    code("""
TRUE_OVB_SLOPE = 1.0
ovb_repetitions = 320
ovb_records = []

for replication in range(ovb_repetitions):
    rng = task_rng("ovb", replication)
    n_observations = 320
    omitted = rng.normal(size=n_observations)
    predictor = 0.85 * omitted + 0.55 * rng.normal(size=n_observations)
    error_scale = 0.5 + 0.35 * np.abs(predictor)
    outcome = 0.4 + TRUE_OVB_SLOPE * predictor + 1.25 * omitted + error_scale * rng.normal(size=n_observations)

    short_design = add_intercept(predictor)
    full_design = np.column_stack([np.ones(n_observations), predictor, omitted])
    specifications = {
        "short + naive": fit_ols_inference(short_design, outcome, covariance_type="naive"),
        "short + HC1": fit_ols_inference(short_design, outcome, covariance_type="HC1"),
        "full + HC1": fit_ols_inference(full_design, outcome, covariance_type="HC1"),
    }
    for specification, result in specifications.items():
        ovb_records.append(
            {
                "replication": replication,
                "specification": specification,
                "estimate": result.coefficients[1],
                "standard_error": result.standard_errors[1],
                "covered": interval_contains(result, 1, TRUE_OVB_SLOPE),
            }
        )

ovb_results = pd.DataFrame(ovb_records)
ovb_summary = (
    ovb_results.groupby("specification", sort=False)
    .agg(
        mean_estimate=("estimate", "mean"),
        empirical_sd=("estimate", "std"),
        mean_reported_se=("standard_error", "mean"),
        coverage=("covered", "mean"),
    )
    .reset_index()
)
ovb_summary["bias"] = ovb_summary["mean_estimate"] - TRUE_OVB_SLOPE
display(ovb_summary.round(4))
"""),
    code("""
fig = go.Figure()
for specification in ovb_summary["specification"]:
    values = ovb_results.loc[
        ovb_results["specification"] == specification,
        "estimate",
    ]
    counts, edges = np.histogram(values, bins=36, density=True)
    centers = 0.5 * (edges[1:] + edges[:-1])
    fig.add_scatter(
        x=centers,
        y=counts,
        mode="lines",
        name=specification,
    )
fig.add_vline(x=TRUE_OVB_SLOPE, line_dash="dash", line_color="black")
fig.update_layout(
    title="A covariance change cannot repair omitted-variable bias",
    xaxis_title="Estimated slope",
    yaxis_title="Density",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
`short + naive`と`short + HC1`の係数分布は同じで、interval幅だけが変わる。真の係数を含まない狭いintervalを精密に計算しても、estimand mismatchは解消しない。full specificationが妥当になるのも、ここで $Z$ が観測され、functional formが正しいとDGPで知っているからである。実データではDAG、制度、measurement、negative controlなど別の識別根拠が必要になる。
"""),
    md(r"""
## 7. Robust-inference decision memo

分析前に次を1枚へ固定する。

| 項目 | 記録する内容 |
|---|---|
| estimand | population、outcome、coefficientの意味、unit |
| sampling unit | 独立に抽出・割当・shockを受ける単位 |
| dependence diagnosis | heteroskedastic、time、entity、multi-wayの候補と根拠 |
| covariance choice | primary estimator、HC variant、HAC lag、cluster definition |
| sensitivity | lag、cluster level、few-cluster処理、alternative specification |
| remaining bias | OVB、measurement error、selection、functional-form risk |
| reporting | coefficient、interval、effect unit、sample/cluster数、claim class |

residual plotやautocorrelationは有用な診断だが、検定に通ったことを独立性の証明とはしない。依存構造はデータ生成・割当・市場時刻からも定める。
"""),
    md(r"""
## 8. 失敗モード

- row数をsample sizeと呼び、実際のcluster数を報告しない
- HC、HAC、clusterをrobustnessの強さの順番だと思う
- single seriesを任意の連続blockへ分け、独立clusterが得られたと解釈する
- HAC lagやcluster levelを結果が有意になるまで変更する
- cluster内のshockを許しながらrow-level naive SEを使う
- few clustersでasymptotic normal critical valueだけを信用する
- covarianceを変更したことでOVB、measurement error、selectionが解消したと主張する
- estimator biasとinterval coverageを同じ数値で要約する
"""),
    md(r"""
## 9. 段階別演習

### 基礎

1. HC0とHC1の行列式を実装し、共通libraryと照合せよ。
2. 各DGPのsampling unitと許す依存を1文で定義せよ。
3. covariance typeだけを変えたとき係数が一致することをtestにせよ。

### 標準

4. AR係数とHAC lagのgridを作り、coverageとinterval幅を同時に報告せよ。
5. cluster sizeとcluster数を別々に変え、どちらが漸近近似を改善するか検証せよ。
6. OVB反例で $\operatorname{Cov}(X,Z)$ を変え、short regressionのbiasとHC1 SEを比較せよ。

### 研究

7. few-cluster settingへwild cluster bootstrapを追加し、normal approximationと比較せよ。
8. entityとtimeのtwo-way dependenceを作り、one-way clusterが残すcoverage errorを調べよ。
"""),
    md(r"""
## 10. Exit Criteria

- [ ] coefficient estimateとcovariance estimateを別々に説明できる
- [ ] sampling unitとcluster definitionを明記できる
- [ ] HC、HAC、cluster sandwichのmeatが何を集計するか導出できる
- [ ] heteroskedastic、serial、clustered DGPでcoverageを比較できる
- [ ] estimator bias、reported SE、empirical SD、coverageを別々に報告できる
- [ ] HAC lagとcluster数の感度を示せる
- [ ] few clustersでsmall-sample correctionだけでは十分でないと説明できる
- [ ] robust SEがomitted-variable biasを直さない反例を作れる
"""),
    md(r"""
## 11. 出典

- [White, A Heteroskedasticity-Consistent Covariance Matrix Estimator and a Direct Test for Heteroskedasticity](https://doi.org/10.2307/1912934) — HC covarianceの原著論文
- [Newey and West, A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix](https://www.nber.org/papers/t0055) — Bartlett weightを用いるHAC estimatorの原論文working-paper版
- [Cameron and Miller, A Practitioner's Guide to Cluster-Robust Inference](https://escholarship.org/uc/item/1jq5d0pq) — cluster単位、few clusters、実務上の診断
- [Bertrand, Duflo, and Mullainathan, How Much Should We Trust Differences-In-Differences Estimates?](https://economics.mit.edu/sites/default/files/2022-08/How%20Much%20Should%20We%20Trust%20Differences%20in%20Difference.pdf) — serial correlationがDiD推論へ与える影響
- [statsmodels Statistics Reference](https://www.statsmodels.org/stable/stats.html) — sandwich covarianceを含む公式API参考資料

次章では、正しいcovarianceだけでは因果主張に足りない理由をpotential outcomesとDAGで定式化し、金融announcement studyとcausal panel event studyの境界を分ける。
"""),
]
