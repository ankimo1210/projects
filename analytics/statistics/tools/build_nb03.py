"""Builder for notebook 03 — The zoo of distributions."""

from nbkit import code, md

cells = [
    md(r"""
# 03. 分布の動物園 — 覚えるのではなく、つながりを見る

> 主要な分布は独立した暗記項目ではない。少数の操作でつながった一族である。

## この章で分かること

- 分布は関係でつながっていること。覚えるべきは辺であって頂点ではない
- 二項分布には極限が 2 つあり、どちらに向かうかは $p$ の振る舞いが決めること
- $\chi^2$・$t$・$F$ が正規分布からどう作られるか(第Ⅱ部で毎回使う)
- **指数型分布族** という共通の骨格
- **十分統計量** — データを潰しても情報が落ちない場所
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from scipy import stats
from stats_textbook import datasets, distributions, plotting, processes, simulation

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. まず地図を見る

分布を 20 個暗記するのは非効率である。関係を 5 つ覚える方がずっと少ない労力で済む。

辺にカーソルを乗せると、その変換や極限が成り立つ条件が出る。
"""),
    code("""
plotting.relation_graph()
"""),
    md(r"""
辺は 3 種類に分かれる。

- **和をとる**: ベルヌーイ $\to$ 二項、指数 $\to$ ガンマ、正規の二乗和 $\to \chi^2$
- **極限をとる**: 二項 $\to$ ポアソン、二項 $\to$ 正規、$t \to$ 正規
- **比をとる**: 正規 $/\sqrt{\chi^2/\nu} \to t$、$\chi^2$ の比 $\to F$

以下ではこの 3 種類を順に確かめる。
"""),
    md(r"""
## 2. 二項分布の 2 つの極限

$X \sim \mathrm{Binomial}(n, p)$ で $n \to \infty$ とするとき、
$p$ をどう扱うかで行き先が変わる。

- $p$ を固定すると **正規分布** へ(ド・モアブル–ラプラス)。平均 $np$、分散 $np(1-p)$
- $np = \lambda$ を固定して $p \to 0$ とすると **ポアソン分布** へ

同じ出発点から違う場所に着く。「稀な事象を大量に観測する」のがポアソン、
「そこそこの確率の事象を大量に観測する」のが正規である。

ポアソン極限を動かして見よう。$\lambda = 2$ に固定し、$n$ を増やしていく
($p = 2/n$ が自動的に小さくなる)。
"""),
    code("""
plotting.poisson_limit_slider([5, 10, 25, 50, 100, 400], lam=2.0, k_max=12)
"""),
    md(r"""
$n$ が大きくなるにつれて棒(二項)が折れ線(ポアソン)に重なっていく。
凡例の **TV 距離**(全変動距離)がその近さを数値にしたものである。

$$
d_{TV}(P, Q) = \tfrac{1}{2}\sum_k |P(k) - Q(k)|
$$

これは「どんな事象で測っても確率の差はこれ以下」という保証を与える。
ル・カムの定理によれば

$$
d_{TV}\big(\mathrm{Binomial}(n,p),\ \mathrm{Poisson}(np)\big) \le n p^2
$$

$np = \lambda$ を固定すれば $np^2 = \lambda^2 / n \to 0$ である。
上界が実際に効いているか確かめよう。
"""),
    code("""
print(f"{'n':>6} {'p':>10} {'TV 距離':>12} {'上界 n p^2':>12} {'比':>7}")
for n in [5, 10, 25, 50, 100, 400, 2000]:
    p = 2.0 / n
    tv = distributions.binomial_poisson_tv_distance(n, p)
    bound = n * p**2
    print(f"{n:6d} {p:10.5f} {tv:12.6f} {bound:12.6f} {tv / bound:7.3f}")
print("\\nどの n でも TV 距離は上界の下にある(比が 1 未満)")
"""),
    md(r"""
## 3. 正規分布から生まれる 3 つ

第Ⅱ部の検定は、ほぼこの 3 つで回っている。定義から作ってみる。

$Z_1, \dots, Z_\nu$ を独立な標準正規とすると

$$
\chi^2_\nu = \sum_{i=1}^{\nu} Z_i^2,
\qquad
t_\nu = \frac{Z}{\sqrt{\chi^2_\nu / \nu}},
\qquad
F_{\nu_1, \nu_2} = \frac{\chi^2_{\nu_1}/\nu_1}{\chi^2_{\nu_2}/\nu_2}
$$

$t$ 分布は「正規を、独立に推定した標準偏差で割ったもの」である。
分母がぶれる分だけ裾が重くなる。標本分散を使う検定で $t$ が出てくる理由がこれである。

定義どおりに作って、`scipy` の分位点と一致するか確かめよう。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
df, n = 5, 400_000
q = [0.05, 0.25, 0.5, 0.75, 0.95, 0.99]

z = rng.normal(size=(n, df))
chi2_built = (z**2).sum(axis=1)
t_built = rng.normal(size=n) / np.sqrt(chi2_built / df)
f_built = (chi2_built / df) / ((rng.normal(size=(n, 10)) ** 2).sum(axis=1) / 10)

for name, built, ref in [
    ("chi2(5)", chi2_built, stats.chi2(df)),
    ("t(5)", t_built, stats.t(df)),
    ("F(5, 10)", f_built, stats.f(df, 10)),
]:
    print(f"{name}")
    print(f"  実測 {np.quantile(built, q).round(3)}")
    print(f"  理論 {ref.ppf(q).round(3)}")
"""),
    md(r"""
一致する。これらは新しい分布ではなく、正規分布の組み合わせに名前を付けたものである。
"""),
    code("""
# t 分布の裾が正規より重いこと、自由度が上がると正規に近づくこと
print(f"{'自由度':>8} {'P(|T| > 2)':>12}   正規なら {2 * stats.norm.sf(2):.4f}")
for nu in [2, 5, 10, 30, 100, 1000]:
    print(f"{nu:8d} {2 * stats.t.sf(2, nu):12.4f}")
"""),
    md(r"""
自由度 2 では正規の 2 倍以上の確率で $|T| > 2$ が起きる。
小標本で正規の臨界値を使うと、有意だと言いすぎることになる。
"""),
    md(r"""
## 4. 指数型分布族 — 共通の骨格

多くの分布は次の形に書ける。

$$
\log p(x \mid \theta) = \eta(\theta)\, T(x) - A(\eta) + \log h(x)
$$

部品はそれぞれ役割を持っている。

| 部品 | 名前 | 役割 |
|---|---|---|
| $\eta(\theta)$ | 自然母数 | 母数を「素直な座標」に置き直したもの |
| $T(x)$ | 十分統計量 | データのうち $\theta$ について語る部分 |
| $A(\eta)$ | 対数分配関数 | 全体が 1 になるように帳尻を合わせる |
| $h(x)$ | 基底測度 | $\theta$ に依らないデータ側の重み |

本書では、この 4 つを **別々の関数として** 保持している。
組み立てた結果が `scipy` と一致することを確かめよう。
"""),
    code("""
family = distributions.EXPONENTIAL_FAMILIES["poisson"]
x = np.array([0, 1, 2, 5])
theta = 2.5
eta = family.natural_param(theta)

print(f"lambda = {theta}")
print(f"  eta(theta) = log(lambda) = {eta:.6f}")
print(f"  A(eta)     = exp(eta)    = {family.log_partition(eta):.6f}")
print(f"  T(x)       = x           = {family.sufficient_stat(x)}")
print(f"  log h(x)   = -log(x!)    = {family.log_base_measure(x).round(4)}")
print(f"\\n組み立て = {distributions.exponential_family_logpdf(family, theta, x).round(8)}")
print(f"scipy    = {stats.poisson.logpmf(x, theta).round(8)}")
"""),
    code("""
# 4 つの族すべてで一致することを確認
checks = [
    ("bernoulli", 0.3, np.array([0, 1, 1, 0]), lambda x, p: stats.bernoulli.logpmf(x, p)),
    ("poisson", 2.5, np.array([0, 1, 4, 9]), lambda x, m: stats.poisson.logpmf(x, m)),
    ("normal_unit_var", 0.4, np.array([-1.5, 0.0, 2.2]), lambda x, m: stats.norm.logpdf(x, m, 1)),
    ("exponential", 1.7, np.array([0.2, 1.0, 3.3]), lambda x, r: stats.expon.logpdf(x, scale=1 / r)),
]
for name, theta, xs, ref in checks:
    got = distributions.exponential_family_logpdf(distributions.EXPONENTIAL_FAMILIES[name], theta, xs)
    print(f"{name:16s} 最大誤差 = {np.abs(got - ref(xs, theta)).max():.2e}")
"""),
    md(r"""
## 5. 十分統計量 — どこまで潰してよいか

**定義** $T(X)$ が $\theta$ の **十分統計量** であるとは、
$T$ を与えたときの $X$ の条件付き分布が $\theta$ に依らないことをいう。

言い換えると、$T$ さえ知っていれば、生データを捨てても $\theta$ についての情報は失われない。

指数型分布族では $T(x)$ がそのまま十分統計量である。
$n$ 個の独立標本なら、対数尤度は

$$
\sum_{i=1}^n \log p(x_i \mid \theta)
= \eta(\theta) \sum_i T(x_i) - n A(\eta) + \sum_i \log h(x_i)
$$

となり、$\theta$ が絡むのは $\sum_i T(x_i)$ だけ。
だから **06 章の最尤推定量は必ず $\sum_i T(x_i)$ の関数になる**。

実験してみよう。同じ和を持つが中身の違う 2 つの標本で、尤度が $\theta$ について同じ形になるか。
"""),
    code("""
a = np.array([0, 1, 2, 5])      # 和 = 8
b = np.array([2, 2, 2, 2])      # 和 = 8、中身は全く違う
family = distributions.EXPONENTIAL_FAMILIES["poisson"]

print(f"{'lambda':>8} {'標本 a の対数尤度':>18} {'標本 b の対数尤度':>18} {'差':>10}")
for lam in [1.0, 2.0, 3.0, 5.0]:
    la = distributions.exponential_family_logpdf(family, lam, a).sum()
    lb = distributions.exponential_family_logpdf(family, lam, b).sum()
    print(f"{lam:8.1f} {la:18.4f} {lb:18.4f} {la - lb:10.4f}")
print("\\n差は lambda に依らない定数(基底測度の差)。")
print("-> lambda についての情報は和だけが担っている")
"""),
    md(r"""
差は $\lambda$ を変えても一定である。つまり 2 つの尤度は縦にずれているだけで、
**形が同じ**。$\lambda$ をどう選ぶべきかについて、両者はまったく同じことを言う。

生データ 4 個を和 1 個に潰しても、$\lambda$ の推定には何の損もない。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
指数型分布族に属する分布は、データを十分統計量 $T(x)$ に潰しても情報が失われない。
だから推定も検定も $T$ の関数として書ける。
分布ごとに別々の理論を作らずに済むのは、この共通の骨格のおかげである。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
ログ集計で「合計と件数だけ保存し、生ログは捨てる」運用は、
裏で十分統計量の性質に頼っている。
ポアソンや正規を仮定してよい量なら、その 2 つで推定は完全に再現できる。
仮定が崩れる量では、この節約はそのまま情報の損失になる。
```
"""),
    md(r"""
## 6. 落とし穴

### 正規近似を $p$ が極端なときに使う

$np$ や $n(1-p)$ が小さいと二項分布は歪んだままで、正規近似は当たらない。
この場合はポアソン側の極限を使う。
"""),
    code("""
n = 50
print(f"{'p':>8} {'np':>7} {'正規近似の誤差':>16} {'ポアソン近似の誤差':>20}")
for p in [0.02, 0.05, 0.2, 0.5]:
    k = np.arange(0, n + 1)
    exact = stats.binom.pmf(k, n, p)
    norm_approx = stats.norm.pdf(k, n * p, np.sqrt(n * p * (1 - p)))
    pois_approx = stats.poisson.pmf(k, n * p)
    e_norm = 0.5 * np.abs(exact - norm_approx).sum()
    e_pois = 0.5 * np.abs(exact - pois_approx).sum()
    print(f"{p:8.2f} {n * p:7.1f} {e_norm:16.4f} {e_pois:20.4f}")
print("\\np が小さいときはポアソン、大きいときは正規が勝つ")
"""),
    md(r"""
### $t$ 分布の自由度を取り違える

自由度は「分母の $\chi^2$ の自由度」であって標本サイズそのものではない。
1 標本の $t$ 検定なら $n - 1$、回帰なら $n - k$ である。

### 指数型でない分布に同じ理屈を持ち込む

一様分布 $U(0, \theta)$ は指数型分布族に属さない。
台(値をとりうる範囲)が $\theta$ に依存するからである。
このとき十分統計量は最大値 $\max_i X_i$ になり、和ではない。
"""),
    md(r"""
## 7. 演習

1. 幾何分布 $P(X = k) = (1-p)^{k-1} p$ を指数型分布族の形に書き、
   $\eta, T, A, h$ を特定せよ。`scipy.stats.geom` と数値照合すること。
2. $\lambda$ を固定せずに $p$ を固定して $n$ を増やしたとき、
   二項分布は正規に近づく。TV 距離を計算して収束の速さを $p = 0.5$ と $p = 0.05$ で比べよ。
3. $F$ 分布を定義どおり作り、`scipy.stats.f` と分位点を照合せよ。
   $F_{\nu_1,\nu_2}$ と $F_{\nu_2,\nu_1}$ の関係を数値で確かめよ。
4. 一様分布 $U(0,\theta)$ が指数型分布族でないことを、台が $\theta$ に依ることから説明せよ。
   また、この場合の十分統計量が $\max_i X_i$ であることを尤度の形から示せ。
5. 正規分布(平均・分散ともに未知)の十分統計量は 2 次元 $(\sum x_i, \sum x_i^2)$ になる。
   これを指数型分布族の形から導け。
"""),
]
