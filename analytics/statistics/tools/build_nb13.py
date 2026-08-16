"""Builder for notebook 13 — Solutions to the exercises of chapters 01-12."""

from nbkit import code, md

cells = [
    md(r"""
# 13. 演習の解答

01–12 章の演習 54 問の解答。
問題文を 1 行で再掲したうえで、導出を求めるものには式変形を、
測定を求めるものには実行できるコードとその読み方を置いた。

答えだけを書いた箇所は無い。「なぜそうなるか」を必ず添えてある。

| 章 | 問題数 | 章 | 問題数 |
|---|---:|---|---:|
| 01 確率の土台 | 5 | 07 区間推定とブートストラップ | 4 |
| 02 確率変数と期待値 | 5 | 08 仮説検定 | 5 |
| 03 分布の動物園 | 5 | 09 回帰の推測 | 4 |
| 04 極限定理 | 5 | 10 一般化線形モデル | 4 |
| 05 確率過程 | 5 | 11 頻度論とベイズ | 4 |
| 06 推定と最尤法 | 5 | 12 キャップストーン | 3 |
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
    # ---------------------------------------------------------------- 01
    md(r"""
## 01 章 確率の土台
"""),
    md(r"""
### 01-1

> 公理 1–3 だけを使って $P(A \cup B) = P(A) + P(B) - P(A \cap B)$ を示せ。

$A \cup B$ を排反な 2 つに分ける。

$$
A \cup B = A \;\cup\; (B \setminus A), \qquad A \cap (B \setminus A) = \emptyset
$$

加法性(公理 3)より $P(A \cup B) = P(A) + P(B \setminus A)$。
同じ手を $B$ に使うと $B = (B \cap A) \cup (B \setminus A)$ もまた排反分割なので

$$
P(B) = P(A \cap B) + P(B \setminus A)
\;\Longrightarrow\;
P(B \setminus A) = P(B) - P(A \cap B)
$$

代入して $P(A \cup B) = P(A) + P(B) - P(A \cap B)$。

要点は「和集合を **排反な部分に組み替える** こと」である。
公理 3 は排反な場合しか語らないので、非排反の主張は必ずこの組み替えを経由する。
"""),
    md(r"""
### 01-2

> 有病率 0.001 と 0.3 で、感度と特異度のどちらを上げるべきか PPV で比べよ。
"""),
    code("""
def ppv(prevalence, sensitivity, specificity):
    tp = prevalence * sensitivity
    fp = (1 - prevalence) * (1 - specificity)
    return tp / (tp + fp)

print(f"{'有病率':>8} {'基準':>10} {'感度 0.999':>12} {'特異度 0.99':>13}")
for prev in [0.001, 0.3]:
    base = ppv(prev, 0.99, 0.95)
    sens = ppv(prev, 0.999, 0.95)
    spec = ppv(prev, 0.99, 0.99)
    print(f"{prev:8.3f} {base:10.4f} {sens:12.4f} {spec:13.4f}")
print("\\n有病率 0.001 では特異度を上げた方が PPV が 5 倍近くになる。")
print("有病率 0.3 ではどちらも効くが、やはり特異度の方が効く")
"""),
    md(r"""
偽陽性は $(1 - \text{有病率}) \times (1 - \text{特異度})$ から出る。
有病率が低いと右辺の第 1 因子がほぼ 1 なので、偽陽性の量は特異度がほぼ単独で決める。
感度をいくら上げても、分子の真陽性が有病率で頭打ちになっている。

**低有病率のスクリーニングでは特異度に投資する。** これが一般則である。
有病率が上がるほど差は縮まるが、逆転はしない。
"""),
    md(r"""
### 01-3

> 独立な 2 回目の検査で 2 回続けて陽性のときの $P(D \mid ++)$ を求め、
> 1 回目の事後を 2 回目の事前に使えることを乗法定理から確かめよ。
"""),
    code("""
prev, sens, spec = 0.001, 0.99, 0.95

# 一括計算: 2 回とも陽性の尤度は条件付き独立なので二乗になる
num = prev * sens**2
den = num + (1 - prev) * (1 - spec)**2
direct = num / den

# 逐次計算: 1 回目の事後を 2 回目の事前として使う
post1 = ppv(prev, sens, spec)
sequential = ppv(post1, sens, spec)

print(f"1 回陽性の事後   P(D|+)  = {post1:.6f}")
print(f"一括計算         P(D|++) = {direct:.6f}")
print(f"逐次計算         P(D|++) = {sequential:.6f}")
print(f"差                        = {abs(direct - sequential):.2e}")
"""),
    md(r"""
一致する理由は乗法定理そのものである。

$$
P(D \mid ++) = \frac{P(++ \mid D) P(D)}{P(++)}
= \frac{P(+ \mid D)\,P(+ \mid D)\,P(D)}{P(++)}
$$

条件付き独立 $P(++ \mid D) = P(+ \mid D)^2$ を使うと、
$P(+ \mid D)P(D) / P(+)$ すなわち 1 回目の事後が中に現れる。
だから **事後は次の事前になる**。ベイズ更新が逐次的に使えるのはこの構造による。

ただし条件付き独立が必要である。同じ機械の同じ癖で 2 回とも陽性になるなら
$P(++ \mid D^c) > P(+ \mid D^c)^2$ となり、この式は使えない。
"""),
    md(r"""
### 01-4

> 相関 0 だが独立でない 2 つの事象の例を作り、$P(A \cap B) \ne P(A)P(B)$ を数値で確かめよ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 200_000
x = rng.choice([-2, -1, 1, 2], size=n)

A = x > 0           # 符号
B = np.abs(x) == 2  # 大きさ

pa, pb, pab = A.mean(), B.mean(), (A & B).mean()
print(f"P(A) = {pa:.4f}  P(B) = {pb:.4f}")
print(f"P(A ∩ B) = {pab:.4f}   P(A)P(B) = {pa * pb:.4f}   -> ここは一致する")
print(f"相関 corr(1_A, 1_B) = {np.corrcoef(A, B)[0, 1]:.4f}")

# 独立でない例: 符号と「x = 2 かどうか」
C = x == 2
pc, pac = C.mean(), (A & C).mean()
print(f"\\nP(A) = {pa:.4f}  P(C) = {pc:.4f}")
print(f"P(A ∩ C) = {pac:.4f}   P(A)P(C) = {pa * pc:.4f}   -> 一致しない")
print(f"相関 corr(1_A, 1_C) = {np.corrcoef(A, C)[0, 1]:.4f}")
"""),
    md(r"""
指示関数どうしでは相関 0 と独立が一致してしまう
($\mathrm{Cov}(1_A, 1_B) = P(A \cap B) - P(A)P(B)$ そのものだから)。
相関 0 と独立が食い違うのは **2 値でない確率変数** のときである。
"""),
    code("""
u = rng.normal(size=200_000)
v = u**2
print(f"corr(U, U^2) = {np.corrcoef(u, v)[0, 1]:.4f}  -> ほぼ 0")
# 独立なら E[U^2 | U > 1] = E[U^2] のはずである
print(f"E[U^2]            = {v.mean():.4f}")
print(f"E[U^2 | U > 1]    = {v[u > 1].mean():.4f}")
print("\\n条件付き期待値が動くので独立ではない。相関 0 は独立を意味しない")
"""),
    md(r"""
### 01-5

> モンティ・ホールを扉 $n$ 枚に一般化し、変える戦略の勝率を $n$ の式で書いて確かめよ。

最初に当たりを引く確率は $1/n$。外した(確率 $(n-1)/n$)場合、
司会が $n-2$ 枚のヤギを開けるので、残る 1 枚が必ず当たりである。よって

$$
P(\text{変えて勝つ}) = \frac{n-1}{n}, \qquad
P(\text{変えずに勝つ}) = \frac{1}{n}
$$

$n = 3$ で $2/3$、$n$ が大きいほど変える戦略が有利になる。
情報は「司会が知っていて意図的に外れを開けた」という条件付けから来ている。
"""),
    code("""
def monty(n, switch, n_reps=20_000, seed=0):
    rng = np.random.default_rng(seed)
    prize = rng.integers(0, n, n_reps)
    choice = rng.integers(0, n, n_reps)
    if not switch:
        return float((prize == choice).mean())
    # 司会が n-2 枚を開けた後、残る 1 枚に移る。
    # 最初が当たりなら必ず外し、外れなら必ず当たる。
    return float((prize != choice).mean())

print(f"{'n':>5} {'変えない':>10} {'変える':>10} {'理論 (n-1)/n':>14}")
for n_doors in [3, 5, 10, 100]:
    print(f"{n_doors:5d} {monty(n_doors, False):10.4f} {monty(n_doors, True):10.4f} "
          f"{(n_doors - 1) / n_doors:14.4f}")
"""),
    # ---------------------------------------------------------------- 02
    md(r"""
## 02 章 確率変数と期待値
"""),
    md(r"""
### 02-1

> $\mathrm{Var}(X - Y)$ を分散と共分散で表せ。正の相関のとき差のばらつきはどうなるか。

$$
\mathrm{Var}(X - Y) = \mathrm{Var}(X) + \mathrm{Var}(Y) - 2\,\mathrm{Cov}(X, Y)
$$

和のときは符号が $+2\mathrm{Cov}$ になる。したがって $\mathrm{Cov} > 0$ なら
**差のばらつきは和より小さい**。

これは実務でよく効く。前後比較や対応のある差を取ると、
被験者間のばらつき(共通成分)が引き算で消えるので、
同じ標本数でも検出力が上がる。対応のある $t$ 検定が強いのはこの理由による。
"""),
    code("""
x, y = datasets.bivariate_normal(200_000, rho=0.8, seed=RANDOM_SEED)
print(f"Var(X) = {x.var(ddof=1):.4f}   Var(Y) = {y.var(ddof=1):.4f}   "
      f"Cov = {np.cov(x, y, ddof=1)[0, 1]:.4f}")
print(f"Var(X - Y) 実測 = {(x - y).var(ddof=1):.4f}   "
      f"公式 = {x.var(ddof=1) + y.var(ddof=1) - 2 * np.cov(x, y, ddof=1)[0, 1]:.4f}")
print(f"Var(X + Y) 実測 = {(x + y).var(ddof=1):.4f}")
print("\\n正の相関なので、差のばらつきは和のばらつきよりずっと小さい")
"""),
    md(r"""
### 02-2

> $X \sim N(\mu, \sigma^2)$ のとき $E[e^X] = e^{\mu + \sigma^2/2}$ を示し、数値照合せよ。

積分を平方完成する。

$$
E[e^X] = \int e^{x} \frac{1}{\sqrt{2\pi}\sigma}
e^{-\frac{(x-\mu)^2}{2\sigma^2}} dx
$$

指数部は

$$
x - \frac{(x-\mu)^2}{2\sigma^2}
= -\frac{1}{2\sigma^2}\left[ x^2 - 2(\mu + \sigma^2)x + \mu^2 \right]
= -\frac{(x - \mu - \sigma^2)^2}{2\sigma^2} + \mu + \frac{\sigma^2}{2}
$$

残った積分は $N(\mu + \sigma^2, \sigma^2)$ の全確率で 1 なので
$E[e^X] = e^{\mu + \sigma^2/2}$。

イェンセンの不等式は凸関数について $E[g(X)] \ge g(E[X])$ を主張する。
$e^x$ は凸なので $E[e^X] \ge e^{\mu}$ でなければならず、
実際 $e^{\mu + \sigma^2/2} > e^\mu$ となって向きが一致する。
差 $e^{\sigma^2/2}$ はばらつきが生む上乗せである。
"""),
    code("""
mu, sigma = 2.0, 1.0
s = datasets.normal_sample(500_000, mu=mu, sigma=sigma, seed=RANDOM_SEED)
print(f"E[e^X] 実測  = {np.exp(s).mean():.4f}")
print(f"公式         = {np.exp(mu + sigma**2 / 2):.4f}")
print(f"e^E[X]       = {np.exp(mu):.4f}   <- イェンセンの下側")
"""),
    md(r"""
### 02-3

> 相関 0 だが従属な例を $V = U^2$ 以外にもう 1 つ作れ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
theta = rng.uniform(0, 2 * np.pi, 300_000)
u, v = np.cos(theta), np.sin(theta)          # 単位円上の一様点

print(f"corr(U, V) = {np.corrcoef(u, v)[0, 1]:.4f}")
print(f"E[V^2]           = {(v**2).mean():.4f}")
print(f"E[V^2 | |U|>0.9] = {(v[np.abs(u) > 0.9]**2).mean():.4f}")
print("\\nU が大きいと V は 0 に近づく(U^2 + V^2 = 1 なので完全に従属)。")
print("それでも相関は 0 である。相関は線形関係しか測らない")
"""),
    md(r"""
### 02-4

> $E[Y \mid X]$ が二乗誤差を最小にすることを示せ。交差項が消える理由を明示すること。

任意の予測子 $g(X)$ について、$m(X) = E[Y \mid X]$ を挟んで分解する。

$$
E[(Y - g(X))^2] = E[(Y - m(X))^2] + 2E[(Y - m(X))(m(X) - g(X))]
+ E[(m(X) - g(X))^2]
$$

交差項は繰り返し期待値の法則で消える。$X$ で条件付けると
$m(X) - g(X)$ は定数として外に出せて、

$$
E[(Y - m(X))(m(X) - g(X))]
= E\big[\, (m(X) - g(X)) \; E[\,Y - m(X) \mid X\,] \,\big] = 0
$$

内側が $E[Y \mid X] - m(X) = 0$ だからである。したがって

$$
E[(Y - g(X))^2] = E[(Y - m(X))^2] + E[(m(X) - g(X))^2] \ge E[(Y - m(X))^2]
$$

等号は $g = m$ のときに限る。
第 2 項は非負なので、**条件付き期待値からのずれは必ず損になる**。
"""),
    md(r"""
### 02-5

> 相関 $\rho$ の二変量正規で、$X$ から $Y$ を予測した最小二乗誤差が $1 - \rho^2$ になることを示せ。

標準化して $\mathrm{Var}(X) = \mathrm{Var}(Y) = 1$ とすると
$E[Y \mid X] = \rho X$ なので

$$
E[(Y - \rho X)^2] = \mathrm{Var}(Y) - 2\rho\,\mathrm{Cov}(X, Y) + \rho^2 \mathrm{Var}(X)
= 1 - 2\rho^2 + \rho^2 = 1 - \rho^2
$$

$\rho^2$ が「$X$ で説明できた分散の割合」、$1 - \rho^2$ が残りである。
これが単回帰の $R^2$ の正体でもある。
"""),
    code("""
print(f"{'rho':>6} {'残差分散 実測':>14} {'1 - rho^2':>12}")
for rho in [0.0, 0.3, 0.6, 0.9]:
    x, y = datasets.bivariate_normal(200_000, rho=rho, seed=RANDOM_SEED)
    print(f"{rho:6.1f} {((y - rho * x)**2).mean():14.4f} {1 - rho**2:12.4f}")
"""),
    # ---------------------------------------------------------------- 03
    md(r"""
## 03 章 分布の動物園
"""),
    md(r"""
### 03-1

> 幾何分布 $P(X = k) = (1-p)^{k-1}p$ を指数型分布族の形に書き、$\eta, T, A, h$ を特定せよ。

$$
P(X = k) = p\,(1-p)^{k-1}
= \exp\big[\, k \log(1-p) \;-\; \log\tfrac{1-p}{p} \,\big]
$$

指数型分布族の標準形 $h(k)\exp[\eta T(k) - A(\eta)]$ と比べて

| 部品 | 幾何分布 |
|---|---|
| 自然母数 $\eta$ | $\log(1-p)$ |
| 十分統計量 $T(k)$ | $k$ |
| 対数分配関数 $A(\eta)$ | $\log\frac{1-p}{p} = \log\frac{e^\eta}{1 - e^\eta}$ |
| 基底測度 $h(k)$ | $1$ |

$A'(\eta) = E[T] = 1/p$ になることも確かめられる。
"""),
    code("""
from scipy import stats as sps

p = 0.3
k = np.arange(1, 12)
eta = np.log(1 - p)
A = np.log((1 - p) / p)
mine = np.exp(k * eta - A)
print(f"{'k':>4} {'指数型分布族の形':>18} {'scipy.stats.geom':>18}")
for kk, m, s in zip(k, mine, sps.geom.pmf(k, p)):
    print(f"{kk:4d} {m:18.8f} {s:18.8f}")
print(f"\\n最大差 = {np.abs(mine - sps.geom.pmf(k, p)).max():.2e}")
print(f"A'(eta) から E[X] = {1 / p:.4f}、実測平均 = {sps.geom.mean(p):.4f}")
"""),
    md(r"""
### 03-2

> $p$ を固定して $n$ を増やしたときの二項の正規近似を、TV 距離で $p=0.5$ と $p=0.05$ で比べよ。
"""),
    code("""
from scipy import stats as sps

def tv_binom_normal(n, p):
    k = np.arange(0, n + 1)
    pmf = sps.binom.pmf(k, n, p)
    mu, sd = n * p, np.sqrt(n * p * (1 - p))
    # 連続修正つきで正規に離散化する
    approx = sps.norm.cdf(k + 0.5, mu, sd) - sps.norm.cdf(k - 0.5, mu, sd)
    return 0.5 * float(np.abs(pmf - approx).sum())

print(f"{'n':>7} {'TV (p=0.5)':>13} {'TV (p=0.05)':>13}")
for n in [10, 50, 200, 1000, 5000]:
    print(f"{n:7d} {tv_binom_normal(n, 0.5):13.5f} {tv_binom_normal(n, 0.05):13.5f}")
print("\\np = 0.05 は同じ n でも収束が遅い。歪度 (1-2p)/sqrt(np(1-p)) が大きいからである。")
print("目安として np(1-p) > 10 が必要で、p=0.05 なら n > 200 が要る")
"""),
    md(r"""
### 03-3

> $F$ 分布を定義どおり作って `scipy` と照合し、$F_{\nu_1,\nu_2}$ と $F_{\nu_2,\nu_1}$ の関係を確かめよ。

$F_{\nu_1,\nu_2} = \frac{\chi^2_{\nu_1}/\nu_1}{\chi^2_{\nu_2}/\nu_2}$ の逆数は
分子と分母を入れ替えた形なので $1/F_{\nu_1,\nu_2} \sim F_{\nu_2,\nu_1}$。
したがって分位点には

$$
F_{\nu_1,\nu_2,\,\alpha} = \frac{1}{F_{\nu_2,\nu_1,\,1-\alpha}}
$$

という関係がある。片側の表しか無かった時代に使われた関係である。
"""),
    code("""
from scipy import stats as sps

rng = np.random.default_rng(RANDOM_SEED)
nu1, nu2 = 5, 12
f_sim = (rng.chisquare(nu1, 400_000) / nu1) / (rng.chisquare(nu2, 400_000) / nu2)

print(f"{'分位点':>8} {'定義どおり':>12} {'scipy.stats.f':>14}")
for q in [0.25, 0.5, 0.9, 0.95, 0.99]:
    print(f"{q:8.2f} {np.quantile(f_sim, q):12.4f} {sps.f.ppf(q, nu1, nu2):14.4f}")

print(f"\\nF(5,12) の 0.95 分位点          = {sps.f.ppf(0.95, nu1, nu2):.4f}")
print(f"1 / F(12,5) の 0.05 分位点      = {1 / sps.f.ppf(0.05, nu2, nu1):.4f}")
"""),
    md(r"""
### 03-4

> $U(0,\theta)$ が指数型分布族でないことを台の依存から説明し、十分統計量が $\max_i X_i$ であることを示せ。

密度は $p(x \mid \theta) = \frac{1}{\theta} \mathbf{1}\{0 \le x \le \theta\}$。
指数型分布族の形 $h(x)\exp[\eta(\theta)T(x) - A(\theta)]$ では、
$h$ も $\exp$ も $x$ について正なので **密度が 0 になる領域は $\theta$ に依存できない**。
ところがこの分布は $x > \theta$ で 0 になるので、台が母数に依存する。よって当てはまらない。

尤度は

$$
L(\theta) = \prod_i \frac{1}{\theta}\mathbf{1}\{x_i \le \theta\}
= \frac{1}{\theta^n} \mathbf{1}\{\max_i x_i \le \theta\}
$$

データは $\max_i x_i$ を通してしか $\theta$ に触れない。
因子分解定理より $\max_i X_i$ が十分統計量である。
"""),
    md(r"""
### 03-5

> 正規分布(平均・分散とも未知)の十分統計量が $(\sum x_i, \sum x_i^2)$ になることを導け。

$$
p(x \mid \mu, \sigma^2) = \frac{1}{\sqrt{2\pi}\sigma}
\exp\left[ -\frac{x^2}{2\sigma^2} + \frac{\mu x}{\sigma^2}
- \frac{\mu^2}{2\sigma^2} \right]
$$

指数の中で $x$ に触れているのは $x$ と $x^2$ の 2 項だけである。
自然母数を $\eta = \left(\frac{\mu}{\sigma^2},\, -\frac{1}{2\sigma^2}\right)$、
十分統計量を $T(x) = (x, x^2)$ と取れば標準形になる。

$n$ 個の積を取ると指数は $\eta_1 \sum x_i + \eta_2 \sum x_i^2$ となるので、
十分統計量は $(\sum x_i, \sum x_i^2)$ の 2 次元である。
母数が 2 つあるので次元も 2 になる。
"""),
    # ---------------------------------------------------------------- 04
    md(r"""
## 04 章 極限定理
"""),
    md(r"""
### 04-1

> 歪度の大きい分布で、標本平均が正規に十分近づく $n$ を KS 統計量で決めよ。
"""),
    code("""
from scipy import stats as sps

def ks_of_mean(sampler, n, n_reps=4000, seed=0):
    means = simulation.sampling_distribution(np.mean, sampler, n=n, n_reps=n_reps, seed=seed)
    z = (means - means.mean()) / means.std(ddof=1)
    return float(sps.kstest(z, "norm").statistic)

lognormal = lambda m, rng: rng.lognormal(0.0, 1.0, m)
exponential = lambda m, rng: rng.exponential(1.0, m)

print(f"{'n':>6} {'対数正規 KS':>13} {'指数 KS':>11}")
for n in [2, 5, 10, 30, 100, 300]:
    print(f"{n:6d} {ks_of_mean(lognormal, n):13.4f} {ks_of_mean(exponential, n):11.4f}")

skew_ln = float(sps.lognorm.stats(1.0, moments="s"))
print(f"\\n対数正規(sigma=1) の歪度 = {skew_ln:.3f}、指数分布の歪度 = 2.000")
print("歪度が大きいほど収束が遅い。KS < 0.02 に達するのは")
print("指数なら n = 30 前後、対数正規は n = 300 でもまだ届かない")
"""),
    md(r"""
歪度 $\gamma$ の分布の標本平均は、Edgeworth 展開の主要項が $\gamma/\sqrt{n}$ で減る。
つまり **必要な $n$ は歪度の 2 乗に比例する**。
対数正規($\gamma \approx 6.18$)が指数($\gamma = 2$)の約 10 倍かかるのはこの比である。
"""),
    md(r"""
### 04-2

> パレート $\alpha = 1.5$(分散なし)と $\alpha = 2.5$ で中心極限定理が成り立つか確かめよ。
"""),
    code("""
from scipy import stats as sps

def scaled_mean_ks(alpha, n, n_reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    draws = rng.pareto(alpha, size=(n_reps, n)) + 1.0
    means = draws.mean(axis=1)
    z = (means - np.median(means)) / (means.std(ddof=1) + 1e-300)
    return float(sps.kstest(z, "norm").statistic)

print(f"{'n':>6} {'alpha=1.5 (分散なし)':>22} {'alpha=2.5 (分散あり)':>22}")
for n in [10, 100, 1000, 10_000]:
    print(f"{n:6d} {scaled_mean_ks(1.5, n):22.4f} {scaled_mean_ks(2.5, n):22.4f}")
print("\\nalpha=2.5 は n とともに正規に近づく。alpha=1.5 は近づかない。")
print("中心極限定理は分散の存在を要求する。平均だけでは足りない")
"""),
    md(r"""
$\alpha \le 2$ のパレートは分散を持たないので、標本平均は正規ではなく
**安定分布** に収束する(一般化中心極限定理)。
収束先が違うので、いくら $n$ を増やしても正規にはならない。

実務上の含意ははっきりしている。裾が重い量(損失、待ち時間、都市人口)では
「$n$ を増やせば正規」という前提を置いてはいけない。
"""),
    md(r"""
### 04-3

> デルタ法で $\sqrt{\hat p}$ の漸近分散を求め、$p \to 0$ で近似が悪くなる理由を述べよ。

$\hat p$ は $\mathrm{AN}\!\left(p, \frac{p(1-p)}{n}\right)$。
$g(p) = \sqrt{p}$ に対し $g'(p) = \frac{1}{2\sqrt{p}}$ なので、デルタ法より

$$
\mathrm{Var}(\sqrt{\hat p}) \approx g'(p)^2 \cdot \frac{p(1-p)}{n}
= \frac{1}{4p} \cdot \frac{p(1-p)}{n}
= \frac{1-p}{4n}
$$

$p$ が消えるのが面白いところで、これが分散安定化変換の一例である。

$p \to 0$ で悪くなる理由は 2 つある。第 1 に $g'(p) = 1/(2\sqrt p) \to \infty$ なので、
$\hat p$ のわずかな揺らぎが大きく増幅され、1 次のテイラー近似が効かない。
第 2 に $\hat p \ge 0$ という境界が近いので、$\hat p$ 自身の正規近似も破れている。
"""),
    code("""
print(f"{'p':>7} {'n':>6} {'実測 Var':>12} {'(1-p)/(4n)':>12} {'比':>7}")
for p in [0.5, 0.1, 0.01]:
    for n in [50, 500]:
        sampler = lambda m, rng, _p=p: (rng.random(m) < _p).astype(float)
        stat = simulation.sampling_distribution(
            lambda s: np.sqrt(s.mean()), sampler, n=n, n_reps=8000, seed=0)
        emp, approx = stat.var(ddof=1), (1 - p) / (4 * n)
        print(f"{p:7.2f} {n:6d} {emp:12.6f} {approx:12.6f} {emp / approx:7.2f}")
print("\\np = 0.5 では比が 1 に近い。p = 0.01, n = 50 では大きく外れる")
"""),
    md(r"""
### 04-4

> 概収束はするが確率収束が遅い例、確率収束はするが概収束しない例をそれぞれ作れ。

**概収束するが遅い例**: $X_n = \max(U_1, \dots, U_n)$、$U_i \sim U(0,1)$。
単調増加で上に有界なので概収束する(極限は 1)。
しかし $P(|X_n - 1| > \varepsilon) = (1-\varepsilon)^n$ で、
$\varepsilon$ が小さいと減りが遅い。

**確率収束するが概収束しない例**: 典型的な「動く区間」の列である。
$[0,1]$ 上の一様分布で、$n = 2^k + j$($0 \le j < 2^k$)に対し

$$
X_n = \mathbf{1}\left\{ U \in \left[\tfrac{j}{2^k}, \tfrac{j+1}{2^k}\right) \right\}
$$

とすると $P(X_n = 1) = 2^{-k} \to 0$ なので確率収束するが、
どの $U$ についても $X_n = 1$ が無限回起きるので概収束しない。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
u = rng.random(20_000)

print("概収束するが遅い例: X_n = max(U_1..U_n)")
print(f"{'n':>7} {'P(|X_n - 1| > 0.01)':>22} {'理論 0.99^n':>13}")
for n in [10, 100, 500, 1000]:
    draws = rng.random((5000, n)).max(axis=1)
    print(f"{n:7d} {float((np.abs(draws - 1) > 0.01).mean()):22.4f} {0.99**n:13.4f}")

print("\\n確率収束するが概収束しない例: 動く区間")
print(f"{'n':>7} {'k':>4} {'P(X_n = 1)':>12} {'2^-k':>9}")
for n in [1, 3, 7, 15, 31, 63]:
    k = int(np.floor(np.log2(n)))
    j = n - 2**k
    hit = float(((u >= j / 2**k) & (u < (j + 1) / 2**k)).mean())
    print(f"{n:7d} {k:4d} {hit:12.4f} {2.0**-k:9.4f}")
print("\\n確率は 0 に行くが、各点では 1 が無限回戻ってくる")
"""),
    md(r"""
### 04-5

> 走る平均の跳び幅を監視して裾の重い分布を検出する手続きを設計し、誤検出率と検出率を測れ。

**設計**: 走る平均 $\bar X_k$ の 1 標本あたりの跳び

$$
\Delta_k = |\bar X_k - \bar X_{k-1}| = \frac{|X_k - \bar X_{k-1}|}{k}
$$

を見る。分散が有限なら $k\Delta_k$ は概ね一定のスケールに収まるが、
裾が重いと突出した $k\Delta_k$ が現れる。
そこで $\max_k k\Delta_k$ を標本の四分位範囲で正規化した量を統計量に取り、
正規分布での分布から閾値を決める。
"""),
    code("""
def tail_alarm_statistic(sample):
    x = np.asarray(sample, dtype=float)
    run = np.cumsum(x) / np.arange(1, x.size + 1)
    jumps = np.abs(np.diff(run)) * np.arange(2, x.size + 1)
    iqr = float(np.subtract(*np.percentile(x, [75, 25])))
    return float(jumps.max() / max(iqr, 1e-12))

n, n_reps = 500, 2000
null = simulation.sampling_distribution(
    tail_alarm_statistic, datasets.SAMPLERS["normal"], n=n, n_reps=n_reps, seed=0)
threshold = float(np.quantile(null, 0.95))
print(f"閾値(正規のもとで 95 パーセンタイル) = {threshold:.3f}\\n")

print(f"{'分布':>12} {'警報率':>10} {'意味':>16}")
for name in ["normal", "uniform", "exponential", "cauchy"]:
    stat = simulation.sampling_distribution(
        tail_alarm_statistic, datasets.SAMPLERS[name], n=n, n_reps=n_reps, seed=1)
    rate = float((stat > threshold).mean())
    label = "誤検出" if name in ("normal", "uniform") else "検出"
    print(f"{name:>12} {rate:10.4f} {label:>16}")
print("\\nコーシーはほぼ確実に検出でき、正規・一様の誤検出は名目 5% 前後に収まる。")
print("指数分布は裾が軽いので検出されない。これは仕様どおりである")
"""),
    # ---------------------------------------------------------------- 05
    md(r"""
## 05 章 確率過程
"""),
    md(r"""
### 05-1

> 3 状態のマルコフ連鎖の定常分布を手計算で解き、`stationary()` と照合せよ。

$\pi P = \pi$ と $\sum \pi_i = 1$ を連立させる。
$P$ の 1 列を落として正規化条件で置き換えれば、3 元 1 次方程式になる。
下では線形方程式として直接解き、固有ベクトルによる `stationary()` と突き合わせている。
"""),
    code("""
P = np.array([
    [0.7, 0.2, 0.1],
    [0.3, 0.5, 0.2],
    [0.2, 0.3, 0.5],
])
chain = processes.MarkovChain(P, states=("晴", "曇", "雨"))

# pi (P - I) = 0 の最後の式を sum(pi) = 1 で置き換えて解く
A = np.vstack([(P.T - np.eye(3))[:-1], np.ones(3)])
b = np.array([0.0, 0.0, 1.0])
pi_manual = np.linalg.solve(A, b)

print(f"手計算(連立方程式) : {pi_manual.round(6)}")
print(f"stationary()       : {chain.stationary().round(6)}")
print(f"最大差             : {np.abs(pi_manual - chain.stationary()).max():.2e}")
print(f"\\n100 歩後の分布     : {chain.distribution_after(100, np.array([1.0, 0.0, 0.0])).round(6)}")
print("出発点によらず定常分布に落ち着く(既約かつ非周期だから)")
"""),
    md(r"""
### 05-2

> 可約な連鎖で `stationary()` が何を返すか調べ、なぜ意味がないか説明せよ。
"""),
    code("""
# 2 つの閉じたクラス {0,1} と {2,3} を持つ連鎖
Q = np.array([
    [0.6, 0.4, 0.0, 0.0],
    [0.5, 0.5, 0.0, 0.0],
    [0.0, 0.0, 0.3, 0.7],
    [0.0, 0.0, 0.8, 0.2],
])
red = processes.MarkovChain(Q)
print(f"stationary()                 : {red.stationary().round(6)}")
print(f"クラス {{0,1}} から出発 100 歩 : {red.distribution_after(100, np.array([1.0, 0, 0, 0])).round(6)}")
print(f"クラス {{2,3}} から出発 100 歩 : {red.distribution_after(100, np.array([0, 0, 1.0, 0])).round(6)}")
print("\\n出発点で行き先が変わる。定常分布は 1 つに決まらない")
"""),
    md(r"""
この連鎖には定常分布が **無数にある**。
$\pi^{(1)} = (5/9, 4/9, 0, 0)$ と $\pi^{(2)} = (0, 0, 8/15, 7/15)$ の
任意の凸結合 $\alpha \pi^{(1)} + (1-\alpha)\pi^{(2)}$ がすべて $\pi P = \pi$ を満たす。

`stationary()` は固有値 1 の固有ベクトルを 1 本返すだけなので、
この族から数値誤差で選ばれた 1 つが返る。値そのものに意味は無い。

時間平均は出発したクラスの定常分布に収束する。
エルゴード性($\pi$ が一意で時間平均が空間平均に一致する)には
**既約性** が要る。可約な連鎖ではまず既約なクラスに分解してから考える。
"""),
    md(r"""
### 05-3

> 正規増分のランダムウォークでも位置の sd が $\sqrt{t}$ になることを確かめ、
> 増分を裾の重いものに変えるとどうなるか調べよ。
"""),
    code("""
print(f"{'t':>6} {'Rademacher sd':>15} {'正規増分 sd':>13} {'sqrt(t)':>10}")
for t in [25, 100, 400, 1600]:
    rade = processes.random_walk(n_steps=t, n_paths=4000, step="rademacher", seed=0)[:, -1]
    norm = processes.random_walk(n_steps=t, n_paths=4000, step="normal", seed=0)[:, -1]
    print(f"{t:6d} {rade.std(ddof=1):15.3f} {norm.std(ddof=1):13.3f} {np.sqrt(t):10.3f}")

rng = np.random.default_rng(RANDOM_SEED)
print(f"\\n{'t':>6} {'コーシー増分の IQR':>20} {'sqrt(t) との比':>16}")
for t in [25, 100, 400, 1600]:
    pos = rng.standard_cauchy((4000, t)).sum(axis=1)
    iqr = float(np.subtract(*np.percentile(pos, [75, 25])))
    print(f"{t:6d} {iqr:20.2f} {iqr / np.sqrt(t):16.2f}")
print("\\n分散が有限なら増分の分布によらず sd は sqrt(t)。")
print("コーシーでは散らばりが t に比例して増える(sqrt(t) ではない)。")
print("これは 04 章の安定分布と同じ理由である")
"""),
    md(r"""
### 05-4

> 非一様ポアソン過程 $\lambda(t) = 5 + 4\sin(2\pi t/24)$ に一様ポアソンを当てはめ、何がどれだけ外れるか測れ。
"""),
    code("""
def nonhomogeneous_counts(t_max=24.0, bins=24, n_reps=3000, seed=0):
    rng = np.random.default_rng(seed)
    edges = np.linspace(0.0, t_max, bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    lam = 5 + 4 * np.sin(2 * np.pi * centers / 24)
    return rng.poisson(lam, size=(n_reps, bins)), lam

counts, lam_true = nonhomogeneous_counts()
lam_hat = counts.mean()
print(f"当てはめた一様強度 lambda_hat = {lam_hat:.4f}(真の平均 5.0)")
print(f"\\n{'時刻':>6} {'真の強度':>10} {'観測平均':>10} {'一様の予測':>12} {'ずれ':>8}")
for h in [0, 3, 6, 12, 18, 21]:
    print(f"{h:6d} {lam_true[h]:10.3f} {counts[:, h].mean():10.3f} "
          f"{lam_hat:12.3f} {counts[:, h].mean() - lam_hat:8.3f}")

total = counts.sum(axis=1)
print(f"\\n1 日合計: 平均 {total.mean():.2f}   分散 {total.var(ddof=1):.2f}")
print(f"一様ポアソンなら平均 = 分散のはず。比 = {total.var(ddof=1) / total.mean():.3f}")
print("\\n合計だけ見ると一様との区別がつかない(比がほぼ 1)。")
print("外れるのは時刻ごとの強度で、ピーク時 6 時に 1.8 件、谷の 18 時に -1.8 件ずれる")
"""),
    md(r"""
重要なのは **どこを見ると気づけないか** である。
1 日の合計件数は一様ポアソンでも非一様ポアソンでも同じ Poisson になるので、
合計だけを監視していると非定常性を見逃す。
時刻別に分けて初めて $\pm 4$ の変動が見える。

実務ではコールセンターの人員配置がこれで失敗する。
1 日の総呼数が予測どおりでも、ピーク時の待ち行列は破綻する。
"""),
    md(r"""
### 05-5

> 指数分布以外に無記憶性を持つ連続分布が存在しないことを示せ。

生存関数を $S(t) = P(X > t)$ とおくと、無記憶性は

$$
S(s + t) = S(s)\,S(t) \qquad \forall\, s, t \ge 0
$$

これはコーシーの関数方程式の乗法版である。
$g(t) = \log S(t)$ と置くと $g(s+t) = g(s) + g(t)$ となり、
$S$ が右連続かつ単調(生存関数なので自動的に満たす)であることから
**可測な解は線形に限る**、すなわち $g(t) = -\lambda t$。したがって

$$
S(t) = e^{-\lambda t}
$$

で指数分布に決まる。$\lambda > 0$ は $S$ が減少することから従う。

可測性を落とすと(選択公理を使って)病的な解が作れるが、
確率分布としては使えない。離散版では幾何分布が対応物になる。
"""),
    # ---------------------------------------------------------------- 06
    md(r"""
## 06 章 推定と最尤法
"""),
    md(r"""
### 06-1

> 指数分布の最尤推定量が $1/\bar X$ になることを示せ。

対数尤度は

$$
\ell(\lambda) = \sum_{i=1}^{n} \left( \log \lambda - \lambda x_i \right)
= n \log \lambda - \lambda \sum_i x_i
$$

微分して 0 と置くと

$$
\ell'(\lambda) = \frac{n}{\lambda} - \sum_i x_i = 0
\;\Longrightarrow\;
\hat\lambda = \frac{n}{\sum_i x_i} = \frac{1}{\bar X}
$$

$\ell''(\lambda) = -n/\lambda^2 < 0$ なので最大である。
$\bar X$ が $1/\lambda$ の不偏推定量なのに $\hat\lambda = 1/\bar X$ は
$\lambda$ の不偏推定量ではない。**不変性は最尤法の性質で、不偏性は保たれない。**
"""),
    code("""
x = datasets.exponential_sample(400, rate=2.0, seed=RANDOM_SEED)
fit = estimation.mle("exponential", x)
print(f"1 / xbar   = {1 / x.mean():.6f}")
print(f"mle()      = {fit.estimate:.6f}   (se = {fit.se:.6f})")
ests = simulation.sampling_distribution(
    lambda s: 1 / s.mean(), lambda m, rng: rng.exponential(0.5, m), n=20, n_reps=8000, seed=0)
print(f"\\nn = 20 での E[lambda_hat] = {ests.mean():.4f}(真値 2.0)")
print("小標本では上に偏る。1/x は凸なのでイェンセンの不等式どおりである")
"""),
    md(r"""
### 06-2

> 正規分布の分散の最尤推定量の偏りが $-\sigma^2/n$ であることを示し、数値で確認せよ。

$\hat\sigma^2_{\text{MLE}} = \frac{1}{n}\sum_i (X_i - \bar X)^2$。
既知の事実 $\sum_i (X_i - \bar X)^2 \sim \sigma^2 \chi^2_{n-1}$ から

$$
E\left[\hat\sigma^2_{\text{MLE}}\right] = \frac{\sigma^2 (n-1)}{n}
= \sigma^2 - \frac{\sigma^2}{n}
$$

よって偏りは $-\sigma^2/n$ である。

原因は $\bar X$ を推定に使ったことにある。
真の $\mu$ からの偏差二乗和なら不偏だが、$\bar X$ は定義上データに最も近い点なので、
偏差二乗和が系統的に小さくなる。失った自由度が 1 で、それが $n-1$ の由来である。
"""),
    code("""
sigma = 2.0
print(f"{'n':>6} {'E[MLE]':>10} {'sigma^2 - sigma^2/n':>20} {'偏り':>9} {'-sigma^2/n':>12}")
for n in [5, 10, 50, 200]:
    ests = simulation.sampling_distribution(
        lambda s: s.var(ddof=0), lambda m, rng: rng.normal(0, sigma, m),
        n=n, n_reps=20_000, seed=0)
    print(f"{n:6d} {ests.mean():10.4f} {sigma**2 * (n - 1) / n:20.4f} "
          f"{ests.mean() - sigma**2:9.4f} {-sigma**2 / n:12.4f}")
"""),
    md(r"""
### 06-3

> $U(0,\theta)$ の最尤推定量とその分散を求め、Cramér–Rao 下限を下回れる理由を説明せよ。

尤度は $L(\theta) = \theta^{-n}\mathbf{1}\{\max_i x_i \le \theta\}$ で、
$\theta$ について減少関数だから、制約 $\theta \ge \max_i x_i$ の下では
**$\hat\theta = \max_i X_i$** が最大にする(微分では出ない)。

$M = \max_i X_i$ の分布関数は $P(M \le m) = (m/\theta)^n$ なので

$$
E[M] = \frac{n}{n+1}\theta, \qquad
\mathrm{Var}(M) = \frac{n\,\theta^2}{(n+1)^2 (n+2)} = O\!\left(\frac{\theta^2}{n^2}\right)
$$

一方、形式的に計算した Cramér–Rao 下限は $\theta^2/n$ である。
分散は $n^{-2}$ で減るので、$n$ が大きければ **下限を下回る**。

矛盾ではない。Cramér–Rao 不等式は
「台が母数に依存しない」「積分と微分が交換できる」という正則条件を仮定する。
$U(0,\theta)$ は台が $\theta$ に依存するのでこの条件を満たさず、
不等式そのものが適用できない。
"""),
    code("""
theta = 3.0
print(f"{'n':>6} {'Var(max) 実測':>15} {'理論 n t^2/((n+1)^2(n+2))':>28} {'CR 下限 t^2/n':>16}")
for n in [10, 50, 200]:
    ests = simulation.sampling_distribution(
        np.max, lambda m, rng: rng.uniform(0, theta, m), n=n, n_reps=20_000, seed=0)
    theory = n * theta**2 / ((n + 1) ** 2 * (n + 2))
    print(f"{n:6d} {ests.var(ddof=1):15.6f} {theory:28.6f} {theta**2 / n:16.6f}")
print("\\n下限を大きく下回っている。正則条件が破れているので不等式が効かない")
"""),
    md(r"""
### 06-4

> デルタ法で $\log\hat\lambda$ の漸近分散を求め、シミュレーションで確かめよ。

$\hat\lambda$ の漸近分散は $\lambda^2/n$(指数分布のフィッシャー情報量 $1/\lambda^2$ の逆数を $n$ で割る)。
$g(\lambda) = \log\lambda$、$g'(\lambda) = 1/\lambda$ なのでデルタ法より

$$
\mathrm{Var}(\log\hat\lambda) \approx \frac{1}{\lambda^2} \cdot \frac{\lambda^2}{n}
= \frac{1}{n}
$$

$\lambda$ が消える。対数変換が分散安定化になっている
($\sqrt{\hat p}$ が二項の分散安定化だったのと同じ構図)。
実務では、この性質のおかげで対数スケールの区間の方が被覆が良くなることが多い。
"""),
    code("""
print(f"{'lambda':>8} {'n':>6} {'Var(log lambda_hat)':>22} {'1/n':>9}")
for lam in [0.5, 2.0, 10.0]:
    for n in [30, 200]:
        ests = simulation.sampling_distribution(
            lambda s: np.log(1 / s.mean()),
            lambda m, rng, _l=lam: rng.exponential(1 / _l, m), n=n, n_reps=8000, seed=0)
        print(f"{lam:8.1f} {n:6d} {ests.var(ddof=1):22.6f} {1 / n:9.6f}")
print("\\nlambda の値によらず 1/n に近い。対数変換が分散を安定化している")
"""),
    md(r"""
### 06-5

> 2 つの正規分布の混合で尤度が 2 峰になることを示し、初期値で結果が変わることを確認せよ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 400
z = rng.random(n) < 0.4
sample = np.where(z, rng.normal(-2.0, 1.0, n), rng.normal(3.0, 1.0, n))

def mixture_loglik(mu1, mu2, w=0.4, sd=1.0):
    from scipy import stats as sps
    dens = w * sps.norm.pdf(sample, mu1, sd) + (1 - w) * sps.norm.pdf(sample, mu2, sd)
    return float(np.log(dens).sum())

print("mu1 と mu2 を入れ替えても尤度は同じ(ラベル交換不変):")
print(f"  loglik(-2, 3) = {mixture_loglik(-2.0, 3.0):.4f}")
print(f"  loglik(3, -2) = {mixture_loglik(3.0, -2.0):.4f}")

from scipy import optimize
print(f"\\n{'初期値':>16} {'収束先 (mu1, mu2)':>26} {'対数尤度':>12}")
for start in [(-5.0, 5.0), (5.0, -5.0), (0.0, 0.1), (2.0, 2.5)]:
    res = optimize.minimize(lambda p: -mixture_loglik(p[0], p[1]), start, method="Nelder-Mead")
    print(f"{str(start):>16} {str(np.round(res.x, 3)):>26} {-res.fun:12.4f}")
print("\\n初期値によって別の峰に落ちる。混合モデルの尤度は多峰である。")
print("EM も局所解に落ちるので、複数の初期値から回して最良を選ぶ必要がある")
"""),
    md(r"""
2 峰になる根本的な理由は **ラベル交換不変性** である。
成分に付けた番号は識別できないので、$(\mu_1, \mu_2)$ と $(\mu_2, \mu_1)$ は
必ず同じ尤度を与える。したがって尤度面は対称で、最低でも 2 つの大域最適を持つ。
成分数 $K$ なら $K!$ 個になる。

さらに $\sigma$ も推定する場合、1 点に分散 0 を張り付ける方向で尤度が発散するので、
大域最大が存在しない。実務では分散に下限を置くか、罰則を入れる。
"""),
    # ---------------------------------------------------------------- 07
    md(r"""
## 07 章 区間推定とブートストラップ
"""),
    md(r"""
### 07-1

> 3 本同時の同時被覆率を相関がある場合でも測り、Bonferroni で 95% に戻す水準を求めよ。

$m$ 本すべてが当たる確率は、独立なら $0.95^3 = 0.857$。
各区間を $1 - \alpha/m$ 水準にすれば、Bonferroni 不等式

$$
P(\text{少なくとも 1 本外す}) \le \sum_{j=1}^{m} P(\text{$j$ 本目を外す}) = m \cdot \frac{\alpha}{m} = \alpha
$$

より同時被覆が $1-\alpha$ 以上になる。$m=3$、$\alpha=0.05$ なら各区間は
$1 - 0.05/3 = 0.9833$ 水準、つまり **98.33%** にする。
"""),
    code("""
from scipy import stats as sps

def joint_coverage(rho, level, n=30, n_reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    cov = np.linalg.cholesky(np.array([[1, rho, rho], [rho, 1, rho], [rho, rho, 1]]))
    hits = 0
    for _ in range(n_reps):
        data = (rng.standard_normal((n, 3)) @ cov.T)
        ok = True
        for j in range(3):
            s = data[:, j]
            half = sps.t.ppf(0.5 + level / 2, n - 1) * s.std(ddof=1) / np.sqrt(n)
            if not (s.mean() - half <= 0.0 <= s.mean() + half):
                ok = False
                break
        hits += ok
    return hits / n_reps

print(f"{'相関':>6} {'各区間 95%':>13} {'各区間 98.33%':>16}")
for rho in [0.0, 0.5, 0.9]:
    print(f"{rho:6.1f} {joint_coverage(rho, 0.95):13.4f} {joint_coverage(rho, 1 - 0.05 / 3):16.4f}")
print(f"\\n独立時の理論値 0.95^3 = {0.95**3:.4f}")
print("相関が強いと 3 本が同時に外れやすくなるので、同時被覆はむしろ上がる。")
print("Bonferroni は上界なので、相関があるときは保守的(95% を超える)になる")
"""),
    md(r"""
### 07-2

> 対数正規で $n$ を変えて $t$ 区間の被覆率を測り、名目に近づく $n$ を決めよ。04-1 と関係づけよ。
"""),
    code("""
truth = float(np.exp(0.5))          # 対数正規(0,1) の平均 = exp(sigma^2/2)
print(f"真の平均 = {truth:.4f}")
print(f"{'n':>6} {'t 区間の被覆率':>16} {'名目との差':>12}")
for n in [10, 30, 100, 300, 1000]:
    cov = simulation.coverage_probability(
        lambda m, rng: rng.lognormal(0.0, 1.0, m),
        lambda s: tuple(intervals.t_interval(s)),
        truth=truth, n=n, n_reps=4000, seed=0)
    print(f"{n:6d} {cov.estimate:16.4f} {cov.estimate - 0.95:12.4f}")
print("\\nn = 300 でようやく 0.94 台に乗る。n = 30 では 0.90 を切る")
"""),
    md(r"""
04-1 で測った KS 統計量と対応している。
標本平均が正規に近づいていない $n$ では、$t$ 区間の前提も成立していない。
KS が 0.02 を切る $n$ と、被覆が 0.94 を超える $n$ はほぼ同じところに来る。

外し方が **非対称** なのも重要である。対数正規は右に裾を引くので、
$\bar X$ は真の平均を下に外すことが多く、区間は下側に外れやすい。
被覆率だけでなく、どちら側に外すかも見る必要がある。
"""),
    md(r"""
### 07-3

> 比 $\bar X / \bar Y$ のブートストラップ区間を作って被覆率を測れ。$\bar Y \to 0$ で何が起きるか。
"""),
    code("""
def ratio_coverage(mu_y, n=40, n_reps=600, seed=0):
    rng = np.random.default_rng(seed)
    truth = 2.0 / mu_y
    hits = 0
    for _ in range(n_reps):
        x = rng.normal(2.0, 1.0, n)
        y = rng.normal(mu_y, 1.0, n)
        idx = rng.integers(0, n, size=(1000, n))
        boot = x[idx].mean(axis=1) / y[idx].mean(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        hits += lo <= truth <= hi
    return hits / n_reps

print(f"{'E[Y]':>7} {'真の比':>9} {'被覆率':>9}")
for mu_y in [4.0, 2.0, 1.0, 0.5, 0.2]:
    print(f"{mu_y:7.1f} {2.0 / mu_y:9.2f} {ratio_coverage(mu_y):9.4f}")
print("\\nE[Y] が 0 に近づくと被覆が崩れる")
"""),
    md(r"""
$\bar Y$ が 0 をまたぎうるとき、比 $\bar X / \bar Y$ の分布は
**両側に発散する裾** を持ち、期待値すら存在しない
(正規どうしの比はコーシーになる)。
ブートストラップ分布のパーセンタイルは、リサンプルで $\bar Y^*$ が 0 に近づいた
少数の標本に引きずられて極端に広くなったり、逆に真値を外したりする。

正しい対処は 2 つある。比ではなく **差** $\bar X - r_0 \bar Y$ を検定量にして
$r_0$ について反転する(Fieller の方法)か、
$\bar Y$ が 0 から十分離れていることを前提として明示することである。
"""),
    md(r"""
### 07-4

> 順列検定と $t$ 検定を裾の重い分布で比較せよ。どちらの第 1 種の誤り率が名目どおりか。
"""),
    code("""
def type1(kind, test, n=25, n_reps=1500, seed=0):
    rng = np.random.default_rng(seed)
    rejects = 0
    for _ in range(n_reps):
        if kind == "normal":
            x, y = rng.normal(0, 1, n), rng.normal(0, 1, n)
        else:
            x, y = rng.standard_cauchy(n), rng.standard_cauchy(n)
        if test == "t":
            p = testing.two_sample_t_test(x, y).pvalue
        else:
            p = intervals.permutation_test(x, y, n_perm=500, seed=0)
        rejects += p < 0.05
    return rejects / n_reps

print(f"{'分布':>10} {'t 検定':>10} {'順列検定':>10}")
for kind in ["normal", "cauchy"]:
    print(f"{kind:>10} {type1(kind, 't'):10.4f} {type1(kind, 'perm'):10.4f}")
print("\\n名目は 0.05。正規ではどちらも名目どおり。")
print("コーシーでは t 検定が保守的になりすぎ、順列検定も平均差では不安定になる")
"""),
    md(r"""
順列検定が仮定するのは **交換可能性** だけである。
帰無仮説の下で 2 群のラベルが入れ替え可能なら、
分布が何であっても第 1 種の誤り率は正確に名目値になる。

ただしそれは **検定統計量が定義できる範囲** の話である。
平均差を統計量に取ると、コーシーでは統計量そのものが安定しない。
中央値差や順位和(Wilcoxon)に替えれば裾に強くなる。
検定の枠組みと統計量の選択は別問題であり、両方を選ぶ必要がある。
"""),
    # ---------------------------------------------------------------- 08
    md(r"""
## 08 章 仮説検定
"""),
    md(r"""
### 08-1

> $1-(1-\alpha)^m$ を導きシミュレーションで確認せよ。独立でない場合はどうなるか。

$m$ 回の独立な検定が **すべて正しく非棄却** になる確率は $(1-\alpha)^m$。
余事象を取れば少なくとも 1 回誤る確率は

$$
P(\text{FWER}) = 1 - (1-\alpha)^m
$$

$\alpha = 0.05$、$m = 20$ で 0.642 になる。20 個の無関係な仮説を検定すれば、
何も無くても 3 回に 2 回は「発見」が出る。

独立でない場合、Bonferroni 不等式から

$$
P(\text{FWER}) \le m\alpha
$$

が常に成り立つ(上界)。正の相関があると実際の FWER は $1-(1-\alpha)^m$ より **下がる**。
検定が完全に一致していれば FWER は $\alpha$ のままである。
"""),
    code("""
def fwer(m, rho, n=30, n_reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    cov = rho * np.ones((m, m)) + (1 - rho) * np.eye(m)
    L = np.linalg.cholesky(cov)
    any_reject = 0
    for _ in range(n_reps):
        data = rng.standard_normal((n, m)) @ L.T
        p = np.array([testing.t_test(data[:, j]).pvalue for j in range(m)])
        any_reject += bool((p < 0.05).any())
    return any_reject / n_reps

print(f"{'m':>5} {'理論 1-(1-a)^m':>16} {'独立 実測':>11} {'rho=0.9 実測':>14} {'Bonferroni 上界 m*a':>21}")
for m in [1, 5, 20]:
    print(f"{m:5d} {1 - 0.95**m:16.4f} {fwer(m, 0.0):11.4f} {fwer(m, 0.9):14.4f} {min(m * 0.05, 1.0):21.4f}")
print("\\n相関が強いと実際の FWER は下がる。Bonferroni は常に安全側の上界である")
"""),
    md(r"""
### 08-2

> 検出力 0.8 に必要な $n$ を効果量の関数として図示し、$n \propto 1/d^2$ を確認せよ。
"""),
    code("""
effects = np.array([0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.0])
ns = np.array([testing.required_n(float(d), alpha=0.05, power=0.8) for d in effects])
print(f"{'効果量 d':>10} {'必要な n':>10} {'n * d^2':>10}")
for d, n in zip(effects, ns):
    print(f"{d:10.2f} {n:10d} {n * d**2:10.2f}")
print("\\nn * d^2 がほぼ一定(約 7.9)。つまり n は 1/d^2 に比例する。")
print("効果量が半分なら必要な標本は 4 倍になる")

import plotly.graph_objects as go
fig = go.Figure([
    go.Scatter(x=effects, y=ns, mode="lines+markers", name="必要な n"),
    go.Scatter(x=effects, y=7.9 / effects**2, mode="lines",
               line={"dash": "dash", "color": "black"}, name="7.9 / d^2"),
])
fig.update_xaxes(type="log")
fig.update_yaxes(type="log")
plotting.apply_defaults(fig, title="検出力 0.8 に必要な標本サイズ",
                        xaxis_title="効果量 d(対数軸)", yaxis_title="n(対数軸)")
"""),
    md(r"""
両対数で傾き $-2$ の直線になる。これは検出力の式

$$
n \approx \frac{2(z_{1-\alpha/2} + z_{\text{power}})^2}{d^2}
$$

から従う。定数 $2(1.96 + 0.84)^2 \approx 15.7$ は 2 標本の場合で、
1 標本ならその半分の 7.9 になる。上の実測がこの値に一致している。
"""),
    md(r"""
### 08-3

> 帰無が真である割合を変えて、BH の FDR 制御と検出力がどう変わるか測れ。
"""),
    code("""
from scipy import stats as sps

def bh_experiment(null_fraction, m=1000, effect=0.5, n_reps=200, seed=0):
    rng = np.random.default_rng(seed)
    fdps, powers = [], []
    for _ in range(n_reps):
        is_null = rng.random(m) < null_fraction
        z = rng.standard_normal(m) + np.where(is_null, 0.0, effect * np.sqrt(30))
        p = 2 * (1 - sps.norm.cdf(np.abs(z)))
        rejected = testing.benjamini_hochberg(p, alpha=0.05)
        fdps.append(testing.false_discovery_proportion(rejected, is_null))
        powers.append(float((rejected & ~is_null).sum() / max((~is_null).sum(), 1)))
    return float(np.mean(fdps)), float(np.mean(powers))

print(f"{'帰無の割合':>12} {'FDR 実測':>10} {'名目上界 0.05*pi0':>19} {'検出力':>9}")
for frac in [0.5, 0.8, 0.95]:
    fdr, power = bh_experiment(frac)
    print(f"{frac:12.2f} {fdr:10.4f} {0.05 * frac:19.4f} {power:9.4f}")
print("\\nBH の FDR は 0.05 でなく 0.05 * pi0 に制御される(pi0 = 帰無の割合)。")
print("帰無が 95% を占めると FDR は 0.048 まで上がり、検出力は落ちる")
"""),
    md(r"""
BH 法が保証するのは $\mathrm{FDR} \le \pi_0 \alpha$ である($\pi_0$ は帰無が真の割合)。
$\pi_0$ が小さい(本物の効果が多い)ほど実際の FDR は名目より下に来るので、
BH は保守的になる。$\pi_0$ を推定して補正する Storey の $q$ 値が
検出力を取り戻す方向の改良である。

検出力が $\pi_0$ とともに落ちるのは、棄却の閾値 $\frac{k}{m}\alpha$ が
順位 $k$ に依存するからである。本物が少ないと $k$ が伸びず、閾値が厳しくなる。
"""),
    md(r"""
### 08-4

> 逐次的に検定を繰り返すと第 1 種の誤り率がどこまで上がるか測れ。
"""),
    code("""
def sequential_alpha(n_looks, n_max=200, n_reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    looks = np.linspace(n_max // n_looks, n_max, n_looks).astype(int)
    stopped = 0
    for _ in range(n_reps):
        x = rng.standard_normal(n_max)     # 帰無が真
        for k in looks:
            if testing.t_test(x[:k]).pvalue < 0.05:
                stopped += 1
                break
    return stopped / n_reps

print(f"{'覗いた回数':>12} {'第 1 種の誤り率':>16}")
for looks in [1, 2, 5, 10, 20, 50]:
    print(f"{looks:12d} {sequential_alpha(looks):16.4f}")
print("\\n名目 0.05 が、50 回覗くと 0.2 を超える。")
print("データを足しながら「有意になったら止める」は、検定を壊す")
"""),
    md(r"""
理屈の上では、無限に覗き続ければ第 1 種の誤り率は **1 に収束する**
(帰無の下でも $t$ 統計量は再帰的にどこまでも動くため)。
上の実測はその途中経過である。

対処は 3 つある。覗く回数を事前に決めて $\alpha$ を配分する(O'Brien–Fleming の
$\alpha$ 消費関数)、逐次確率比検定を使う、あるいは
ベイズの事後確率で止める(こちらは覗く回数に依存しない)。
A/B テストの実務では 1 番目か 3 番目が使われる。
"""),
    md(r"""
### 08-5

> 同じデータで $t$ 検定と順列検定の p 値を、正規と裾の重い分布の両方で比較せよ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
print(f"{'分布':>10} {'標本':>6} {'t 検定 p':>12} {'順列検定 p':>13} {'差':>9}")
for kind in ["normal", "cauchy"]:
    for trial in range(3):
        if kind == "normal":
            x, y = rng.normal(0, 1, 30), rng.normal(0.5, 1, 30)
        else:
            x, y = rng.standard_cauchy(30), rng.standard_cauchy(30) + 0.5
        pt = testing.two_sample_t_test(x, y).pvalue
        pp = intervals.permutation_test(x, y, n_perm=3000, seed=0)
        print(f"{kind:>10} {trial + 1:6d} {pt:12.5f} {pp:13.5f} {abs(pt - pp):9.5f}")
print("\\n正規では両者はほぼ一致する(t 検定の前提が満たされているので)。")
print("コーシーでは大きく食い違う。どちらを信じるかは前提の妥当性で決まる")
"""),
    # ---------------------------------------------------------------- 09
    md(r"""
## 09 章 回帰の推測
"""),
    md(r"""
### 09-1

> 無関係な変数を足すと $R^2$ が必ず上がることを示し、自由度調整済み $R^2$ と比べよ。

最小二乗は残差二乗和 $\mathrm{RSS}$ を最小化する。
列を 1 本足した設計行列 $[X, z]$ の解空間は $X$ の解空間を **含む** ので、
新しい最小値は元の最小値以下である。

$$
\mathrm{RSS}_{k+1} \le \mathrm{RSS}_{k}
\;\Longrightarrow\;
R^2 = 1 - \frac{\mathrm{RSS}}{\mathrm{TSS}} \text{ は減らない}
$$

$z$ の係数を 0 にすれば元の解が再現できるので、悪くなりようがない。
等号は $z$ が既存の列の張る空間に入るときに限る。

自由度調整済み $R^2 = 1 - (1-R^2)\frac{n-1}{n-k}$ は、
$k$ が増えると第 2 因子が大きくなるので、
$R^2$ の増分が小さければ **下がる**。これが罰則の役割である。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 60
x1 = rng.normal(size=n)
y = 1.0 + 2.0 * x1 + rng.normal(0, 1.0, n)

X = np.column_stack([np.ones(n), x1])
print(f"{'追加した無関係な変数':>22} {'k':>4} {'R^2':>9} {'調整済み R^2':>14}")
for extra in range(0, 26, 5):
    Xa = np.column_stack([X, rng.normal(size=(n, extra))]) if extra else X
    fit = regression.ols(Xa, y)
    k = Xa.shape[1]
    adj = 1 - (1 - fit.r_squared) * (n - 1) / (n - k)
    print(f"{extra:22d} {k:4d} {fit.r_squared:9.4f} {adj:14.4f}")
print("\\nR^2 は単調に上がり、25 本足せば 0.75 を超える。")
print("調整済み R^2 は下がる。無関係な変数を足した代償が見えている")
"""),
    md(r"""
### 09-2

> 誤差が AR(1) で自己相関しているデータで、通常の標準誤差の被覆率がどれだけ狂うか測れ。
"""),
    code("""
from scipy import stats as sps

def ar1_coverage(phi, n=100, n_reps=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(-2, 2, n)
    X = np.column_stack([np.ones(n), x])
    hits = 0
    for _ in range(n_reps):
        e = np.empty(n)
        e[0] = rng.normal(0, 1 / np.sqrt(max(1 - phi**2, 1e-9)))
        for t in range(1, n):
            e[t] = phi * e[t - 1] + rng.normal(0, 1)
        y = 1.0 + 0.5 * x + e
        fit = regression.ols(X, y)
        half = sps.t.ppf(0.975, n - 2) * fit.se[1]
        hits += abs(fit.params[1] - 0.5) <= half
    return hits / n_reps

print(f"{'AR(1) の phi':>14} {'傾きの被覆率':>14}")
for phi in [0.0, 0.3, 0.6, 0.9]:
    print(f"{phi:14.1f} {ar1_coverage(phi):14.4f}")
print("\\n名目は 0.95。phi = 0.9 では 0.6 前後まで落ちる。")
print("独立でない誤差は「実効的な標本サイズ」を減らすので、標準誤差が小さすぎる")
"""),
    md(r"""
AR(1) 誤差の実効標本サイズはおよそ $n \frac{1-\phi}{1+\phi}$ である。
$\phi = 0.9$ なら $n = 100$ が実質 5 程度にまで落ちる。
通常の標準誤差はこの縮小を知らないので、区間が狭すぎる。

対処は Newey–West の HAC 標準誤差か、
誤差構造を明示的にモデル化する(GLS、時系列モデル)ことである。
不均一分散に対する HC(次問)とは別の問題であり、HC では直らない。
"""),
    md(r"""
### 09-3

> HC0–HC3 の被覆率を $n = 20, 50, 200$ で比較し、小標本で HC3 が推奨される理由を示せ。
"""),
    code("""
from scipy import stats as sps

def hc_coverage(n, kind, n_reps=3000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.linspace(-2, 2, n)
    X = np.column_stack([np.ones(n), x])
    hits = 0
    for _ in range(n_reps):
        y = 1.0 + 0.5 * x + rng.normal(0, 0.3 + 0.6 * np.abs(x))   # 不均一分散
        fit = regression.ols(X, y)
        se = regression.robust_se(X, fit.resid, kind=kind)[1]
        half = sps.t.ppf(0.975, n - 2) * se
        hits += abs(fit.params[1] - 0.5) <= half
    return hits / n_reps

print(f"{'n':>6} {'通常':>9} {'HC0':>9} {'HC1':>9} {'HC2':>9} {'HC3':>9}")
for n in [20, 50, 200]:
    row = [hc_coverage(n, k) for k in ["HC0", "HC1", "HC2", "HC3"]]
    rng = np.random.default_rng(0)
    print(f"{n:6d} {'':>9} " + " ".join(f"{v:9.4f}" for v in row))
print("\\nn = 20 では HC0 が 0.90 を切り、HC3 が最も名目に近い。")
print("n = 200 では 4 つとも同じになる")
"""),
    md(r"""
HC0 は残差二乗 $e_i^2$ をそのまま使うが、
最小二乗の残差は真の誤差より系統的に小さい($E[e_i^2] = (1-h_{ii})\sigma_i^2$)。
HC2 は $1-h_{ii}$ で、HC3 は $(1-h_{ii})^2$ で割って補正する。

小標本ではレバレッジ $h_{ii}$ が大きい点が出やすいので補正が効く。
HC3 は最も強く補正するため保守的だが、**小標本では保守的な方が安全** である。
$n$ が大きいと $h_{ii} \to 0$ なので 4 つとも一致する。
"""),
    md(r"""
### 09-4

> レバレッジの高い点を除くと係数がどう動くか調べ、Cook の距離を自分で実装せよ。

Cook の距離は、$i$ 番目の観測を除いたときに **当てはめ値全体がどれだけ動くか** を測る。

$$
D_i = \frac{\sum_j (\hat y_j - \hat y_{j(i)})^2}{k \, \hat\sigma^2}
= \frac{e_i^2}{k \, \hat\sigma^2} \cdot \frac{h_{ii}}{(1 - h_{ii})^2}
$$

右辺の形が要点である。第 1 因子は **残差** の大きさ、第 2 因子は **レバレッジ**。
どちらか一方だけでは危険な点にならない。
レバレッジが高くても回帰線の上に乗っていれば影響は無いし、
残差が大きくても $x$ が中央にあれば傾きは動かない。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 40
x = np.concatenate([rng.normal(0, 1, n - 1), [6.0]])     # 最後の点だけ x が遠い
y = 1.0 + 0.5 * x + rng.normal(0, 0.5, n)
y[-1] += 4.0                                             # かつ外れている
X = np.column_stack([np.ones(n), x])

fit = regression.ols(X, y)
h = regression.leverage(X)
k = X.shape[1]
cook = fit.resid**2 / (k * fit.sigma2) * h / (1 - h) ** 2

order = np.argsort(cook)[::-1][:4]
print(f"{'i':>4} {'x':>8} {'残差':>9} {'レバレッジ h':>14} {'Cook D':>10}")
for i in order:
    print(f"{i:4d} {x[i]:8.3f} {fit.resid[i]:9.3f} {h[i]:14.4f} {cook[i]:10.4f}")

keep = np.arange(n) != order[0]
refit = regression.ols(X[keep], y[keep])
print(f"\\n全点での傾き       = {fit.params[1]:.4f}")
print(f"最大 Cook 点を除く = {refit.params[1]:.4f}(真値 0.5)")
print(f"\\n参考: レバレッジ最大だが残差が小さい点の Cook D も見る")
low = np.argsort(np.abs(fit.resid))[:1][0]
print(f"  i={low}: h = {h[low]:.4f}, 残差 = {fit.resid[low]:.3f}, Cook D = {cook[low]:.5f}")
print("残差が小さければレバレッジが高くても Cook D は小さい。両方を含む指標である")
"""),
    # ---------------------------------------------------------------- 10
    md(r"""
## 10 章 一般化線形モデル
"""),
    md(r"""
### 10-1

> プロビットリンクで当てはめ、logit と係数・当てはめ確率を比較せよ。どちらが正しいと言えるか。
"""),
    code("""
from scipy import stats as sps, optimize

rng = np.random.default_rng(RANDOM_SEED)
n = 800
x = rng.normal(0, 1.5, n)
X = np.column_stack([np.ones(n), x])
y = (rng.random(n) < 1 / (1 + np.exp(-(0.5 + 1.5 * x)))).astype(float)

logit = glm.irls(X, y, family="binomial")

def probit_negloglik(beta):
    p = np.clip(sps.norm.cdf(X @ beta), 1e-10, 1 - 1e-10)
    return -float((y * np.log(p) + (1 - y) * np.log(1 - p)).sum())

probit = optimize.minimize(probit_negloglik, np.zeros(2), method="BFGS").x

print(f"{'':>10} {'切片':>10} {'傾き':>10} {'傾き / 1.6':>12}")
print(f"{'logit':>10} {logit.params[0]:10.4f} {logit.params[1]:10.4f} {'':>12}")
print(f"{'probit':>10} {probit[0]:10.4f} {probit[1]:10.4f} {logit.params[1] / 1.6:12.4f}")

p_logit = 1 / (1 + np.exp(-(X @ logit.params)))
p_probit = sps.norm.cdf(X @ probit)
print(f"\\n当てはめ確率の最大差 = {np.abs(p_logit - p_probit).max():.4f}")
print(f"相関                 = {np.corrcoef(p_logit, p_probit)[0, 1]:.6f}")
"""),
    md(r"""
係数は約 1.6 倍違う。ロジスティック分布の標準偏差が $\pi/\sqrt{3} \approx 1.814$、
標準正規が 1 なので、スケールの違いがそのまま係数比に出る
(経験則の 1.6 はこの比の実用的な近似である)。

**どちらが正しいとは言えない。** 当てはめ確率はほぼ同一で、
データからは区別できない。違いが出るのは極端な裾($p < 0.01$ など)だけで、
そこはデータが最も少ない領域である。

選択は解釈のしやすさで決めるのが実務的である。
logit は係数がオッズ比の対数として読めるので疫学・医学で好まれ、
probit は潜在変数モデル(正規誤差の閾値超え)として読めるので経済学で好まれる。
"""),
    md(r"""
### 10-2

> 準ポアソン補正(標準誤差を $\sqrt{\phi}$ 倍)を実装し、負の二項データでの被覆率改善を測れ。
"""),
    code("""
def quasipoisson_coverage(correct, n=200, n_reps=1500, seed=0):
    from scipy import stats as sps
    rng = np.random.default_rng(seed)
    x = np.linspace(-1, 1, n)
    X = np.column_stack([np.ones(n), x])
    beta_true = np.array([1.5, 0.8])
    hits = 0
    for _ in range(n_reps):
        mu = np.exp(X @ beta_true)
        # 負の二項: 平均 mu、分散 mu + mu^2/r で過分散
        r = 3.0
        y = rng.negative_binomial(r, r / (r + mu)).astype(float)
        fit = glm.irls(X, y, family="poisson")
        se = fit.se[1]
        if correct:
            phi = glm.dispersion(fit, y, X, family="poisson")
            se = se * np.sqrt(phi)
        half = sps.norm.ppf(0.975) * se
        hits += abs(fit.params[1] - beta_true[1]) <= half
    return hits / n_reps

print(f"{'標準誤差':>18} {'被覆率':>9}")
print(f"{'ポアソンのまま':>18} {quasipoisson_coverage(False):9.4f}")
print(f"{'準ポアソン補正':>18} {quasipoisson_coverage(True):9.4f}")
print("\\n名目は 0.95。補正なしでは 0.6 前後まで落ち、補正すると回復する")
"""),
    md(r"""
ポアソン回帰は $\mathrm{Var}(Y) = \mu$ を仮定するが、
負の二項では $\mathrm{Var}(Y) = \mu + \mu^2/r > \mu$ になる。
分散を過小評価しているので標準誤差が小さすぎ、区間が狭すぎる。

準ポアソンは分散を $\phi\mu$ と置き、
$\hat\phi = \frac{1}{n-k}\sum_i \frac{(y_i - \hat\mu_i)^2}{\hat\mu_i}$
(ピアソン統計量を自由度で割ったもの)で推定して標準誤差を $\sqrt{\hat\phi}$ 倍する。
点推定は変わらない。**壊れているのは標準誤差だけ** だからである
(09 章の頑健標準誤差と同じ構図)。
"""),
    md(r"""
### 10-3

> 正準リンクの場合に IRLS が Newton–Raphson と一致することを、スコアとヘッセを書き下して示せ。

正準リンクでは自然母数が $\theta_i = \eta_i = x_i^\top \beta$ になる。
指数型分布族の対数尤度は

$$
\ell(\beta) = \sum_i \left[ \frac{y_i \theta_i - b(\theta_i)}{a(\phi)} + c(y_i, \phi) \right]
$$

$b'(\theta_i) = \mu_i$、$b''(\theta_i) = V(\mu_i)$ を使うと

$$
\text{スコア} \quad \nabla \ell = \frac{1}{a(\phi)} X^\top (y - \mu)
$$

$$
\text{ヘッセ} \quad \nabla^2 \ell = -\frac{1}{a(\phi)} X^\top W X,
\qquad W = \mathrm{diag}\big(V(\mu_i)\big)
$$

正準リンクでは $\frac{d\mu_i}{d\eta_i} = V(\mu_i)$ なので、
**ヘッセ行列が $\beta$ の 2 階微分としても期待値としても同じ形になる**
(観測情報量 = 期待情報量)。ここが正準リンク特有の性質である。

Newton の更新は

$$
\beta^{(t+1)} = \beta^{(t)} + (X^\top W X)^{-1} X^\top (y - \mu)
= (X^\top W X)^{-1} X^\top W z,
\qquad z = \eta + W^{-1}(y - \mu)
$$

最後の変形は $X^\top W \eta = X^\top W X \beta^{(t)}$ を使った。
右辺は作業応答 $z$ と重み $W$ による **重み付き最小二乗** そのもので、
これが IRLS の 1 反復である。非正準リンクでは
観測情報量と期待情報量が食い違い、IRLS はフィッシャースコアリングに対応する。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 300
x = rng.normal(0, 1, n)
X = np.column_stack([np.ones(n), x])
y = (rng.random(n) < 1 / (1 + np.exp(-(0.3 + 1.2 * x)))).astype(float)

# 手書きの Newton-Raphson(スコアとヘッセを直接使う)
beta = np.zeros(2)
for _ in range(30):
    eta = X @ beta
    mu = 1 / (1 + np.exp(-eta))
    W = mu * (1 - mu)
    score = X.T @ (y - mu)
    hess = X.T @ (X * W[:, None])
    beta = beta + np.linalg.solve(hess, score)

fit = glm.irls(X, y, family="binomial")
print(f"手書き Newton-Raphson : {beta.round(8)}")
print(f"glm.irls              : {fit.params.round(8)}")
print(f"最大差                : {np.abs(beta - fit.params).max():.2e}")
"""),
    md(r"""
### 10-4

> 露出時間が異なるカウントに対し、オフセット項 $\log\mu = \log(\text{exposure}) + X\beta$ を入れたポアソン回帰を実装せよ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 400
x = rng.normal(0, 1, n)
exposure = rng.uniform(0.5, 10.0, n)          # 観測時間がばらばら
X = np.column_stack([np.ones(n), x])
rate = np.exp(-0.5 + 0.9 * x)                 # 単位時間あたりの発生率
y = rng.poisson(rate * exposure).astype(float)

# オフセットは既知の係数 1 の項。IRLS の作業応答から差し引けば実装できる。
def poisson_offset_irls(X, y, offset, max_iter=50, tol=1e-12):
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        eta = X @ beta + offset
        mu = np.exp(eta)
        W = mu
        z = (eta - offset) + (y - mu) / np.maximum(mu, 1e-10)
        new = np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (W * z))
        if np.max(np.abs(new - beta)) < tol:
            beta = new
            break
        beta = new
    return beta

with_offset = poisson_offset_irls(X, y, np.log(exposure))
without = glm.irls(X, y, family="poisson").params
naive_rate = glm.irls(X, y / exposure, family="poisson").params

print(f"{'':>22} {'切片':>10} {'傾き':>10}")
print(f"{'真値':>22} {-0.5:10.4f} {0.9:10.4f}")
print(f"{'オフセットあり':>22} {with_offset[0]:10.4f} {with_offset[1]:10.4f}")
print(f"{'オフセットなし':>22} {without[0]:10.4f} {without[1]:10.4f}")
print(f"{'率を応答にする(誤り)':>22} {naive_rate[0]:10.4f} {naive_rate[1]:10.4f}")
print("\\nオフセットありだけが真値を復元する")
"""),
    md(r"""
オフセットは **係数を 1 に固定した説明変数** である。
露出時間が 2 倍なら期待件数も 2 倍になる、という既知の関係を
推定せずにモデルへ入れる。

$y/\text{exposure}$ を応答にする素朴な方法が駄目な理由は 2 つある。
比はもう整数でないのでポアソンの尤度が意味を持たない。
そして露出が短い観測ほど比の分散が大きいのに、その情報が捨てられる。
オフセットなら分散構造が正しく $\mathrm{Var}(y) = \mu = \text{exposure} \cdot e^{X\beta}$ になる。
"""),
    # ---------------------------------------------------------------- 11
    md(r"""
## 11 章 頻度論とベイズ
"""),
    md(r"""
### 11-1

> 一様事前と Jeffreys 事前で信用区間の頻度論的被覆率を $p = 0.05, 0.5$ で比較せよ。
"""),
    code("""
def credible_coverage(p, n, prior, n_reps=6000):
    a, b = bridge.PRIORS[prior]
    return simulation.coverage_probability(
        lambda m, rng, _p=p: (rng.random(m) < _p).astype(float),
        lambda s: tuple(bridge.credible_interval(int(s.sum()), s.size, a, b)),
        truth=p, n=n, n_reps=n_reps, seed=0).estimate

print(f"{'p':>6} {'n':>5} {'一様 Beta(1,1)':>16} {'Jeffreys Beta(.5,.5)':>22}")
for p in [0.05, 0.5]:
    for n in [20, 100]:
        print(f"{p:6.2f} {n:5d} {credible_coverage(p, n, 'uniform'):16.4f} "
              f"{credible_coverage(p, n, 'jeffreys'):22.4f}")
print("\\np = 0.05 では Jeffreys の方が名目 0.95 に近い。")
print("p = 0.5 ではどちらも良く、差はほとんど無い")
"""),
    md(r"""
Jeffreys 事前 $\mathrm{Beta}(0.5, 0.5)$ は端点 0 と 1 に密度を集めるので、
極端な $p$ でも区間が境界に張り付きにくい。
一様事前は端点で密度が平坦なので、$p$ が 0 に近いと区間が真値より内側に寄る。

Jeffreys 事前は **フィッシャー情報量の平方根に比例** するように作られており、
母数の取り方を変えても同じ事前になるという不変性を持つ。
被覆が良いのは偶然ではなく、この構成が漸近的に頻度論的性質を持つためである。
"""),
    md(r"""
### 11-2

> $p$ について一様な事前が $\theta = \log\frac{p}{1-p}$ については一様でないことを Jacobian で示せ。

$\theta = \log\frac{p}{1-p}$ の逆変換は $p = \frac{e^\theta}{1+e^\theta} = \sigma(\theta)$。
ヤコビアンは

$$
\frac{dp}{d\theta} = \sigma(\theta)\big(1 - \sigma(\theta)\big) = p(1-p)
$$

密度の変換則 $f_\Theta(\theta) = f_P(p) \left| \frac{dp}{d\theta} \right|$ より、
$f_P(p) = 1$($p$ について一様)なら

$$
f_\Theta(\theta) = p(1-p) = \frac{e^\theta}{(1 + e^\theta)^2}
$$

これはロジスティック分布の密度であり、**一様ではない**。
$\theta = 0$($p = 0.5$)で最大値 $1/4$ を取り、両裾で 0 に落ちる。

つまり「$p$ について無情報」と「ロジットについて無情報」は両立しない。
**無情報性は母数の取り方に相対的** であり、事前分布そのものの性質ではない。
これが「無情報事前」という言い方の落とし穴である。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
p_draws = rng.uniform(0, 1, 400_000)              # p について一様
theta = np.log(p_draws / (1 - p_draws))

hist, edges = np.histogram(theta, bins=60, range=(-6, 6), density=True)
centers = 0.5 * (edges[:-1] + edges[1:])
logistic = np.exp(centers) / (1 + np.exp(centers)) ** 2

print(f"{'theta':>8} {'実測密度':>10} {'p(1-p) の理論':>15}")
for i in range(0, 60, 10):
    print(f"{centers[i]:8.2f} {hist[i]:10.4f} {logistic[i]:15.4f}")
print(f"\\n最大差 = {np.abs(hist - logistic).max():.4f}")
print("一様だったはずの事前が、ロジットスケールでは山なりになっている")

import plotly.graph_objects as go
fig = go.Figure([
    go.Bar(x=centers, y=hist, name="p 一様事前を theta で見た密度"),
    go.Scatter(x=centers, y=logistic, mode="lines", name="p(1-p) (ロジスティック密度)",
               line={"color": "black"}),
])
plotting.apply_defaults(fig, title="「無情報」は母数の取り方に依存する",
                        xaxis_title="theta = log(p / (1-p))", yaxis_title="密度")
"""),
    md(r"""
### 11-3

> Wald 区間の代わりに Wilson 区間を使うと被覆率がどう変わるか測れ。
"""),
    code("""
from scipy import stats as sps

def wilson(k, n, level=0.95):
    z = sps.norm.ppf(0.5 + level / 2)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - half, center + half

def cov_of(fn, p, n, n_reps=6000):
    return simulation.coverage_probability(
        lambda m, rng, _p=p: (rng.random(m) < _p).astype(float),
        fn, truth=p, n=n, n_reps=n_reps, seed=0).estimate

wald_fn = lambda s: tuple(intervals.wald_interval(
    s.mean(), float(np.sqrt(max(s.mean() * (1 - s.mean()), 1e-12) / s.size))))
wilson_fn = lambda s: wilson(int(s.sum()), s.size)
jeff_fn = lambda s: tuple(bridge.credible_interval(int(s.sum()), s.size))

print(f"{'p':>6} {'n':>5} {'Wald':>9} {'Wilson':>9} {'Jeffreys':>10}")
for p, n in [(0.1, 20), (0.1, 100), (0.5, 20), (0.02, 50)]:
    print(f"{p:6.2f} {n:5d} {cov_of(wald_fn, p, n):9.4f} "
          f"{cov_of(wilson_fn, p, n):9.4f} {cov_of(jeff_fn, p, n):10.4f}")
print("\\np = 0.1, n = 20 で Wald 0.88、Wilson と Jeffreys は 0.95 前後。")
print("Wilson は頻度論の枠内にいながら Jeffreys とほぼ同じ被覆を出す")
"""),
    md(r"""
Wilson 区間はスコア検定を反転して作る。
$\frac{\hat p - p}{\sqrt{p(1-p)/n}}$ の分母に **仮説の $p$** を使うところが Wald と違う
(Wald は $\hat p$ を使う)。$\hat p = 0$ でも分母が 0 にならないので区間が潰れない。

面白いのは、Wilson 区間の中心 $\frac{k + z^2/2}{n + z^2}$ が
$\mathrm{Beta}(z^2/2, z^2/2)$ 事前の事後平均と同じ形をしていることである。
$z \approx 1.96$ なら疑似観測数は約 1.92。
**頻度論的に良い区間が、実質的にベイズ的な縮小を行っている。**
11 章の主張がここでも繰り返される。
"""),
    md(r"""
### 11-4

> ベイズ因子と p 値が逆の結論を出すデータを $n \le 1000$ の範囲で構成せよ。
"""),
    code("""
from scipy import stats as sps

print("p 値は有意、ベイズ因子は H0 支持になる (k, n) を探す:")
print(f"{'n':>6} {'k':>6} {'p 値':>10} {'ベイズ因子':>12} {'判定の食い違い':>16}")
found = []
for n in [200, 400, 600, 800, 1000]:
    for k in range(n // 2, n):
        pv = float(sps.binomtest(k, n, 0.5).pvalue)
        if pv >= 0.05:
            continue
        bf = bridge.bayes_factor_proportion(k, n, p0=0.5)
        if bf < 1 / 3:                      # ベイズは H0 を支持
            found.append((n, k, pv, bf))
            print(f"{n:6d} {k:6d} {pv:10.5f} {bf:12.4f} {'有意 vs H0 支持':>16}")
            break

print(f"\\n見つかった例: {len(found)} 件")
print("いずれも p < 0.05 で「有意」だが、ベイズ因子は 3 倍以上 H0 に有利である。")
print("効果量 |p_hat - 0.5| が小さいのに n が大きいので p 値だけが小さくなる")
"""),
    md(r"""
逆向き(p 値は有意でないがベイズ因子が $H_1$ を支持)は、
一様事前の下では作りにくい。$H_1$ の事前が広いほど $H_0$ が有利になるためである。
$H_1$ の事前を観測の周りに集中させれば作れるが、
それは「答えを見てから事前を決めた」ことになる。
"""),
    # ---------------------------------------------------------------- 12
    md(r"""
## 12 章 キャップストーン
"""),
    md(r"""
### 12-1

> 次数を 12 に上げて 3 視点の差がどうなるか調べよ。訓練 MSE と真の関数との MSE の乖離はどちらに開くか。
"""),
    code("""
from stats_textbook.plotting.bridge import capstone_features

x, y = datasets.make_capstone_dataset(seed=0)
lams = np.logspace(-4, 3, 40)
folds = np.arange(x.size) % 5

def true_mse(w, degree):
    grid = np.linspace(x.min(), x.max(), 500)
    raw = np.vander(x, degree + 1, increasing=True)
    pg = np.vander(grid, degree + 1, increasing=True)
    pg[:, 1:] = (pg[:, 1:] - raw[:, 1:].mean(0)) / raw[:, 1:].std(0)
    return float(np.mean((np.sin(1.5 * grid) + 0.3 * grid - pg @ w) ** 2))

print(f"{'次数':>5} {'視点':>16} {'||w||':>10} {'訓練 MSE':>10} {'真との MSE':>12}")
for degree in [5, 12]:
    phi = capstone_features(x, degree)
    w_ols = np.linalg.lstsq(phi, y, rcond=None)[0]
    w_bayes = np.linalg.solve(phi.T @ phi + np.eye(phi.shape[1]), phi.T @ y)
    errs = []
    for lam in lams:
        e = 0.0
        for f in range(5):
            tr, te = folds != f, folds == f
            w = np.linalg.solve(phi[tr].T @ phi[tr] + lam * np.eye(phi.shape[1]), phi[tr].T @ y[tr])
            e += float(((y[te] - phi[te] @ w) ** 2).sum())
        errs.append(e)
    w_cv = np.linalg.solve(
        phi.T @ phi + lams[int(np.argmin(errs))] * np.eye(phi.shape[1]), phi.T @ y)
    for label, w in [("頻度論", w_ols), ("ベイズ", w_bayes), ("機械学習", w_cv)]:
        print(f"{degree:5d} {label:>16} {np.linalg.norm(w):10.2f} "
              f"{np.mean((y - phi @ w) ** 2):10.4f} {true_mse(w, degree):12.4f}")
print("\\n乖離は最小二乗側に開く。訓練 MSE は下がるのに真との MSE は上がる。")
print("罰則を入れた 2 つは次数を上げてもほとんど劣化しない")
"""),
    md(r"""
### 12-2

> $\sigma_w$ を 0.1 から 10 まで変え、事後平均が最小二乗とリッジの間をどう動くか追え。
"""),
    code("""
phi = capstone_features(x, degree=5)
w_ols = np.linalg.lstsq(phi, y, rcond=None)[0]
sigma = 1.0

sws = np.logspace(-1, 1, 25)
norms = []
for sw in sws:
    lam = sigma**2 / sw**2
    w = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
    norms.append(float(np.linalg.norm(w)))

print(f"{'sigma_w':>9} {'lambda':>10} {'||w||':>9}")
for sw in [0.1, 0.3, 1.0, 3.0, 10.0]:
    lam = sigma**2 / sw**2
    w = np.linalg.solve(phi.T @ phi + lam * np.eye(phi.shape[1]), phi.T @ y)
    print(f"{sw:9.1f} {lam:10.4f} {np.linalg.norm(w):9.4f}")
print(f"\\n最小二乗の ||w|| = {np.linalg.norm(w_ols):.4f}")
print("sigma_w -> ∞(事前が無情報)で最小二乗に、sigma_w -> 0 で 0 ベクトルに近づく")

import plotly.graph_objects as go
fig = go.Figure([
    go.Scatter(x=sws, y=norms, mode="lines+markers", name="事後平均の ||w||"),
    go.Scatter(x=sws, y=[np.linalg.norm(w_ols)] * len(sws), mode="lines",
               line={"dash": "dash", "color": "black"}, name="最小二乗の ||w||"),
])
fig.update_xaxes(type="log")
plotting.apply_defaults(fig, title="事前の広さが縮小の強さを決める",
                        xaxis_title="sigma_w(対数軸)", yaxis_title="||w||")
"""),
    md(r"""
### 12-3

> 交差検証の分割数を 2, 5, 10, 40(leave-one-out)と変えて、選ばれる $\lambda$ の安定性を測れ。
"""),
    code("""
def cv_lambda(n_folds, shift=0):
    idx = (np.arange(x.size) + shift) % n_folds
    errs = []
    for lam in lams:
        e = 0.0
        for f in range(n_folds):
            tr, te = idx != f, idx == f
            if te.sum() == 0:
                continue
            w = np.linalg.solve(phi[tr].T @ phi[tr] + lam * np.eye(phi.shape[1]), phi[tr].T @ y[tr])
            e += float(((y[te] - phi[te] @ w) ** 2).sum())
        errs.append(e)
    return float(lams[int(np.argmin(errs))])

print(f"{'分割数':>8} {'選ばれた lambda':>18} {'分割をずらした 4 通り':>28}")
for k in [2, 5, 10, 40]:
    variants = [cv_lambda(k, s) for s in range(4)]
    print(f"{k:8d} {cv_lambda(k):18.4f}   {str([round(v, 4) for v in variants]):>26}")
print("\\n分割数が小さいほど、分割の切り方で選ばれる lambda が動く。")
print("leave-one-out(40 分割)は決定的なので、ずらしても変わらない")
"""),
    md(r"""
分割数のトレードオフは次のとおりである。

- **分割数が小さい**(2 分割): 訓練集合が小さいので当てはめが悪く、
  $\lambda$ が大きめに選ばれやすい。分割の切り方による分散も大きい
- **分割数が大きい**(leave-one-out): 訓練集合がほぼ全体なので偏りは小さいが、
  $n$ 個の訓練集合が互いにほとんど同じなので、推定量の分散は下がらない。
  計算コストも $n$ 倍になる

実務で 5 分割や 10 分割が標準になっているのは、この両端の中間だからである。
本問のように $n = 40$ と小さいときは、分割をずらして複数回走らせ、
選ばれた $\lambda$ の散らばりを見ておくのが安全である。
"""),
    md(r"""
---

以上で 01–12 章の演習 54 問すべての解答が終わりである。

解答を書いていて 2 つ、本文より重い事実が出てきた。

1 つは **06-3**。一様分布の最尤推定量は Cramér–Rao 下限を下回る。
分散が $\theta^2/n^2$ の速さで減り、下限の $\theta^2/n$ より速い。
矛盾ではなく、台が母数に依存して正則条件が破れているので不等式が適用できない。
「下限だから下回れない」と暗記していると、ここで足をすくわれる。

もう 1 つは **11-2**。$p$ について一様な事前は、ロジットについては一様でない。
ヤコビアン $p(1-p)$ がそのまま密度になる。
無情報性は事前分布の性質ではなく、母数の取り方との関係でしか定義できない。
「無情報事前を使ったので主観は入っていない」という説明は、この時点で成り立たない。
"""),
]
