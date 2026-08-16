"""Builder for notebook 12 — Capstone: one dataset seen through three lenses."""

from nbkit import code, md

cells = [
    md(r"""
# 12. キャップストーン — 1 つのデータ、3 つの視点

> 同じ回帰問題を頻度論・ベイズ・機械学習で解き、一致する所と割れる所を見る。

## この章で分かること

- **同じ計算が 3 つの意味を持つ** こと — リッジ回帰は正則化でも事前分布でも汎化の道具でもある
- ベイズ事後平均とリッジ回帰が **厳密に一致** し、$\lambda \to 0$ で最小二乗に戻ること
- 3 者が違う答えを出すのは **最小化している量が違う** からであること
- 訓練誤差で勝つことと、真の関数に近いことが別であること
- このデータが analytics の 5 書すべてで共通であること
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    bridge, datasets, distributions, estimation, glm, intervals, plotting,
    processes, regression, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 問題設定

真の関数

$$
f(x) = \sin(1.5 x) + 0.3 x
$$

に正規ノイズ(標準偏差 0.35)を乗せた 40 点を、5 次多項式で当てはめる。

このデータは `linear_algebra` / `neural_net` / `bayesian` / `machine_learning` /
`statistics` の 5 書で **同一の生成器** から作られている。
各書が同じ問題を自分の道具で解いており、`analytics/report` の横断テストが
5 書の数値一致を検証している。
"""),
    code("""
x, y = datasets.make_capstone_dataset(seed=0)
print(f"n = {x.size}   x in [{x.min():.3f}, {x.max():.3f}]   真の関数 f(x) = sin(1.5x) + 0.3x")
plotting.capstone_three_lenses()
"""),
    md(r"""
## 2. 頻度論の視点

母数 $w$ は定数である。最小二乗で点推定し、標準誤差・$t$ 値・$p$ 値を付ける。
問いは「係数はいくつで、その不確実性はどれだけか」である。
"""),
    code("""
from stats_textbook.plotting.bridge import capstone_features

phi = capstone_features(x, degree=5)
fit = regression.ols(phi, y)
print(f"{'次数':>6} {'係数':>10} {'標準誤差':>10} {'t 値':>9} {'p 値':>11}")
for j in range(phi.shape[1]):
    print(f"{j:6d} {fit.params[j]:10.4f} {fit.se[j]:10.4f} "
          f"{fit.tvalues[j]:9.3f} {fit.pvalues[j]:11.4f}")
print(f"\\nR^2 = {fit.r_squared:.4f}   残差の sd = {np.sqrt(fit.sigma2):.4f}(真のノイズ 0.35)")
print(f"p < 0.05 の係数: {int((fit.pvalues < 0.05).sum())} / {fit.pvalues.size} 本")
print(f"係数ベクトルのノルム ||w|| = {np.linalg.norm(fit.params):.4f}")
"""),
    md(r"""
## 3. ベイズの視点

母数に事前分布 $w \sim N(0, \sigma_w^2 I)$ を置く。
尤度が $y \mid w \sim N(\Phi w, \sigma^2 I)$ なら、事後平均は

$$
\hat{w}_{\text{post}} = \left( \frac{\Phi^\top \Phi}{\sigma^2}
+ \frac{I}{\sigma_w^2} \right)^{-1} \frac{\Phi^\top y}{\sigma^2}
$$

これは $\lambda = \sigma^2 / \sigma_w^2$ としたリッジ回帰と **厳密に同じ式** である。
正則化項は、事前分布の別名にすぎない。
"""),
    code("""
sigma, sigma_w = 1.0, 1.0
lam = sigma**2 / sigma_w**2

ridge = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
prec = phi.T @ phi / sigma**2 + np.eye(phi.shape[1]) / sigma_w**2
post_mean = np.linalg.solve(prec, phi.T @ y / sigma**2)

print(f"リッジ(lambda = {lam})   : {ridge.round(6)}")
print(f"ベイズ事後平均            : {post_mean.round(6)}")
print(f"最大差                    : {np.abs(ridge - post_mean).max():.2e}")
print(f"\\n||w||: 最小二乗 {np.linalg.norm(fit.params):.4f} -> ベイズ {np.linalg.norm(ridge):.4f}")
print("事前分布が係数を原点に引き寄せている。これが「正則化」の正体")
"""),
    code("""
print(f"{'lambda':>10} {'||w||':>10} {'最小二乗との最大差':>20}")
for lam_try in [1e-10, 1e-4, 0.01, 1.0, 100.0]:
    w = np.linalg.solve(phi.T @ phi + lam_try * np.eye(phi.shape[1]), phi.T @ y)
    print(f"{lam_try:10.0e} {np.linalg.norm(w):10.4f} {np.abs(w - fit.params).max():20.2e}")
print("\\nlambda -> 0 で最小二乗に戻る。頻度論は「事前分布を置かないベイズ」でもある")
"""),
    md(r"""
## 4. 機械学習の視点

母数の解釈には関心がない。関心があるのは **未見のデータへの予測誤差** である。
$\lambda$ は理屈からではなく、交差検証で選ぶ。
"""),
    code("""
lams = np.logspace(-4, 3, 40)
folds = np.arange(x.size) % 5
cv_err = []
for lam_try in lams:
    err = 0.0
    for f in range(5):
        tr, te = folds != f, folds == f
        w = np.linalg.solve(phi[tr].T @ phi[tr] + lam_try * np.eye(phi.shape[1]), phi[tr].T @ y[tr])
        err += float(((y[te] - phi[te] @ w) ** 2).sum())
    cv_err.append(err / x.size)
best = lams[int(np.argmin(cv_err))]
w_cv = np.linalg.solve(phi.T @ phi + best * np.eye(phi.shape[1]), phi.T @ y)
print(f"交差検証が選んだ lambda = {best:.6f}   (CV MSE = {min(cv_err):.4f})")
print(f"||w|| = {np.linalg.norm(w_cv):.4f}")
print(f"\\n訓練データでの MSE: 最小二乗 {np.mean((y - phi @ fit.params) ** 2):.4f}"
      f"   CV リッジ {np.mean((y - phi @ w_cv) ** 2):.4f}")
print("罰則を強めれば訓練 MSE は必ず悪化する。")
print("交差検証は下端を選んだので、両者はほぼ同じ当てはめになった")
"""),
    md(r"""
交差検証は罰則グリッドの下端($\lambda = 10^{-4}$)を選んだ。
5 次多項式は 40 点をこのノイズ水準で過学習しないので、
「縮めるな」というのが正しい答えである。
ここでは **機械学習の答えが頻度論の答えとほぼ一致する**。

視点の違いが必ず答えの違いになるわけではない。
違いが出るのはモデルが過学習できるときである。次節でそれを測る。
"""),
    md(r"""
## 5. 3 視点の突き合わせ

訓練データでの誤差と、真の関数からの距離を並べる。
真の関数を知っているのは合成データだからであり、実務では測れない量である。
"""),
    code("""
def true_mse(w, degree=5):
    grid = np.linspace(x.min(), x.max(), 500)
    raw = np.vander(x, degree + 1, increasing=True)
    pg = np.vander(grid, degree + 1, increasing=True)
    pg[:, 1:] = (pg[:, 1:] - raw[:, 1:].mean(0)) / raw[:, 1:].std(0)
    return float(np.mean((np.sin(1.5 * grid) + 0.3 * grid - pg @ w) ** 2))

print(f"{'視点':>20} {'||w||':>9} {'訓練 MSE':>10} {'真の関数との MSE':>18}")
for label, w in [("頻度論(最小二乗)", fit.params), ("ベイズ(事後平均)", ridge),
                 ("機械学習(CV リッジ)", w_cv)]:
    print(f"{label:>20} {np.linalg.norm(w):9.4f} "
          f"{np.mean((y - phi @ w) ** 2):10.4f} {true_mse(w):18.4f}")
print("\\n5 次では罰則が損をしている。ベイズ(lambda=1)だけが真の関数から遠い")
"""),
    md(r"""
5 次では、事前分布を置くと **真の関数から遠ざかる**(0.0488 に対して 0.1558)。
$\lambda = 1$ は、この問題に対しては強すぎる事前分布である。
「正則化すれば汎化する」は無条件には成り立たない。

では罰則が得をするのはいつか。モデルが過学習できるときである。
次数を上げて同じ 3 者を測り直す。
"""),
    code("""
def cv_ridge_at(degree):
    pd_ = capstone_features(x, degree=degree)
    errs = []
    for lam_try in lams:
        e = 0.0
        for f in range(5):
            tr, te = folds != f, folds == f
            w = np.linalg.solve(
                pd_[tr].T @ pd_[tr] + lam_try * np.eye(pd_.shape[1]), pd_[tr].T @ y[tr])
            e += float(((y[te] - pd_[te] @ w) ** 2).sum())
        errs.append(e)
    b = float(lams[int(np.argmin(errs))])
    return pd_, b, np.linalg.solve(pd_.T @ pd_ + b * np.eye(pd_.shape[1]), pd_.T @ y)

print("次数を上げると 3 視点が割れる:")
print(f"{'次数':>5} {'最小二乗 ||w||':>15} {'真との MSE':>12} "
      f"{'CV lambda':>11} {'CV ||w||':>10} {'真との MSE':>12}")
for degree in [5, 7, 9, 11]:
    pd_, b, w_d = cv_ridge_at(degree)
    w_ols_d = np.linalg.lstsq(pd_, y, rcond=None)[0]
    print(f"{degree:5d} {np.linalg.norm(w_ols_d):15.2f} {true_mse(w_ols_d, degree):12.4f} "
          f"{b:11.4f} {np.linalg.norm(w_d):10.2f} {true_mse(w_d, degree):12.4f}")
print("\\n過学習できるモデルになって初めて、交差検証は縮めよと言い、そして得をする")
"""),
    md(r"""
読み方。

**一致する所**: ベイズ事後平均とリッジは同じ計算である。
$\lambda \to 0$ で頻度論に戻る。3 者は連続的につながっている。

**割れる所**: 訓練 MSE は罰則が小さいほど良くなる。定義上そうなる。
真の関数との距離は次数に依存する。5 次では罰則が損をし、
高次では最小二乗が壊れて罰則が勝つ。

3 者は違う量を最小化しているので、違う答えを出すのが正しい。
そして **どれが良いかは問題設定で変わる**。
先験的にどれか 1 つを選べる、という主張の方が誤りである。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
3 つの視点は同じ計算に別の意味を与えている。
リッジ回帰は、頻度論には正則化、ベイズには事前分布、機械学習には汎化のための道具に見える。
違う答えが出るのは、最小化している量が違うからであって、どれかが間違っているからではない。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
同じモデルを組んでも、報告すべき数字は目的で変わる。
規制当局に出すなら係数の信頼区間、意思決定を支援するなら事後分布、
本番投入するなら交差検証の予測誤差である。
どれか 1 つだけを見て他を代用させると、答えられない問いに答えたことになる。
```
"""),
    md(r"""
## 6. 姉妹本との接続

同じ 40 点を、analytics の他の 4 書が別の角度から扱っている。

| 教材 | この問題をどう見るか |
|---|---|
| `linear_algebra` | 計画行列の SVD と条件数。なぜ高次の係数が不安定になるか |
| `neural_net` | 勾配降下と重み減衰。リッジを最適化の側から見る |
| `bayesian` | 事後分布の全体。点推定でなく分布そのものを扱う |
| `machine_learning` | モデル選択と汎化。交差検証の設計 |

`analytics/report` の `test_capstone_consistency.py` が、
リッジ・ベイズ事後平均・重み減衰つき勾配降下・`scikit-learn` の Ridge が
同じ係数に到達することを検証している。
主張ではなく、テストが通るかどうかで確かめられる形にしてある。
"""),
    md(r"""
## 7. 演習

1. 次数を 12 に上げて 3 視点の差がどうなるか調べよ。
   訓練 MSE と真の関数との MSE の乖離はどちらに開くか。
2. $\sigma_w$ を 0.1 から 10 まで変えて、事後平均が最小二乗とリッジの間を
   どう動くか追え。$\|w\|$ を $\sigma_w$ の関数として描くとよい。
3. 交差検証の分割数を 2, 5, 10, 40(leave-one-out)と変えて、
   選ばれる $\lambda$ の安定性を測れ。

解答は 13 章にある。
"""),
]
