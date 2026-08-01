"""Builder for notebook 02 — Random variables and expectation."""

from nbkit import code, md

cells = [
    md(r"""
# 02. 確率変数と期待値 — 分布を数値に潰す

> 期待値は無条件に足し算できる。分散はそうではない。この非対称性が独立性の値打ちを決める。

## この章で分かること

- 確率変数は「結果に数を割り当てる関数」であること
- 期待値の線形性は **独立でなくても** 成り立つこと
- 分散の加法性は共分散がゼロのときだけ成り立つこと
- $E[g(X)] \ne g(E[X])$ であること(イェンセンの不等式)
- 条件付き期待値 $E[Y \mid X]$ が二乗誤差を最小にする予測子であること
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import datasets, distributions, plotting, processes, simulation

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 確率変数は関数である

**確率変数** $X$ は標本空間から実数への写像 $X : \Omega \to \mathbb{R}$ である。
サイコロ 2 個の目の和なら、$\Omega$ の要素 $(3, 5)$ に $8$ を割り当てる関数。

「変数」という名前に反して、これは変数ではなく関数である。
ランダムなのは入力の方で、写像そのものは決まっている。

分布は 2 通りに書ける。

- 離散なら **確率質量関数** $p(x) = P(X = x)$
- 連続なら **確率密度関数** $f(x)$、ただし $P(a \le X \le b) = \int_a^b f(x)\,dx$

どちらの場合も **累積分布関数** $F(x) = P(X \le x)$ は定義できる。
連続の場合、$f(x)$ 自体は確率ではない。1 を超えることもある。
確率になるのは積分してからである。
"""),
    md(r"""
## 2. 期待値と分散 — 非対称な 2 つ

**定義**

$$
E[X] = \sum_x x\, p(x)
\quad\text{または}\quad
\int x f(x)\,dx
$$

$$
\mathrm{Var}(X) = E\big[(X - E[X])^2\big] = E[X^2] - (E[X])^2
$$

**主張 1(期待値の線形性)** 任意の確率変数 $X, Y$ と定数 $a, b$ について

$$
E[aX + bY] = a E[X] + b E[Y]
$$

**独立性は要らない。** 和の期待値は常に期待値の和である。

**主張 2(分散の加法性)**

$$
\mathrm{Var}(X + Y) = \mathrm{Var}(X) + \mathrm{Var}(Y) + 2\,\mathrm{Cov}(X, Y)
$$

こちらは $\mathrm{Cov}(X, Y) = 0$ のときにだけ、きれいな加法性になる。

相関 0.8 の 2 変数で、両者の違いを見よう。
"""),
    code("""
x, y = datasets.bivariate_normal(200_000, rho=0.8, seed=RANDOM_SEED)
cov = np.cov(x, y)[0, 1]

print("期待値は独立でなくても足せる:")
print(f"  E[x + y]        = {(x + y).mean():+.4f}")
print(f"  E[x] + E[y]     = {x.mean() + y.mean():+.4f}")
print("\\n分散は共分散の分だけずれる:")
print(f"  Var(x + y)      = {(x + y).var():.4f}")
print(f"  Var(x) + Var(y) = {x.var() + y.var():.4f}")
print(f"  差              = {(x + y).var() - (x.var() + y.var()):.4f}   2*Cov = {2 * cov:.4f}")
"""),
    md(r"""
差はちょうど $2\,\mathrm{Cov}(X,Y)$ に一致する。

正の相関があると和のばらつきは大きくなり、負の相関があると小さくなる。
後者が分散投資の原理である。
"""),
    code("""
print(f"{'相関':>6} {'Var(x+y)':>10} {'Var(x)+Var(y)':>14}")
for rho in [-0.9, -0.5, 0.0, 0.5, 0.9]:
    a, b = datasets.bivariate_normal(200_000, rho=rho, seed=1)
    print(f"{rho:6.1f} {(a + b).var():10.4f} {a.var() + b.var():14.4f}")
print("\\n負の相関では和のばらつきが個々の和より小さくなる")
"""),
    md(r"""
## 3. 同時分布と周辺化

2 つの確率変数を同時に扱うときは **同時分布** $f(x, y)$ を考える。
片方を積分して消すと **周辺分布** になる。

$$
f_X(x) = \int f(x, y)\, dy
$$

周辺化は「$y$ が何であったかを忘れる」操作である。
同時分布を一方向に潰した影が周辺分布だと思えばよい。
"""),
    code("""
x, y = datasets.bivariate_normal(20_000, rho=0.7, seed=1)
plotting.joint_marginal_heatmap(x, y, bins=40)
"""),
    md(r"""
中央のヒートマップが同時分布、右と上の棒が周辺分布である。
同時分布は右上がりに傾いているが、周辺分布はどちらも左右対称になる。
**周辺分布を 2 つ見ても、同時分布は復元できない。** 傾きの情報が落ちているからである。
"""),
    md(r"""
## 4. 共分散と相関 — 相関 0 は独立ではない

$$
\mathrm{Cov}(X, Y) = E\big[(X - E[X])(Y - E[Y])\big],
\qquad
\rho = \frac{\mathrm{Cov}(X, Y)}{\sqrt{\mathrm{Var}(X)\mathrm{Var}(Y)}}
$$

独立ならば $\mathrm{Cov} = 0$ である。**逆は成り立たない。**

相関は「直線的な」関係だけを測る。曲がった関係は見えない。
$U \sim \mathrm{Uniform}(-1, 1)$ と $V = U^2$ で確かめよう。
$V$ は $U$ から完全に決まるので、これ以上ないほど従属である。
"""),
    code("""
rng = np.random.default_rng(2)
u = rng.uniform(-1, 1, 200_000)
v = u**2

print(f"corr(u, v) = {np.corrcoef(u, v)[0, 1]:+.4f}   <- ほぼ 0")
print("\\nしかし u を知れば v の分布は激変する:")
for lo, hi in [(-1.0, -0.9), (-0.1, 0.1), (0.9, 1.0)]:
    sel = (u > lo) & (u < hi)
    print(f"  u in ({lo:+.1f}, {hi:+.1f}) のとき E[v] = {v[sel].mean():.4f}")
print(f"  条件を付けない E[v]          = {v.mean():.4f}")
"""),
    md(r"""
$u$ が両端にあるとき $v$ は 1 に近く、$u$ が 0 付近なら $v$ もほぼ 0。
完全に従属しているのに、相関係数は 0 である。

**相関 0 を独立の証拠に使ってはいけない。**
"""),
    md(r"""
## 5. 変数変換とイェンセンの不等式

$Y = g(X)$ の期待値は、$Y$ の分布を求めなくても計算できる。

$$
E[g(X)] = \int g(x) f(x)\, dx
$$

ここで注意すべきは、一般に

$$
E[g(X)] \ne g(E[X])
$$

であること。$g$ が凸なら $E[g(X)] \ge g(E[X])$、凹なら不等号が逆になる
(**イェンセンの不等式**)。等号は $g$ が線形か $X$ が定数のときだけ。
"""),
    code("""
s = datasets.normal_sample(200_000, mu=2.0, sigma=1.0, seed=3)

print("凸関数 exp:")
print(f"  E[exp(X)] = {np.exp(s).mean():.4f}   >= exp(E[X]) = {np.exp(s.mean()):.4f}")
print("凹関数 log(要 X > 0 なので指数分布で):")
e = datasets.exponential_sample(200_000, rate=1.0, seed=3)
print(f"  E[log(X)] = {np.log(e).mean():+.4f}   <= log(E[X]) = {np.log(e.mean()):+.4f}")
"""),
    md(r"""
実務ではこれが効いてくる。対数収益率の平均を取ってから指数を戻すと、
元の収益率の平均より小さくなる。「平均的な成長率」を求めたつもりが、
別の量を計算していることになる。
"""),
    md(r"""
## 6. 条件付き期待値は最良の予測子である

$X$ を観測した後の $Y$ の平均を **条件付き期待値** $E[Y \mid X]$ という。
これは $X$ の関数であり、したがってそれ自体が確率変数である。

**主張** 二乗誤差 $E[(Y - h(X))^2]$ を最小にする関数 $h$ は $h(X) = E[Y \mid X]$ である。

**証明のスケッチ** 任意の $h$ について
$Y - h(X) = (Y - E[Y \mid X]) + (E[Y \mid X] - h(X))$ と分解する。
第 1 項は $X$ の任意の関数と無相関なので交差項が消え、
二乗誤差は $E[(Y - E[Y\mid X])^2]$ に非負の項が足された形になる。

二変量正規なら $E[Y \mid X = x] = \rho x$ になる。3 つの予測子で競わせよう。
"""),
    code("""
x, y = datasets.bivariate_normal(200_000, rho=0.7, seed=4)

candidates = {
    "E[y|x] = 0.7x  (最良)": 0.7 * x,
    "0.4x  (弱すぎ)": 0.4 * x,
    "1.0x  (強すぎ)": 1.0 * x,
    "y の平均 = 0  (x を無視)": np.zeros_like(y),
}
for name, pred in candidates.items():
    print(f"{name:26s} MSE = {np.mean((y - pred) ** 2):.4f}")
print(f"\\n理論下限 1 - rho^2 = {1 - 0.7**2:.4f}")
"""),
    md(r"""
$0.7x$ が最小で、理論下限 $1 - \rho^2$ に一致する。
係数を上下どちらにずらしても悪化する。

**予測の限界は $\rho$ が決めている。** どんなに賢い関数を持ってきても、
二変量正規では $1 - \rho^2$ より下には行けない。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
期待値の線形性は無条件に成り立つが、分散の加法性は共分散がゼロのときだけ成り立つ。
この非対称性が、独立性の仮定がどこで効いてくるかを決めている。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
ポートフォリオの分散投資は、分散の加法性が崩れることを利益に変える操作である。
相関の低い資産を混ぜると、合計の分散が個々の分散の和より小さくなる。
2008 年に多くの資産の相関が同時に上がったとき、この前提そのものが壊れた。
分散投資は相関の推定に賭けている。
```
"""),
    md(r"""
## 7. 落とし穴

### 相関 0 を独立の証拠にする

§4 で見たとおり、相関は直線関係しか測らない。
非線形な依存関係は相関係数に現れない。

### $E[g(X)]$ と $g(E[X])$ を混同する

平均を取ってから変換するのと、変換してから平均を取るのは違う。
どちらが欲しいのかを、変換の前に決めておく。

### 裾の重い分布で標本平均を鵜呑みにする

期待値が存在しない分布では、標本平均は何にも収束しない。
それでも `np.mean` は必ず数値を返す。
"""),
    code("""
print("コーシー分布の標本平均(seed を変えるたび別の値になる):")
for seed in range(5):
    s = datasets.heavy_tailed_sample(200_000, kind="cauchy", seed=seed)
    print(f"  seed={seed}: 標本平均 = {s.mean():+10.4f}   標本 sd = {s.std():12.2f}")
print("\\n数値は返るが、収束先は存在しない(04 章で扱う)")
"""),
    md(r"""
## 8. 演習

1. $\mathrm{Var}(X - Y)$ を $\mathrm{Var}(X)$, $\mathrm{Var}(Y)$, $\mathrm{Cov}(X, Y)$ で表せ。
   相関が正のとき、差のばらつきは和のばらつきと比べてどうなるか。
2. $X \sim N(\mu, \sigma^2)$ のとき $E[e^X] = e^{\mu + \sigma^2/2}$ を示し、
   $\mu = 2, \sigma = 1$ の数値と照合せよ。イェンセンの不等式が主張する向きと一致するか。
3. 相関 0 だが従属な例を、$V = U^2$ 以外にもう 1 つ作り、数値で確かめよ。
4. $E[Y \mid X]$ が二乗誤差を最小にすることを、本文のスケッチを埋めて示せ。
   交差項が消える理由(繰り返し期待値の法則)を明示すること。
5. 相関 $\rho$ の二変量正規で、$X$ から $Y$ を予測したときの最小二乗誤差が
   $1 - \rho^2$ になることを示し、$\rho$ を変えて数値で確かめよ。
"""),
]
