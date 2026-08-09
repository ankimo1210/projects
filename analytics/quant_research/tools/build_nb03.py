"""Builder for notebook 03: SVD, PCA, and yield-curve changes."""

from nbkit import code, md

cells = [
    md(r"""
# 03. Week 3 — SVD・PCA・金利カーブ変化

> 主成分は最初からlevel、slope、curvatureという名前を持たない。loadingの形を見て、初めて経済的な仮説を付ける。

## 学習目標

- 固有分解とSVDの関係を説明する
- 中心化したデータ行列からPCAを実装する
- yield levelではなくyield changeへPCAを適用する理由を説明する
- explained varianceと低rank再構成誤差を検証する
- 符号不定性、近接固有値、rolling-windowのsubspace安定性を診断する

## 前提知識

- Week 2の特異値、条件数、直交行列
- 共分散と分散の基礎
- basis pointの換算 $1\,\mathrm{bp}=10^{-4}$
"""),
    code("""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

from quant_textbook import (
    align_component_signs,
    make_yield_change_panel,
    pca_from_svd,
)

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
MATURITIES = (0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0)
"""),
    md(r"""
## 1. 直感とデータ契約 — levelではなくchange

時点 $t$、満期 $\tau_j$ のzero yieldを $y_t(\tau_j)$ とする。本章の入力は

$$
\Delta y_t(\tau_j)=y_t(\tau_j)-y_{t-1}(\tau_j)
$$

を行に並べた行列である。yield levelは強い持続性を持ちやすく、共通trendや標本期間の開始点が分散を支配する。risk factorとして日次変動を圧縮する問いでは、changeが自然な出発点になる。

ただし、forecastやlong-run equilibriumの問いではlevelが必要なこともある。「PCAは常にchangeへ」という規則ではなく、ここでのestimandを明示した選択である。

合成panelの単位はdecimal yield changeで、図だけbasis pointへ変換する。
"""),
    code("""
panel = make_yield_change_panel(
    n_observations=500,
    maturities=MATURITIES,
    noise_std=0.00005,
    seed=RANDOM_SEED,
)
changes = panel.changes.to_numpy()
maturities = panel.changes.columns.to_numpy(dtype=float)

print("shape:", changes.shape)
print("maximum absolute daily change (bp):", np.max(np.abs(changes)) * 1e4)
print("column means (bp):", np.round(changes.mean(axis=0) * 1e4, 4))
"""),
    code("""
fig = go.Figure()
for row_index in range(0, 80, 8):
    fig.add_scatter(
        x=maturities,
        y=changes[row_index] * 1e4,
        mode="lines+markers",
        name=f"observation {row_index}",
    )
fig.update_layout(
    title="Synthetic JGB-like yield-curve changes",
    xaxis_title="Maturity (years)",
    yaxis_title="Yield change (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. PCAをSVDから導く

中心化行列を $X_c=X-\mathbf{1}\bar{x}^\top$ とし、thin SVDを

$$
X_c=U\Sigma V^\top
$$

と書く。標本共分散は

$$
S=\frac{1}{n-1}X_c^\top X_c
=V\frac{\Sigma^2}{n-1}V^\top
$$

だから、loadingは $V$ の列、scoreは $U\Sigma=X_cV$、第 $k$ 成分の分散は

$$
\lambda_k=\frac{\sigma_k^2}{n-1}
$$

である。共分散行列を明示的に作らずSVDを使えば、Week 2と同様に不要な条件数の二乗を避けられる。
"""),
    code("""
pca = pca_from_svd(changes, n_components=5, center=True)

print("explained variance ratio:", np.round(pca.explained_variance_ratio, 4))
print("cumulative ratio:", np.round(np.cumsum(pca.explained_variance_ratio), 4))
print("orthogonality error:", np.linalg.norm(pca.components @ pca.components.T - np.eye(5)))
"""),
    md(r"""
### 2.1 共分散固有分解との一致とscree

SVDと共分散行列の固有分解は、同じ標本PCAを別の経路で計算する。実装契約として、固有値とloadingが数値誤差の範囲で一致することを確認する。ただし、近接固有値では個々の固有ベクトルよりsubspaceの一致を優先する。

scree plotは各成分の標本分散と累積割合を可視化する。肘は成分数の候補であり、hedge誤差や学習外riskまで自動的に最適化する基準ではない。
"""),
    code("""
full_pca = pca_from_svd(changes, n_components=len(maturities), center=True)
centered_changes = changes - changes.mean(axis=0)
sample_covariance = centered_changes.T @ centered_changes / (changes.shape[0] - 1)

eigenvalues, eigenvectors = np.linalg.eigh(sample_covariance)
descending = np.argsort(eigenvalues)[::-1]
eigenvalues = eigenvalues[descending]
eigenvector_rows = eigenvectors[:, descending].T
aligned_eigenvectors, _ = align_component_signs(
    eigenvector_rows,
    full_pca.components,
)

print(
    "maximum eigenvalue disagreement:",
    np.max(np.abs(eigenvalues - full_pca.explained_variance)),
)
print(
    "minimum matched loading similarity:",
    np.min(np.diag(aligned_eigenvectors @ full_pca.components.T)),
)

component_numbers = np.arange(1, len(maturities) + 1)
fig = go.Figure()
fig.add_bar(
    x=component_numbers,
    y=full_pca.explained_variance_ratio,
    name="Individual variance ratio",
)
fig.add_scatter(
    x=component_numbers,
    y=np.cumsum(full_pca.explained_variance_ratio),
    mode="lines+markers",
    name="Cumulative variance ratio",
    yaxis="y2",
)
fig.update_layout(
    title="Scree plot of yield-change PCA",
    xaxis_title="Principal component",
    yaxis={"title": "Individual variance ratio"},
    yaxis2={
        "title": "Cumulative variance ratio",
        "overlaying": "y",
        "side": "right",
        "range": [0.0, 1.05],
    },
    template="plotly_white",
)
fig.show()
"""),
    code("""
fig = go.Figure()
for component_index in range(3):
    fig.add_scatter(
        x=maturities,
        y=pca.components[component_index],
        mode="lines+markers",
        name=f"PC{component_index + 1}",
    )
fig.update_layout(
    title="First three PCA loadings on yield changes",
    xaxis_title="Maturity (years)",
    yaxis_title="Loading",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
loadingは満期方向の重み、scoreは各観測がそのloading方向へどれだけ動いたかである。両者を分けて見るため、最初の120観測についてscoreを時系列表示する。合成データでは潜在factorも既知なので、scoreとの相関行列をreasonableness checkとして併記できる。
"""),
    code("""
latent_factors = panel.factors.to_numpy()
score_factor_correlations = np.corrcoef(
    pca.scores[:, :3].T,
    latent_factors.T,
)[:3, 3:]
print("absolute score-to-latent-factor correlations:")
print(np.round(np.abs(score_factor_correlations), 3))

fig = go.Figure()
for component_index in range(3):
    fig.add_scatter(
        x=np.arange(120),
        y=1e4 * pca.scores[:120, component_index],
        mode="lines",
        name=f"PC{component_index + 1} score",
    )
fig.update_layout(
    title="PCA factor scores for the first 120 observations",
    xaxis_title="Observation",
    yaxis_title="Score (bp)",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
loadingが全満期で同符号・同程度ならlevel-like、短期と長期で符号が異なればslope-like、中期が両端と異なればcurvature-likeと**事後的に**呼べる。番号だけで名称を決めない。

合成generatorにはこの3形状を埋め込んでいるため、回収できるのはreasonableness checkであって市場発見ではない。実データでは満期集合、標本期間、欠損処理に対して解釈が安定するか検証する。
"""),
    md(r"""
## 3. Eckart–Youngと低rank再構成

SVDを大きい特異値から $k$ 個だけ残した $X_k$ は、Frobenius normで最良のrank-$k$近似である。

$$
X_k=U_k\Sigma_kV_k^\top,
\qquad
\lVert X_c-X_k\rVert_F^2=\sum_{j>k}\sigma_j^2
$$

explained variance ratioは「情報の重要性」そのものではなく、この標本での二乗変動の割合である。小さい成分がhedgeやtail eventに重要な可能性は残る。
"""),
    code("""
reconstruction_errors = []
for component_count in range(1, len(maturities) + 1):
    model = pca_from_svd(changes, n_components=component_count, center=True)
    reconstructed = model.inverse_transform()
    reconstruction_errors.append(np.linalg.norm(changes - reconstructed, ord="fro"))

fig = go.Figure(
    go.Scatter(
        x=np.arange(1, len(maturities) + 1),
        y=reconstruction_errors,
        mode="lines+markers",
    )
)
fig.update_layout(
    title="Low-rank reconstruction error",
    xaxis_title="Number of components",
    yaxis_title="Frobenius reconstruction error",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 4. 符号不定性

固有ベクトル $v$ が解なら $-v$ も解である。loadingとscoreを同時に反転すれば再構成は変わらない。

$$
(-s_k)(-v_k)^\top=s_kv_k^\top
$$

したがってrolling PCAで符号が反転しても、それだけでは市場構造の変化ではない。referenceとの内積が正になるよう符号を揃えてから比較する。
"""),
    code("""
flipped_components = pca.components.copy()
flipped_scores = pca.scores.copy()
flipped_components[[0, 2]] *= -1.0
flipped_scores[:, [0, 2]] *= -1.0

aligned_components, aligned_scores = align_component_signs(
    flipped_components,
    pca.components,
    scores=flipped_scores,
)

before = np.diag(flipped_components @ pca.components.T)
after = np.diag(aligned_components @ pca.components.T)
same_reconstruction = np.allclose(
    flipped_scores @ flipped_components,
    aligned_scores @ aligned_components,
)

print("component correlations before:", np.round(before, 3))
print("component correlations after:", np.round(after, 3))
print("same reconstruction:", same_reconstruction)
"""),
    md(r"""
## 5. Rolling安定性 — componentとsubspaceを分ける

固有値が近い2成分は、その2次元subspaceの中で回転できる。個々のloading相関が低くても、spanは安定している場合がある。

最初のwindowだけでreference loading $V_r$ をfitして固定する。window loadingを $V_w$ とすると、$V_wV_r^\top$ の特異値はprincipal angleのcosineになる。最小値が1に近ければ、選んだsubspaceは近い。この比較は各window終了後に利用可能な観測だけを使う。
"""),
    code("""
window_size = 140
step_size = 30
window_ends = []
component_correlations = []
subspace_similarities = []

reference_components = pca_from_svd(
    changes[:window_size],
    n_components=3,
    center=True,
).components
for start in range(0, changes.shape[0] - window_size + 1, step_size):
    stop = start + window_size
    window_pca = pca_from_svd(changes[start:stop], n_components=3, center=True)
    aligned, _ = align_component_signs(window_pca.components, reference_components)
    component_correlations.append(np.diag(aligned @ reference_components.T))
    subspace_singular_values = np.linalg.svd(
        aligned @ reference_components.T,
        compute_uv=False,
    )
    subspace_similarities.append(subspace_singular_values.min())
    window_ends.append(stop)

component_correlations = np.asarray(component_correlations)

fig = go.Figure()
for component_index in range(3):
    fig.add_scatter(
        x=window_ends,
        y=component_correlations[:, component_index],
        mode="lines+markers",
        name=f"PC{component_index + 1} correlation",
    )
fig.add_scatter(
    x=window_ends,
    y=subspace_similarities,
    mode="lines+markers",
    name="3D subspace similarity",
    line={"width": 4, "dash": "dash"},
)
fig.update_layout(
    title="Rolling component and subspace stability",
    xaxis_title="Window end observation",
    yaxis_title="Similarity",
    yaxis_range=[-0.1, 1.05],
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 6. Centeringとstandardization

PCAはscaleに依存する。満期ごとの分散を1へ揃えるとcorrelation PCAに相当し、変動の大きい満期が支配するのを防ぐ。一方で、実際のbp riskの大きさを消す。

- covariance PCA: 元の単位を保持する
- correlation PCA: 各満期の形状を等しく重視する

どちらが正しいかではなく、risk量を圧縮するのか、相関構造を調べるのかで選ぶ。
"""),
    code("""
standard_deviations = changes.std(axis=0, ddof=1)
standardized = (changes - changes.mean(axis=0)) / standard_deviations
correlation_pca = pca_from_svd(standardized, n_components=3, center=True)

fig = go.Figure()
fig.add_scatter(
    x=maturities,
    y=pca.components[0],
    mode="lines+markers",
    name="Covariance PCA PC1",
)
fig.add_scatter(
    x=maturities,
    y=correlation_pca.components[0],
    mode="lines+markers",
    name="Correlation PCA PC1",
)
fig.update_layout(
    title="Normalization changes PCA loadings",
    xaxis_title="Maturity (years)",
    yaxis_title="Loading",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
### 6.1 満期subsetへの感応度

満期を除くと単に列数が減るだけでなく、PCAが解く共分散問題そのものが変わる。共通満期上でfull-sample loadingを正規化し、subset PCAの対応loadingとの内積を測る。同時に、3次元spanのprincipal-angle similarityも確認する。

ここでは同じ標本を使う記述的な感応度分析であり、過去時点のrisk modelではない。本番評価でsubsetを結果に合わせて選ぶと将来情報を取り込むため、入力満期の規則は事前に固定するか、各時点の過去window内だけで選ぶ。
"""),
    code("""
subset_masks = {
    "1y to 20y": (maturities >= 1.0) & (maturities <= 20.0),
    "2y to 15y": (maturities >= 2.0) & (maturities <= 15.0),
}

fig = go.Figure()
for subset_name, subset_mask in subset_masks.items():
    subset_pca = pca_from_svd(
        changes[:, subset_mask],
        n_components=3,
        center=True,
    )
    restricted_reference = pca.components[:3, subset_mask].copy()
    restricted_reference /= np.linalg.norm(restricted_reference, axis=1, keepdims=True)
    aligned_subset, _ = align_component_signs(
        subset_pca.components,
        restricted_reference,
    )
    loading_similarities = np.einsum(
        "ij,ij->i",
        aligned_subset,
        restricted_reference,
    )

    reference_basis, _ = np.linalg.qr(restricted_reference.T, mode="reduced")
    subset_basis, _ = np.linalg.qr(aligned_subset.T, mode="reduced")
    subspace_similarity = np.linalg.svd(
        subset_basis.T @ reference_basis,
        compute_uv=False,
    ).min()

    print(
        subset_name,
        "loading similarities:",
        np.round(loading_similarities, 3),
        "minimum subspace similarity:",
        round(float(subspace_similarity), 3),
    )
    fig.add_bar(
        x=["PC1", "PC2", "PC3"],
        y=loading_similarities,
        name=subset_name,
    )

fig.update_layout(
    title="Maturity-subset sensitivity of matched PCA loadings",
    xaxis_title="Matched component",
    yaxis_title="Loading similarity",
    yaxis_range=[0.0, 1.05],
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 7. 失敗モード — PC番号をfactor名へ直結する

「PC1=level、PC2=slope、PC3=curvature」は経験則であり定義ではない。

- loadingの形を図示せず命名する
- yield levelとchangeを混ぜる
- 符号反転をregime changeと呼ぶ
- 固有値が近いのに個別componentだけを追う
- 全期間でfitしたPCAを過去のrisk modelへ使う
- 欠損満期を将来情報で補間する

時点 $t$ の分析で使うPCAは、時点 $t$ 以前だけでfitする。rolling評価ではsign alignmentとsubspace metricの両方を残す。
"""),
    md(r"""
## 8. 段階別演習

### 基礎

1. $S=X_c^\top X_c/(n-1)$ の固有値が $\sigma_k^2/(n-1)$ になることを示せ。
2. PC1の符号を反転し、再構成が変わらないことを数値確認せよ。
3. 1–5成分の累積explained varianceを表にせよ。

### 標準

4. covariance PCAとcorrelation PCAのloading・scoreを比較し、問いの違いを述べよ。
5. maturity集合から1点ずつ除き、3次元subspace similarityを測れ。
6. rolling window sizeを80、140、250へ変え、安定性と追随性のtrade-offを論じよ。

### 研究

7. `regime_shift_at` を使う合成panelで、component相関とsubspace metricのどちらが先に変化を検知するか調べよ。
8. PCA factorを用いるhedgeの目的関数を定義し、小さいvariance成分を捨てるriskを反例で示せ。
"""),
    md(r"""
## 9. Exit Criteria

- [ ] 中心化行列のSVDからPCAを導出できる
- [ ] yield changeへPCAを使う理由と例外を説明できる
- [ ] loadingを見てからlevel-like、slope-like、curvature-likeと解釈する
- [ ] 共分散固有分解との一致、scree、scoreを数値と図で診断できる
- [ ] 満期subsetでcomponentとsubspaceの感応度を比較できる
- [ ] 符号不定性を補正し、近接固有値ではsubspaceを比較できる
- [ ] rolling fitで未来情報を使わない
"""),
    md(r"""
## 10. 出典

- [NumPy `linalg.svd`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html) — SVDの規約と形状
- [NumPy `linalg.eigh`](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html) — 対称行列の固有分解
- [Federal Reserve: The TIPS Yield Curve and Inflation Compensation](https://www.federalreserve.gov/pubs/feds/2008/200805/) — yield curveの第1–3主成分とlevel/slope/curvature解釈
- [Federal Reserve: A Dynamic Factor Model of the Yield Curve](https://www.federalreserve.gov/pubs/feds/2012/201232/index.html) — level、slope、curvature proxyとmacro interpretation
- [Federal Reserve FEDS 2012-32 Figure Data](https://www.federalreserve.gov/pubs/feds/2012/201232/figure_data.html) — factor proxyの公開データと定義

次章では、PCAで見た低次元構造をcurve basisとして使い、ridgeと固定decayのNelson–Siegelへ進む。
"""),
]
