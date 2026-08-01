"""Builder for notebook 04 — Limit theorems (the book's flagship chapter)."""

from nbkit import code, md

cells = [
    md(r"""
# 04. 極限定理 — なぜ正規分布はどこにでも現れるのか

> 中心極限定理は分散が有限であることを要求する。これは但し書きではなく、成否の分かれ目である。

## この章で分かること

- 大数の法則が保証すること — 標本平均は **どこへ行くか**
- 中心極限定理が保証すること — 標本平均は **どうぶれるか**
- 収束には 3 種類あり、強さが違うこと
- デルタ法 — 極限定理を変換した量に持ち越す道具
- 分散が無い分布では、中心極限定理は成り立たないこと
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
## 1. 大数の法則 — どこへ行くか

$X_1, X_2, \dots$ が独立同分布で $E[X_i] = \mu$ が存在するとき、標本平均

$$
\bar X_n = \frac{1}{n}\sum_{i=1}^n X_i
$$

は $\mu$ に収束する。これが **大数の法則** である。

「収束する」の意味は 2 通りあり、弱法則は確率収束、強法則は概収束を主張する。
違いは §3 で扱う。まずは走る平均が落ち着く様子を見る。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
x = rng.exponential(1.0, 50_000)         # 真の平均 1.0
running = np.cumsum(x) / np.arange(1, x.size + 1)

print(f"{'n':>7} {'標本平均':>10} {'真値との差':>12}")
for n in [10, 100, 1_000, 10_000, 50_000]:
    print(f"{n:7d} {running[n - 1]:10.4f} {running[n - 1] - 1.0:+12.4f}")
"""),
    md(r"""
差が縮んでいく。ただし、**どれくらいの速さで** 縮むかは大数の法則は教えてくれない。
それを言うのが中心極限定理である。
"""),
    md(r"""
## 2. 中心極限定理 — どうぶれるか

$E[X_i] = \mu$、$\mathrm{Var}(X_i) = \sigma^2 < \infty$ のとき

$$
\sqrt{n}\,\frac{\bar X_n - \mu}{\sigma} \;\xrightarrow{d}\; N(0, 1)
$$

読み方は「$\bar X_n$ のゆらぎは $1/\sqrt{n}$ の速さで縮み、
$\sqrt{n}$ 倍に拡大して見ると、その形は正規分布に近づく」である。

驚くべきは **元の分布が何であっても** 同じ形に行き着くこと。
ただし条件がある。$\sigma^2 < \infty$ である。

4 つの分布で比べよう。正規・一様・指数は平均 0・分散 1 に揃えてあるので、
収束の速さの違いは **分布の形(歪度)だけ** による。
コーシーは分散が存在しないので揃えようがない。
"""),
    code("""
plotting.clt_convergence(
    ["normal", "uniform", "exponential", "cauchy"],
    ns=[1, 2, 5, 15, 50, 200],
    n_reps=4000,
)
"""),
    md(r"""
### 図の読み方

- **normal** は $n = 1$ から既に正規である(正規分布の和は正規)
- **uniform** は対称なので 2 つ足した時点でほぼ正規に見える
- **exponential** は右に歪んでいるので遅い。$n = 15$ でもまだ左右非対称
- **cauchy** はいつまでも寄らない

凡例の「枠外」は、標準化した標本平均が表示範囲 $[-5, 5]$ の外に出た割合である。
正規・一様・指数は 0%、コーシーは $n$ とともに増える。
$\sqrt{n}$ で拡大しているのに縮まないので、拡大した分だけ外へ逃げていく。
"""),
    code("""
print(f"{'n':>5} " + " ".join(f"{name:>12}" for name in ["normal", "uniform", "exponential", "cauchy"]))
print("      " + " ".join(f"{'標準化後の sd':>12}" for _ in range(1)))
for n in [1, 5, 50, 200]:
    row = []
    for name in ["normal", "uniform", "exponential", "cauchy"]:
        m = simulation.sampling_distribution(np.mean, datasets.SAMPLERS[name], n=n, n_reps=4000, seed=0)
        row.append(f"{np.std(m * np.sqrt(n)):12.2f}")
    print(f"{n:5d} " + " ".join(row))
print("\\n分散が有限な 3 つは sd が 1 のまま。コーシーだけ n とともに膨らむ")
"""),
    md(r"""
$\sqrt{n}$ で標準化すると、分散が有限な分布では sd が 1 に固定される。
これが中心極限定理の言っている「$1/\sqrt{n}$ の速さ」の中身である。

コーシーでは逆に膨らんでいく。実は $\bar X_n$ の分布はコーシーのままで、
$n$ をどれだけ増やしても 1 個のときと同じ分布である。
$\sqrt{n}$ を掛ければ当然広がる。
"""),
    code("""
# コーシーの標本平均は、n によらず元のコーシーと同じ分布になる
print(f"{'n':>6} {'標本平均の分位点 (5%, 50%, 95%)':>40}")
for n in [1, 10, 100, 1000]:
    m = simulation.sampling_distribution(
        np.mean, datasets.SAMPLERS["cauchy"], n=n, n_reps=20_000, seed=1
    )
    print(f"{n:6d} {str(np.quantile(m, [0.05, 0.5, 0.95]).round(3)):>40}")
print(f"\\n理論(標準コーシー): {stats.cauchy.ppf([0.05, 0.5, 0.95]).round(3)}")
print("平均を取っても分布が縮まない -> 標本を増やす意味がない")
"""),
    md(r"""
これは実務的に重い意味を持つ。
標本を 1000 倍に増やしても推定精度がまったく改善しない分布が存在する、ということである。
"""),
    md(r"""
## 3. 収束の 3 種類

「$X_n \to X$」には強さの違う 3 つの意味がある。

**概収束(almost sure)**

$$
P\big(\lim_{n\to\infty} X_n = X\big) = 1
$$

ほとんどすべての標本経路が、実際に収束する。最も強い。

**確率収束(in probability)**

$$
\forall \varepsilon > 0,\quad P(|X_n - X| > \varepsilon) \to 0
$$

大きく外れる確率が 0 に行く。外れる回数は無限にあってよい。

**分布収束(in distribution)**

$$
F_n(x) \to F(x) \quad \text{(F の連続点で)}
$$

分布の形だけが近づく。$X_n$ と $X$ が近い値を取る必要はまったくない。

含意は **概収束 $\Rightarrow$ 確率収束 $\Rightarrow$ 分布収束** の一方向で、逆は成り立たない。

分布収束するのに確率収束しない例を作ろう。
"""),
    code("""
rng = np.random.default_rng(2)
z = rng.normal(size=200_000)
xn, yn = z, -z            # yn は各 n で xn と同分布

print("xn と yn はまったく同じ分布:")
print(f"  平均 {xn.mean():+.4f} / {yn.mean():+.4f}   sd {xn.std():.4f} / {yn.std():.4f}")
print(f"  分位点 {np.quantile(xn, [0.1, 0.5, 0.9]).round(3)} / {np.quantile(yn, [0.1, 0.5, 0.9]).round(3)}")
print(f"\\nしかし E|xn - yn| = {np.abs(xn - yn).mean():.4f}  (0 に行かない)")
print("-> yn は xn に分布収束するが、確率収束はしない")
"""),
    md(r"""
中心極限定理が主張しているのは **分布収束だけ** である。
「$\sqrt{n}(\bar X_n - \mu)/\sigma$ が、ある特定の正規確率変数に近づく」とは言っていない。
形が近づくと言っているだけである。
"""),
    md(r"""
## 4. デルタ法 — 変換した量へ持ち越す

推定したいのが $\theta$ ではなく $g(\theta)$ のことがよくある。
オッズ比、対数変換、比率など。

**主張(デルタ法)** $\sqrt{n}(\hat\theta - \theta) \xrightarrow{d} N(0, \sigma^2)$ で
$g$ が $\theta$ で微分可能かつ $g'(\theta) \ne 0$ なら

$$
\sqrt{n}\big(g(\hat\theta) - g(\theta)\big) \xrightarrow{d} N\big(0,\ g'(\theta)^2 \sigma^2\big)
$$

**直感** $g$ を $\theta$ の周りで 1 次近似すると
$g(\hat\theta) \approx g(\theta) + g'(\theta)(\hat\theta - \theta)$。
定数倍された正規分布は正規分布である。

ロジット変換で確かめよう。$\hat p$ の漸近分散は $p(1-p)/n$、
$g(p) = \log\frac{p}{1-p}$ の微分は $g'(p) = \frac{1}{p(1-p)}$ なので、
デルタ法の予測は

$$
\mathrm{Var}\big(\log \tfrac{\hat p}{1 - \hat p}\big) \approx
\frac{1}{p^2(1-p)^2}\cdot\frac{p(1-p)}{n} = \frac{1}{n\,p(1-p)}
$$
"""),
    code("""
def logit_of_mean(s):
    \"\"\"log(p_hat / (1 - p_hat)); infinite when the sample is all 0s or all 1s.\"\"\"
    p_hat = s.mean()
    if p_hat <= 0.0 or p_hat >= 1.0:
        return np.nan          # the delta method has nothing to say here
    return np.log(p_hat / (1 - p_hat))


print(f"{'p':>6} {'n':>6} {'実測 sd':>10} {'デルタ法':>10} {'比':>7} {'退化した標本':>14}")
for p in [0.1, 0.3, 0.5]:
    for n in [20, 100, 400]:
        def sampler(m, rng, _p=p):
            return (rng.random(m) < _p).astype(float)

        logits = simulation.sampling_distribution(
            logit_of_mean, sampler, n=n, n_reps=20_000, seed=3
        )
        degenerate = int(np.isnan(logits).sum())
        finite = logits[~np.isnan(logits)]
        theory = np.sqrt(1.0 / (n * p * (1 - p)))
        got = finite.std(ddof=1)
        print(f"{p:6.1f} {n:6d} {got:10.5f} {theory:10.5f} {got / theory:7.3f} {degenerate:14d}")
"""),
    md(r"""
比が 1 に近く、$n$ が大きいほど近似は良くなる。

最右列に注目してほしい。$p = 0.1$、$n = 20$ では、
成功が 1 回も起きない標本が少なからず出る。
そのとき $\hat p = 0$ でロジットは $-\infty$ になり、**推定値そのものが存在しない**。

デルタ法は「$\hat\theta$ が $\theta$ の近くにいる」ことを前提に 1 次近似する道具である。
$\hat\theta$ が定義域の端に落ちる確率が無視できないうちは、前提が成り立っていない。
漸近論の主張はすべて「$n$ が十分大きければ」という条件付きであり、
**手元の $n$ が十分かどうかは別途確かめる必要がある**。本書がシミュレーションを使う理由がここにある。

デルタ法は 06 章で最尤推定量の漸近正規性を得た後、その変換にそのまま適用される。
極限定理を「使い回す」ための道具である。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
中心極限定理は分散が有限であることを要求する。
これは技術的な但し書きではなく、定理が成り立つかどうかの分かれ目である。
コーシー分布の標本平均は、何個平均しても 1 個のときと同じ分布のままになる。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
金融の損益、保険の支払額、ネットワークの遅延、都市の人口には裾の重い分布が現れる。
標本平均と正規近似で安全側の見積もりをしたつもりが、
実際には最悪ケースを大幅に過小評価していることがある。
標準誤差を計算する前に、裾の重さを確かめる習慣が要る。
```
"""),
    md(r"""
## 5. 落とし穴

### 「$n \ge 30$ なら正規」という経験則

歪んだ分布ではまったく足りない。必要な $n$ を実測してみよう。
標準化した標本平均が正規分布からどれだけ離れているかを、
コルモゴロフ–スミルノフ統計量で測る。
"""),
    code("""
print(f"{'分布':>14} " + " ".join(f"n={n:<6d}" for n in [5, 30, 100, 500]))
for name in ["normal", "uniform", "exponential"]:
    row = []
    for n in [5, 30, 100, 500]:
        m = simulation.sampling_distribution(
            np.mean, datasets.SAMPLERS[name], n=n, n_reps=4000, seed=4
        )
        d = stats.kstest(m * np.sqrt(n), "norm").statistic
        row.append(f"{d:8.4f}")
    print(f"{name:>14} " + " ".join(row))
print("\\nKS 統計量(0 が完全一致)。指数分布は n=30 でもまだ正規から離れている")
"""),
    md(r"""
### 分散が無い分布に標準誤差を計算する

`np.std(x) / np.sqrt(n)` はどんな配列に対しても数値を返す。
返ってきた数値が意味を持つかどうかは、別の話である。

### 収束の種類を取り違える

「$\hat\theta_n$ は $\theta$ に収束する」と言うとき、どの意味かを確かめる。
一致性は確率収束、中心極限定理は分布収束を主張している。
"""),
    md(r"""
## 6. 演習

1. 歪度の大きい分布(たとえば対数正規)を作り、
   標本平均が正規に十分近づく $n$ を KS 統計量で決めよ。歪度との関係を論じよ。
2. パレート分布 $\alpha = 1.5$(平均は存在するが分散は存在しない)で
   中心極限定理が成り立つか確かめよ。$\alpha = 2.5$ ではどうか。
3. デルタ法を使って $\sqrt{\hat p}$ の漸近分散を求め、数値で確かめよ。
   $p$ が 0 に近いとき、この近似はなぜ悪くなるか。
4. 概収束はするが確率収束の速度が遅い例、および確率収束はするが
   概収束しない例をそれぞれ作れ。
5. 走る平均の跳び幅を監視して、裾の重い分布を検出する簡単な手続きを設計せよ。
   正規・指数・コーシーに適用して、誤検出率と検出率を測れ。
"""),
]
