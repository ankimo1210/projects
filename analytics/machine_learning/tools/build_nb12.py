"""Builder for notebook 12 — Exercise solutions (chapters 01-10)."""

from nbkit import build, code, md

cells = [
    md(r"""
# 12. 演習の解答(01〜10 章)

> 各章の Exercises に対する解答集。計算で示せるものはコード、概念問題は簡潔な解説で答えます。
> 本文は日本語、コードは英語。数値は乱数 seed 固定で再現します。
"""),
    code("""
import numpy as np
import matplotlib.pyplot as plt
from ml_textbook import datasets
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

np.random.seed(0)
print("setup ok")
"""),
    md("""
## 01. 全体像

- **Ex1** `class_sep` を上げると線形モデルでも分離が容易になり精度↑(下のコード)。
- **Ex3** データ数 `n` を増やすと、検証曲線の U 字の底はより **深い木**(高複雑度)側へ動く — データが多いほど過学習しにくいため。
- **Ex4** moons の `noise` が大きいほど境界はぼやけ精度↓(下のコード)。
- **Ex2/Ex5** は 03 章(多項式次数)・07 章(k-means の k)で実機確認する(概念解答)。
"""),
    code("""
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

print("Ex1 — class_sep vs linear CV accuracy")
for sep in [0.5, 1.5, 3.0]:
    Xs, ys = datasets.make_classification_dataset(n=400, class_sep=sep, seed=0)
    print(f"  class_sep={sep}: {cross_val_score(LogisticRegression(), Xs, ys, cv=5).mean():.3f}")

print("Ex4 — moons noise vs tree CV accuracy")
for nz in [0.1, 0.4]:
    Xm, ym = datasets.make_moons_dataset(n=300, noise=nz, seed=0)
    print(f"  noise={nz}: {cross_val_score(DecisionTreeClassifier(max_depth=5, random_state=0), Xm, ym, cv=5).mean():.3f}")
"""),
    md("""
## 02. 前処理・特徴量

- **Ex1** 外れ値が大きいほど StandardScaler の歪みが増す(robust は不変)。
- **Ex2** 決定木はスケール不変なので、スケーリングの有無で精度は実質変わらない(下のコード)。
- **Ex3** 順序のあるカテゴリ(low<mid<high)なら ordinal が妥当。
- **Ex4** Titanic は robust と standard で大差なし(外れ値が支配的でないため)。
- **Ex5** target leakage はノイズを増やすほど相関が下がり CV 精度が現実的な値へ落ちる。
"""),
    code("""
from sklearn.neighbors import KNeighborsClassifier

bc = datasets.load_breast_cancer_dataset()
print("Ex2 — decision tree is scale-invariant; k-NN is not")
print(f"  tree  raw   : {cross_val_score(DecisionTreeClassifier(random_state=0), bc.data, bc.target, cv=5).mean():.3f}")
print(f"  tree  scaled: {cross_val_score(make_pipeline(StandardScaler(), DecisionTreeClassifier(random_state=0)), bc.data, bc.target, cv=5).mean():.3f}")
print(f"  kNN   raw   : {cross_val_score(KNeighborsClassifier(), bc.data, bc.target, cv=5).mean():.3f}")
print(f"  kNN   scaled: {cross_val_score(make_pipeline(StandardScaler(), KNeighborsClassifier()), bc.data, bc.target, cv=5).mean():.3f}")
"""),
    md("""
## 03. 線形モデル

- **Ex1** Ridge の最小テスト RMSE の `alpha` は `RidgeCV` の選択とほぼ一致する。
- **Ex2** Lasso の `alpha` を上げるほど 0 になる係数が増える。
- **Ex5** Diabetes では Ridge ≈ OLS ≳ Lasso(下のコード)。
- **Ex3/Ex4** 次数↑で過学習・`C`↑で境界が急になる(03 章スライダーで確認済み)。
"""),
    code("""
from sklearn.linear_model import LinearRegression, Ridge, Lasso, RidgeCV

db = datasets.load_diabetes_dataset()
print("Ex5 — Diabetes CV R2")
for name, m in [("OLS", LinearRegression()), ("Ridge(1.0)", Ridge(alpha=1.0)), ("Lasso(0.1)", Lasso(alpha=0.1, max_iter=10000))]:
    r2 = cross_val_score(make_pipeline(StandardScaler(), m), db.data, db.target, cv=5, scoring="r2").mean()
    print(f"  {name:11s}: {r2:.3f}")

Xs = StandardScaler().fit_transform(db.data)
print("Ex2 — Lasso zeros grow with alpha:",
      {a: int(np.sum(np.abs(Lasso(alpha=a, max_iter=10000).fit(Xs, db.target).coef_) < 1e-8)) for a in [0.1, 1.0, 5.0]})
"""),
    md("""
## 04. 評価と検証

- **Ex1** 不均衡を強める(0.01)と PR-AUC の方が大きく悪化する(ROC は真陰性に薄められ楽観的)。
- **Ex3** `CalibratedClassifierCV` で GaussianNB の ECE が下がる(下のコード)。
- **Ex5** テストでモデルを選ぶと seed ごとに「最良」が入れ替わり不安定 — だから CV で選ぶ。
- **Ex2/Ex4** は 04 章のスライダー/リークデモで確認済み。
"""),
    code("""
from sklearn.naive_bayes import GaussianNB
from sklearn.calibration import CalibratedClassifierCV
from ml_textbook.metrics import expected_calibration_error, roc_auc, pr_auc

Xtr, Xte, ytr, yte = train_test_split(bc.data, bc.target, test_size=0.4, random_state=0, stratify=bc.target)
raw = GaussianNB().fit(Xtr, ytr)
cal = CalibratedClassifierCV(GaussianNB(), method="isotonic", cv=5).fit(Xtr, ytr)
print("Ex3 — calibration reduces ECE")
print(f"  raw GaussianNB ECE : {expected_calibration_error(yte, raw.predict_proba(Xte)[:, 1]):.3f}")
print(f"  calibrated ECE     : {expected_calibration_error(yte, cal.predict_proba(Xte)[:, 1]):.3f}")

print("Ex1 — rarer positives hurt PR-AUC more than ROC-AUC")
for w in [(0.9, 0.1), (0.99, 0.01)]:
    Xi, yi = datasets.make_imbalanced_classification_dataset(n=4000, weights=w, seed=0)
    s = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xi[:2000], yi[:2000]).predict_proba(Xi[2000:])[:, 1]
    print(f"  pos={w[1]}: ROC-AUC {roc_auc(yi[2000:], s):.3f}  PR-AUC {pr_auc(yi[2000:], s):.3f}")
"""),
    md("""
## 05. 木ベース

- **Ex4** Wine では深さ無制限の RF と制限ありで CV はほぼ同等(RF はバギングで過学習に強い)。
- **Ex5** 不純度重要度と permutation 重要度では上位の順位が入れ替わりうる(下のコード)。
- **Ex1/Ex2/Ex3** 基準(gini/entropy)・木の本数・学習率は 05 章で可視化済み。
"""),
    code("""
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

wine = datasets.load_wine_dataset()
print("Ex4 — Wine RF: depth-limited vs unlimited")
print(f"  max_depth=3 : {cross_val_score(RandomForestClassifier(max_depth=3, n_estimators=300, random_state=0), wine.data, wine.target, cv=5).mean():.3f}")
print(f"  unlimited   : {cross_val_score(RandomForestClassifier(n_estimators=300, random_state=0), wine.data, wine.target, cv=5).mean():.3f}")

rf = RandomForestClassifier(n_estimators=300, random_state=0).fit(Xtr, ytr)
imp_rank = np.array(bc.feature_names)[np.argsort(rf.feature_importances_)[::-1]][:5]
perm = permutation_importance(rf, Xte, yte, n_repeats=10, random_state=0)
perm_rank = np.array(bc.feature_names)[np.argsort(perm.importances_mean)[::-1]][:5]
print("Ex5 — top-5 differ between methods")
print("  impurity   :", list(imp_rank))
print("  permutation:", list(perm_rank))
"""),
    md("""
## 06. SVM とカーネル

- **Ex1** `C` を 1000→1 にするとマージンが広がり、サポートベクトルが増える(下のコード)。
- **Ex4** 同心円は線形 SVM では解けず RBF で解ける(下のコード)。
- **Ex2/Ex3/Ex5** gamma の過学習・kernel 比較・GridSearch は 06 章/10 章で確認。
"""),
    code("""
from sklearn.svm import SVC

Xb, yb = datasets.make_blobs_dataset(n=120, centers=2, cluster_std=2.4, seed=3)
print("Ex1 — support vectors vs C")
for C in [1000, 1]:
    print(f"  C={C}: {len(SVC(kernel='linear', C=C).fit(Xb, yb).support_)} support vectors")

Xc, yc = datasets.make_circles_dataset(n=300, noise=0.08, factor=0.4, seed=0)
print("Ex4 — circles: linear vs RBF kernel")
print(f"  linear: {cross_val_score(SVC(kernel='linear'), Xc, yc, cv=5).mean():.3f}")
print(f"  rbf   : {cross_val_score(SVC(kernel='rbf'), Xc, yc, cv=5).mean():.3f}")
"""),
    md("""
## 07. 教師なし

- **Ex1** k-means は初期重心で収束先(inertia)が変わる=局所解(下のコード、複数 seed)。
- **Ex4** PCA で 10 成分に落としても分類精度はほぼ保てる(下のコード)。
- **Ex5** Isolation Forest の `contamination` を上げると検出数は増えるが ROC-AUC はスコア順位で決まるため大きくは動かない。
- **Ex2/Ex3** エルボー/シルエットの不一致・GMM の共分散型は 07 章で扱った。
"""),
    code("""
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

Xk, _ = datasets.make_blobs_dataset(n=400, centers=4, cluster_std=1.6, seed=2)
inertias = [round(float(KMeans(n_clusters=4, n_init=1, random_state=s).fit(Xk).inertia_), 1) for s in range(5)]
print("Ex1 — k-means inertia varies with init seed (local optima):", inertias)

digits = datasets.load_digits_dataset()
Xd = StandardScaler().fit_transform(digits.data)
full = cross_val_score(LogisticRegression(max_iter=2000), Xd, digits.target, cv=5).mean()
pca10 = cross_val_score(make_pipeline(PCA(n_components=10, random_state=0), LogisticRegression(max_iter=2000)), Xd, digits.target, cv=5).mean()
print(f"Ex4 — digits logistic: 64-dim {full:.3f} vs PCA-10 {pca10:.3f}")
"""),
    md("""
## 08. 時系列

- **Ex1** トレンド `slope=0` にすると、ランダム CV と TimeSeriesSplit の差は縮む(外挿が不要になるため)。
- **Ex2** ラグ数を増やすとウォークフォワード RMSE は一旦改善し、過剰だと頭打ち/悪化(下のコード)。
- **Ex5** レジーム変化後のデータも訓練に含めると RMSE は回復する。
- **Ex3/Ex4** naive ベースライン・予測ホライズンは 08 章で確認。
"""),
    code("""
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, TimeSeriesSplit
from ml_textbook.validation import walk_forward_validation

print("Ex1 — random vs time-split R2 with and without trend")
for slope in [0.0, 0.04]:
    t, y = datasets.make_time_series_trend_seasonality(n=300, slope=slope, seed=0)
    Xt = t.reshape(-1, 1).astype(float)
    rf = RandomForestRegressor(n_estimators=150, random_state=0)
    r = cross_val_score(rf, Xt, y, cv=KFold(5, shuffle=True, random_state=0), scoring="r2").mean()
    ts = cross_val_score(rf, Xt, y, cv=TimeSeriesSplit(5), scoring="r2").mean()
    print(f"  slope={slope}: random {r:.2f}  time-split {ts:.2f}  gap {r - ts:.2f}")

ys = datasets.make_noisy_sine_series(n=400, periods=6, noise=0.2, seed=0)[1]

def lagmat(s, k):
    import pandas as pd
    d = pd.DataFrame({"y": s})
    for L in range(1, k + 1):
        d[f"l{L}"] = d["y"].shift(L)
    return d.dropna()

print("Ex2 — walk-forward RMSE vs n_lags")
for k in [1, 5, 20]:
    d = lagmat(ys, k)
    sc = [r["score"] for r in walk_forward_validation(
        RandomForestRegressor(n_estimators=150, random_state=0),
        d.drop(columns="y").to_numpy(), d["y"].to_numpy(),
        initial=200, horizon=20, metric=lambda a, b: float(np.sqrt(np.mean((a - b) ** 2))))]
    print(f"  n_lags={k}: {np.mean(sc):.3f}")
"""),
    md("""
## 09. 解釈

- **Ex1** 交絡で作った `proxy` を除くと、真の原因 `cause` の係数が大きくなる(proxy が吸っていた分が戻る)。
- **Ex2** permutation の `n_repeats` を増やすと重要度の標準偏差(誤差棒)が小さくなる。
- **Ex3/Ex4/Ex5** PDP の山なり・ICE の広がり・反実仮想は 09 章で確認。
"""),
    code("""
import pandas as pd
from sklearn.linear_model import LinearRegression
from ml_textbook.interpretation import coefficient_table

rng = np.random.default_rng(1)
n = 1500
z = rng.standard_normal(n)
proxy = z + 0.3 * rng.standard_normal(n)
cause = rng.standard_normal(n)
yv = 2.0 * z + 1.5 * cause + 0.3 * rng.standard_normal(n)

with_proxy = make_pipeline(StandardScaler(), LinearRegression()).fit(pd.DataFrame({"proxy": proxy, "cause": cause}), yv)
without = make_pipeline(StandardScaler(), LinearRegression()).fit(pd.DataFrame({"cause": cause}), yv)
print("Ex1 — dropping the confounded proxy changes the 'cause' coefficient")
print(f"  cause coef WITH proxy   : {with_proxy.named_steps['linearregression'].coef_[1]:.3f}")
print(f"  cause coef WITHOUT proxy : {without.named_steps['linearregression'].coef_[0]:.3f}")
"""),
    md("""
## 10. 実践パイプライン

- **Ex2** 通常 CV はチューニングと採点に同じ fold を使うため、ネスト CV よりわずかに楽観的(下のコード)。
- **Ex3** 保存→再読込で予測は完全一致(`Pipeline` は前処理ごと永続化されるため)。
- **Ex1/Ex4/Ex5** モデル種別を含む探索・部分ドリフト・誤差分析は 10 章で扱った。
"""),
    code("""
from ml_textbook import preprocessing, pipelines
from ml_textbook.models import get_logistic_regression

X, y = datasets.make_titanic_like_dataset(n=800, seed=0)
num, cat = preprocessing.split_feature_types(X)
pipe = pipelines.make_full_pipeline(num, cat, get_logistic_regression())
grid = {"model__C": [0.1, 1.0, 10.0]}

from sklearn.model_selection import GridSearchCV, StratifiedKFold
non_nested = GridSearchCV(pipe, grid, cv=5).fit(X, y).best_score_
nested = pipelines.nested_cv_score(pipe, grid, X, y, inner=3, outer=5).mean()
print("Ex2 — non-nested CV is slightly optimistic vs nested")
print(f"  non-nested best CV : {non_nested:.3f}")
print(f"  nested CV          : {nested:.3f}  (gap {non_nested - nested:+.3f})")
"""),
    md("""
## おわりに

演習は「手を動かして数字で確かめる」のが目的です。ここでは代表的な解を示しましたが、
パラメータを変えて挙動が変わる境界を自分で探すと、各章の直感がより強固になります。
本書全体のまとめは 11 章キャップストーンを参照してください。
"""),
]

if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "12_exercise_solutions.ipynb"
    build(cells, str(out))
