"""Builder for notebook 10 — Generalised linear models."""

from nbkit import code, md

cells = [
    md(r"""
# 10. 一般化線形モデル — 指数型分布族から 1 本の道具へ

> 分布とリンク関数を選べば、当てはめの手続きは 1 つで済む。

## この章で分かること

- 二値やカウントの応答に線形回帰を当てると何が壊れるか
- GLM は **分布・リンク関数・線形予測子** の 3 つを選ぶだけであること
- **IRLS** — どの族でも同じ 1 つのループで当てはまること
- 自前実装が `statsmodels` と一致すること(それが信じる根拠になる)
- **過分散** — ポアソン回帰で最も起きやすい失敗
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    datasets, distributions, estimation, glm, intervals, plotting,
    processes, regression, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 線形回帰では足りない

応答が 0 か 1 のとき、$y = X\beta + \varepsilon$ を当てるとどうなるか。
当てはめ値は実数全体を動くので、**確率が 0 未満や 1 超になる**。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 300
x = rng.normal(0, 1.5, n)
y = (rng.random(n) < 1 / (1 + np.exp(-(0.5 + 1.5 * x)))).astype(float)
plotting.link_function_fits(x, y, families=("binomial", "gaussian"))
"""),
    code("""
X = np.column_stack([np.ones(n), x])
linear = glm.irls(X, y, family="gaussian")
pred = X @ linear.params
print(f"線形確率モデルの当てはめ値の範囲: [{pred.min():.4f}, {pred.max():.4f}]")
print(f"  0 未満になった点: {int((pred < 0).sum())} 個")
print(f"  1 超になった点  : {int((pred > 1).sum())} 個")
print("\\n確率のはずが確率になっていない。リンク関数はこれを直す")
"""),
    md(r"""
## 2. GLM の 3 つの構成要素

**定義** 一般化線形モデルは次の 3 つで決まる。

1. **分布** — 指数型分布族(03 章)から選ぶ。応答の性質で決まる
2. **線形予測子** $\eta = X\beta$ — ここは線形回帰と同じ
3. **リンク関数** $g(\mu) = \eta$ — 平均 $\mu$ と $\eta$ をつなぐ

**正準リンク**は、自然母数 $\eta(\theta)$ と線形予測子を一致させる選び方である。
03 章で書いた $\eta(\theta)$ がそのままリンク関数になる。
"""),
    code("""
table = [
    ("gaussian", "恒等 g(mu) = mu", "実数", "1(一定)"),
    ("binomial", "logit g(mu) = log(mu/(1-mu))", "[0, 1]", "mu(1-mu)"),
    ("poisson", "log g(mu) = log(mu)", "非負整数", "mu"),
]
print(f"{'族':>10} {'正準リンク':>32} {'応答の範囲':>12} {'分散関数 V(mu)':>16}")
for row in table:
    print(f"{row[0]:>10} {row[1]:>32} {row[2]:>12} {row[3]:>16}")
print("\\n分散関数が族ごとに決まる = 重み付き最小二乗の重みが決まる(次節)")
"""),
    md(r"""
## 3. IRLS — 全部を同じループで解く

各反復で、リンクを現在の当てはめの周りで 1 次近似する。

$$
z = \eta + \frac{y - \mu}{d\mu/d\eta}
\qquad\text{(作業応答)}
$$

$$
w = \frac{(d\mu/d\eta)^2}{V(\mu)}
\qquad\text{(重み)}
$$

あとは $z$ を $X$ に**重み付き最小二乗**で回帰するだけ。これを収束するまで繰り返す。

正準リンクの場合、この手続きは対数尤度に対する Newton–Raphson 法と**厳密に一致する**。
だから数回で収束する。

反復を 1 つずつ見てみよう。
"""),
    code("""
print(f"{'反復':>6} {'切片':>12} {'傾き':>12} {'逸脱度':>12}")
for it in range(1, 7):
    r = glm.irls(X, y, family="binomial", max_iter=it, tol=0.0)
    print(f"{it:6d} {r.params[0]:12.6f} {r.params[1]:12.6f} {r.deviance:12.6f}")
final = glm.irls(X, y, family="binomial")
print(f"\\n収束: {final.n_iter} 反復   真値 = (0.5, 1.5)")
"""),
    code("""
plotting.irls_convergence(X, y, family="binomial", max_iter=8)
"""),
    md(r"""
## 4. statsmodels と一致するか

本書の IRLS は numpy だけで書いた 40 行ほどのループである。
それを信じてよい理由は、実務標準と一致することである。
"""),
    code("""
import statsmodels.api as sm

mine = glm.irls(X, y, family="binomial")
ref = sm.GLM(y, X, family=sm.families.Binomial()).fit()
print(f"{'':>10} {'本書の IRLS':>16} {'statsmodels':>16} {'差':>12}")
for i, name in enumerate(["切片", "傾き"]):
    print(f"{name:>10} {mine.params[i]:16.10f} {ref.params[i]:16.10f} "
          f"{abs(mine.params[i] - ref.params[i]):12.2e}")
print(f"{'標準誤差':>10} {mine.se[1]:16.10f} {ref.bse[1]:16.10f} "
      f"{abs(mine.se[1] - ref.bse[1]):12.2e}")
print(f"{'逸脱度':>10} {mine.deviance:16.10f} {ref.deviance:16.10f} "
      f"{abs(mine.deviance - ref.deviance):12.2e}")
assert np.allclose(mine.params, ref.params, rtol=1e-8)
assert np.allclose(mine.se, ref.bse, rtol=1e-5)
print("\\n係数と逸脱度は 1e-11 で一致。標準誤差だけ 1e-6 台のずれが残る")
"""),
    md(r"""
### 標準誤差だけずれるのはなぜか

係数と逸脱度が 1e-11 で一致するのに、標準誤差だけ 1e-6 台のずれが残る。
収束が甘いのではない。**共分散をどの重みで計算するか**が違うのである。

`statsmodels` は最後の重み付き最小二乗で使った重みをそのまま共分散に使う。
その重みは**1 つ前の反復の $\mu$** から作られたものである。
本書の実装は収束後の $\mu$ で重みを計算し直す。差は収束判定の許容と同じ桁になる。

確かめてみよう。`statsmodels` 自身の重みを本書の式に入れれば、ぴったり一致するはずである。
"""),
    code("""
from scipy import special

mu_final = special.expit(X @ ref.params)
w_recomputed = mu_final * (1 - mu_final)          # 本書の重み(収束後の mu)
w_statsmodels = np.asarray(ref.model.weights)      # statsmodels の重み(1 つ前の mu)

def se_from_weights(w):
    return np.sqrt(np.diag(np.linalg.pinv((X * w[:, None]).T @ X)))

print(f"重みの最大差 = {np.abs(w_recomputed - w_statsmodels).max():.3e}")
print(f"\\n本書の重みでの標準誤差       = {se_from_weights(w_recomputed)[1]:.10f}")
print(f"statsmodels の重みでの標準誤差 = {se_from_weights(w_statsmodels)[1]:.10f}")
print(f"statsmodels の報告値           = {ref.bse[1]:.10f}")
print("\\n statsmodels の重みを入れると完全に一致する。")
print("どちらかが誤りなのではなく、評価点が違うだけである")
"""),
    md(r"""
数値計算の実装を照合するときは、**どの桁まで一致すべきかを事前に決めておく**必要がある。
「一致しない」と騒ぐ前に、一致しない理由が定式化の差なのか実装の誤りなのかを切り分ける。
ここでは前者だった。
"""),
    md(r"""
## 5. ポアソン回帰 — カウントデータ

$\log \mu = X\beta$ なので、係数は**加算**ではなく**倍率**として読む。
$x$ が 1 増えると期待件数が $e^\beta$ 倍になる。
"""),
    code("""
rng = np.random.default_rng(1)
m = 300
Xp = np.column_stack([np.ones(m), rng.normal(size=m)])
yp = rng.poisson(np.exp(Xp @ np.array([0.7, 0.4]))).astype(float)
fp = glm.irls(Xp, yp, family="poisson")
print(f"係数     = {fp.params.round(6)}   真値 = [0.7, 0.4]")
print(f"標準誤差 = {fp.se.round(6)}")
print(f"逸脱度   = {fp.deviance:.6f}   反復 = {fp.n_iter}")
print(f"\\n傾き {fp.params[1]:.4f} -> 説明変数が 1 増えると期待件数が "
      f"exp({fp.params[1]:.4f}) = {np.exp(fp.params[1]):.4f} 倍になる")
"""),
    md(r"""
## 6. 逸脱度と過分散

**逸脱度**は「飽和モデル(各点を完全に当てるモデル)との対数尤度の差の 2 倍」である。
線形回帰の残差平方和にあたる量で、モデル比較に使う。絶対値自体には意味がない。

より実務的に重要なのが**過分散**である。ポアソン分布は $\mathrm{Var} = \mathrm{E}$ を
仮定しているが、実データはほぼ必ず分散の方が大きい。
そのときポアソン回帰の標準誤差は**小さく出すぎる**。

過分散統計量 $\phi$(ピアソン $\chi^2$ を残差自由度で割ったもの)で検出できる。
"""),
    code("""
rng = np.random.default_rng(4)
k = 2000
Xo = np.column_stack([np.ones(k), rng.normal(size=k)])
mu = np.exp(Xo @ np.array([1.0, 0.5]))

true_poisson = rng.poisson(mu).astype(float)
overdispersed = rng.negative_binomial(2.0, 2.0 / (2.0 + mu)).astype(float)

print(f"{'データ':>20} {'素の分散/平均':>14} {'phi':>10} {'傾きの標準誤差':>16}")
for label, data in [("真のポアソン", true_poisson), ("負の二項(過分散)", overdispersed)]:
    fo = glm.irls(Xo, data, family="poisson")
    phi = glm.dispersion(fo, data, Xo, "poisson")
    print(f"{label:>20} {data.var() / data.mean():14.4f} {phi:10.4f} {fo.se[1]:16.6f}")
print("\\n注意: 素の分散/平均は真のポアソンでも 1 にならない(ここでは 1.81)。")
print("mu 自体が説明変数とともに動くので、その分だけ全体の分散が膨らむ(全分散の法則)。")
print("phi はモデルの当てはめ値で条件付けたうえで測るので、真のポアソンでは 1 に戻る。")
print("\\nphi が 1 から大きく離れたら、標準誤差を sqrt(phi) 倍に補正する必要がある")
"""),
    code("""
# 補正しないとどれだけ楽観的になるか
fo = glm.irls(Xo, overdispersed, family="poisson")
phi = glm.dispersion(fo, overdispersed, Xo, "poisson")
print(f"過分散データでの傾きの推定:")
print(f"  補正なしの標準誤差 = {fo.se[1]:.6f}")
print(f"  sqrt(phi) 倍に補正 = {fo.se[1] * np.sqrt(phi):.6f}   ({np.sqrt(phi):.2f} 倍)")
print(f"\\n補正なしだと信頼区間の幅が {np.sqrt(phi):.2f} 分の 1 になる。")
print("有意でないものが有意に見える")
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
GLM は分布・リンク関数・線形予測子の 3 つを選ぶだけで、当てはめの手続きは共通である。
その共通の手続きが IRLS で、各反復は重み付き最小二乗にすぎない。
分布ごとに別々のアルゴリズムを覚える必要がないのは、
指数型分布族という共通の骨格のおかげである。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
保険の請求件数、ウェブサイトのクリック、設備の故障件数。
いずれもポアソン回帰の出番だが、実データはほぼ必ず過分散である。
過分散を見ずにポアソンを当てると、標準誤差が小さく出て有意が量産される。
当てはめの前に分散と平均の比を見る習慣が、そのまま誤りを防ぐ。
```
"""),
    md(r"""
## 7. 落とし穴

### 完全分離ではロジスティック回帰の係数が発散する

説明変数が応答を完全に決めてしまうと、尤度は上限に**到達しない**。
係数をいくらでも大きくすれば尤度が上がり続けるので、最尤推定量が存在しない。
"""),
    code("""
xs = np.array([-3.0, -2.0, -1.0, 1.0, 2.0, 3.0])
ys = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
Xs = np.column_stack([np.ones(6), xs])
for max_iter in [2, 5, 10, 20, 50]:
    r = glm.irls(Xs, ys, family="binomial", max_iter=max_iter, tol=0.0)
    print(f"反復 {max_iter:3d}: 傾き = {r.params[1]:10.4f}   逸脱度 = {r.deviance:.3e}")
print("\\n傾きが際限なく大きくなり、逸脱度が 0 に向かう。")
print("理論上は最尤推定量が存在せず、傾きは無限大へ発散する。")
print("ここで頭打ちに見えるのは、実装が当てはめ確率を境界から離す")
print("クリップを入れているためである(そうしないと重みが 0 になって計算が壊れる)。")
print("\\n実務では正則化を入れるか、その変数を落とす")
"""),
    md(r"""
### リンク関数の選択はモデルの一部である

「当てはまりが悪いからリンクを変える」のは、モデルを変えることである。
データを見てから選ぶと、その後の p 値は意味を失う(08 章の多重比較と同じ構造)。

### 逸脱度の絶対値には意味がない

「逸脱度 322」だけでは何も言えない。同じデータに当てた別のモデルとの**差**にだけ意味がある。
入れ子になったモデルなら、その差が $\chi^2$ 分布に従う。
"""),
    code("""
# 入れ子モデルの比較: 傾きは要るか
null_fit = glm.irls(Xp[:, :1], yp, family="poisson")
full_fit = glm.irls(Xp, yp, family="poisson")
from scipy import stats

diff = null_fit.deviance - full_fit.deviance
print(f"切片のみ  逸脱度 = {null_fit.deviance:.4f}")
print(f"傾きあり  逸脱度 = {full_fit.deviance:.4f}")
print(f"差        = {diff:.4f}   自由度 1 の chi2 での p 値 = {stats.chi2.sf(diff, 1):.3e}")
print("\\n差にだけ意味がある。絶対値 322 という数字は単独では読めない")
"""),
    md(r"""
## 8. 演習

1. プロビットリンク($g = \Phi^{-1}$)で当てはめ、logit と係数・当てはめ確率を比較せよ。
   どちらが「正しい」と言えるか。
2. 過分散に対する準ポアソン補正(標準誤差を $\sqrt{\phi}$ 倍)を実装し、
   負の二項データでの被覆率が改善することを測れ。
3. 正準リンクの場合に IRLS が Newton–Raphson と一致することを、
   スコア関数とヘッセ行列を書き下して示せ。
4. 露出時間が異なるカウントデータに対して、オフセット項
   $\log \mu = \log(\text{exposure}) + X\beta$ を入れたポアソン回帰を実装せよ。
"""),
]
