"""Builder for notebook 06 — Estimation and maximum likelihood."""

from nbkit import code, md

cells = [
    md(r"""
# 06. 推定と最尤法 — データから母数を当てる

> 良い推定量とは何かを先に決めなければ、良い推定量は選べない。

## この章で分かること

- 推定量の良さには 3 つの独立した意味があること(不偏性・一致性・有効性)
- **最尤法** — 観測されたデータを最も起こりやすくする母数を選ぶ
- **Fisher 情報** は対数尤度の尖り具合であり、推定の難しさをそのまま表すこと
- **Cramér–Rao 下限** — どんな不偏推定量もこれより良くはなれない
- **期待情報と観測情報の違い**。一致するのは最尤推定量の上だけである
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    datasets, distributions, estimation, intervals, plotting, processes, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 推定量の良さを定義する

**推定量** は data から母数への関数である。$\hat\theta = T(X_1, \dots, X_n)$。
データがランダムなので、推定量もランダムである。**推定量には分布がある。**

良さの尺度は 3 つあり、互いに独立している。

**定義**

- **不偏性**: $E[\hat\theta] = \theta$。平均的には当たる
- **一致性**: $\hat\theta \xrightarrow{p} \theta$。$n \to \infty$ で真値に収束する
- **有効性**: 分散が小さい。同じ不偏推定量でも、ばらつきの小さい方が良い

不偏でも役に立たない推定量は簡単に作れる。
正規分布の平均を「標本平均」と「最初の 1 個」で推定してみよう。
どちらも不偏である。
"""),
    code("""
def first_obs(s):
    return float(s[0])

print(f"{'推定量':>16} {'平均(真値 2.0)':>16} {'分散':>10}")
results = {}
for name, stat in [("標本平均", np.mean), ("最初の 1 個", first_obs)]:
    hats = simulation.sampling_distribution(
        stat, lambda n, rng: rng.normal(2.0, 1.0, n), n=25, n_reps=20_000, seed=RANDOM_SEED
    )
    results[name] = hats
    print(f"{name:>16} {hats.mean():16.4f} {hats.var():10.4f}")

ratio = results["最初の 1 個"].var() / results["標本平均"].var()
print(f"\\nどちらも不偏。分散は {ratio:.1f} 倍違う = これが有効性の差である")
"""),
    md(r"""
どちらも「平均的には当たる」が、片方は 25 倍ばらつく。
不偏性は最低条件であって、良さの尺度としては弱い。
"""),
    md(r"""
## 2. 最尤法

**尤度** $L(\theta) = \prod_i p(x_i \mid \theta)$ は「この $\theta$ だったとして、
観測されたデータが出る確率」である。$\theta$ の関数として見ている点が重要で、
確率分布ではない($\theta$ について積分しても 1 にならない)。

**最尤推定量** はこれを最大にする $\theta$ である。

$$
\hat\theta_{\mathrm{MLE}} = \arg\max_\theta L(\theta) = \arg\max_\theta \sum_i \log p(x_i \mid \theta)
$$

対数を取る理由は 2 つある。積が和になるので微分しやすく、
数百個の小さな確率を掛けるアンダーフローを避けられる。

ポアソン分布の対数尤度を描いてみよう。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
x = rng.poisson(3.0, 100)
print(f"真の lambda = 3.0   標本平均 = {x.mean():.4f}")
plotting.likelihood_curve("poisson", x)
"""),
    md(r"""
頂点が最尤推定量である。この場合は標本平均に一致している。偶然ではない。

## 3. 03 章の伏線 — なぜ標本平均になるのか

指数型分布族の対数尤度は

$$
\sum_i \log p(x_i \mid \theta) = \eta(\theta) \sum_i T(x_i) - n A(\eta) + \sum_i \log h(x_i)
$$

の形をしている。$\theta$ が絡むのは $\sum_i T(x_i)$ の項だけなので、
**最尤推定量は必ず十分統計量の関数になる**。ポアソンなら $T(x) = x$ で、和すなわち標本平均。

4 つの族すべてで確かめよう。
"""),
    code("""
rng = np.random.default_rng(1)
cases = [
    ("bernoulli", 0.3, (rng.random(500) < 0.3).astype(float), "標本比率"),
    ("poisson", 3.0, rng.poisson(3.0, 500).astype(float), "標本平均"),
    ("normal_unit_var", 1.2, rng.normal(1.2, 1.0, 500), "標本平均"),
    ("exponential", 2.5, rng.exponential(1 / 2.5, 500), "標本平均の逆数"),
]
print(f"{'族':>18} {'真値':>7} {'MLE':>9} {'標準誤差':>10}  閉じた形")
for name, truth, data, closed in cases:
    r = estimation.mle(name, data)
    print(f"{name:>18} {truth:7.2f} {r.estimate:9.4f} {r.se:10.4f}  {closed}")
"""),
    md(r"""
## 4. Fisher 情報 — 尤度の尖り具合

**定義**

$$
I(\theta) = -E\left[\frac{\partial^2}{\partial\theta^2} \log p(X \mid \theta)\right]
$$

対数尤度の曲率(の期待値)である。尖っていれば $\theta$ を少し動かしただけで
尤度が大きく落ちる。つまり **データが $\theta$ について強く語っている**。
平らなら、どの $\theta$ でも同じくらいもっともらしく、決め手がない。

ここで区別すべきものが 2 つある。

- **期待情報** $I(\theta)$ — まだ見ていないデータについての平均。理論的な量
- **観測情報** $-\ell''(\hat\theta)$ — 手元の標本の対数尤度の曲率そのもの

推定量が実際に使えるのは後者である。両者はいつ一致するのか。
"""),
    code("""
rng = np.random.default_rng(1)
lam, n = 2.5, 50
x = rng.poisson(lam, n)
hat = estimation.mle("poisson", x).estimate

def ll(theta):
    return estimation.log_likelihood("poisson", theta, x)

print(f"真値 lambda = {lam}   標本平均(= MLE) = {hat:.4f}\\n")
print(f"{'評価点':>12} {'観測情報':>12} {'期待情報':>12} {'差':>10}")
for label, theta in [("真値で", lam), ("MLE で", hat)]:
    obs = estimation.observed_information(ll, theta)
    exp = estimation.expected_fisher_information("poisson", theta, n)
    print(f"{label:>12} {obs:12.2f} {exp:12.2f} {obs - exp:10.4f}")
print("\\nMLE で評価したときだけ一致する。")
print("真値では、標本平均が真値からずれている分だけ食い違う")
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
Fisher 情報は対数尤度の尖り具合であり、推定の難しさをそのまま表す。
尖っていれば少ないデータで決まり、平らならいくらデータを集めても決まらない。
そして手元にあるのは期待情報ではなく観測情報である。
両者が一致するのは最尤推定量の上だけである。
```
"""),
    md(r"""
## 5. Cramér–Rao 下限

**主張** $\hat\theta$ が $\theta$ の不偏推定量なら

$$
\mathrm{Var}(\hat\theta) \ge \frac{1}{I(\theta)}
$$

**どんなに賢い不偏推定量を設計しても、この下には行けない。**
情報が足りないのであって、工夫が足りないのではない。

最尤推定量はこの下限を漸近的に達成する。見てみよう。
"""),
    code("""
plotting.mle_sampling_distribution("poisson", 3.0, ns=[10, 30, 100, 400], n_reps=3000)
"""),
    code("""
lam = 3.0
print(f"{'n':>6} {'MLE の実測分散':>16} {'Cramer-Rao 下限':>18} {'比':>7}")
for n in [10, 30, 100, 400]:
    hats = simulation.sampling_distribution(
        lambda s: estimation.mle("poisson", s).estimate,
        lambda m, rng: rng.poisson(lam, m).astype(float),
        n=n, n_reps=8000, seed=2,
    )
    bound = estimation.cramer_rao_bound("poisson", lam, n)
    print(f"{n:6d} {hats.var():16.6f} {bound:18.6f} {hats.var() / bound:7.3f}")
print("\\n比が 1 に張り付く = 最尤推定量は漸近的に有効(これ以上良くできない)")
"""),
    md(r"""
## 6. 漸近正規性

さらに強いことが言える。$n$ が大きければ

$$
\sqrt{n}\,(\hat\theta - \theta) \;\xrightarrow{d}\; N\!\left(0, \frac{1}{I_1(\theta)}\right)
$$

つまり最尤推定量は**正規分布に近づき、その分散は Fisher 情報で決まる**。
上の図で、標本分布(棒)が理論曲線(線)に重なっていくのがこれである。

04 章のデルタ法と組み合わせれば、$g(\hat\theta)$ の分布も自動的に出る。
オッズ、対数、比率 — 変換した量の標準誤差はここから来ている。
"""),
    md(r"""
```{admonition} 実社会では
:class: note
A/B テストの必要サンプル数、臨床試験の症例数設計、センサーの校正回数。
いずれも「どれだけ集めれば決まるか」の見積もりで、Fisher 情報がその答えを与える。
逆に、いくら集めても決まらない量があるときは、尤度が平らになっていないかを疑う。
モデルを複雑にしすぎて母数が識別できていない場合がこれにあたる。
```
"""),
    md(r"""
## 7. 落とし穴

### 最尤推定量は不偏とは限らない

正規分布の分散の最尤推定量は $n$ で割る。不偏推定量は $n-1$ で割る。
最尤法は不偏性を目標にしていないので、これは欠陥ではなく仕様である。
"""),
    code("""
sigma2 = 4.0
mle_var = simulation.sampling_distribution(
    lambda s: float(s.var(ddof=0)), lambda n, rng: rng.normal(0, 2.0, n),
    n=10, n_reps=20_000, seed=3,
)
unbiased = simulation.sampling_distribution(
    lambda s: float(s.var(ddof=1)), lambda n, rng: rng.normal(0, 2.0, n),
    n=10, n_reps=20_000, seed=3,
)
print(f"真値 = {sigma2}   n = 10")
print(f"  MLE  (n で割る)   平均 = {mle_var.mean():.4f}   偏り = {mle_var.mean() - sigma2:+.4f}")
print(f"  不偏 (n-1 で割る) 平均 = {unbiased.mean():.4f}   偏り = {unbiased.mean() - sigma2:+.4f}")
print(f"\\nしかし分散は MLE の方が小さい: {mle_var.var():.4f} 対 {unbiased.var():.4f}")
print("不偏性と有効性は両立しないことがある。どちらを取るかは目的次第")
"""),
    md(r"""
### 尤度が多峰なら最適化は局所解に落ちる

本章の 4 つの族では尤度が単峰なので閉じた形で解けたが、
混合モデルや階層モデルでは峰が複数できる。初期値によって答えが変わる。

### 台が母数に依存する場合は Cramér–Rao が使えない

一様分布 $U(0, \theta)$ では、$\theta$ が値のとりうる範囲そのものを決めている。
このとき尤度は $\theta$ について不連続で、微分を前提とした議論が成り立たない。
実際、最尤推定量($\max_i X_i$)の分散は Cramér–Rao 下限を**下回る**。
"""),
    md(r"""
## 8. 演習

1. 指数分布 $p(x \mid \lambda) = \lambda e^{-\lambda x}$ の対数尤度を微分して、
   最尤推定量が $1/\bar X$ になることを示せ。
2. 正規分布の分散の最尤推定量の偏りが $-\sigma^2/n$ であることを示し、
   $n$ を変えて数値で確認せよ。
3. 一様分布 $U(0,\theta)$ の最尤推定量を求めよ。その分散を計算し、
   Cramér–Rao 下限と比較して、なぜ下回れるのかを説明せよ。
4. デルタ法(04 章)を使って $\log\hat\lambda$ の漸近分散を求め、
   シミュレーションで確かめよ。
5. 2 つの正規分布の混合からデータを作り、尤度が 2 峰になることを示せ。
   初期値を変えて最適化し、結果が変わることを確認せよ。
"""),
]
